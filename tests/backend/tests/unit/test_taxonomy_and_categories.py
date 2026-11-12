"""Unit tests for Google Translate integration, weighted ranking, 3-category taxonomy, and UI."""

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest
from pydantic import HttpUrl, SecretStr
from src.backend.app.api.main import OFFICIAL_COLLECTOR_SOURCES, AppSettings, create_application
from src.backend.app.collectors.rss_collector import RSSCollector
from src.backend.app.core.taxonomy import (
    DOMESTIC_SOURCE_NAMES,
    GLOBAL_SOURCE_NAMES,
    OFFICIAL_MEDIA_SOURCES,
    SUBTOPIC_GROUPS,
    match_category,
)
from src.backend.app.schemas.collector import CollectorSource
from src.backend.app.schemas.content import SuccessContent
from src.backend.app.schemas.news import NewsDetailResponse, NewsListResponse
from src.backend.app.services.ranking_service import (
    RankingCandidate,
    RankingRequest,
    RankingService,
    compute_keyword_and_popularity,
)
from src.backend.app.workers.ai_processor import (
    GoogleTranslateContentProcessor,
    TranslatingNewsCollector,
    translate_to_korean,
)


class _Stream(httpx.AsyncByteStream):
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield self.payload


async def _public_dns(_host: str, _port: int) -> tuple[str, ...]:
    return ("8.8.8.8",)


def test_rss_collector_extracts_item_guid_permalink_and_rejects_homepage_root() -> None:
    rss_xml = (
        b"<rss><channel><link>https://zdnet.co.kr/</link>"
        b"<item><title>Article 1</title>"
        b"<link>https://zdnet.co.kr/</link>"
        b'<guid isPermaLink="true">https://zdnet.co.kr/view/?no=20261108162434</guid>'
        b"<pubDate>Sun, 08 Nov 2026 12:00:00 +0900</pubDate>"
        b"<description>Body</description></item>"
        b"<item><title>Homepage Only</title>"
        b"<link>https://zdnet.co.kr/</link>"
        b"<pubDate>Sun, 08 Nov 2026 12:00:00 +0900</pubDate></item>"
        b"</channel></rss>"
    )
    src = CollectorSource(
        source_name="지디넷코리아",
        feed_url=HttpUrl("https://zdnet.co.kr/rss"),
        allowed_hosts=("zdnet.co.kr",),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404, stream=_Stream(b""))
        return httpx.Response(200, stream=_Stream(rss_xml))

    collector = RSSCollector((src,), transport=httpx.MockTransport(handler), resolver=_public_dns)
    result = asyncio.run(collector.collect(src))
    assert len(result.articles) == 1
    assert str(result.articles[0].canonical_url) == "https://zdnet.co.kr/view/?no=20261108162434"
    assert result.rejected_count == 1


def test_official_media_sources_and_collector_sources_cover_all_17_sources() -> None:
    domestic = tuple(spec for spec in OFFICIAL_MEDIA_SOURCES if spec.region == "DOMESTIC")
    global_sources = tuple(spec for spec in OFFICIAL_MEDIA_SOURCES if spec.region == "GLOBAL")
    assert len(OFFICIAL_MEDIA_SOURCES) == 17
    assert len(domestic) == 14
    assert len(global_sources) == 3
    assert len(DOMESTIC_SOURCE_NAMES) == 14
    assert len(GLOBAL_SOURCE_NAMES) == 3
    assert len(OFFICIAL_COLLECTOR_SOURCES) == 17
    for spec in OFFICIAL_MEDIA_SOURCES:
        assert str(spec.feed_url).startswith("https://")
        assert (spec.feed_url.path not in (None, "", "/")) or bool(spec.feed_url.query)


def test_subtopic_groups_and_match_category_classify_three_categories() -> None:
    assert len(SUBTOPIC_GROUPS) == 15
    assert match_category("멀티모달 LLM 파운데이션 모델 및 AI 에이전트 공개") == "AI"
    assert match_category("스타트업 시리즈B 벤처캐피탈 투자 유치 및 영업이익 증가") == "ECONOMY"
    assert match_category("개인정보 보호 가이드라인 법안 및 대학 에듀테크 교육") == "SOCIETY"


def test_weighted_ranking_combines_recency_priority_keywords_and_popularity() -> None:
    pub_time = datetime(2026, 11, 8, 9, 0, tzinfo=UTC)
    sample_content = SuccessContent(
        content_hash="a" * 64,
        summary_lines=(
            "첫 번째 요약 문장입니다.",
            "두 번째 요약 문장입니다.",
            "세 번째 요약 문장입니다.",
        ),
        translated_text="번역 본문입니다.",
    )
    kw_freq, pop_idx = compute_keyword_and_popularity(
        "멀티모달 LLM 파운데이션 모델과 AI 에이전트 GPU 반도체",
        sample_content.summary_lines,
        "클라우드 데이터센터 NPU 가속기 추론 서버 오픈소스 로컬 모델",
        source_priority=1,
    )
    assert kw_freq >= 4
    assert pop_idx >= 30

    low_signal = RankingCandidate(
        id=UUID(int=1),
        published_at=pub_time,
        source_priority=5,
        keyword_frequency=1,
        popularity_index=10,
        content=sample_content,
    )
    high_signal = RankingCandidate(
        id=UUID(int=2),
        published_at=pub_time,
        source_priority=5,
        keyword_frequency=kw_freq,
        popularity_index=pop_idx,
        content=sample_content,
    )
    assert RankingService.calculate_weighted_score(
        high_signal, reference_time=pub_time
    ) > RankingService.calculate_weighted_score(low_signal, reference_time=pub_time)
    ranked = RankingService.rank(RankingRequest(candidates=(low_signal, high_signal), limit=5))
    assert ranked[0].news.id == UUID(int=2)


@pytest.mark.asyncio
async def test_google_translate_processor_and_collector_monkeypatched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_translate(text: str) -> str:
        return f"[한국어번역] {text}"

    monkeypatch.setattr(
        "src.backend.app.workers.ai_processor._translate_sync_with_deep_translator",
        _fake_translate,
    )
    translated = await translate_to_korean(
        "OpenAI unveils next generation agent", enable_network=True
    )
    assert translated.startswith("[한국어번역]")

    src = CollectorSource(
        source_name="TechCrunch",
        feed_url=HttpUrl("https://techcrunch.com/feed/"),
        allowed_hosts=("techcrunch.com",),
    )
    rss_xml = (
        b"<rss><channel><item>"
        b"<title>OpenAI launches autonomous coding agent</title>"
        b"<link>https://techcrunch.com/2026/11/08/openai-coding-agent/</link>"
        b"<pubDate>Sun, 08 Nov 2026 12:00:00 +0000</pubDate>"
        b"<description>Enterprise developers adopt autonomous agent workflows.</description>"
        b"</item></channel></rss>"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404, stream=_Stream(b""))
        return httpx.Response(200, stream=_Stream(rss_xml))

    base = RSSCollector((src,), transport=httpx.MockTransport(handler), resolver=_public_dns)
    collected = await base.collect(src)
    assert collected.articles[0].title == "OpenAI launches autonomous coding agent"

    processor = GoogleTranslateContentProcessor(enable_network_translation=True)
    processed = await processor.process(collected.articles[0])
    assert isinstance(processed, SuccessContent)
    assert len(processed.summary_lines) == 3
    assert processed.summary_lines[0].startswith("[한국어번역]")

    translating_collector = TranslatingNewsCollector(base, enable_network=True)
    translated_collection = await translating_collector.collect(src)
    expected_title = (
        "OpenAI launches autonomous coding agent"
        " ||| [한국어번역] OpenAI launches autonomous coding agent"
    )
    assert translated_collection.articles[0].title == expected_title


@pytest.mark.asyncio
async def test_application_crawls_rss_serves_categories_and_toggle_ui() -> None:
    sample_xml_by_host: tuple[tuple[str, bytes], ...] = (
        (
            "www.hankyung.com",
            (
                "<rss><channel><item>"
                "<title>챗GPT 월 2만9000원 안 내도 된다?…AI '토큰 요금제' 뭐길래</title>"
                "<link>https://www.hankyung.com/article/202610317619i</link>"
                "<pubDate>Sun, 08 Nov 2026 12:00:00 +0900</pubDate>"
                "<description>KT가 73종의 AI 모델을 골라 쓰는 토큰 요금제를 도입했다.</description>"
                "</item></channel></rss>"
            ).encode(),
        ),
        (
            "techcrunch.com",
            (
                b"<rss><channel><item>"
                b"<title>After the midterms, things are looking rocky for data centers</title>"
                b"<link>https://techcrunch.com/2026/11/07/data-centers-ai/</link>"
                b"<pubDate>Sun, 08 Nov 2026 12:00:00 +0000</pubDate>"
                b"<description>AI infrastructure and GPU data centers face new rules.</description>"
                b"</item></channel></rss>"
            ),
        ),
        (
            "www.yna.co.kr",
            (
                "<rss><channel><item>"
                '<title>LH "공공이 개발사업 시행하면 속도 빨라지고 부정부패 줄어"</title>'
                "<link>https://www.yna.co.kr/view/AKR20261108031800003</link>"
                "<pubDate>Sun, 08 Nov 2026 12:00:00 +0900</pubDate>"
                "<description>공공 개발사업 정책·제도 및 개인정보 가이드라인 개선.</description>"
                "</item></channel></rss>"
            ).encode(),
        ),
    )

    def rss_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404, stream=_Stream(b""))
        host_header = request.headers.get("host", "")
        for host_key, payload in sample_xml_by_host:
            if host_key == host_header:
                return httpx.Response(200, stream=_Stream(payload))
        generic = (
            f"<rss><channel><item>"
            f"<title>{host_header} 멀티모달 LLM 추론 모델 공개</title>"
            f"<link>https://{host_header}/article/20261108</link>"
            f"<pubDate>2026-11-08 16:00:00</pubDate>"
            f"<description>파운데이션 모델과 AI 에이전트 기술이 발전하고 있다.</description>"
            f"</item></channel></rss>"
        ).encode()
        return httpx.Response(200, stream=_Stream(generic))

    mock_collector = RSSCollector(
        OFFICIAL_COLLECTOR_SOURCES,
        transport=httpx.MockTransport(rss_handler),
        resolver=_public_dns,
        max_items_per_feed=2,
    )
    settings = AppSettings(
        database_url=SecretStr("sqlite+aiosqlite:///:memory:"),
        enable_live_rss=True,
        max_items_per_feed=2,
    )
    app = create_application(
        settings=settings,
        collector=mock_collector,
        enable_network_translation=False,
    )
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            index_res = await client.get("/")
            assert index_res.status_code == 200
            assert '<aside class="sidebar"' in index_res.text
            # v1.0.3 UI: 카테고리는 사이드바 동적 영역과 news-ui.js가 담당한다.
            assert 'id="sidebar-categories"' in index_res.text
            assert "news-ui.js" in index_res.text
            assert "settings.html" in index_res.text

            css_res = await client.get("/mockup/mockup.css")
            assert css_res.status_code == 200
            assert "--bg: #f8fafc;" in css_res.text
            assert "--surface: #ffffff;" in css_res.text
            assert "display: none;" in css_res.text
            assert "calc(1.3rem * 0.7)" in css_res.text

            # 백그라운드 크롤링이 끝날 때까지 수집 상태를 폴링한다.
            for _ in range(100):
                status_res = await client.get("/v1/collection/status")
                assert status_res.status_code == 200
                if not status_res.json().get("collecting"):
                    break
                await asyncio.sleep(0.05)

            for category in ("AI", "ECONOMY", "SOCIETY"):
                response = await client.get(
                    f"/v1/news?category={category}&sort=rank&page_size=20&fresh_hours=0"
                )
                assert response.status_code == 200
                parsed = NewsListResponse.model_validate_json(response.text)
                assert len(parsed.items) >= 1
                for item in parsed.items:
                    assert str(item.original_url).startswith("https://")
                    assert (item.original_url.path not in (None, "", "/")) or bool(
                        item.original_url.query
                    )

            hk_res = await client.get(
                "/v1/news?category=ECONOMY&q=산업 동향&sort=rank&page_size=10&fresh_hours=0"
            )
            assert hk_res.status_code == 200
            hk_parsed = NewsListResponse.model_validate_json(hk_res.text)
            hk_items = [item for item in hk_parsed.items if item.source_name == "한국경제"]
            assert len(hk_items) == 1
            assert str(hk_items[0].original_url) == "https://www.hankyung.com/article/202610317619i"

            hk_detail_res = await client.get(f"/v1/news/{hk_items[0].id}")
            assert hk_detail_res.status_code == 200
            hk_detail = NewsDetailResponse.model_validate_json(hk_detail_res.text)
            assert len(hk_detail.content.summary_lines) == 3

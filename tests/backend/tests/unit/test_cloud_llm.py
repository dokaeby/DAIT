"""cloud_llm 단위 테스트.

외부 Grok/Groq 네트워크 호출 없이 Fake 클라이언트와 httpx.MockTransport로 검증한다.
cloudLLM 브랜치 test_ai_processor.py를 현재 app 아키텍처에 맞게 이식했다.
"""

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from pydantic import SecretStr, ValidationError
from src.backend.app.schemas.collector import CollectedArticle
from src.backend.app.schemas.content import InsufficientContent, SuccessContent
from src.backend.app.workers.cloud_llm import (
    PROMPT_VERSION,
    ArticleContent,
    CloudLLMContentProcessor,
    CloudLLMSettings,
    CloudSummaryProcessor,
    ContentStatus,
    GrokClient,
    GrokSummaryCompletion,
    ProcessedContent,
)

DOMESTIC_BODY = (
    "국내 증시가 외국인 매수세에 힘입어 강세를 보였다. "
    "코스피는 전 거래일 대비 1.8% 상승한 2,640을 기록했다. "
    "분석가들은 반도체 업황 개선과 환율 안정이 상승을 이끌었다고 분석했다. "
    "다만 단기 차익 실현 물량이 늘어나면서 변동성은 커질 수 있다는 전망도 나온다."
)
FOREIGN_BODY = (
    "Global chip demand pushed semiconductor stocks higher on Tuesday. "
    "Analysts said orders from AI data centers drove the rally. "
    "The trend is expected to continue through next quarter."
)
VALID_LINES = ["핵심 결론 한 문장.", "배경과 원인 한 문장.", "전망과 영향 한 문장."]


def _settings(*, api_key: str = "test-xai-key", groq_key: str = "") -> CloudLLMSettings:
    return CloudLLMSettings(
        xai_api_key=SecretStr(api_key),
        groq_api_key=SecretStr(groq_key),
        grok_model="grok-test",
        grok_batch_size=1,
        llm_min_request_interval_seconds=0.0,
    )


def _domestic_article() -> ArticleContent:
    return ArticleContent(title="국내 증시 강세", body_text=DOMESTIC_BODY)


def _foreign_article() -> ArticleContent:
    return ArticleContent(
        title="Chip stocks rally on AI demand", body_text=FOREIGN_BODY, is_foreign=True
    )


class FakeGrokClient:
    """네트워크 없이 호출을 기록하고 설정된 결과/예외를 반환하는 Fake."""

    def __init__(self, result: str | Exception | list[str | Exception]) -> None:
        self._queue = list(result) if isinstance(result, list) else [result]
        self.calls: list[dict[str, str]] = []

    async def complete(self, *, system_instruction: str, user_prompt: str) -> str:
        self.calls.append({"system": system_instruction, "user": user_prompt})
        result = self._queue.pop(0) if len(self._queue) > 1 else self._queue[0]
        if isinstance(result, Exception):
            raise result
        return result


def _completion_payload(**overrides: object) -> str:
    payload: dict[str, object] = {"summary_lines": list(VALID_LINES)}
    payload.update(overrides)
    return json.dumps(payload, ensure_ascii=False)


def _processor(
    settings: CloudLLMSettings | None = None,
    client: FakeGrokClient | None = None,
    batch_size: int | None = None,
) -> CloudSummaryProcessor:
    kwargs: dict[str, int] = {}
    if batch_size is not None:
        kwargs["batch_size"] = batch_size
    return CloudSummaryProcessor(settings or _settings(), client=client, **kwargs)


def test_domestic_article_returns_three_summary_lines() -> None:
    client = FakeGrokClient(_completion_payload())
    processor = _processor(client=client)

    result = asyncio.run(processor.process(_domestic_article()))

    assert result.status is ContentStatus.READY
    assert result.engine == "grok"
    assert result.summary_lines == tuple(VALID_LINES)
    assert result.translated_title is None
    assert result.model_id == "grok-test"
    assert result.prompt_version == PROMPT_VERSION
    assert len(result.content_hash) == 64
    assert len(client.calls) == 1
    assert "3문장" in client.calls[0]["user"]
    assert "기사 제목: 국내 증시 강세" in client.calls[0]["user"]


def test_foreign_article_translates_title_and_summarizes() -> None:
    client = FakeGrokClient(_completion_payload(translated_title="AI 수요에 반도체 주가 급등"))
    processor = _processor(client=client)

    result = asyncio.run(processor.process(_foreign_article()))

    assert result.status is ContentStatus.READY
    assert result.engine == "grok"
    assert result.translated_title == "AI 수요에 반도체 주가 급등"
    assert "외국어 뉴스" in client.calls[0]["user"]


def test_insufficient_body_returns_insufficient_without_llm_call() -> None:
    client = FakeGrokClient(_completion_payload())
    processor = _processor(client=client)
    article = ArticleContent(title="짧은 기사", body_text="너무 짧다.")

    result = asyncio.run(processor.process(article))

    assert result.status is ContentStatus.INSUFFICIENT
    assert result.engine == "none"
    assert client.calls == []


def test_cache_hit_makes_zero_api_calls() -> None:
    client = FakeGrokClient(_completion_payload())
    processor = _processor(client=client)
    article = _domestic_article()

    first = asyncio.run(processor.process(article))
    second = asyncio.run(processor.process(article))

    assert first.engine == "grok"
    assert not first.cached
    assert second.cached
    assert second.engine == "grok"
    assert len(client.calls) == 1


def test_missing_api_key_uses_regex_fallback() -> None:
    settings = CloudLLMSettings(xai_api_key=SecretStr(""), llm_min_request_interval_seconds=0.0)
    processor = CloudSummaryProcessor(settings)  # client=None → GrokClient.from_settings → None

    result = asyncio.run(processor.process(_domestic_article()))

    assert result.status is ContentStatus.READY
    assert result.engine == "regex-fallback"
    assert len(result.summary_lines) == 3


def test_api_error_falls_back_to_regex_summary() -> None:
    client = FakeGrokClient(RuntimeError("boom"))
    processor = _processor(client=client)

    result = asyncio.run(processor.process(_domestic_article()))

    assert result.engine == "regex-fallback"
    assert processor.stats_snapshot()["grok_fallback"] == 1


def test_malformed_json_falls_back() -> None:
    client = FakeGrokClient("not-json-at-all")
    processor = _processor(client=client)

    result = asyncio.run(processor.process(_domestic_article()))

    assert result.engine == "regex-fallback"


def test_wrong_summary_line_count_falls_back() -> None:
    client = FakeGrokClient(json.dumps({"summary_lines": ["하나.", "둘."]}, ensure_ascii=False))
    processor = _processor(client=client)

    result = asyncio.run(processor.process(_domestic_article()))

    assert result.engine == "regex-fallback"


def test_extra_field_in_completion_falls_back() -> None:
    client = FakeGrokClient(_completion_payload(extra_field="unexpected"))
    processor = _processor(client=client)

    result = asyncio.run(processor.process(_domestic_article()))

    assert result.engine == "regex-fallback"


def test_regex_fallback_always_returns_three_lines() -> None:
    client = FakeGrokClient(RuntimeError("down"))
    processor = _processor(client=client)
    article = ArticleContent(title="t", body_text=DOMESTIC_BODY + " 추가 문장.")

    result = asyncio.run(processor.process(article))

    assert result.engine == "regex-fallback"
    assert len(result.summary_lines) == 3


def test_completion_schema_rejects_empty_line() -> None:
    with pytest.raises(ValidationError):
        GrokSummaryCompletion.model_validate({"summary_lines": ["", "둘.", "셋."]})


def test_processed_content_is_immutable() -> None:
    result = ProcessedContent(
        status=ContentStatus.READY,
        summary_lines=("가.", "나.", "다."),
        content_hash="0" * 64,
    )
    with pytest.raises(ValidationError):
        result.engine = "regex-fallback"  # type: ignore[misc]


def test_grok_enabled_reflects_api_key_presence() -> None:
    assert _settings(api_key="k").grok_enabled
    assert not _settings(api_key="").grok_enabled
    assert not _settings(api_key="   ").grok_enabled


def test_groq_enabled_reflects_api_key_presence() -> None:
    assert _settings(groq_key="g").groq_enabled
    assert not _settings().groq_enabled


def test_settings_keeps_secret_out_of_repr() -> None:
    settings = _settings(api_key="super-secret-value")
    assert "super-secret-value" not in repr(settings)


def test_from_env_returns_none_without_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DAIT_XAI_API_KEY", raising=False)
    monkeypatch.delenv("DAIT_GROQ_API_KEY", raising=False)
    assert CloudLLMSettings.from_env() is None


def test_from_env_reads_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DAIT_XAI_API_KEY", "xai-secret")
    monkeypatch.setenv("DAIT_GROQ_API_KEY", "")
    monkeypatch.setenv("DAIT_GROK_MODEL", "grok-test-env")
    settings = CloudLLMSettings.from_env()
    assert settings is not None
    assert settings.grok_enabled
    assert not settings.groq_enabled
    assert settings.grok_model == "grok-test-env"


def test_httpx_client_sends_openai_compatible_request() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers.get("authorization")
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": _completion_payload()}}]},
        )

    async def run() -> str:
        client = GrokClient.from_settings(_settings(), transport=httpx.MockTransport(handler))
        assert client is not None
        try:
            return await client.complete(system_instruction="sys", user_prompt="usr")
        finally:
            await client.aclose()

    content = asyncio.run(run())

    assert json.loads(content)["summary_lines"] == VALID_LINES
    assert captured["url"] == "https://api.x.ai/v1/chat/completions"
    assert captured["authorization"] == "Bearer test-xai-key"
    payload = captured["payload"]
    assert payload["model"] == "grok-test"
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["messages"][0] == {"role": "system", "content": "sys"}
    assert payload["messages"][1] == {"role": "user", "content": "usr"}


def test_grok_client_from_settings_returns_none_without_api_key() -> None:
    settings = CloudLLMSettings(
        xai_api_key=SecretStr(""),
        groq_api_key=SecretStr(""),
        llm_min_request_interval_seconds=0.0,
    )
    assert GrokClient.from_settings(settings) is None


def test_groq_key_preferred_over_xai() -> None:
    settings = _settings(api_key="xai-key", groq_key="groq-key")
    client = GrokClient.from_settings(
        settings,
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})),
    )
    assert client is not None
    assert client.model == settings.groq_model


def test_grok_client_retries_on_429_then_succeeds() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(429, json={"error": "rate limited"})
        return httpx.Response(
            200, json={"choices": [{"message": {"content": _completion_payload()}}]}
        )

    settings = _settings()
    settings = settings.model_copy(update={"llm_min_request_interval_seconds": 0.0})

    async def run() -> str:
        client = GrokClient.from_settings(settings, transport=httpx.MockTransport(handler))
        assert client is not None
        try:
            # 재시도 백오프를 줄이기 위해 모듈 상수를 패치한다.
            import src.backend.app.workers.cloud_llm as mod

            orig = mod.GROK_RETRY_BACKOFF_SECONDS
            mod.GROK_RETRY_BACKOFF_SECONDS = 0.001
            try:
                return await client.complete(system_instruction="s", user_prompt="u")
            finally:
                mod.GROK_RETRY_BACKOFF_SECONDS = orig
        finally:
            await client.aclose()

    content = asyncio.run(run())

    assert calls["count"] == 2
    assert json.loads(content)["summary_lines"] == VALID_LINES


def test_httpx_client_raises_processing_error_on_bad_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": True})

    async def run() -> None:
        client = GrokClient.from_settings(_settings(), transport=httpx.MockTransport(handler))
        assert client is not None
        try:
            await client.complete(system_instruction="s", user_prompt="u")
        finally:
            await client.aclose()

    from src.backend.app.workers.ai_processor import ProcessingError

    with pytest.raises(ProcessingError):
        asyncio.run(run())


def test_batch_coalesces_calls_into_single_request() -> None:
    articles = [_domestic_article() for _ in range(3)]
    payload = {
        "results": [
            {"summary_lines": list(VALID_LINES), "translated_title": None} for _ in range(3)
        ]
    }
    client = FakeGrokClient(json.dumps(payload, ensure_ascii=False))
    processor = _processor(client=client, batch_size=4)

    async def run() -> list[ProcessedContent]:
        return list(await asyncio.gather(*(processor.process(a) for a in articles)))

    results = asyncio.run(run())

    assert len(client.calls) == 1
    assert "results" in client.calls[0]["user"]
    assert all(r.engine == "grok" for r in results)
    stats = processor.stats_snapshot()
    assert stats["grok_calls"] == 1
    assert stats["grok_success"] == 3


def test_batch_result_count_mismatch_retries_individually() -> None:
    client = FakeGrokClient(
        [
            json.dumps({"results": []}, ensure_ascii=False),
            _completion_payload(),
            _completion_payload(),
        ]
    )
    processor = _processor(client=client, batch_size=4)

    async def run() -> list[ProcessedContent]:
        return list(
            await asyncio.gather(
                processor.process(_domestic_article()),
                processor.process(_domestic_article()),
            )
        )

    results = asyncio.run(run())

    assert len(client.calls) == 3
    assert all(r.engine == "grok" for r in results)
    stats = processor.stats_snapshot()
    assert stats["grok_calls"] == 3
    assert stats["grok_success"] == 2


def test_numeric_guard_rejects_invented_numbers() -> None:
    client = FakeGrokClient(
        _completion_payload(summary_lines=["주가가 99% 급등했다.", "배경 설명.", "전망 설명."])
    )
    processor = _processor(client=client)

    result = asyncio.run(processor.process(_domestic_article()))

    assert result.engine == "regex-fallback"
    assert processor.stats_snapshot()["grok_fallback"] == 1


def test_batch_size_bounds_enforced() -> None:
    with pytest.raises(ValueError, match="batch_size"):
        CloudSummaryProcessor(_settings(), client=FakeGrokClient("{}"), batch_size=9)


def _collected_article(**overrides: object) -> CollectedArticle:
    base: dict[str, object] = {
        "source_name": "테스트통신",
        "title": "국내 증시 강세",
        "canonical_url": "https://example.com/news/1",
        "published_at": datetime(2026, 1, 1, tzinfo=UTC),
        "raw_text": DOMESTIC_BODY,
        "category": "AI",
    }
    base.update(overrides)
    return CollectedArticle.model_validate(base)


def test_content_processor_maps_ready_result() -> None:
    client = FakeGrokClient(_completion_payload())
    inner = CloudSummaryProcessor(_settings(), client=client, batch_size=1)
    processor = CloudLLMContentProcessor(_settings(), processor=inner)

    result = asyncio.run(processor.process(_collected_article()))

    assert isinstance(result, SuccessContent)
    assert result.summary_lines == tuple(VALID_LINES)
    assert result.translated_text
    assert len(result.content_hash) == 64


def test_content_processor_maps_insufficient() -> None:
    client = FakeGrokClient(_completion_payload())
    inner = CloudSummaryProcessor(
        _settings(),
        client=client,
        batch_size=1,
    )
    processor = CloudLLMContentProcessor(_settings(), processor=inner)

    result = asyncio.run(processor.process(_collected_article(raw_text="짧다.")))

    assert isinstance(result, InsufficientContent)


def test_remote_paragraphs_used_when_body_extractor_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An accessible article must not be rejected because one extractor returned empty."""
    from src.backend.app.workers import cloud_llm

    async def fetch_page(*_args: object) -> tuple[str, str]:
        return f"<article><p>{FOREIGN_BODY}</p></article>", ""

    monkeypatch.setattr(cloud_llm, "fetch_article_html_and_body", fetch_page)
    client = FakeGrokClient(_completion_payload())
    processor = CloudLLMContentProcessor(
        _settings(), processor=CloudSummaryProcessor(_settings(), client=client, batch_size=1)
    )
    result = asyncio.run(
        processor.process(
            _foreign_collected_article().model_copy(update={"raw_text": "Short RSS."})
        )
    )
    assert isinstance(result, SuccessContent)
    assert FOREIGN_BODY in client.calls[0]["user"]


def test_rss_html_keeps_text_when_body_extractor_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Local HTML extraction failure must retain useful RSS text even if detail fetch fails."""
    from src.backend.app.workers import cloud_llm

    async def unavailable(*_args: object) -> tuple[str, str]:
        return "", ""

    monkeypatch.setattr(cloud_llm, "extract_clean_body_with_trafilatura", lambda _: "")
    monkeypatch.setattr(cloud_llm, "fetch_article_html_and_body", unavailable)
    client = FakeGrokClient(_completion_payload())
    processor = CloudLLMContentProcessor(
        _settings(), processor=CloudSummaryProcessor(_settings(), client=client, batch_size=1)
    )
    article = _foreign_collected_article().model_copy(update={"raw_text": f"<p>{FOREIGN_BODY}</p>"})
    result = asyncio.run(processor.process(article))
    assert isinstance(result, SuccessContent)
    assert FOREIGN_BODY in client.calls[0]["user"]


def test_content_processor_foreign_title_translation() -> None:
    payload = _completion_payload(translated_title="AI 수요에 반도체 주가 급등")
    client = FakeGrokClient(payload)
    inner = CloudSummaryProcessor(_settings(), client=client, batch_size=1)
    processor = CloudLLMContentProcessor(_settings(), processor=inner)

    result = asyncio.run(
        processor.process(
            _collected_article(
                source_name="TechCrunch",
                title="Chip stocks rally on AI demand",
                raw_text=FOREIGN_BODY,
            )
        )
    )

    assert isinstance(result, SuccessContent)
    assert result.translated_text == "AI 수요에 반도체 주가 급등"


def _foreign_collected_article() -> CollectedArticle:
    return _collected_article(
        source_name="TechCrunch",
        title="Chip stocks rally on AI demand",
        raw_text=FOREIGN_BODY,
    )


def test_content_processor_translates_english_grok_summary_lines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Grok가 요약 3줄을 영어로 반환해도 저장 전 한국어로 번역한다."""
    payload = _completion_payload(
        summary_lines=[
            "Chip stocks rallied on AI demand.",
            "Data center orders drove the trend.",
            "The rally is expected to continue.",
        ]
    )
    client = FakeGrokClient(payload)
    inner = CloudSummaryProcessor(_settings(), client=client, batch_size=1)
    processor = CloudLLMContentProcessor(_settings(), processor=inner)

    async def fake_translate(text: str) -> str:
        return "번역된 한국어 문장입니다."

    monkeypatch.setattr("src.backend.app.workers.cloud_llm.translate_to_korean", fake_translate)

    result = asyncio.run(processor.process(_foreign_collected_article()))

    assert isinstance(result, SuccessContent)
    assert len(result.summary_lines) == 3
    assert all(any("가" <= ch <= "힣" for ch in line) for line in result.summary_lines)


def test_content_processor_rejects_untranslated_foreign_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """번역마저 실패하면 영어 요약을 저장하지 않고 ProcessingError를 던진다."""
    from src.backend.app.workers.ai_processor import ProcessingError

    payload = _completion_payload(
        summary_lines=[
            "Chip stocks rallied on AI demand.",
            "Data center orders drove the trend.",
            "The rally is expected to continue.",
        ]
    )
    client = FakeGrokClient(payload)
    inner = CloudSummaryProcessor(_settings(), client=client, batch_size=1)
    processor = CloudLLMContentProcessor(_settings(), processor=inner)

    async def untranslated(text: str) -> str:
        return text

    monkeypatch.setattr("src.backend.app.workers.cloud_llm.translate_to_korean", untranslated)

    with pytest.raises(ProcessingError):
        asyncio.run(processor.process(_foreign_collected_article()))

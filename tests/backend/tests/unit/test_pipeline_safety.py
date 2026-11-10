"""robots·수집·잡·캐시 안전장치 테스트. 네트워크는 전부 fake로 대체한다."""

import sqlite3
from datetime import UTC, datetime

import pytest

from dait.core.config import Settings
from dait.core.url_safety import FetchedBody, FetchFailedError
from dait.repositories import job_repository
from dait.repositories.db import transaction
from dait.services import cache_retry_service, collection_service, robots_service

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
PUBLIC_IP = "93.184.216.34"
FEED_URL = "https://news.example.com/feed.xml"
ROBOTS_URL = "https://news.example.com/robots.txt"


def public_resolver(host: str) -> list[str]:
    """테스트용 DNS: 공인 IP로 해석한다."""
    return [PUBLIC_IP]


def make_fetcher(feed_body: bytes, robots_body: bytes | None = None):
    """URL별 응답을 돌려주는 fake fetcher를 만든다."""

    def fetch(url: str) -> FetchedBody:
        if url == ROBOTS_URL:
            if robots_body is None:
                raise FetchFailedError(404)
            return FetchedBody(body=robots_body, content_type="text/plain", final_url=url)
        if url == FEED_URL:
            return FetchedBody(body=feed_body, content_type="application/rss+xml", final_url=url)
        raise FetchFailedError(404)

    return fetch


RSS_OK = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<item><title>AI 모델 공개</title><link>https://news.example.com/a1</link>
<pubDate>Thu, 01 Jan 2026 10:00:00 GMT</pubDate><description>요약 가</description></item>
<item><title>로봇 윤리 논란</title><link>https://news.example.com/a2</link>
<pubDate>Thu, 01 Jan 2026 11:00:00 GMT</pubDate><description>요약 나</description></item>
</channel></rss>""".encode()

RSS_BAD_LINK = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<item><title>내부 링크</title><link>http://news.example.com/insecure</link>
<pubDate>Thu, 01 Jan 2026 10:00:00 GMT</pubDate></item>
<item><title>정상</title><link>https://news.example.com/a3</link>
<pubDate>Thu, 01 Jan 2026 10:00:00 GMT</pubDate></item>
</channel></rss>""".encode()


def seed_source(db_url: str, source_id: str = "srcA", base_url: str = FEED_URL) -> None:
    """활성 출처 한 건을 직접 넣는다."""
    conn = sqlite3.connect(db_url.removeprefix("sqlite:///"))
    try:
        conn.execute(
            "INSERT INTO sources (id, name, kind, base_url, priority, enabled, "
            "created_at, updated_at) VALUES (?, '테스트통신', 'RSS', ?, 10, 1, ?, ?)",
            (source_id, base_url, NOW.isoformat(), NOW.isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def _clean_caches() -> None:
    """모듈 수준 캐시가 테스트 사이에 새지 않게 한다."""
    robots_service.clear_cache()
    cache_retry_service.clear_memory_state()


class TestRobots:
    """robots_service.check_robots 판정."""

    def test_disallow_blocks(self) -> None:
        """Disallow 규칙이 있으면 해당 경로는 거부된다."""
        robots = b"User-agent: *\nDisallow: /feed.xml\n"
        fetch = make_fetcher(b"", robots)
        assert not robots_service.check_robots(
            FEED_URL, FEED_URL, fetch=fetch, resolver=public_resolver
        )

    def test_allow_when_no_robots(self) -> None:
        """robots.txt 404는 제한 없음으로 허용한다."""
        fetch = make_fetcher(b"")
        assert robots_service.check_robots(
            FEED_URL, FEED_URL, fetch=fetch, resolver=public_resolver
        )

    def test_unavailable_is_conservative_deny(self) -> None:
        """robots를 가져오지 못하면 보수적으로 거부한다."""

        def fetch(url: str) -> FetchedBody:
            raise OSError("down")

        assert not robots_service.check_robots(
            FEED_URL, FEED_URL, fetch=fetch, resolver=public_resolver
        )


class TestCollection:
    """collection_service.run_collection."""

    def test_collects_and_dedupes(self, settings: Settings, db_url: str) -> None:
        """피드를 수집해 PENDING 기사로 저장하고, 같은 시간 창 재실행은 SKIPPED."""
        seed_source(db_url)
        fetch = make_fetcher(RSS_OK)
        first = collection_service.run_collection(
            settings, now=NOW, fetcher=fetch, resolver=public_resolver
        )
        assert first[0].status == "SUCCEEDED"
        assert first[0].inserted == 2

        conn = sqlite3.connect(db_url.removeprefix("sqlite:///"))
        rows = conn.execute(
            "SELECT n.title, c.status FROM news n JOIN content_results c "
            "ON c.news_id = n.id WHERE n.source_id = 'srcA'"
        ).fetchall()
        conn.close()
        assert len(rows) == 2
        assert all(status == "PENDING" for _, status in rows)

        second = collection_service.run_collection(
            settings, now=NOW, fetcher=fetch, resolver=public_resolver
        )
        assert second[0].status == "SKIPPED"

    def test_non_https_and_bad_links_rejected(self, settings: Settings, db_url: str) -> None:
        """http 링크는 거부되고 https 정상 항목만 저장된다."""
        seed_source(db_url)
        fetch = make_fetcher(RSS_BAD_LINK)
        result = collection_service.run_collection(
            settings, now=NOW, fetcher=fetch, resolver=public_resolver
        )
        assert result[0].inserted == 1
        assert result[0].rejected == 1

    def test_content_dedupe_across_urls(self, settings: Settings, db_url: str) -> None:
        """URL이 달라도 제목+요약이 같으면 중복으로 센다."""
        seed_source(db_url)
        rss = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<item><title>같은 기사</title><link>https://news.example.com/x1</link>
<pubDate>Thu, 01 Jan 2026 10:00:00 GMT</pubDate><description>동일 요약</description></item>
<item><title>같은 기사</title><link>https://news.example.com/x2</link>
<pubDate>Thu, 01 Jan 2026 10:00:00 GMT</pubDate><description>동일 요약</description></item>
</channel></rss>""".encode()
        result = collection_service.run_collection(
            settings, now=NOW, fetcher=make_fetcher(rss), resolver=public_resolver
        )
        assert result[0].inserted == 1
        assert result[0].duplicates == 1

    def test_robots_disallow_skips_source(self, settings: Settings, db_url: str) -> None:
        """robots가 피드를 막으면 수집이 실패로 기록되고 기사는 저장되지 않는다."""
        seed_source(db_url)
        robots = b"User-agent: *\nDisallow: /\n"
        result = collection_service.run_collection(
            settings,
            now=NOW,
            fetcher=make_fetcher(RSS_OK, robots),
            resolver=public_resolver,
        )
        assert result[0].status == "FAILED"
        assert result[0].error_code == "UNSAFE_URL"

    def test_fetch_failure_records_job_attempt(self, settings: Settings, db_url: str) -> None:
        """fetch 실패 시 job_attempts에 error_code가 남고 RETRYING이 된다."""
        seed_source(db_url)

        def failing(url: str) -> FetchedBody:
            if url == ROBOTS_URL:
                raise FetchFailedError(404)
            raise FetchFailedError(503)

        result = collection_service.run_collection(
            settings, now=NOW, fetcher=failing, resolver=public_resolver
        )
        assert result[0].status == "FAILED"
        assert result[0].error_code == "FETCH_FAILED"

        with transaction(db_url) as conn:
            job = conn.execute("SELECT id, status FROM jobs").fetchone()
            assert job is not None
            attempts = conn.execute(
                "SELECT step, attempt_no, error_code FROM job_attempts WHERE job_id = ?",
                (job[0],),
            ).fetchall()
        assert job[1] == "RETRYING"
        assert attempts == [("COLLECT", 1, "FETCH_FAILED")]


class TestJobRepository:
    """job_repository dedupe·attempt 기록."""

    def test_dedupe_key_conflict(self, db_url: str) -> None:
        """같은 dedupe_key 두 번째 등록은 None을 돌려준다."""
        with transaction(db_url) as conn:
            first = job_repository.create_job(conn, None, "COLLECT", "k1", NOW, NOW)
            second = job_repository.create_job(conn, None, "COLLECT", "k1", NOW, NOW)
            assert first is not None
            assert second is None
            assert job_repository.get_by_dedupe_key(conn, "k1") is not None

    def test_attempt_count_and_record(self, db_url: str) -> None:
        """attempt 기록 횟수가 쌓인다."""
        with transaction(db_url) as conn:
            job = job_repository.create_job(conn, None, "COLLECT", "k2", NOW, NOW)
            assert job is not None
            for no in (1, 2):
                job_repository.record_attempt(conn, job.id, "COLLECT", no, "E", NOW)
            assert job_repository.count_attempts(conn, job.id, "COLLECT") == 2
            job_repository.update_status(conn, job.id, "DEAD_LETTER", None, NOW)
            row = conn.execute("SELECT status FROM jobs WHERE id = ?", (job.id,)).fetchone()
            assert row is not None
            assert row[0] == "DEAD_LETTER"


class TestCacheRetry:
    """cache_retry_service 메모리 fallback."""

    def test_cache_roundtrip(self, settings: Settings) -> None:
        """Redis 없이도 set→get이 동작하고 TTL이 붙는다."""
        cache_retry_service.cache_set(settings, "k", "v", 300)
        assert cache_retry_service.cache_get(settings, "k") == "v"
        assert cache_retry_service.cache_get(settings, "missing") is None

    def test_lock_excludes_concurrent(self, settings: Settings) -> None:
        """같은 이름의 락은 한 번에 하나만 잡는다."""
        results: list[bool] = []
        with cache_retry_service.locked(settings, "n1") as first:
            assert first is True
            with cache_retry_service.locked(settings, "n1") as second:
                results.append(second)
        assert results == [False]

    def test_list_cache_key_hides_query(self) -> None:
        """캐시 키에 검색어 원문이 들어가지 않는다."""
        key = cache_retry_service.list_cache_key("AI", "비밀검색어", "rank", 10, None)
        assert "비밀검색어" not in key
        assert key.startswith("news:list:")

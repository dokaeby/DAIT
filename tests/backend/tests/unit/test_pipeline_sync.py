"""pipeline → public 뉴스 동기화 서비스 단위 테스트."""

import json
import sqlite3

import pytest

from dait.core.config import Settings
from dait.services import pipeline_sync_service


def _connect() -> sqlite3.Connection:
    """contract 테이블 + ATTACH된 pipeline 스키마를 가진 sqlite 연결을 만든다."""
    conn = sqlite3.connect(":memory:")
    conn.execute("ATTACH DATABASE ':memory:' AS pipeline")
    conn.execute(
        "CREATE TABLE sources (id TEXT PRIMARY KEY, name TEXT, kind TEXT, "
        "base_url TEXT, priority INTEGER, enabled INTEGER, robots_checked_at TEXT, "
        "created_at TEXT, updated_at TEXT)"
    )
    conn.execute(
        "CREATE TABLE news (id TEXT PRIMARY KEY, source_id TEXT, title TEXT, "
        "canonical_url TEXT UNIQUE, published_at TEXT, collected_at TEXT, "
        "category TEXT, original_language TEXT, content_hash TEXT, created_at TEXT)"
    )
    conn.execute(
        "CREATE TABLE content_results (news_id TEXT PRIMARY KEY, status TEXT, "
        "summary_lines TEXT, translated_text TEXT, model_id TEXT, prompt_version TEXT, "
        "processed_at TEXT, updated_at TEXT)"
    )
    conn.execute(
        "CREATE TABLE pipeline.news (id TEXT PRIMARY KEY, canonical_url TEXT, "
        "source_name TEXT, title TEXT, category TEXT, published_at TEXT, raw_text TEXT)"
    )
    conn.execute(
        "CREATE TABLE pipeline.content_results (news_id TEXT PRIMARY KEY, status TEXT, "
        "line_1 TEXT, line_2 TEXT, line_3 TEXT, translated_text TEXT, "
        "model_id TEXT, prompt_version TEXT)"
    )
    conn.execute("INSERT INTO sources (id, name) VALUES ('src_1', '테크M')")
    return conn


def _insert_pipeline_news(
    conn: sqlite3.Connection,
    news_id: str,
    *,
    source_name: str = "테크M",
    category: str = "AI",
    status: str = "SUCCESS",
    lines: tuple[str | None, str | None, str | None] = ("첫째", "둘째", "셋째"),
    canonical_url: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO pipeline.news VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            news_id,
            canonical_url or f"https://example.com/{news_id}",
            source_name,
            f"기사 {news_id}",
            category,
            "2026-11-12T01:00:00+00:00",
            "raw",
        ),
    )
    conn.execute(
        "INSERT INTO pipeline.content_results VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            news_id,
            status,
            *lines,
            "번역",
            "groq",
            "cloud-llm",
        ),
    )


def test_sync_inserts_success_rows_with_ready_status() -> None:
    """SUCCESS + 3줄 요약 기사는 READY로 복사된다."""
    conn = _connect()
    _insert_pipeline_news(conn, "n1")
    inserted = pipeline_sync_service.sync_pipeline_news(conn)
    assert inserted == 1
    row = conn.execute(
        "SELECT n.category, n.original_language, n.published_at, c.status, "
        "c.summary_lines, c.model_id "
        "FROM news n JOIN content_results c ON c.news_id = n.id"
    ).fetchone()
    assert row is not None
    category, language, published_at, status, summary, model = row
    assert published_at == "2026-11-12T01:00:00+00:00"
    assert category == "AI"
    assert language == "ko"
    assert status == "READY"
    assert json.loads(summary) == ["첫째", "둘째", "셋째"]
    assert model == "groq"


def test_sync_maps_society_to_politics_and_missing_lines_to_insufficient() -> None:
    """SOCIETY는 POLITICS로 변환되고, 요약 3줄이 부족하면 INSUFFICIENT다."""
    conn = _connect()
    _insert_pipeline_news(conn, "n1", category="SOCIETY", lines=("하나", None, "셋"))
    inserted = pipeline_sync_service.sync_pipeline_news(conn)
    assert inserted == 1
    row = conn.execute("SELECT category FROM news").fetchone()
    status_row = conn.execute("SELECT status, summary_lines FROM content_results").fetchone()
    assert row == ("POLITICS",)
    assert status_row is not None
    assert status_row[0] == "INSUFFICIENT"
    assert json.loads(status_row[1]) == ["하나", "셋"]


def test_sync_skips_unprocessed_unknown_source_and_duplicates() -> None:
    """SUCCESS가 아니거나, 출처 미등록·카테고리 불명·canonical_url 중복은 건너뛴다."""
    conn = _connect()
    _insert_pipeline_news(conn, "n_pending", status="PROCESSING")
    _insert_pipeline_news(conn, "n_unknown_src", source_name="없는매체")
    _insert_pipeline_news(conn, "n_bad_cat", category="WEATHER")
    _insert_pipeline_news(conn, "n1")
    conn.execute(
        "INSERT INTO news (id, source_id, title, canonical_url, published_at, "
        "collected_at, category, original_language, content_hash, created_at) "
        "VALUES ('existing', 'src_1', '기존', ?, '2026-11-01', '2026-11-01', "
        "'AI', 'ko', NULL, '2026-11-01')",
        ("https://example.com/n_dup",),
    )
    _insert_pipeline_news(conn, "n_dup", canonical_url="https://example.com/n_dup")
    inserted = pipeline_sync_service.sync_pipeline_news(conn)
    assert inserted == 1
    assert conn.execute("SELECT COUNT(*) FROM news").fetchone() == (2,)


def test_sync_if_needed_skips_sqlite() -> None:
    """SQLite에서는 pipeline 스키마가 없으므로 동기화를 시도하지 않는다."""
    settings = Settings(database_url="sqlite:///:memory:")
    pipeline_sync_service.sync_if_needed(settings)  # 예외 없이 반환


def test_sync_if_needed_runs_for_postgres_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """postgres URL이면 동기화 본체를 호출하고, 실패해도 예외를 밖으로 던지지 않는다."""
    calls: list[object] = []

    class _FakeTransaction:
        def __enter__(self):
            return object()

        def __exit__(self, *args: object) -> None:
            return None

    def fake_sync(conn: object) -> int:
        calls.append(conn)
        return 3

    monkeypatch.setattr(pipeline_sync_service, "transaction", lambda url: _FakeTransaction())
    monkeypatch.setattr(pipeline_sync_service, "sync_pipeline_news", fake_sync)
    pipeline_sync_service._state["last_sync_monotonic"] = 0.0
    settings = Settings(database_url="postgresql://u:p@h/db")
    pipeline_sync_service.sync_if_needed(settings)
    assert len(calls) == 1


def test_sync_if_needed_swallows_sync_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """동기화가 실패해도 API 호출은 계속 진행된다."""

    class _FakeTransaction:
        def __enter__(self):
            return object()

        def __exit__(self, *args: object) -> None:
            return None

    def boom(conn: object) -> int:
        raise RuntimeError

    monkeypatch.setattr(pipeline_sync_service, "transaction", lambda url: _FakeTransaction())
    monkeypatch.setattr(pipeline_sync_service, "sync_pipeline_news", boom)
    pipeline_sync_service._state["last_sync_monotonic"] = 0.0
    settings = Settings(database_url="postgresql://u:p@h/db")
    pipeline_sync_service.sync_if_needed(settings)  # 예외 없이 반환

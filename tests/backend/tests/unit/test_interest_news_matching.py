"""Interest counts must match paginated lists, including overlap and empty topics."""

import sqlite3

from dait.repositories import news_repository


def test_interest_union_counts_search_and_pages() -> None:
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript("""
            CREATE TABLE sources(id TEXT PRIMARY KEY, name TEXT, priority INTEGER);
            CREATE TABLE news(id TEXT PRIMARY KEY, source_id TEXT, title TEXT,
                published_at TEXT, category TEXT, canonical_url TEXT);
            CREATE TABLE content_results(news_id TEXT PRIMARY KEY, summary_lines TEXT, status TEXT);
            INSERT INTO sources VALUES ('s', 'Source', 1);
        """)
        for index, (title, status) in enumerate(
            [
                ("AI 에이전트 개발 도구", "READY"),
                ("코딩 개발자 도구", "READY"),
                ("에이전트 출시", "READY"),
                ("일반 소식", "READY"),
                ("에이전트 실패", "FAILED"),
            ]
        ):
            conn.execute(
                "INSERT INTO news VALUES (?, 's', ?, ?, 'AI', ?)",
                (str(index), title, "2026-11-12T00:00:00+00:00", f"https://example.com/{index}"),
            )
            conn.execute("INSERT INTO content_results VALUES (?, '[]', ?)", (str(index), status))
        scope = ("ai.agents", "ai.devtools")
        assert news_repository.count_public_news(conn, None, "", scope) == 3
        assert news_repository.count_public_news(conn, None, "", ("ai.agents",)) == 2
        assert news_repository.count_public_news(conn, None, "", ("ai.devtools",)) == 2
        assert news_repository.count_public_news(conn, None, "", ("ai.models",)) == 0
        assert news_repository.count_public_news(conn, None, "출시", scope) == 1
        assert news_repository.count_public_news(conn, "ECONOMY", "", scope) == 0
        first = news_repository.list_public_news(conn, None, "", "latest", 2, 0, scope)
        second = news_repository.list_public_news(conn, None, "", "latest", 2, 2, scope)
        assert len(first) == 2
        assert len(second) == 1
        assert len({row.id for row in first + second}) == 3
        assert news_repository.count_public_news(conn, None, "") == 4
    finally:
        conn.close()

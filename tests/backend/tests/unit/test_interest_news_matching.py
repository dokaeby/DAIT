"""Interest counts must match paginated lists, including overlap and empty topics."""

import sqlite3

from dait.repositories import news_repository
from dait.services import feed_index_service


def test_interest_union_counts_search_and_pages() -> None:
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript("""
            CREATE TABLE sources(id TEXT PRIMARY KEY, name TEXT, priority INTEGER);
            CREATE TABLE news(id TEXT PRIMARY KEY, source_id TEXT, title TEXT,
                published_at TEXT, category TEXT, canonical_url TEXT);
            CREATE TABLE content_results(news_id TEXT PRIMARY KEY, summary_lines TEXT,
                status TEXT, updated_at TEXT, extracted_text TEXT, translated_text TEXT);
            CREATE TABLE news_classified(news_id TEXT PRIMARY KEY,
                content_updated_at TEXT, classified_at TEXT);
            CREATE TABLE news_topics(news_id TEXT, topic_code TEXT,
                PRIMARY KEY (news_id, topic_code));
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
            conn.execute(
                "INSERT INTO content_results VALUES (?, '[]', ?, "
                "'2026-11-12T00:00:00+00:00', NULL, NULL)",
                (str(index), status),
            )
        conn.execute("ALTER TABLE news ADD COLUMN original_language TEXT DEFAULT 'ko'")
        conn.execute("UPDATE news SET original_language = 'en' WHERE id = '0'")
        # 관심사 조회는 저장된 분류 결과만 읽으므로 먼저 1회 분류를 실행한다.
        feed_index_service.classify_pending(conn)
        assert news_repository.count_public_news(conn, None, "", None, "en") == 1
        assert (
            len(news_repository.list_public_news(conn, None, "", "latest", 4, 0, None, "en")) == 1
        )
        assert news_repository.count_public_news(conn, None, "", ("en.ai.agents",)) == 1
        assert news_repository.count_public_news(conn, None, "", ("en.ai.models",)) == 0
        assert news_repository.count_public_news(conn, None, "", ("ai.agents", "en.ai.agents")) == 2
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
        # 콘텐츠가 갱신되면 다음 스윕에서 재분류된다.
        conn.execute(
            "UPDATE content_results SET summary_lines = '[\"GPU 데이터센터\"]', "
            "updated_at = '2026-11-13T00:00:00+00:00' WHERE news_id = '3'"
        )
        feed_index_service.classify_pending(conn)
        assert news_repository.count_public_news(conn, None, "", ("ai.infra",)) == 1
        # Legacy imports marked overseas articles as und, sometimes ko after translation.
        conn.execute("UPDATE sources SET name = 'TechCrunch' WHERE id = 's'")
        conn.execute("UPDATE news SET original_language = 'und' WHERE id = '0'")
        assert news_repository.count_public_news(conn, None, "", None, "en") == 4
        assert news_repository.count_public_news(conn, None, "", ("en.ai.agents",)) == 2
        overseas = news_repository.list_public_news(conn, None, "", "latest", 8, 0, None, "en")
        assert all(row.original_language == "en" for row in overseas)
        # A funding story must be reachable from the investment subtopic,
        # even if neither its title nor translated summary says startup/funding.
        conn.execute(
            "UPDATE news SET category = 'ECONOMY', title = ? WHERE id = '0'",
            ("OpenAI raises an additional $11 billion at a $1.25 trillion valuation",),
        )
        conn.execute(
            "UPDATE content_results SET summary_lines = ? WHERE news_id = '0'",
            ('["새로운 자본 조달 라운드에서 110억 달러를 확보했다."]',),
        )
        assert news_repository.count_public_news(conn, "ECONOMY", "", None, "en") == 1
        assert (
            news_repository.count_public_news(conn, None, "", ("en.economy.startups",), "en") == 1
        )
        funding = news_repository.list_public_news(
            conn, "ECONOMY", "", "latest", 8, 0, ("en.economy.startups",), "en"
        )
        assert [row.id for row in funding] == ["0"]
        assert news_repository.count_public_news(conn, None, "", ("en.economy.jobs",), "en") == 0
    finally:
        conn.close()

"""Domestic and overseas chip totals use the same language scope as article lists."""

import sqlite3
from contextlib import nullcontext

import pytest
from pydantic import SecretStr

from dait.core.config import Settings
from dait.services import feed_index_service, news_activity_service


def test_counts_keep_saved_interests_in_their_region(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript("""
            CREATE TABLE sources(id TEXT, name TEXT);
            CREATE TABLE news(id TEXT, source_id TEXT, title TEXT, category TEXT,
                original_language TEXT, canonical_url TEXT, published_at TEXT);
            CREATE TABLE content_results(news_id TEXT, summary_lines TEXT, status TEXT,
                updated_at TEXT);
            CREATE TABLE news_classified(news_id TEXT PRIMARY KEY,
                content_updated_at TEXT, classified_at TEXT);
            CREATE TABLE news_topics(news_id TEXT, topic_code TEXT,
                PRIMARY KEY (news_id, topic_code));
            CREATE TABLE user_interests(user_id TEXT, interest_code TEXT);
            INSERT INTO sources VALUES ('s', 'Source');
            INSERT INTO news VALUES ('ko', 's', 'AI 에이전트', 'AI', 'ko',
                'https://x.test/ko', '2026-11-12T00:00:00+00:00');
            INSERT INTO news VALUES ('en', 's', 'AI agent', 'AI', 'en',
                'https://x.test/en', '2026-11-12T00:00:00+00:00');
            INSERT INTO content_results VALUES ('ko', '[]', 'READY', '2026-11-12T00:00:00+00:00');
            INSERT INTO content_results VALUES ('en', '[]', 'READY', '2026-11-12T00:00:00+00:00');
            INSERT INTO user_interests VALUES ('u', 'ai.agents');
            INSERT INTO user_interests VALUES ('u', 'en.ai.agents');
        """)
        # 관심사 조회는 저장된 분류만 읽으므로 1회 분류를 실행한다.
        feed_index_service.classify_pending(conn)

        def fake_transaction(_database_url: str) -> nullcontext[sqlite3.Connection]:
            return nullcontext(conn)

        monkeypatch.setattr(news_activity_service, "transaction", fake_transaction)
        settings = Settings(database_url="sqlite:///:memory:", jwt_secret=SecretStr("0" * 32))
        domestic = news_activity_service.activity(settings, "u", "", [], True, "ko")
        overseas = news_activity_service.activity(settings, "u", "", [], True, "en")
        assert domestic.total == 1
        assert domestic.interest_counts == {"ai.agents": 1}
        assert overseas.total == 1
        assert overseas.interest_counts == {"en.ai.agents": 1}
        conn.execute("DELETE FROM user_interests WHERE interest_code = 'en.ai.agents'")
        assert news_activity_service.activity(settings, "u", "", [], True, "en").total == 0
        conn.execute("DELETE FROM user_interests")
        assert news_activity_service.activity(settings, "u", "", [], True, "en").total == 1
    finally:
        conn.close()

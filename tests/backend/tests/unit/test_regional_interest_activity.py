"""Domestic and overseas chip totals use the same language scope as article lists."""

import sqlite3
from contextlib import nullcontext
from types import SimpleNamespace

from dait.services import news_activity_service


def test_counts_keep_saved_interests_in_their_region(monkeypatch) -> None:
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript("""
            CREATE TABLE sources(id TEXT, name TEXT);
            CREATE TABLE news(id TEXT, source_id TEXT, title TEXT, category TEXT,
                original_language TEXT, canonical_url TEXT);
            CREATE TABLE content_results(news_id TEXT, summary_lines TEXT, status TEXT);
            CREATE TABLE user_interests(user_id TEXT, interest_code TEXT);
            INSERT INTO sources VALUES ('s', 'Source');
            INSERT INTO news VALUES ('ko', 's', 'AI 에이전트', 'AI', 'ko', 'https://x.test/ko');
            INSERT INTO news VALUES ('en', 's', 'AI agent', 'AI', 'en', 'https://x.test/en');
            INSERT INTO content_results VALUES ('ko', '[]', 'READY');
            INSERT INTO content_results VALUES ('en', '[]', 'READY');
            INSERT INTO user_interests VALUES ('u', 'ai.agents');
            INSERT INTO user_interests VALUES ('u', 'en.ai.agents');
        """)
        monkeypatch.setattr(news_activity_service, "transaction", lambda _: nullcontext(conn))
        settings = SimpleNamespace(database_url="test")
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

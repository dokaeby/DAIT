import sqlite3

import pytest
from app.database import initialize_database
from app.db_common import connect

TABLES = {
    "audit_logs",
    "auth_identities",
    "content_results",
    "job_attempts",
    "jobs",
    "news",
    "news_relations",
    "notification_deliveries",
    "refresh_sessions",
    "schedules",
    "sources",
    "user_settings",
    "users",
}


# 입력: `tmp_path`.
# 출력: 반환값 없음. assertion 실패 시 테스트가 실패한다.
# 동작: 해당 이름의 테스트 시나리오와 기대 결과를 검증한다.
def test_initialize_creates_all_13_tables_and_enables_foreign_keys(tmp_path):
    db_path = tmp_path / "dait.db"

    initialize_database(db_path)

    with connect(db_path) as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]

    assert tables == TABLES
    assert foreign_keys == 1


# 입력: `tmp_path`.
# 출력: 반환값 없음. assertion 실패 시 테스트가 실패한다.
# 동작: 해당 이름의 테스트 시나리오와 기대 결과를 검증한다.
def test_initialize_is_idempotent(tmp_path):
    db_path = tmp_path / "dait.db"

    initialize_database(db_path)
    initialize_database(db_path)

    with connect(db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM news").fetchone()[0] == 3
        assert connection.execute("SELECT COUNT(*) FROM schedules").fetchone()[0] == 1


# 입력: `tmp_path`.
# 출력: 반환값 없음. assertion 실패 시 테스트가 실패한다.
# 동작: 해당 이름의 테스트 시나리오와 기대 결과를 검증한다.
def test_schema_enforces_default_count_relation_and_foreign_key_constraints(tmp_path):
    db_path = tmp_path / "dait.db"
    initialize_database(db_path)

    with connect(db_path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE user_settings SET default_count = ? WHERE user_id = ?",
                (7, "usr_demo_local"),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO news_relations "
                "(id, news_id, related_news_id, reason, score, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    "rel_bad",
                    "news_openai_001",
                    "news_openai_001",
                    "self",
                    1.0,
                    "2026-11-06T00:00:00Z",
                ),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO schedules "
                "(id, user_id, local_time, timezone, enabled, criteria_json, "
                "created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "sch_bad",
                    "usr_missing",
                    "08:30",
                    "Asia/Seoul",
                    1,
                    '{"categories":["AI"]}',
                    "2026-11-06T00:00:00Z",
                    "2026-11-06T00:00:00Z",
                ),
            )


# 입력: `tmp_path`.
# 출력: 반환값 없음. assertion 실패 시 테스트가 실패한다.
# 동작: 해당 이름의 테스트 시나리오와 기대 결과를 검증한다.
def test_independent_connections_see_committed_seed(tmp_path):
    db_path = tmp_path / "dait.db"
    initialize_database(db_path)

    first = connect(db_path)
    second = connect(db_path)
    try:
        first.execute(
            "UPDATE user_settings SET default_count = ? WHERE user_id = ?",
            (5, "usr_demo_local"),
        )
        first.commit()

        value = second.execute(
            "SELECT default_count FROM user_settings WHERE user_id = ?",
            ("usr_demo_local",),
        ).fetchone()[0]
    finally:
        first.close()
        second.close()

    assert value == 5

"""users·refresh_tokens 저장소와 마이그레이션 테스트 (UT-DB-001 포함)."""

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest
from alembic import command

from dait.repositories.db import connect, transaction
from dait.repositories.token_repository import insert_refresh_token
from dait.repositories.user_repository import DuplicateEmailError, find_by_email, insert_user
from dait.schemas.token import RefreshTokenRecord
from dait.schemas.user import UserRecord, UserRole, UserStatus
from support import alembic_config

NOW = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)


def make_user(user_id: str = "u1", email: str = "usera@example.com") -> UserRecord:
    """테스트용 사용자 레코드를 만든다."""
    return UserRecord(
        id=user_id,
        email=email,
        password_hash="$argon2id$fake",  # noqa: S106 - 테스트용 가짜 해시
        status=UserStatus.ACTIVE,
        role=UserRole.USER,
        created_at=NOW,
    )


def make_token(
    token_id: str = "t1",  # noqa: S107 - 테스트용 id
    user_id: str = "u1",
    digest: str = "a" * 64,
) -> RefreshTokenRecord:
    """테스트용 refresh 토큰 레코드를 만든다."""
    return RefreshTokenRecord(
        id=token_id,
        user_id=user_id,
        family_id="f1",
        token_hash=digest,
        expires_at=NOW + timedelta(days=14),
        created_at=NOW,
    )


def test_insert_and_find_user(db_url: str) -> None:
    """저장한 사용자를 이메일로 찾으면 같은 값이 나온다."""
    with transaction(db_url) as conn:
        insert_user(conn, make_user())
        found = find_by_email(conn, "usera@example.com")
    assert found == make_user()
    assert "argon2id" not in repr(found)


def test_find_unknown_email_returns_none(db_url: str) -> None:
    """없는 이메일은 None이다."""
    with transaction(db_url) as conn:
        assert find_by_email(conn, "nobody@example.com") is None


def test_duplicate_email_is_rejected(db_url: str) -> None:
    """UT-DB-001: 같은 이메일을 두 번 저장하면 거부한다."""
    with transaction(db_url) as conn:
        insert_user(conn, make_user("u1"))
    with pytest.raises(DuplicateEmailError), transaction(db_url) as conn:
        insert_user(conn, make_user("u2"))


def test_sql_injection_text_is_just_a_value(db_url: str) -> None:
    """따옴표가 섞인 이메일도 값으로만 취급되어 다른 행을 건드리지 않는다."""
    with transaction(db_url) as conn:
        insert_user(conn, make_user())
        assert find_by_email(conn, "x' OR '1'='1") is None
        assert find_by_email(conn, "usera@example.com") is not None


def test_refresh_token_requires_existing_user(db_url: str) -> None:
    """없는 사용자의 토큰은 외래키 때문에 저장되지 않는다."""
    with pytest.raises(sqlite3.IntegrityError), transaction(db_url) as conn:
        insert_refresh_token(conn, make_token(user_id="ghost"))


def test_refresh_token_hash_is_unique(db_url: str) -> None:
    """같은 토큰 해시는 두 번 저장되지 않는다."""
    with transaction(db_url) as conn:
        insert_user(conn, make_user())
        insert_refresh_token(conn, make_token("t1"))
    with pytest.raises(sqlite3.IntegrityError), transaction(db_url) as conn:
        insert_refresh_token(conn, make_token("t2"))


def test_deleting_user_removes_tokens(db_url: str) -> None:
    """사용자를 지우면 토큰도 함께 지워진다(탈퇴 때 쓸 ON DELETE CASCADE)."""
    with transaction(db_url) as conn:
        insert_user(conn, make_user())
        insert_refresh_token(conn, make_token())
    with transaction(db_url) as conn:
        conn.execute("DELETE FROM users WHERE id = ?", ("u1",))
    conn = connect(db_url)
    try:
        assert conn.execute("SELECT COUNT(*) FROM refresh_tokens").fetchone() == (0,)
    finally:
        conn.close()


def test_role_check_constraint_rejects_unknown_role(db_url: str) -> None:
    """허용되지 않은 역할은 DB가 거부한다."""
    with pytest.raises(sqlite3.IntegrityError), transaction(db_url) as conn:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, status, role, created_at) "
            "VALUES ('u9', 'x@example.com', 'h', 'ACTIVE', 'ROOT', '2026-11-08T00:00:00+00:00')"
        )


def test_migration_downgrade_and_upgrade_again(db_url: str) -> None:
    """마이그레이션은 되돌릴 수 있고 다시 적용할 수 있다."""
    config = alembic_config(db_url)
    command.downgrade(config, "base")
    conn = connect(db_url)
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()
    assert "users" not in tables
    assert "refresh_tokens" not in tables
    command.upgrade(config, "head")

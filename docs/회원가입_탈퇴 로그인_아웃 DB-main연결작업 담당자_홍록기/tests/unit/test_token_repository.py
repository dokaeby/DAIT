"""refresh_tokens 폐기 쿼리 테스트 (조건부 UPDATE, family·사용자 범위)."""

from datetime import UTC, datetime, timedelta

from dait.repositories.db import transaction
from dait.repositories.token_repository import (
    find_by_hash,
    insert_refresh_token,
    revoke_all_for_user,
    revoke_family,
    revoke_if_active,
)
from dait.repositories.user_repository import insert_user
from dait.schemas.token import RefreshTokenRecord
from dait.schemas.user import UserRecord, UserRole, UserStatus

NOW = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)


def add_user(db_url: str, user_id: str) -> None:
    """사용자를 한 명 저장한다."""
    with transaction(db_url) as conn:
        insert_user(
            conn,
            UserRecord(
                id=user_id,
                email=f"{user_id}@example.com",
                password_hash="$argon2id$fake",  # noqa: S106 - 테스트용 가짜 해시
                status=UserStatus.ACTIVE,
                role=UserRole.USER,
                created_at=NOW,
            ),
        )


def add_token(db_url: str, token_id: str, user_id: str, family_id: str) -> str:
    """토큰을 저장하고 해시를 돌려준다."""
    digest = token_id.ljust(64, "0")
    with transaction(db_url) as conn:
        insert_refresh_token(
            conn,
            RefreshTokenRecord(
                id=token_id,
                user_id=user_id,
                family_id=family_id,
                token_hash=digest,
                expires_at=NOW + timedelta(days=14),
                created_at=NOW,
            ),
        )
    return digest


def test_find_by_hash(db_url: str) -> None:
    """해시로 찾으면 폐기 전에는 revoked_at이 None이고, 없는 해시는 None이다."""
    add_user(db_url, "u1")
    digest = add_token(db_url, "t1", "u1", "f1")
    with transaction(db_url) as conn:
        found = find_by_hash(conn, digest)
        assert found is not None
        assert (found.user_id, found.family_id, found.revoked_at) == ("u1", "f1", None)
        assert find_by_hash(conn, "9" * 64) is None


def test_revoke_if_active_succeeds_only_once(db_url: str) -> None:
    """같은 토큰을 두 번 폐기하면 두 번째는 False다(동시 사용 방어의 기반)."""
    add_user(db_url, "u1")
    digest = add_token(db_url, "t1", "u1", "f1")
    with transaction(db_url) as conn:
        assert revoke_if_active(conn, "t1", NOW) is True
        assert revoke_if_active(conn, "t1", NOW) is False
        stored = find_by_hash(conn, digest)
        assert stored is not None
        assert stored.revoked_at == NOW


def test_revoke_family_is_limited_to_that_family(db_url: str) -> None:
    """family 폐기는 그 계열만 막고 같은 사용자의 다른 계열은 그대로 둔다."""
    add_user(db_url, "u1")
    add_token(db_url, "t1", "u1", "f1")
    add_token(db_url, "t2", "u1", "f1")
    other = add_token(db_url, "t3", "u1", "f2")
    with transaction(db_url) as conn:
        assert revoke_family(conn, "f1", NOW) == 2
        stored = find_by_hash(conn, other)
        assert stored is not None
        assert stored.revoked_at is None


def test_revoke_all_for_user_is_scoped_and_idempotent(db_url: str) -> None:
    """사용자 전체 폐기는 그 사용자만 대상이고 두 번째 호출은 0건이다."""
    add_user(db_url, "u1")
    add_user(db_url, "u2")
    add_token(db_url, "t1", "u1", "f1")
    add_token(db_url, "t2", "u1", "f2")
    bystander = add_token(db_url, "t3", "u2", "f3")
    with transaction(db_url) as conn:
        assert revoke_all_for_user(conn, "u1", NOW) == 2
        assert revoke_all_for_user(conn, "u1", NOW) == 0
        stored = find_by_hash(conn, bystander)
        assert stored is not None
        assert stored.revoked_at is None

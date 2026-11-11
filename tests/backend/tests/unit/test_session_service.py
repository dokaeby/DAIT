"""refresh 회전·재사용 탐지·로그아웃·탈퇴·인증 확인 서비스 테스트 (UT-AUTH-008~012, UT-DB-009)."""

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from dait.core.config import Settings
from dait.core.errors import InvalidCredentialsError, InvalidTokenError, TooManyAttemptsError
from dait.repositories.db import connect, transaction
from dait.repositories.user_repository import delete_user, find_by_id
from dait.schemas.auth import AuthResponse, LoginRequest, RefreshRequest, SignupRequest
from dait.schemas.user import UserRecord
from dait.services import account_service, auth_service
from dait.services.login_throttle import create_throttles

NOW = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)
PASSWORD = "Str0ng!Passw0rd-xyz"  # noqa: S105 - 테스트 전용 가짜 비밀번호
WRONG = "Wr0ng!Passw0rd-xyz"


def signup(
    settings: Settings, email: str = "usera@example.com", now: datetime = NOW
) -> AuthResponse:
    """테스트용 사용자를 가입시킨다."""
    request = SignupRequest.model_validate(
        {
            "email": email,
            "password": PASSWORD,
            "password_confirm": PASSWORD,
            "terms_accepted": True,
        }
    )
    return auth_service.signup(settings, request, None, now)


def do_refresh(settings: Settings, token: str, now: datetime = NOW) -> str:
    """refresh를 호출하고 새 refresh 토큰을 돌려준다."""
    request = RefreshRequest.model_validate({"refresh_token": token})
    return auth_service.refresh(settings, request, None, now).refresh_token


def rows(settings: Settings, query: str) -> list[tuple[object, ...]]:
    """테스트 DB에서 조회한 행을 돌려준다."""
    conn = connect(settings.database_url)
    try:
        return [tuple(r) for r in conn.execute(query).fetchall()]
    finally:
        conn.close()


def test_refresh_rotates_and_keeps_family(settings: Settings) -> None:
    """UT-AUTH-008: 이전 토큰은 폐기, 새 토큰 해시 저장, family 유지."""
    first = signup(settings).tokens.refresh_token
    second = do_refresh(settings, first, NOW + timedelta(minutes=1))
    assert second != first
    stored = rows(
        settings, "SELECT token_hash, family_id, revoked_at FROM refresh_tokens ORDER BY created_at"
    )
    assert len(stored) == 2
    assert stored[0][0] == hashlib.sha256(first.encode()).hexdigest()
    assert stored[0][2] is not None
    assert stored[1][0] == hashlib.sha256(second.encode()).hexdigest()
    assert stored[1][2] is None
    assert stored[0][1] == stored[1][1]
    assert second not in str(stored)


def test_refreshed_access_token_is_valid(settings: Settings) -> None:
    """회전으로 받은 access 토큰으로 본인 인증이 된다."""
    now = datetime.now(UTC)
    signed = signup(settings, now=now)
    request = RefreshRequest.model_validate({"refresh_token": signed.tokens.refresh_token})
    tokens = auth_service.refresh(
        settings, request, None, now
    )  # 미래 시각 iat는 PyJWT가 거부하므로 같은 시각으로 갱신한다
    user = account_service.authenticate(settings, tokens.access_token)
    assert user.id == signed.user.id


def test_reused_refresh_revokes_the_whole_family(settings: Settings) -> None:
    """UT-AUTH-009: 폐기된 토큰을 다시 쓰면 같은 family의 새 토큰까지 모두 막힌다."""
    first = signup(settings).tokens.refresh_token
    second = do_refresh(settings, first, NOW + timedelta(minutes=1))
    with pytest.raises(InvalidTokenError):
        do_refresh(settings, first, NOW + timedelta(minutes=2))
    with pytest.raises(InvalidTokenError):
        do_refresh(settings, second, NOW + timedelta(minutes=3))
    assert rows(settings, "SELECT id FROM refresh_tokens WHERE revoked_at IS NULL") == []


def login_again(settings: Settings) -> str:
    """같은 계정으로 새로 로그인해 별도 계열의 refresh 토큰을 받는다."""
    request = LoginRequest.model_validate({"email": "usera@example.com", "password": PASSWORD})
    return auth_service.login(settings, request, create_throttles(), None, NOW).tokens.refresh_token


def test_reuse_does_not_touch_other_logins(settings: Settings) -> None:
    """한 로그인(family)의 재사용 탐지가 같은 사용자의 다른 로그인에는 영향을 주지 않는다."""
    first = signup(settings).tokens.refresh_token
    other = login_again(settings)
    do_refresh(settings, first, NOW + timedelta(minutes=1))
    with pytest.raises(InvalidTokenError):
        do_refresh(settings, first, NOW + timedelta(minutes=2))
    assert do_refresh(settings, other, NOW + timedelta(minutes=3))


def test_unknown_refresh_token_is_rejected(settings: Settings) -> None:
    """모르는 토큰은 거부하고 아무것도 폐기하지 않는다."""
    signup(settings)
    with pytest.raises(InvalidTokenError):
        do_refresh(settings, "x" * 43)
    assert len(rows(settings, "SELECT id FROM refresh_tokens WHERE revoked_at IS NULL")) == 1


def test_expired_refresh_token_is_rejected(settings: Settings) -> None:
    """만료된 refresh 토큰은 거부한다."""
    token = signup(settings).tokens.refresh_token
    with pytest.raises(InvalidTokenError):
        do_refresh(settings, token, NOW + timedelta(days=15))


def test_logout_revokes_all_tokens_and_is_idempotent(settings: Settings) -> None:
    """UT-AUTH-010: 로그아웃하면 모든 refresh가 막히고, 다시 불러도 오류가 없다."""
    signed = signup(settings)
    second_login = login_again(settings)
    auth_service.logout(settings, user_record(settings, signed.user.id), None, NOW)
    auth_service.logout(settings, user_record(settings, signed.user.id), None, NOW)
    for token in (signed.tokens.refresh_token, second_login):
        with pytest.raises(InvalidTokenError):
            do_refresh(settings, token, NOW + timedelta(minutes=1))
    assert rows(settings, "SELECT id FROM refresh_tokens WHERE revoked_at IS NULL") == []


def user_record(settings: Settings, user_id: str) -> UserRecord:
    """id로 사용자 레코드를 읽는다(없으면 AssertionError)."""
    with transaction(settings.database_url) as conn:
        user = find_by_id(conn, user_id)
    assert user is not None
    return user


def test_logout_does_not_touch_other_users(settings: Settings) -> None:
    """한 사용자의 로그아웃이 다른 사용자의 토큰을 폐기하지 않는다."""
    first = signup(settings, "usera@example.com")
    second = signup(settings, "userb@example.com")
    auth_service.logout(settings, user_record(settings, first.user.id), None, NOW)
    assert do_refresh(settings, second.tokens.refresh_token, NOW + timedelta(minutes=1))


def test_withdraw_deletes_user_and_tokens_only_for_that_user(settings: Settings) -> None:
    """UT-AUTH-011 / UT-DB-009: 탈퇴하면 본인 행과 토큰만 지워지고 다른 사용자는 그대로다."""
    first = signup(settings, "usera@example.com")
    second = signup(settings, "userb@example.com")
    account_service.withdraw(
        settings, user_record(settings, first.user.id), PASSWORD, create_throttles(), None, NOW
    )
    assert rows(settings, "SELECT email FROM users") == [("userb@example.com",)]
    assert len(rows(settings, "SELECT id FROM refresh_tokens")) == 1
    assert do_refresh(settings, second.tokens.refresh_token, NOW + timedelta(minutes=1))


def test_withdraw_with_wrong_password_changes_nothing(settings: Settings) -> None:
    """UT-AUTH-012: 재인증에 실패하면 사용자와 토큰이 그대로다."""
    signed = signup(settings)
    before = rows(settings, "SELECT * FROM users") + rows(settings, "SELECT * FROM refresh_tokens")
    with pytest.raises(InvalidCredentialsError):
        account_service.withdraw(
            settings, user_record(settings, signed.user.id), WRONG, create_throttles(), None, NOW
        )
    after = rows(settings, "SELECT * FROM users") + rows(settings, "SELECT * FROM refresh_tokens")
    assert before == after


def test_withdraw_failures_lock_the_account(settings: Settings) -> None:
    """탈퇴 재인증 실패가 5번 쌓이면 맞는 비밀번호도 429로 막혀 무차별 대입을 늦춘다."""
    signed = signup(settings)
    user = user_record(settings, signed.user.id)
    throttles = create_throttles()
    for _ in range(5):
        with pytest.raises(InvalidCredentialsError):
            account_service.withdraw(settings, user, WRONG, throttles, None, NOW)
    with pytest.raises(TooManyAttemptsError):
        account_service.withdraw(settings, user, PASSWORD, throttles, None, NOW)
    assert len(rows(settings, "SELECT id FROM users")) == 1


def test_authenticate_rejects_deleted_user_and_garbage(settings: Settings) -> None:
    """탈퇴한 사용자의 access 토큰과 쓰레기 문자열은 만료 전이라도 거부한다."""
    now = datetime.now(UTC)
    signed = signup(settings, now=now)
    assert account_service.authenticate(settings, signed.tokens.access_token).id == signed.user.id
    with transaction(settings.database_url) as conn:
        assert delete_user(conn, signed.user.id) is True
    with pytest.raises(InvalidTokenError):
        account_service.authenticate(settings, signed.tokens.access_token)
    with pytest.raises(InvalidTokenError):
        account_service.authenticate(settings, "not.a.token")


def test_session_status_hides_internal_fields(settings: Settings) -> None:
    """로그인 상태 응답에는 해시 같은 내부 값이 없고, 로그아웃이면 user가 없다."""
    signed = signup(settings)
    on = account_service.session_status(user_record(settings, signed.user.id))
    off = account_service.session_status(None)
    assert on.authenticated is True
    assert "argon2" not in on.model_dump_json()
    assert "password" not in on.model_dump_json()
    assert off.authenticated is False
    assert off.user is None

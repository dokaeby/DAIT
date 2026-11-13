"""services/auth_service 테스트 (UT-AUTH-001, 005, 006, 007 및 잠금·감사 로그)."""

import hashlib
import logging
from datetime import UTC, datetime, timedelta

import pytest

from dait.core.config import Settings
from dait.core.errors import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    TooManyAttemptsError,
    WeakPasswordError,
)
from dait.core.security import decode_access_token
from dait.repositories.db import connect
from dait.schemas.auth import LoginRequest, SignupRequest
from dait.schemas.user import UserRole, UserStatus
from dait.services import auth_service
from dait.services.login_throttle import LoginThrottles, create_throttles

NOW = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)
PASSWORD = "Str0ng!Passw0rd-xyz"  # noqa: S105 - 테스트 전용 가짜 비밀번호
EMAIL = "usera@example.com"
COMMON = "password123"
HAS_EMAIL = "Xusera-2026!ab"
WRONG = "Wr0ng!Passw0rd-xyz"


def signup_request(email: str = EMAIL, password: str = PASSWORD) -> SignupRequest:
    """유효한 가입 요청을 만든다."""
    return SignupRequest.model_validate(
        {
            "email": email,
            "password": password,
            "password_confirm": password,
            "terms_accepted": True,
        }
    )


def login_request(email: str = EMAIL, password: str = PASSWORD) -> LoginRequest:
    """로그인 요청을 만든다."""
    return LoginRequest.model_validate({"email": email, "password": password})


def rows(settings: Settings, query: str) -> list[tuple[object, ...]]:
    """테스트 DB에서 조회한 행을 돌려준다."""
    conn = connect(settings.database_url)
    try:
        return [tuple(r) for r in conn.execute(query).fetchall()]
    finally:
        conn.close()


def test_signup_creates_active_user_with_hashed_password(settings: Settings) -> None:
    """UT-AUTH-001: 사용자 1건, 해시 저장, status ACTIVE, 최초 토큰 1회."""
    response = auth_service.signup(settings, signup_request(), "1.2.3.4", NOW)
    assert response.user.status is UserStatus.ACTIVE
    assert response.user.role is UserRole.USER
    users = rows(settings, "SELECT email, password_hash FROM users")
    assert len(users) == 1
    assert users[0][0] == EMAIL
    assert str(users[0][1]).startswith("$argon2id$")
    assert users[0][1] != PASSWORD
    assert len(rows(settings, "SELECT id FROM refresh_tokens")) == 1


def test_signup_stores_only_refresh_token_hash(settings: Settings) -> None:
    """UT-AUTH-006 일부: refresh 원문은 DB 어디에도 저장되지 않고 SHA-256 해시만 저장된다."""
    response = auth_service.signup(settings, signup_request(), None, NOW)
    refresh = response.tokens.refresh_token
    stored = rows(settings, "SELECT token_hash FROM refresh_tokens")
    assert stored == [(hashlib.sha256(refresh.encode()).hexdigest(),)]
    dump = str(rows(settings, "SELECT * FROM refresh_tokens")) + str(
        rows(settings, "SELECT * FROM users")
    )
    assert refresh not in dump
    assert PASSWORD not in dump


def test_signup_email_is_stored_lowercase(settings: Settings) -> None:
    """이메일은 소문자로 통일해 저장한다."""
    response = auth_service.signup(settings, signup_request("UserA@Example.COM"), None, NOW)
    assert response.user.email == EMAIL


# 입력: 격리된 테스트 DB 설정과 대소문자만 다른 동일 이메일.
# 출력: 반환값 없음.
# 동작: 중복 이메일을 알리고 사용자·토큰 행을 추가하지 않는지 검증한다.
def test_duplicate_email_is_rejected_without_new_rows(settings: Settings) -> None:
    """UT-AUTH-005 중복 이메일 저장 방지를 검증한다.

    입력: settings는 격리된 SQLite 테스트 설정이다.
    출력: 없음.
    기능: 중복 이메일 오류를 공개하고 기존 사용자·토큰 행 수를 유지하는지 확인한다.
    """
    auth_service.signup(settings, signup_request(), None, NOW)
    with pytest.raises(EmailAlreadyRegisteredError) as caught:
        auth_service.signup(
            settings, signup_request("USERA@example.com", "Other!Passw0rd-123"), None, NOW
        )
    assert caught.value.code == "EMAIL_ALREADY_REGISTERED"
    assert caught.value.message == "이미 가입된 이메일입니다."
    assert len(rows(settings, "SELECT id FROM users")) == 1
    assert len(rows(settings, "SELECT id FROM refresh_tokens")) == 1


def test_weak_password_is_rejected_without_user(settings: Settings) -> None:
    """흔한 비밀번호와 이메일 포함 비밀번호는 사용자를 만들지 않는다."""
    with pytest.raises(WeakPasswordError):
        auth_service.signup(settings, signup_request(password=COMMON), None, NOW)
    with pytest.raises(WeakPasswordError):
        auth_service.signup(settings, signup_request(password=HAS_EMAIL), None, NOW)
    assert rows(settings, "SELECT id FROM users") == []


def test_login_success_issues_new_tokens(settings: Settings) -> None:
    """UT-AUTH-006: 로그인하면 올바른 사용자 id의 access와 새 refresh가 발급된다."""
    now = datetime.now(UTC)  # JWT 검증은 실제 시계를 쓰므로 이 테스트만 현재 시각으로 발급한다.
    signed = auth_service.signup(settings, signup_request(), None, now)
    response = auth_service.login(
        settings, login_request("USERA@example.com"), create_throttles(), "1.2.3.4", now
    )
    claims = decode_access_token(
        response.tokens.access_token, settings.jwt_secret.get_secret_value()
    )
    assert claims.sub == signed.user.id
    assert response.tokens.refresh_token != signed.tokens.refresh_token
    families = rows(settings, "SELECT DISTINCT family_id FROM refresh_tokens")
    assert len(families) == 2  # 로그인마다 새 계열


def test_login_failures_look_identical(settings: Settings) -> None:
    """UT-AUTH-007: 없는 이메일과 틀린 비밀번호는 같은 코드·메시지다."""
    auth_service.signup(settings, signup_request(), None, NOW)
    throttles = create_throttles()
    with pytest.raises(InvalidCredentialsError) as unknown:
        auth_service.login(settings, login_request("nobody@example.com"), throttles, None, NOW)
    with pytest.raises(InvalidCredentialsError) as wrong:
        auth_service.login(settings, login_request(password=WRONG), throttles, None, NOW)
    assert (unknown.value.code, unknown.value.message, unknown.value.status_code) == (
        wrong.value.code,
        wrong.value.message,
        wrong.value.status_code,
    )


def fail_login(settings: Settings, throttles: LoginThrottles, email: str, now: datetime) -> None:
    """틀린 비밀번호로 로그인을 한 번 시도한다(InvalidCredentialsError를 삼킨다)."""
    with pytest.raises((InvalidCredentialsError, TooManyAttemptsError)):
        auth_service.login(
            settings, login_request(email, "Wr0ng!Passw0rd-xyz"), throttles, "9.9.9.9", now
        )


def test_account_is_locked_after_five_failures_even_with_right_password(settings: Settings) -> None:
    """실패 5회 뒤에는 맞는 비밀번호도 429로 막고, 60초 뒤 풀린다."""
    auth_service.signup(settings, signup_request(), None, NOW)
    throttles = create_throttles()
    for _ in range(5):
        fail_login(settings, throttles, EMAIL, NOW)
    with pytest.raises(TooManyAttemptsError):
        auth_service.login(settings, login_request(), throttles, "9.9.9.9", NOW)
    later = NOW + timedelta(seconds=61)
    assert (
        auth_service.login(settings, login_request(), throttles, "9.9.9.9", later).user.email
        == EMAIL
    )


def test_lock_applies_to_unknown_email_too(settings: Settings) -> None:
    """없는 이메일도 같은 규칙으로 잠겨 계정 유무가 드러나지 않는다."""
    throttles = create_throttles()
    for _ in range(5):
        fail_login(settings, throttles, "ghost@example.com", NOW)
    with pytest.raises(TooManyAttemptsError):
        auth_service.login(settings, login_request("ghost@example.com"), throttles, None, NOW)


def test_ip_lock_blocks_other_accounts(settings: Settings) -> None:
    """한 IP에서 20번 실패하면 그 IP의 다른 계정 로그인도 막힌다."""
    auth_service.signup(settings, signup_request(), None, NOW)
    throttles = create_throttles()
    for index in range(20):
        fail_login(settings, throttles, f"ghost{index}@example.com", NOW)
    with pytest.raises(TooManyAttemptsError):
        auth_service.login(settings, login_request(), throttles, "9.9.9.9", NOW)


def test_success_clears_account_failures(settings: Settings) -> None:
    """성공하면 계정 실패 기록이 지워져 다시 처음부터 센다."""
    auth_service.signup(settings, signup_request(), None, NOW)
    throttles = create_throttles()
    for _ in range(4):
        fail_login(settings, throttles, EMAIL, NOW)
    auth_service.login(settings, login_request(), throttles, "9.9.9.9", NOW)
    for _ in range(4):
        fail_login(settings, throttles, EMAIL, NOW)
    assert (
        auth_service.login(settings, login_request(), throttles, "9.9.9.9", NOW).user.email == EMAIL
    )


def test_audit_log_has_event_but_no_secrets(
    settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    """감사 로그에는 이벤트와 사용자 id만 있고 비밀번호·토큰·이메일은 없다."""
    caplog.set_level(logging.INFO, logger="dait.audit")
    response = auth_service.signup(settings, signup_request(), "1.2.3.4", NOW)
    fail_login(settings, create_throttles(), EMAIL, NOW)
    text = caplog.text
    assert "event=signup outcome=success" in text
    assert "event=login outcome=invalid_credentials" in text
    assert response.user.id in text
    for secret in (PASSWORD, response.tokens.access_token, response.tokens.refresh_token, EMAIL):
        assert secret not in text

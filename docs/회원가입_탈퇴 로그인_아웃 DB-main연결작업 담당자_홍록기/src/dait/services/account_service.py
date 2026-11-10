"""로그인한 사용자의 계정 작업(인증 확인, 로그인 상태, 탈퇴)을 처리한다."""

from datetime import datetime

from dait.core.config import Settings
from dait.core.errors import InvalidCredentialsError, InvalidTokenError, TooManyAttemptsError
from dait.core.logging import audit
from dait.core.security import decode_access_token, verify_password
from dait.repositories.db import transaction
from dait.repositories.user_repository import delete_user, find_by_id
from dait.schemas.auth import SessionResponse
from dait.schemas.user import UserPublic, UserRecord, UserStatus
from dait.services.login_throttle import LoginThrottles


def authenticate(settings: Settings, access_token: str) -> UserRecord:
    """access 토큰으로 현재 사용자를 확인한다.

    입력: settings (서명 키가 든 설정), access_token (Authorization 헤더의 JWT)
    출력: UserRecord (토큰 주인이며 아직 ACTIVE인 사용자)
    기능: 서명·만료를 검증한 뒤 DB에서 사용자를 다시 찾는다.
          탈퇴했거나 정지된 사용자의 토큰은 만료 전이라도 InvalidTokenError로 거부한다.
          사용자 id는 토큰에서만 얻는다(IDOR 방지).
    """
    claims = decode_access_token(access_token, settings.jwt_secret.get_secret_value())
    with transaction(settings.database_url) as conn:
        user = find_by_id(conn, claims.sub)
    if user is None or user.status is not UserStatus.ACTIVE:
        raise InvalidTokenError
    return user


def session_status(user: UserRecord | None) -> SessionResponse:
    """로그인 상태를 응답 모델로 만든다.

    입력: user (인증된 사용자, 로그아웃 상태면 None)
    출력: SessionResponse (authenticated와 공개 사용자 정보)
    기능: 해시 같은 내부 값은 담지 않는다.
    """
    if user is None:
        return SessionResponse(authenticated=False)
    public = UserPublic(id=user.id, email=user.email, status=user.status, role=user.role)
    return SessionResponse(authenticated=True, user=public)


def withdraw(
    settings: Settings,
    user: UserRecord,
    password: str,
    throttles: LoginThrottles,
    client_ip: str | None,
    now: datetime,
) -> None:
    """비밀번호를 다시 확인하고 계정을 실제로 삭제한다.

    입력: settings (앱 설정), user (인증된 본인), password (재입력한 평문), throttles (잠금 장치),
          client_ip (IP 단위 잠금과 감사 로그용), now (UTC 시각)
    출력: 없음
    기능: 잠겨 있으면 TooManyAttemptsError, 비밀번호가 틀리면 InvalidCredentialsError이며 이때는
          아무것도 바꾸지 않고 실패를 잠금 횟수에 더한다. 맞으면 한 트랜잭션으로 사용자 행을 지운다.
    """
    ip_key = client_ip or "unknown"
    if throttles.account.is_locked(user.email, now) or throttles.ip.is_locked(ip_key, now):
        audit("withdraw", "locked", user_id=user.id, client_ip=client_ip)
        raise TooManyAttemptsError
    if not verify_password(password, user.password_hash):
        throttles.account.register_failure(user.email, now)
        throttles.ip.register_failure(ip_key, now)
        audit("withdraw", "invalid_credentials", user_id=user.id, client_ip=client_ip)
        raise InvalidCredentialsError
    with transaction(settings.database_url) as conn:
        delete_user(conn, user.id)
    throttles.account.clear(user.email)
    audit("withdraw", "success", user_id=user.id, client_ip=client_ip)

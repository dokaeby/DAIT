"""로그인한 사용자의 계정 작업(인증 확인, 로그인 상태, 탈퇴)을 처리한다."""

from datetime import UTC, datetime, timedelta

from fastapi.security import HTTPAuthorizationCredentials

from dait.core.config import Settings
from dait.core.errors import (
    InvalidCredentialsError,
    InvalidTokenError,
    NicknameTakenError,
    RecentLoginRequiredError,
    TooManyAttemptsError,
)
from dait.core.logging import audit
from dait.core.security import decode_access_token, verify_password
from dait.repositories.db import transaction
from dait.repositories.user_repository import (
    DuplicateNicknameError,
    delete_user,
    find_by_id,
    update_nickname,
)
from dait.schemas.auth import SessionResponse
from dait.schemas.nickname import NicknameResult
from dait.schemas.user import UserPublic, UserRecord, UserStatus
from dait.services.login_throttle import LoginThrottles

_RECENT_LOGIN = timedelta(minutes=5)
_CONFIRM_TEXT = "탈퇴"


# 입력: 앱 설정과 Authorization 헤더에서 받은 access 토큰.
# 출력: 현재 활성 상태인 사용자 레코드.
# 동작: 토큰을 검증하고 DB에서 사용자를 다시 확인한다.
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


# 입력: 인증된 사용자 또는 없음.
# 출력: 로그인 여부와 공개 사용자 정보를 담은 세션 응답.
# 동작: 내부 비밀번호 해시를 제외한 로그인 상태를 만든다.
def session_status(user: UserRecord | None) -> SessionResponse:
    """로그인 상태를 응답 모델로 만든다.

    입력: user (인증된 사용자, 로그아웃 상태면 None)
    출력: SessionResponse (authenticated와 공개 사용자 정보)
    기능: 해시 같은 내부 값은 담지 않는다.
    """
    if user is None:
        return SessionResponse(authenticated=False)
    public = UserPublic(
        id=user.id, email=user.email, status=user.status, role=user.role, nickname=user.nickname
    )
    return SessionResponse(authenticated=True, user=public)


# 입력: 앱 설정, 인증된 사용자, 새 닉네임.
# 출력: 저장된 닉네임 결과.
# 동작: 본인 닉네임을 변경하고 동시 중복을 도메인 오류로 변환한다.
def change_nickname(settings: Settings, user: UserRecord, nickname: str | None) -> NicknameResult:
    """인증된 본인의 닉네임을 변경한다.

    입력: settings (앱 설정), user (인증된 사용자), nickname (새 닉네임 또는 None)
    출력: NicknameResult (저장된 닉네임)
    기능: DB 유니크 제약으로 경합 중에도 중복 닉네임을 차단한다.
    """
    try:
        with transaction(settings.database_url) as conn:
            update_nickname(conn, user.id, nickname)
    except DuplicateNicknameError as exc:
        raise NicknameTakenError from exc
    return NicknameResult(nickname=nickname)


# 입력: 앱 설정, 인증된 사용자, 재입력 비밀번호, 실패 제한 장치, IP, 현재 시각.
# 출력: 반환값 없음.
# 동작: 잠금과 비밀번호를 확인한 뒤 사용자 계정을 삭제한다.
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
    # 비밀번호 없는 계정은 이 경로에서 항상 실패한다(withdraw_without_password를 써야 한다).
    if not verify_password(password, user.password_hash):
        throttles.account.register_failure(user.email, now)
        throttles.ip.register_failure(ip_key, now)
        audit("withdraw", "invalid_credentials", user_id=user.id, client_ip=client_ip)
        raise InvalidCredentialsError
    with transaction(settings.database_url) as conn:
        delete_user(conn, user.id)
    throttles.account.clear(user.email)
    audit("withdraw", "success", user_id=user.id, client_ip=client_ip)


# 입력: 앱 설정, 인증된 사용자, 입력한 확인 문구, 이번 access 토큰의 발급 시각, IP, 현재 시각.
# 출력: 반환값 없음.
# 동작: 방금 로그인했고 확인 문구가 맞을 때만 비밀번호 없는 계정을 삭제한다.
def withdraw_without_password(
    settings: Settings,
    user: UserRecord,
    confirm_text: str | None,
    token_issued_at: datetime,
    client_ip: str | None,
    now: datetime,
) -> None:
    """구글 전용 계정(비밀번호 없음)의 탈퇴를 처리한다.

    입력: settings (앱 설정), user (인증된 본인), confirm_text (입력한 확인 문구),
          token_issued_at (이번 access 토큰의 발급 시각), client_ip, now (UTC 시각)
    출력: 없음
    기능: 로그인한 지 5분이 지났거나 문구가 "탈퇴"가 아니면 RecentLoginRequiredError.
          탈퇴 직후 토큰이 훔쳐진 세션으로 계정을 지우는 일을 어렵게 한다.
    """
    recent = now - token_issued_at <= _RECENT_LOGIN
    if user.password_hash is not None or not recent or confirm_text != _CONFIRM_TEXT:
        audit("withdraw", "recent_login_required", user_id=user.id, client_ip=client_ip)
        raise RecentLoginRequiredError
    with transaction(settings.database_url) as conn:
        delete_user(conn, user.id)
    audit("withdraw", "success", user_id=user.id, client_ip=client_ip)


# 입력: 앱 설정과 Authorization 헤더에서 받은 인증 정보.
# 출력: 이 access 토큰이 발급된 UTC 시각.
# 동작: 토큰을 검증하고 iat 값을 시각으로 바꾼다.
def token_issued_at(
    settings: Settings, credentials: HTTPAuthorizationCredentials | None
) -> datetime:
    """access 토큰의 발급 시각을 돌려준다.

    입력: settings (서명 키), credentials (Authorization 헤더 값, 없으면 None)
    출력: datetime (UTC, 토큰의 iat)
    기능: 토큰이 없거나 잘못됐으면 InvalidTokenError. "방금 로그인했는가" 판단에 쓴다.
    """
    if credentials is None:
        raise InvalidTokenError
    claims = decode_access_token(credentials.credentials, settings.jwt_secret.get_secret_value())
    return datetime.fromtimestamp(claims.iat, UTC)

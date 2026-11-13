"""구글 로그인(OIDC Authorization Code + PKCE) 조정: 시작, 콜백 검증, 계정 연결, 교환 코드.

이메일이 같다는 이유만으로 기존 계정과 합치지 않는다(계정 탈취 방지, docs/decisions.md 참고).
같은 이메일의 이메일 가입 계정이 있으면, 사용자가 원할 때만 그 계정의 비밀번호를 확인한 뒤 연결한다.
"""

import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime
from urllib.parse import urlencode

import jwt
from pydantic import ValidationError

from dait.core.config import Settings
from dait.core.errors import (
    InvalidCredentialsError,
    InvalidTokenError,
    SocialLoginDisabledError,
    TooManyAttemptsError,
)
from dait.core.logging import audit
from dait.core.security import verify_password
from dait.repositories import onboarding_repository
from dait.repositories.db import transaction
from dait.repositories.one_time_store import OneTimeStore
from dait.repositories.social_identity_repository import (
    DuplicateIdentityError,
    find_user_id,
    has_identity,
    insert_identity,
)
from dait.repositories.user_repository import (
    DuplicateEmailError,
    find_by_email,
    find_by_id,
    insert_user,
)
from dait.schemas.auth import AuthResponse
from dait.schemas.social import (
    ExchangeRequest,
    GoogleIdClaims,
    LinkRequest,
    LinkTicket,
    OAuthPending,
    SocialIdentityRecord,
    SocialProvider,
)
from dait.schemas.user import UserRecord, UserRole, UserStatus
from dait.services import auth_service
from dait.services.google_client import GOOGLE_AUTH_URL, GoogleClient, GoogleUnavailableError
from dait.services.login_throttle import LoginThrottles

_STATE_TTL_SECONDS = 600  # 사용자가 구글 화면에서 로그인하는 데 충분한 시간
_XCODE_TTL_SECONDS = 60  # 화면이 곧바로 교환하므로 짧게 둔다
_STATE = "state"
_XCODE = "xcode"
_LINK = "link"
_LINK_TTL_SECONDS = 300  # 비밀번호를 떠올려 입력할 시간


class SocialLoginError(Exception):
    """구글 로그인 실패. reason은 화면에 #google_error=<reason>으로 전달되는 짧은 코드다."""

    # 입력: 실패 사유 코드.
    # 출력: 초기화된 예외.
    # 동작: 사유 코드만 보관한다(구글 응답·토큰 같은 내부 값은 담지 않는다).
    def __init__(self, reason: str) -> None:
        """예외를 만든다.

        입력: reason (state_invalid, provider_unavailable, email_in_use 등)
        출력: 없음
        기능: 내부 원인은 `raise ... from`으로만 잇는다.
        """
        super().__init__(reason)
        self.reason = reason


class _LinkRequiredError(Exception):
    """같은 이메일의 비밀번호 계정이 있어 사용자의 연결 선택이 필요할 때(내부 신호)."""

    # 입력: 연결 대상 사용자 ID와 구글 subject.
    # 출력: 초기화된 예외.
    # 동작: 연결 표를 만들 때 쓸 두 값만 보관한다.
    def __init__(self, user_id: str, subject: str) -> None:
        """예외를 만든다.

        입력: user_id (이메일이 같은 기존 계정의 id), subject (구글 sub)
        출력: 없음
        기능: 호출부(finish_login)가 연결 표를 발급하게 한다.
        """
        super().__init__("link required")
        self.user_id = user_id
        self.subject = subject


# 입력: 앱 설정.
# 출력: 반환값 없음(꺼져 있으면 예외).
# 동작: 구글 설정이 없으면 기능이 없는 것처럼 404를 낸다.
def require_enabled(settings: Settings) -> None:
    """구글 로그인이 켜져 있는지 확인한다.

    입력: settings (앱 설정)
    출력: 없음
    기능: 꺼져 있으면 SocialLoginDisabledError(404).
    """
    if not settings.google_enabled:
        raise SocialLoginDisabledError


def _random_token(nbytes: int = 32) -> str:
    """URL에 안전한 암호학적 난수 문자열을 만든다(기본 256비트)."""
    return secrets.token_urlsafe(nbytes)


def _pkce_challenge(verifier: str) -> str:
    """PKCE S256: verifier의 SHA-256을 패딩 없는 base64url로 인코딩한다."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


# 입력: 앱 설정, 1회용 저장소, 현재 UTC 시각.
# 출력: 구글 로그인 화면 주소와 브라우저 쿠키에 둘 state.
# 동작: state·nonce·PKCE verifier를 만들어 10분 TTL로 저장하고 구글 주소를 조립한다.
def start_login(settings: Settings, store: OneTimeStore, now: datetime) -> tuple[str, str]:
    """구글 로그인을 시작한다.

    입력: settings (GOOGLE_* 설정), store (1회용 저장소), now (UTC 시각)
    출력: tuple (구글로 보낼 URL, state)
    기능: 서버는 nonce와 verifier를 보관하고 구글에는 해시(code_challenge)만 보낸다.
          redirect_uri는 설정값 하나로 고정한다(사용자 입력으로 만들지 않는다).
    """
    require_enabled(settings)
    state = _random_token()
    pending = OAuthPending(nonce=_random_token(), code_verifier=_random_token(64))
    store.put(_STATE, state, pending.model_dump_json(), _STATE_TTL_SECONDS, now)
    query = urlencode(
        {
            "client_id": settings.google_client_id or "",
            "redirect_uri": settings.google_redirect_uri or "",
            "response_type": "code",
            "scope": "openid email",
            "state": state,
            "nonce": pending.nonce,
            "code_challenge": _pkce_challenge(pending.code_verifier),
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
    )
    return f"{GOOGLE_AUTH_URL}?{query}", state


# 입력: 구글이 준 id_token, 앱 설정, 보관해 둔 nonce, 현재 UTC 시각.
# 출력: 검증을 통과한 id_token 본문 값.
# 동작: 구조·대상·만료·nonce·이메일 확인을 검사한다.
def _verify_id_token(
    id_token: str, settings: Settings, nonce: str, now: datetime
) -> GoogleIdClaims:
    """id_token 본문을 검증한다.

    입력: id_token (구글 token 엔드포인트에서 HTTPS로 직접 받은 값), settings, nonce, now
    출력: GoogleIdClaims
    기능: 서명 검증은 하지 않는다. 구글 token 엔드포인트와 TLS로 직접 통신해 받은 토큰은
          OIDC Core 3.1.3.7이 서명 검증을 TLS 검증으로 대신하도록 허용한다.
          iss·aud·exp·nonce·email_verified가 하나라도 어긋나면 SocialLoginError.
    """
    try:
        payload = jwt.decode(id_token, options={"verify_signature": False})
        claims = GoogleIdClaims.model_validate(payload)
    except (jwt.PyJWTError, ValidationError) as exc:
        raise SocialLoginError("invalid_id_token") from exc
    if claims.aud != settings.google_client_id or claims.exp <= now.timestamp():
        raise SocialLoginError("invalid_id_token")
    if not hmac.compare_digest(claims.nonce.encode(), nonce.encode()):
        raise SocialLoginError("invalid_id_token")
    if not claims.email_verified:
        raise SocialLoginError("email_unverified")
    return claims


# 입력: 앱 설정, 검증된 구글 정보, 현재 UTC 시각.
# 출력: 로그인시킬 사용자 ID.
# 동작: (GOOGLE, sub)로 계정을 찾고 없으면 비밀번호 없는 새 계정과 연결을 한 트랜잭션으로 만든다.
def _find_or_create_user(settings: Settings, claims: GoogleIdClaims, now: datetime) -> str:
    """구글 계정에 대응하는 우리 사용자를 찾거나 만든다.

    입력: settings (앱 설정), claims (검증된 구글 정보), now (UTC 시각)
    출력: str (사용자 id)
    기능: 이미 연결돼 있으면 그 계정. 같은 이메일의 비밀번호 계정이 있으면 합치지 않고
          _LinkRequiredError(사용자가 선택해 연결). 동시에 같은 구글 계정이 처음 들어와
          유니크 제약에 걸리면 다시 조회해 로그인으로 처리한다.
    """
    email = claims.email.lower()
    try:
        with transaction(settings.database_url) as conn:
            existing_id = find_user_id(conn, SocialProvider.GOOGLE, claims.sub)
            if existing_id is not None:
                return existing_id
            same_email = find_by_email(conn, email)
            if same_email is not None:
                # 비밀번호가 없거나 이미 구글이 연결된 계정은 연결 대상이 아니다.
                if same_email.password_hash is None or has_identity(
                    conn, same_email.id, SocialProvider.GOOGLE
                ):
                    raise SocialLoginError("google_account_mismatch")
                raise _LinkRequiredError(same_email.id, claims.sub)
            user = UserRecord(
                id=uuid.uuid4().hex,
                email=email,
                password_hash=None,
                status=UserStatus.ACTIVE,
                role=UserRole.USER,
                created_at=now,
            )
            insert_user(conn, user)
            onboarding_repository.enroll(conn, user.id)
            insert_identity(
                conn,
                SocialIdentityRecord(
                    id=uuid.uuid4().hex,
                    user_id=user.id,
                    provider=SocialProvider.GOOGLE,
                    subject=claims.sub,
                    created_at=now,
                ),
            )
            return user.id
    except (DuplicateIdentityError, DuplicateEmailError) as exc:
        with transaction(settings.database_url) as conn:
            raced_id = find_user_id(conn, SocialProvider.GOOGLE, claims.sub)
        if raced_id is None:
            raise SocialLoginError("google_account_mismatch") from exc
        return raced_id


# 입력: 앱 설정, 저장소, 구글 클라이언트, state(쿼리·쿠키), 인증 코드, IP, 현재 시각.
# 출력: 화면이 토큰으로 바꿀 1회용 교환 코드.
# 동작: state 검증 → 코드 교환 → id_token 검증 → 계정 연결/생성 → 교환 코드 발급.
def finish_login(
    settings: Settings,
    store: OneTimeStore,
    google: GoogleClient,
    state: str,
    cookie_state: str | None,
    code: str,
    client_ip: str | None,
    now: datetime,
) -> tuple[str, str]:
    """구글이 돌려보낸 콜백을 처리한다.

    입력: state·code (구글이 붙여 준 쿼리 값), cookie_state (시작 때 심은 쿠키),
          그 밖에 설정·저장소·구글 클라이언트·IP·시각
    출력: tuple (종류 google|google_link, 값). google=60초 1회용 교환 코드,
          google_link=같은 이메일 계정과 연결할지 고르는 5분짜리 표
    기능: state는 확인 결과와 상관없이 먼저 꺼내서 지운다(재사용 불가). 쿠키 state와 다르면
          다른 사람이 시작한 로그인을 끼워 넣은 것(CSRF)이므로 거부한다.
          실패하면 SocialLoginError(reason).
    """
    require_enabled(settings)
    pending_json = store.pop(_STATE, state, now)
    cookie_ok = cookie_state is not None and hmac.compare_digest(
        state.encode(), cookie_state.encode()
    )
    if pending_json is None or not cookie_ok:
        audit("google_login", "state_invalid", client_ip=client_ip)
        raise SocialLoginError("state_invalid")
    try:
        pending = OAuthPending.model_validate_json(pending_json)
        id_token = google.fetch_id_token(code, pending.code_verifier)
    except GoogleUnavailableError as exc:
        audit("google_login", "provider_unavailable", client_ip=client_ip)
        raise SocialLoginError("provider_unavailable") from exc
    except ValidationError as exc:
        raise SocialLoginError("state_invalid") from exc
    try:
        claims = _verify_id_token(id_token, settings, pending.nonce, now)
        user_id = _find_or_create_user(settings, claims, now)
    except _LinkRequiredError as link:
        ticket = _random_token()
        value = LinkTicket(user_id=link.user_id, subject=link.subject).model_dump_json()
        store.put(_LINK, ticket, value, _LINK_TTL_SECONDS, now)
        audit("google_login", "link_offered", user_id=link.user_id, client_ip=client_ip)
        return "google_link", ticket
    except SocialLoginError as exc:
        audit("google_login", exc.reason, client_ip=client_ip)
        raise
    exchange_code = _random_token()
    store.put(_XCODE, exchange_code, user_id, _XCODE_TTL_SECONDS, now)
    audit("google_login", "code_issued", user_id=user_id, client_ip=client_ip)
    return "google", exchange_code


# 입력: 앱 설정, 저장소, 화면이 보낸 교환 요청, IP, 현재 시각.
# 출력: 이메일 로그인과 같은 모양의 인증 응답.
# 동작: 교환 코드를 한 번만 사용해 사용자를 찾고 로그인 세션을 연다.
def exchange(
    settings: Settings,
    store: OneTimeStore,
    request: ExchangeRequest,
    client_ip: str | None,
    now: datetime,
) -> AuthResponse:
    """교환 코드를 토큰으로 바꾼다.

    입력: settings, store, request (교환 코드), client_ip (감사 로그용), now (UTC 시각)
    출력: AuthResponse (사용자·토큰·관심사 안내 여부)
    기능: 없음·만료·이미 사용·탈퇴한 사용자는 모두 같은 InvalidTokenError(401)다.
    """
    require_enabled(settings)
    user_id = store.pop(_XCODE, request.code.get_secret_value(), now)
    user = None
    if user_id is not None:
        with transaction(settings.database_url) as conn:
            user = find_by_id(conn, user_id)
    if user is None or user.status is not UserStatus.ACTIVE:
        audit("google_exchange", "invalid_code", client_ip=client_ip)
        raise InvalidTokenError
    response = auth_service.open_session(settings, user, now)
    audit("google_exchange", "success", user_id=user.id, client_ip=client_ip)
    return response


# 입력: 앱 설정, 저장소, 잠금 장치, 연결 요청(표·비밀번호), IP, 현재 시각.
# 출력: 이메일 로그인과 같은 모양의 인증 응답.
# 동작: 표가 유효하고 기존 계정의 비밀번호가 맞을 때만 구글 계정을 연결하고 로그인시킨다.
def link_account(
    settings: Settings,
    store: OneTimeStore,
    throttles: LoginThrottles,
    request: LinkRequest,
    client_ip: str | None,
    now: datetime,
) -> AuthResponse:
    """사용자가 연결을 선택했을 때 기존 계정에 구글 계정을 붙인다.

    입력: settings, store, throttles (로그인과 같은 잠금), request (표·비밀번호), client_ip, now
    출력: AuthResponse (사용자·토큰)
    기능: 표가 없거나 만료면 InvalidTokenError. 잠겼으면 TooManyAttemptsError.
          비밀번호가 틀리면 InvalidCredentialsError(실패 횟수 증가, 표는 유지해 다시 입력 가능).
          성공하면 표를 지운다. 이메일 소유(구글 확인)와 계정 비밀번호를 모두 알아야 연결된다.
    """
    require_enabled(settings)
    ticket_raw = request.ticket.get_secret_value()
    stored = store.peek(_LINK, ticket_raw, now)
    try:
        ticket = None if stored is None else LinkTicket.model_validate_json(stored)
    except ValidationError:
        ticket = None
    user = None
    if ticket is not None:
        with transaction(settings.database_url) as conn:
            user = find_by_id(conn, ticket.user_id)
    if ticket is None or user is None or user.status is not UserStatus.ACTIVE:
        audit("google_link", "invalid_ticket", client_ip=client_ip)
        raise InvalidTokenError
    ip_key = client_ip or "unknown"
    if throttles.account.is_locked(user.email, now) or throttles.ip.is_locked(ip_key, now):
        audit("google_link", "locked", user_id=user.id, client_ip=client_ip)
        raise TooManyAttemptsError
    if not verify_password(request.password.get_secret_value(), user.password_hash):
        throttles.account.register_failure(user.email, now)
        throttles.ip.register_failure(ip_key, now)
        audit("google_link", "invalid_credentials", user_id=user.id, client_ip=client_ip)
        raise InvalidCredentialsError
    try:
        with transaction(settings.database_url) as conn:
            insert_identity(
                conn,
                SocialIdentityRecord(
                    id=uuid.uuid4().hex,
                    user_id=user.id,
                    provider=SocialProvider.GOOGLE,
                    subject=ticket.subject,
                    created_at=now,
                ),
            )
    except DuplicateIdentityError as exc:
        audit("google_link", "already_linked", user_id=user.id, client_ip=client_ip)
        raise InvalidTokenError from exc
    store.pop(_LINK, ticket_raw, now)
    throttles.account.clear(user.email)
    response = auth_service.open_session(settings, user, now)
    audit("google_link", "success", user_id=user.id, client_ip=client_ip)
    return response

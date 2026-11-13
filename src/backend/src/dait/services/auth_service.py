"""가입·로그인·토큰 갱신·로그아웃 규칙을 처리한다. HTTP 형식은 api, SQL은 repositories가 맡는다."""

import uuid
from datetime import datetime, timedelta

from dait.core.config import Settings
from dait.core.errors import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidTokenError,
    NicknameTakenError,
    TooManyAttemptsError,
    WeakPasswordError,
)
from dait.core.logging import audit
from dait.core.password_policy import is_weak_password
from dait.core.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)
from dait.repositories import onboarding_repository
from dait.repositories.db import DbConnection, transaction
from dait.repositories.interest_repository import replace_codes
from dait.repositories.token_repository import (
    find_by_hash,
    insert_refresh_token,
    revoke_all_for_user,
    revoke_family,
    revoke_if_active,
)
from dait.repositories.user_repository import (
    DuplicateEmailError,
    DuplicateNicknameError,
    find_by_email,
    find_by_id,
    insert_user,
    nickname_exists,
)
from dait.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    SignupRequest,
    TokenPair,
)
from dait.schemas.nickname import NicknameAvailability
from dait.schemas.token import RefreshTokenRecord
from dait.schemas.user import UserPublic, UserRecord, UserRole, UserStatus
from dait.services.login_throttle import LoginThrottles


# 입력: 열린 DB 연결, 앱 설정, 사용자, 현재 시각, 선택적 토큰 계열 ID.
# 출력: 새 access·refresh 토큰 쌍.
# 동작: 토큰을 발급하고 refresh 토큰은 해시만 DB에 저장한다.
def _issue_tokens(
    conn: DbConnection,
    settings: Settings,
    user: UserRecord,
    now: datetime,
    family_id: str | None = None,
) -> TokenPair:
    """토큰 한 쌍을 만들고 refresh 해시를 저장한다.

    입력: conn (열려 있는 트랜잭션 연결), settings (토큰 수명·서명 키),
          user (대상 사용자), now (UTC 시각),
          family_id (회전할 때 이어받는 계열 id, 없으면 새 로그인이라 새 계열)
    출력: TokenPair (access JWT와 refresh 원문)
    기능: refresh 원문은 응답으로만 나가고 DB에는 SHA-256 해시만 저장한다.
    """
    refresh = new_refresh_token()
    insert_refresh_token(
        conn,
        RefreshTokenRecord(
            id=uuid.uuid4().hex,
            user_id=user.id,
            family_id=family_id or uuid.uuid4().hex,
            token_hash=hash_refresh_token(refresh),
            expires_at=now + timedelta(days=settings.refresh_token_days),
            created_at=now,
        ),
    )
    access = create_access_token(
        user.id, settings.jwt_secret.get_secret_value(), settings.access_token_minutes, now
    )
    return TokenPair(access_token=access, refresh_token=refresh)


# 입력: 내부 사용자 레코드와 발급한 토큰 쌍.
# 출력: 비밀번호 해시가 제외된 인증 응답.
# 동작: 내부 사용자 모델을 공개 사용자 모델로 변환한다.
def _to_response(user: UserRecord, tokens: TokenPair) -> AuthResponse:
    """사용자 레코드와 토큰을 응답 모델로 바꾼다.

    입력: user (DB 레코드), tokens (발급된 토큰)
    출력: AuthResponse (비밀번호 해시가 빠진 공개 정보)
    기능: DB 모델과 응답 모델을 분리해 내부 값이 새지 않게 한다.
    """
    public = UserPublic(
        id=user.id, email=user.email, status=user.status, role=user.role, nickname=user.nickname
    )
    return AuthResponse(user=public, tokens=tokens)


# 입력: 앱 설정, 검증된 가입 요청, 클라이언트 IP, 현재 UTC 시각.
# 출력: 새 사용자와 최초 토큰 응답.
# 동작: 비밀번호를 검증·해시하고 사용자·관심사·토큰을 한 트랜잭션으로 저장한다.
def signup(
    settings: Settings, request: SignupRequest, client_ip: str | None, now: datetime
) -> AuthResponse:
    """회원가입을 처리하고 최초 토큰을 발급한다.

    입력: settings (앱 설정), request (검증된 가입 요청), client_ip (감사 로그용), now (UTC 시각)
    출력: AuthResponse (새 사용자와 토큰)
    기능: 흔한 비밀번호는 WeakPasswordError, 이미 쓰는 이메일은 EmailAlreadyRegisteredError.
          중복이어도 해시를 먼저 계산해 응답 시간 차이로 가입 여부를 알아내기 어렵게 한다.
    """
    email = str(request.email).lower()
    raw_password = request.password.get_secret_value()
    if is_weak_password(raw_password, email):
        audit("signup", "weak_password", client_ip=client_ip)
        raise WeakPasswordError
    user = UserRecord(
        id=uuid.uuid4().hex,
        email=email,
        password_hash=hash_password(raw_password),
        status=UserStatus.ACTIVE,
        role=UserRole.USER,
        created_at=now,
        nickname=request.nickname,
    )
    try:
        with transaction(
            settings.database_url
        ) as conn:  # 사용자와 첫 토큰을 한 트랜잭션으로 묶는다.
            insert_user(conn, user)
            onboarding_repository.enroll(conn, user.id)
            if request.interests:  # 관심사 저장이 실패하면 가입도 함께 취소된다.
                replace_codes(conn, user.id, [code.value for code in request.interests])
            tokens = _issue_tokens(conn, settings, user, now)
    except DuplicateEmailError as exc:
        audit("signup", "duplicate", client_ip=client_ip)
        # 제품 정책상 중복 이메일은 사용자가 바로 수정할 수 있도록 명확히 알린다.
        raise EmailAlreadyRegisteredError from exc
    except DuplicateNicknameError as exc:
        raise NicknameTakenError from exc
    audit("signup", "success", user_id=user.id, client_ip=client_ip)
    return _to_response(user, tokens)


# 입력: 앱 설정과 정규화된 닉네임.
# 출력: 닉네임 사용 가능 여부.
# 동작: DB에서 중복을 조회하며 가입 시 유니크 제약으로 다시 검증한다.
def check_nickname(settings: Settings, nickname: str) -> NicknameAvailability:
    """닉네임의 현재 사용 가능 여부를 확인한다.

    입력: settings (앱 설정), nickname (정규화된 닉네임)
    출력: NicknameAvailability (조회한 닉네임과 사용 가능 여부)
    기능: 중복 확인은 안내이며 가입 시 DB 유니크 제약으로 다시 보장한다.
    """
    with transaction(settings.database_url) as conn:
        exists = nickname_exists(conn, nickname)
    return NicknameAvailability(nickname=nickname, available=not exists)


# 입력: 앱 설정, 로그인 요청, 실패 제한 장치, 클라이언트 IP, 현재 시각.
# 출력: 인증된 사용자와 새 토큰 응답.
# 동작: 잠금·자격 증명을 검증하고 토큰과 최초 관심사 안내 여부를 발급한다.
def login(
    settings: Settings,
    request: LoginRequest,
    throttles: LoginThrottles,
    client_ip: str | None,
    now: datetime,
) -> AuthResponse:
    """로그인을 처리하고 새 토큰을 발급한다.

    입력: settings (앱 설정), request (검증된 로그인 요청), throttles (잠금 장치),
          client_ip (IP 단위 잠금과 감사 로그용), now (UTC 시각)
    출력: AuthResponse (사용자와 새 토큰)
    기능: 계정·IP가 잠겼으면 TooManyAttemptsError. 이메일이 없든 비밀번호가 틀리든
          같은 InvalidCredentialsError와 같은 비용의 검증을 거친다.
          성공하면 계정 실패 기록을 지운다.
    """
    email = str(request.email).lower()
    ip_key = client_ip or "unknown"
    if throttles.account.is_locked(email, now) or throttles.ip.is_locked(ip_key, now):
        audit("login", "locked", client_ip=client_ip)
        raise TooManyAttemptsError
    with transaction(settings.database_url) as conn:
        user = find_by_email(conn, email)
    password_ok = verify_password(
        request.password.get_secret_value(), user.password_hash if user else None
    )
    if user is None or not password_ok or user.status is not UserStatus.ACTIVE:
        throttles.account.register_failure(email, now)
        throttles.ip.register_failure(ip_key, now)
        audit(
            "login", "invalid_credentials", user_id=user.id if user else None, client_ip=client_ip
        )
        raise InvalidCredentialsError
    throttles.account.clear(email)
    response = open_session(settings, user, now)
    audit("login", "success", user_id=user.id, client_ip=client_ip)
    return response


# 입력: 앱 설정, 인증이 끝난 사용자, 현재 UTC 시각.
# 출력: 새 토큰과 최초 관심사 안내 여부가 담긴 인증 응답.
# 동작: 새 로그인 계열의 토큰을 발급하고 온보딩 표시를 한 번만 소비한다.
def open_session(settings: Settings, user: UserRecord, now: datetime) -> AuthResponse:
    """인증된 사용자에게 로그인 세션(토큰 한 쌍)을 열어 준다.

    입력: settings (앱 설정), user (이미 인증된 사용자), now (UTC 시각)
    출력: AuthResponse (사용자·토큰·onboarding_required)
    기능: 이메일 로그인과 구글 로그인이 같은 토큰 발급 경로를 쓰게 해, refresh 회전과
          재사용 감지가 두 방식에 똑같이 적용된다.
    """
    with transaction(settings.database_url) as conn:
        tokens = _issue_tokens(conn, settings, user, now)
        onboarding_required = onboarding_repository.consume(conn, user.id)
    return _to_response(user, tokens).model_copy(
        update={"onboarding_required": onboarding_required}
    )


# 입력: 열린 DB 연결, 사용자 ID, 토큰 계열 ID, 현재 시각.
# 출력: 재사용 감지 결과 튜플.
# 동작: 폐기된 refresh 토큰 계열을 모두 폐기한다.
def _revoke_family_for_reuse(
    conn: DbConnection, user_id: str, family_id: str, now: datetime
) -> tuple[str, str, None]:
    """폐기된 토큰이 다시 쓰였을 때 그 계열 전체를 폐기한다.

    입력: conn (열려 있는 트랜잭션 연결), user_id (소유자), family_id (계열 id), now (UTC 시각)
    출력: tuple (실패 사유 "reuse_detected", 소유자 id, None)
    기능: 훔친 토큰 사용을 의심해 같은 로그인에서 나온 새 토큰까지 막는다.
    """
    revoke_family(conn, family_id, now)
    return "reuse_detected", user_id, None


# 입력: 열린 DB 연결, 앱 설정, refresh 토큰 해시, 현재 시각.
# 출력: 회전 결과 사유, 사용자 ID, 새 토큰 쌍.
# 동작: refresh 토큰 상태를 검증하고 정상 토큰을 한 번만 회전한다.
def _rotate(
    conn: DbConnection, settings: Settings, token_hash: str, now: datetime
) -> tuple[str, str | None, TokenPair | None]:
    """refresh 토큰 하나를 검사하고 정상이면 새 토큰으로 회전한다.

    입력: conn (열려 있는 트랜잭션 연결), settings (앱 설정), token_hash (받은 토큰의 SHA-256),
          now (UTC 시각)
    출력: tuple (사유 문자열, 소유자 id 또는 None, 새 TokenPair 또는 None)
    기능: 없음/만료/재사용/탈퇴·정지 사용자는 토큰 None으로 돌려준다.
          예외 대신 값으로 돌려주는 이유는 재사용 감지의 폐기를 커밋한 뒤에 오류를 내기 위해서다.
    """
    stored = find_by_hash(conn, token_hash)
    if stored is None:
        return "unknown", None, None
    if stored.revoked_at is not None:
        return _revoke_family_for_reuse(conn, stored.user_id, stored.family_id, now)
    if stored.expires_at <= now:
        return "expired", stored.user_id, None
    if not revoke_if_active(conn, stored.id, now):  # 동시에 같은 토큰을 쓴 경우도 재사용으로 본다.
        return _revoke_family_for_reuse(conn, stored.user_id, stored.family_id, now)
    user = find_by_id(conn, stored.user_id)
    if user is None or user.status is not UserStatus.ACTIVE:
        return "inactive_user", stored.user_id, None
    tokens = _issue_tokens(conn, settings, user, now, stored.family_id)
    return "success", user.id, tokens


# 입력: 앱 설정, refresh 요청, 클라이언트 IP, 현재 시각.
# 출력: 회전해 발급한 새 토큰 쌍.
# 동작: refresh 토큰을 해시해 검증하고 기존 토큰을 폐기한 뒤 새 토큰을 발급한다.
def refresh(
    settings: Settings, request: RefreshRequest, client_ip: str | None, now: datetime
) -> TokenPair:
    """refresh 토큰을 새 토큰 한 쌍으로 회전한다.

    입력: settings (앱 설정), request (refresh 토큰 원문), client_ip (감사 로그용), now (UTC 시각)
    출력: TokenPair (새 access와 새 refresh, 이전 refresh는 폐기됨)
    기능: 실패 사유와 관계없이 같은 InvalidTokenError를 내서 토큰 존재 여부를 알려 주지 않는다.
          폐기된 토큰이 재사용되면 같은 계열 전체를 폐기한다.
    """
    digest = hash_refresh_token(request.refresh_token.get_secret_value())
    with transaction(settings.database_url) as conn:
        reason, user_id, tokens = _rotate(conn, settings, digest, now)
    if tokens is None:
        audit("refresh", reason, user_id=user_id, client_ip=client_ip)
        raise InvalidTokenError
    audit("refresh", "success", user_id=user_id, client_ip=client_ip)
    return tokens


# 입력: 앱 설정, 인증된 사용자, 클라이언트 IP, 현재 시각.
# 출력: 반환값 없음.
# 동작: 사용자의 모든 활성 refresh 토큰을 폐기하고 감사 로그를 남긴다.
def logout(settings: Settings, user: UserRecord, client_ip: str | None, now: datetime) -> None:
    """한 사용자의 refresh 토큰을 모두 폐기한다.

    입력: settings (앱 설정), user (인증된 본인), client_ip (감사 로그용), now (UTC 시각)
    출력: 없음
    기능: 다른 기기의 로그인도 함께 끊긴다(AGENTS.md 5-1). 이미 모두 폐기돼 있어도 오류 없이 끝난다.
          이미 발급된 access 토큰은 만료(최대 access_token_minutes분)까지 유효하다.
    """
    with transaction(settings.database_url) as conn:
        revoke_all_for_user(conn, user.id, now)
    audit("logout", "success", user_id=user.id, client_ip=client_ip)

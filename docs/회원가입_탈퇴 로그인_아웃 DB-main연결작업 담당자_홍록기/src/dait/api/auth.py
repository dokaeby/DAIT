"""인증 라우트(/v1/auth). 요청을 받아 서비스에 넘기고 응답 형식만 맞춘다."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request

from dait.api.deps import client_ip, get_current_user, get_optional_user, get_throttles
from dait.api.two_factor import get_code_store, get_mailer
from dait.core.config import Settings, get_settings
from dait.core.errors import AlreadyLoggedInError
from dait.core.mailer import Mailer
from dait.repositories.code_store import CodeStore
from dait.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    ResultResponse,
    SignupRequest,
    TokenPair,
)
from dait.schemas.two_factor import TwoFactorRequired
from dait.schemas.user import UserRecord
from dait.services import auth_service, interest_service, two_factor_service
from dait.services.login_throttle import LoginThrottles

router = APIRouter(prefix="/v1/auth", tags=["auth"])
SettingsDep = Annotated[Settings, Depends(get_settings)]


def _attach_interests(response: AuthResponse, settings: Settings) -> AuthResponse:
    """응답에 DB에 저장된 관심사 목록을 붙인다.

    입력: response (서비스가 만든 가입·로그인 응답), settings (앱 설정)
    출력: AuthResponse (interests가 채워진 응답)
    기능: 로그인 직후 메인 화면이 관심사를 바로 쓰게 한다. 관심사 기능을 뺄 때는 이 함수와
          호출 두 곳만 지우면 된다(인증 서비스는 관심사를 모른다).
    """
    items = interest_service.list_interests(settings, response.user.id).interests
    return response.model_copy(update={"interests": items})


# def(동기)로 선언해야 argon2 해시와 sqlite 호출이 스레드풀에서 돌아 이벤트 루프를 막지 않는다.
@router.post("/signup", response_model=AuthResponse, status_code=201)
def signup(
    body: SignupRequest,
    request: Request,
    settings: SettingsDep,
    current: Annotated[UserRecord | None, Depends(get_optional_user)],
) -> AuthResponse:
    """이메일·비밀번호로 가입하고 로그인 토큰을 받는다.

    입력: body (이메일, 비밀번호 8~128자, 비밀번호 확인, 약관 동의), request, settings,
          current (이미 로그인된 요청이면 사용자)
    출력: AuthResponse (201, 사용자 정보와 access·refresh 토큰)
    기능: 로그인된 상태면 409 ALREADY_LOGGED_IN, 이미 가입된 이메일은 409 SIGNUP_FAILED,
          흔하거나 이메일을 포함한 비밀번호는 422 WEAK_PASSWORD.
    """
    if current is not None:
        raise AlreadyLoggedInError
    response = auth_service.signup(settings, body, client_ip(request), datetime.now(UTC))
    return _attach_interests(response, settings)


@router.post("/login", response_model=AuthResponse | TwoFactorRequired)
def login(
    body: LoginRequest,
    request: Request,
    settings: SettingsDep,
    throttles: Annotated[LoginThrottles, Depends(get_throttles)],
    current: Annotated[UserRecord | None, Depends(get_optional_user)],
    store: Annotated[CodeStore, Depends(get_code_store)],
    mailer: Annotated[Mailer, Depends(get_mailer)],
    background: BackgroundTasks,
) -> AuthResponse | TwoFactorRequired:
    """이메일·비밀번호로 로그인하고 토큰을 받는다.

    입력: body (이메일, 비밀번호), request, settings, throttles, current (이미 로그인된 사용자)
    출력: AuthResponse (200, 사용자 정보와 새 토큰) 또는 TwoFactorRequired (200, 코드 확인 필요)
    기능: 로그인된 상태면 409, 틀린 이메일·비밀번호는 같은 401, 실패가 쌓이면 429로 잠근다.
          TWO_FACTOR_ENABLED가 꺼져 있으면(기본) 예전과 똑같이 토큰을 준다. 켜져 있으면
          비밀번호가 맞을 때 토큰 대신 코드 확인 요구를 주고 메일은 응답 뒤에 보낸다.
    """
    if current is not None:
        raise AlreadyLoggedInError
    now = datetime.now(UTC)
    if not settings.two_factor_enabled:
        response = auth_service.login(settings, body, throttles, client_ip(request), now)
        return _attach_interests(response, settings)
    user = auth_service.verify_credentials(settings, body, throttles, client_ip(request), now)
    challenge, mail = two_factor_service.start_login(settings, store, user, client_ip(request), now)
    background.add_task(two_factor_service.deliver, mailer, mail)
    return challenge


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest, request: Request, settings: SettingsDep) -> TokenPair:
    """refresh 토큰으로 새 access·refresh 토큰을 받는다(로그인 유지).

    입력: body (refresh 토큰), request, settings
    출력: TokenPair (새 토큰, 이전 refresh는 더 이상 쓸 수 없음)
    기능: 없거나 만료되거나 이미 쓴 토큰은 모두 같은 401이다.
          이미 쓴 토큰이면 같은 계열을 전부 막는다.
    """
    return auth_service.refresh(settings, body, client_ip(request), datetime.now(UTC))


@router.post("/logout", response_model=ResultResponse)
def logout(
    request: Request, settings: SettingsDep, user: Annotated[UserRecord, Depends(get_current_user)]
) -> ResultResponse:
    """로그아웃: 이 사용자의 refresh 토큰을 모두 폐기한다.

    입력: request, settings, user (Bearer 토큰으로 확인된 본인)
    출력: ResultResponse ({"result": "done"})
    기능: 토큰이 없으면 401. 두 번 불러도 같은 결과다.
    """
    auth_service.logout(settings, user, client_ip(request), datetime.now(UTC))
    return ResultResponse()

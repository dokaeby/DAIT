"""구글 로그인 라우트(/v1/auth/google). 구글 설정이 없으면 모두 404다."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Query, Request
from fastapi.responses import RedirectResponse

from dait.api.deps import (
    client_ip,
    get_google_client,
    get_one_time_store,
    get_optional_user,
    get_throttles,
)
from dait.core.config import AppEnv, Settings, get_settings
from dait.core.errors import AlreadyLoggedInError
from dait.repositories.one_time_store import OneTimeStore
from dait.schemas.auth import AuthResponse
from dait.schemas.social import ExchangeRequest, LinkRequest
from dait.schemas.user import UserRecord
from dait.services import interest_service, social_auth_service
from dait.services.google_client import GoogleClient
from dait.services.login_throttle import LoginThrottles
from dait.services.social_auth_service import SocialLoginError

router = APIRouter(prefix="/v1/auth/google", tags=["auth"])
SettingsDep = Annotated[Settings, Depends(get_settings)]
StoreDep = Annotated[OneTimeStore, Depends(get_one_time_store)]

_COOKIE = "google_oauth_state"
_COOKIE_PATH = "/v1/auth/google"
_COOKIE_MAX_AGE = 600
_AFTER_LOGIN = "/"  # 화면과 API가 같은 출처라 상대 경로로 돌려보낸다(열린 리다이렉트 방지)


def _redirect(target: str) -> RedirectResponse:
    """캐시되지 않는 302 응답을 만든다. 교환 코드가 중간 캐시에 남지 않게 한다."""
    return RedirectResponse(target, status_code=302, headers={"Cache-Control": "no-store"})


# 입력: HTTP 요청, 앱 설정, 1회용 저장소, 현재 로그인 사용자.
# 출력: 구글 로그인 화면으로 가는 302 응답.
# 동작: state를 쿠키에 심고 구글 주소로 보낸다.
@router.get("/status")
def google_login_status(settings: SettingsDep) -> dict[str, bool]:
    """Expose availability only; credentials remain on the server."""
    return {"enabled": settings.google_enabled}


@router.get("/login", status_code=302, response_class=RedirectResponse)
def login(
    settings: SettingsDep,
    store: StoreDep,
    current: Annotated[UserRecord | None, Depends(get_optional_user)],
) -> RedirectResponse:
    """구글 로그인을 시작한다.

    입력: settings, store (1회용 저장소), current (이미 로그인한 요청이면 사용자)
    출력: 302 (구글 로그인 화면), state 쿠키 포함
    기능: 구글 설정이 없으면 404, 이미 로그인된 상태면 409.
    """
    social_auth_service.require_enabled(settings)
    if current is not None:
        raise AlreadyLoggedInError
    url, state = social_auth_service.start_login(settings, store, datetime.now(UTC))
    response = _redirect(url)
    response.set_cookie(
        _COOKIE,
        state,
        max_age=_COOKIE_MAX_AGE,
        path=_COOKIE_PATH,
        httponly=True,
        secure=settings.app_env is AppEnv.RELEASE,
        samesite="lax",  # 구글에서 돌아오는 최상위 이동에는 쿠키가 실려야 한다
    )
    return response


# 입력: 구글이 붙인 쿼리(state, code, error), 쿠키 state, 앱 설정, 저장소, 구글 클라이언트.
# 출력: 화면으로 돌아가는 302 응답(교환 코드 또는 오류 사유를 # 뒤에 붙임).
# 동작: 콜백을 검증하고 성공이면 1회용 교환 코드를 발급한다.
@router.get("/callback", status_code=302, response_class=RedirectResponse)
def callback(
    request: Request,
    settings: SettingsDep,
    store: StoreDep,
    google: Annotated[GoogleClient, Depends(get_google_client)],
    state: Annotated[str | None, Query(max_length=128)] = None,
    code: Annotated[str | None, Query(max_length=2048)] = None,
    error: Annotated[str | None, Query(max_length=100)] = None,
    cookie_state: Annotated[str | None, Cookie(alias=_COOKIE, max_length=128)] = None,
) -> RedirectResponse:
    """구글 로그인 결과를 받아 화면으로 돌려보낸다.

    입력: request, settings, store, google, state·code·error (구글이 붙인 쿼리),
          cookie_state (시작 때 심은 쿠키)
    출력: 302 → `/#google=<교환 코드>` 또는 `/#google_error=<사유>`
    기능: 토큰은 URL에 싣지 않고 60초 1회용 교환 코드만 싣는다. #(프래그먼트) 뒤 값은
          서버 로그나 Referer로 전송되지 않는다. 사용자가 구글에서 취소하면 access_denied.
    """
    social_auth_service.require_enabled(settings)
    if error is not None or state is None or code is None:
        reason = "access_denied" if error is not None else "state_invalid"
        response = _redirect(f"{_AFTER_LOGIN}#google_error={reason}")
    else:
        try:
            kind, value = social_auth_service.finish_login(
                settings,
                store,
                google,
                state,
                cookie_state,
                code,
                client_ip(request),
                datetime.now(UTC),
            )
            response = _redirect(f"{_AFTER_LOGIN}#{kind}={value}")
        except SocialLoginError as exc:
            response = _redirect(f"{_AFTER_LOGIN}#google_error={exc.reason}")
    response.delete_cookie(_COOKIE, path=_COOKIE_PATH)
    return response


# 입력: 교환 코드 요청, HTTP 요청, 앱 설정, 저장소.
# 출력: 이메일 로그인과 같은 모양의 인증 응답.
# 동작: 교환 코드를 한 번만 사용해 토큰을 발급한다.
@router.post("/exchange", response_model=AuthResponse)
def exchange(
    body: ExchangeRequest, request: Request, settings: SettingsDep, store: StoreDep
) -> AuthResponse:
    """교환 코드를 로그인 토큰으로 바꾼다.

    입력: body (교환 코드), request, settings, store
    출력: AuthResponse (사용자·토큰·관심사)
    기능: 없음·만료·이미 사용은 모두 같은 401이다. 설정이 없으면 404.
    """
    response = social_auth_service.exchange(
        settings, store, body, client_ip(request), datetime.now(UTC)
    )
    items = interest_service.list_interests(settings, response.user.id).interests
    return response.model_copy(update={"interests": items})


# 입력: 연결 요청(표·비밀번호), HTTP 요청, 앱 설정, 저장소, 로그인 잠금 장치.
# 출력: 이메일 로그인과 같은 모양의 인증 응답.
# 동작: 사용자가 연결을 선택하고 기존 비밀번호를 맞게 입력했을 때 구글 계정을 연결한다.
@router.post("/link", response_model=AuthResponse)
def link(
    body: LinkRequest,
    request: Request,
    settings: SettingsDep,
    store: StoreDep,
    throttles: Annotated[LoginThrottles, Depends(get_throttles)],
) -> AuthResponse:
    """같은 이메일의 기존 계정에 구글 계정을 연결하고 로그인한다.

    입력: body (연결 표, 기존 계정 비밀번호), request, settings, store, throttles
    출력: AuthResponse (사용자·토큰·관심사)
    기능: 표가 없거나 만료면 401, 비밀번호가 틀리면 401(다시 입력 가능), 실패가 쌓이면 429.
    """
    response = social_auth_service.link_account(
        settings, store, throttles, body, client_ip(request), datetime.now(UTC)
    )
    items = interest_service.list_interests(settings, response.user.id).interests
    return response.model_copy(update={"interests": items})

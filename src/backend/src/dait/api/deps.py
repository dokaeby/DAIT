"""라우트가 공통으로 쓰는 의존성: 현재 사용자, 로그인 잠금 장치, 클라이언트 IP."""

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from dait.core.config import Settings, get_settings
from dait.core.errors import InvalidTokenError
from dait.schemas.user import UserRecord
from dait.services import account_service
from dait.services.login_throttle import LoginThrottles, create_throttles

# auto_error=False: 헤더가 없을 때의 응답을 FastAPI 기본(403)이 아니라 우리 오류 형식(401)으로 낸다.
_bearer = HTTPBearer(auto_error=False)
Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]


def get_throttles() -> LoginThrottles:
    """로그인 잠금 장치를 의존성으로 제공한다.

    입력: 없음
    출력: LoginThrottles (create_app이 앱마다 하나씩 바꿔 끼운다)
    기능: 기본 구현은 앱 밖에서 직접 쓸 때를 위한 자리 표시이며 호출마다 새로 만든다.
    """
    return create_throttles()


def client_ip(request: Request) -> str | None:
    """요청을 보낸 IP를 꺼낸다.

    입력: request (현재 요청)
    출력: str 또는 None (알 수 없을 때)
    기능: 프록시 헤더(X-Forwarded-For)는 위조할 수 있어 믿지 않고 접속 소켓 주소만 쓴다.
    """
    return request.client.host if request.client else None


def get_current_user(
    credentials: Credentials, settings: Annotated[Settings, Depends(get_settings)]
) -> UserRecord:
    """보호 라우트의 기본 거부 관문: 유효한 Bearer 토큰이 없으면 401.

    입력: credentials (Authorization 헤더), settings (앱 설정)
    출력: UserRecord (인증된 본인)
    기능: 헤더가 없거나 토큰이 잘못·만료됐거나 사용자가 없으면 InvalidTokenError.
    """
    if credentials is None:
        raise InvalidTokenError
    return account_service.authenticate(settings, credentials.credentials)


def get_optional_user(
    credentials: Credentials, settings: Annotated[Settings, Depends(get_settings)]
) -> UserRecord | None:
    """로그인 여부만 알고 싶은 라우트용: 인증 실패를 오류 대신 None으로 돌려준다.

    입력: credentials (Authorization 헤더), settings (앱 설정)
    출력: UserRecord 또는 None (로그아웃 상태·잘못된 토큰)
    기능: 가입·로그인의 중복 접근 막기와 로그인 상태 확인에 쓴다.
    """
    try:
        return get_current_user(credentials, settings)
    except InvalidTokenError:
        return None

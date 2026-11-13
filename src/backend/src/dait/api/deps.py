"""라우트가 공통으로 쓰는 의존성: 현재 사용자, 로그인 잠금 장치, 클라이언트 IP."""

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from dait.core.config import Settings, get_settings
from dait.core.errors import InvalidTokenError
from dait.repositories.one_time_store import OneTimeStore
from dait.schemas.user import UserRecord
from dait.services import account_service
from dait.services.google_client import GoogleClient, HttpxGoogleClient
from dait.services.login_throttle import LoginThrottles, create_throttles

# auto_error=False: 헤더가 없을 때의 응답을 FastAPI 기본(403)이 아니라 우리 오류 형식(401)으로 낸다.
_bearer = HTTPBearer(auto_error=False)
Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]


# 입력: 없음.
# 출력: 로그인 계정·IP 실패 제한 장치 묶음.
# 동작: 앱 의존성으로 교체 가능한 기본 실패 제한 장치를 만든다.
def get_throttles() -> LoginThrottles:
    """로그인 잠금 장치를 의존성으로 제공한다.

    입력: 없음
    출력: LoginThrottles (create_app이 앱마다 하나씩 바꿔 끼운다)
    기능: 기본 구현은 앱 밖에서 직접 쓸 때를 위한 자리 표시이며 호출마다 새로 만든다.
    """
    return create_throttles()


# 입력: 앱 설정.
# 출력: OAuth state·교환 코드를 담는 1회용 저장소.
# 동작: 앱 의존성으로 교체되는 기본 자리 표시이며 호출마다 새로 만든다.
def get_one_time_store(
    settings: Annotated[Settings, Depends(get_settings)],
) -> OneTimeStore:
    """1회용 저장소를 의존성으로 제공한다.

    입력: settings (Redis 주소가 든 설정)
    출력: OneTimeStore (create_app이 앱마다 하나로 바꿔 끼운다)
    기능: 메모리 대체 저장소는 인스턴스에 있으므로 앱 하나가 같은 인스턴스를 써야 한다.
    """
    return OneTimeStore(settings.redis_url)


# 입력: 앱 설정.
# 출력: 구글과 통신하는 클라이언트.
# 동작: 테스트가 가짜로 바꿔 끼울 수 있게 의존성으로 제공한다.
def get_google_client(settings: Annotated[Settings, Depends(get_settings)]) -> GoogleClient:
    """구글 클라이언트를 의존성으로 제공한다.

    입력: settings (GOOGLE_* 값이 든 설정)
    출력: GoogleClient (실제 httpx 구현)
    기능: 테스트에서는 dependency_overrides로 네트워크 없는 가짜로 바꾼다.
    """
    return HttpxGoogleClient(settings)


# 입력: 현재 HTTP 요청.
# 출력: 접속 소켓의 클라이언트 IP 또는 없음.
# 동작: 위조 가능한 전달 헤더 대신 실제 연결 주소를 읽는다.
def client_ip(request: Request) -> str | None:
    """요청을 보낸 IP를 꺼낸다.

    입력: request (현재 요청)
    출력: str 또는 None (알 수 없을 때)
    기능: 프록시 헤더(X-Forwarded-For)는 위조할 수 있어 믿지 않고 접속 소켓 주소만 쓴다.
    """
    return request.client.host if request.client else None


# 입력: 선택적 Bearer 인증 정보와 앱 설정.
# 출력: 유효한 access 토큰의 활성 사용자.
# 동작: 보호 라우트에서 토큰 부재·오류를 401 도메인 오류로 거부한다.
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


# 입력: 선택적 Bearer 인증 정보와 앱 설정.
# 출력: 인증된 사용자 또는 없음.
# 동작: 로그인 상태 확인 경로에서 인증 실패를 로그아웃 상태로 변환한다.
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

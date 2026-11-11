"""이메일 2차 인증 라우트(/v1/auth/2fa). 요청을 서비스에 넘기고 응답 형식만 맞춘다."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request

from dait.api.deps import client_ip
from dait.core.config import Settings, get_settings
from dait.core.mailer import Mailer, SmtpMailer
from dait.repositories.code_store import CodeStore, SqliteCodeStore
from dait.schemas.auth import AuthResponse
from dait.schemas.two_factor import ResendRequest, ResendResponse, VerifyRequest
from dait.services import interest_service, two_factor_service

router = APIRouter(prefix="/v1/auth/2fa", tags=["auth"])
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_code_store(settings: SettingsDep) -> CodeStore:
    """코드 저장소를 의존성으로 제공한다.

    입력: settings (앱 설정)
    출력: CodeStore (지금은 sqlite 구현, Redis로 바꿀 때 이 함수만 바꾼다)
    기능: 요청마다 가볍게 만든다. 연결은 저장소가 호출마다 열고 닫는다.
    """
    return SqliteCodeStore(settings.database_url)


def get_mailer(settings: SettingsDep) -> Mailer:
    """메일 발송기를 의존성으로 제공한다.

    입력: settings (앱 설정)
    출력: Mailer (Google SMTP 구현, 시험은 dependency_overrides로 가짜를 끼운다)
    기능: 만들 때는 연결하지 않는다. 2차 인증이 꺼져 있으면 부르지도 않는다.
    """
    return SmtpMailer(
        settings.smtp_host,
        settings.smtp_port,
        settings.smtp_username,
        settings.smtp_app_password,
        settings.smtp_from,
    )


# def(동기)로 선언해 sqlite 호출이 스레드풀에서 돌게 한다. 메일은 응답 뒤 백그라운드에서 보낸다.
@router.post("/verify", response_model=AuthResponse)
def verify(
    body: VerifyRequest,
    request: Request,
    settings: SettingsDep,
    store: Annotated[CodeStore, Depends(get_code_store)],
) -> AuthResponse:
    """메일로 받은 코드를 확인하고 로그인 토큰을 받는다.

    입력: body (challenge_id, 6자리 code), request, settings, store
    출력: AuthResponse (200, 사용자 정보와 access·refresh 토큰, 관심사)
    기능: 틀림·만료·시도 초과·이미 사용은 모두 같은 401 INVALID_TWO_FACTOR.
    """
    response = two_factor_service.verify(
        settings, store, body, client_ip(request), datetime.now(UTC)
    )
    items = interest_service.list_interests(settings, response.user.id).interests
    return response.model_copy(update={"interests": items})


@router.post("/resend", response_model=ResendResponse)
def resend(
    body: ResendRequest,
    request: Request,
    settings: SettingsDep,
    store: Annotated[CodeStore, Depends(get_code_store)],
    mailer: Annotated[Mailer, Depends(get_mailer)],
    background: BackgroundTasks,
) -> ResendResponse:
    """새 코드를 메일로 다시 받는다.

    입력: body (challenge_id), request, settings, store, mailer, background
    출력: ResendResponse (200, 다음 재발송까지 기다릴 초)
    기능: 60초 안이거나 5번을 넘기면 429, 없는 챌린지는 401.
    """
    response, mail = two_factor_service.resend(
        settings, store, body, client_ip(request), datetime.now(UTC)
    )
    background.add_task(two_factor_service.deliver, mailer, mail)
    return response

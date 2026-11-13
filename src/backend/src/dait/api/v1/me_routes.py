"""내 계정 라우트(/v1/me). 사용자 id는 항상 토큰에서만 얻고 경로로 받지 않는다."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from dait.api.deps import client_ip, get_current_user, get_optional_user, get_throttles
from dait.core.config import Settings, get_settings
from dait.schemas.auth import ResultResponse, SessionResponse, WithdrawRequest
from dait.schemas.nickname import NicknameResult, NicknameUpdate
from dait.schemas.user import UserRecord
from dait.services import account_service, feed_index_service, interest_service
from dait.services.login_throttle import LoginThrottles

router = APIRouter(prefix="/v1/me", tags=["me"])


@router.get("/session", response_model=SessionResponse)
def session(
    settings: Annotated[Settings, Depends(get_settings)],
    user: Annotated[UserRecord | None, Depends(get_optional_user)],
) -> SessionResponse:
    """로그인 상태를 알려 준다(화면의 메뉴 노출 판단용).

    입력: settings (앱 설정), user (유효한 Bearer 토큰이 있으면 본인, 없으면 None)
    출력: SessionResponse (authenticated와 사용자 정보)
    기능: 토큰이 없거나 틀리거나 만료돼도 오류가 아니라 authenticated=false로 200을 돌려준다.
          로그인 상태면 DB에 저장된 관심사 목록도 함께 준다.
    """
    status = account_service.session_status(user)
    if user is None:
        return status
    feed_index_service.request_classify(settings)
    items = interest_service.list_interests(settings, user.id).interests
    return status.model_copy(update={"interests": items})


@router.patch("/nickname", response_model=NicknameResult)
def change_nickname(
    body: NicknameUpdate,
    settings: Annotated[Settings, Depends(get_settings)],
    user: Annotated[UserRecord, Depends(get_current_user)],
) -> NicknameResult:
    """로그인한 본인의 닉네임을 갱신한다."""
    return account_service.change_nickname(settings, user, body.nickname)


@router.delete("", response_model=ResultResponse)
def withdraw(
    body: WithdrawRequest,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    throttles: Annotated[LoginThrottles, Depends(get_throttles)],
    user: Annotated[UserRecord, Depends(get_current_user)],
) -> ResultResponse:
    """회원탈퇴: 비밀번호를 다시 확인하고 계정과 토큰을 실제로 삭제한다.

    입력: body (재입력한 비밀번호), request, settings, throttles, user (본인)
    출력: ResultResponse ({"result": "done"})
    기능: 비밀번호가 틀리면 401(변경 없음), 실패가 쌓이면 429, 토큰이 없으면 401.
    """
    account_service.withdraw(
        settings,
        user,
        body.password.get_secret_value(),
        throttles,
        client_ip(request),
        datetime.now(UTC),
    )
    return ResultResponse()

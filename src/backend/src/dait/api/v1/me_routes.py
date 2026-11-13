"""내 계정 라우트(/v1/me). 사용자 id는 항상 토큰에서만 얻고 경로로 받지 않는다."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from dait.api.deps import (
    Credentials,
    client_ip,
    get_current_user,
    get_optional_user,
    get_throttles,
)
from dait.core.config import Settings, get_settings
from dait.schemas.auth import ResultResponse, SessionResponse, WithdrawRequest
from dait.schemas.nickname import NicknameResult, NicknameUpdate
from dait.schemas.user import UserRecord
from dait.services import account_service, interest_service
from dait.services.login_throttle import LoginThrottles

router = APIRouter(prefix="/v1/me", tags=["me"])


# 입력: 앱 설정과 선택적으로 인증된 사용자.
# 출력: 로그인 여부·사용자·관심사 응답.
# 동작: 유효한 사용자가 있으면 저장된 관심사를 결합하고 없으면 로그아웃 상태를 반환한다.
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
    items = interest_service.list_interests(settings, user.id).interests
    return status.model_copy(update={"interests": items})


# 입력: 새 닉네임 요청, 앱 설정, 인증된 사용자.
# 출력: 저장된 닉네임 결과.
# 동작: 본인 계정의 닉네임을 고유 제약과 함께 갱신한다.
@router.patch("/nickname", response_model=NicknameResult)
def change_nickname(
    body: NicknameUpdate,
    settings: Annotated[Settings, Depends(get_settings)],
    user: Annotated[UserRecord, Depends(get_current_user)],
) -> NicknameResult:
    """로그인한 본인의 닉네임을 갱신한다.

    입력: body는 새 닉네임이고 settings는 DB 설정이며 user는 인증된 본인이다.
    출력: 저장된 닉네임을 담은 NicknameResult다.
    기능: 다른 사용자의 닉네임이면 409로 거부하고 본인 레코드만 변경한다.
    """
    return account_service.change_nickname(settings, user, body.nickname)


# 입력: 비밀번호 재확인 요청, HTTP 요청, 앱 설정, 로그인 제한, 인증된 사용자.
# 출력: 완료 결과.
# 동작: 비밀번호를 다시 확인한 뒤 사용자와 연관 데이터를 실제 삭제한다.
@router.delete("", response_model=ResultResponse)
def withdraw(
    body: WithdrawRequest,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    throttles: Annotated[LoginThrottles, Depends(get_throttles)],
    user: Annotated[UserRecord, Depends(get_current_user)],
    credentials: Credentials,
) -> ResultResponse:
    """회원탈퇴: 본인 확인 뒤 계정과 토큰을 실제로 삭제한다.

    입력: body (비밀번호 또는 구글 전용 계정의 확인 문구), request, settings, throttles,
          user (본인), credentials (access 토큰: 발급 시각 확인용)
    출력: ResultResponse ({"result": "done"})
    기능: 비밀번호 계정은 비밀번호가 틀리면 401(변경 없음), 실패가 쌓이면 429.
          구글 전용 계정은 로그인 5분 이내 + "탈퇴" 입력이 아니면 403. 토큰이 없으면 401.
    """
    now = datetime.now(UTC)
    if user.password_hash is None:
        issued_at = account_service.token_issued_at(settings, credentials)
        account_service.withdraw_without_password(
            settings, user, body.confirm_text, issued_at, client_ip(request), now
        )
        return ResultResponse()
    password = body.password.get_secret_value() if body.password else ""
    account_service.withdraw(settings, user, password, throttles, client_ip(request), now)
    return ResultResponse()

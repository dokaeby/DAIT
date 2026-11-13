"""관심사 라우트. main에서 이 라우터 한 줄을 빼면 관심사 기능만 빠지고 나머지는 동작한다."""

from typing import Annotated

from fastapi import APIRouter, Depends

from dait.api.deps import get_current_user
from dait.core.config import Settings, get_settings
from dait.schemas.interest import CatalogResponse, InterestsUpdateRequest, MyInterestsResponse
from dait.schemas.user import UserRecord
from dait.services import interest_service

router = APIRouter(tags=["interests"])


# 입력: 없음.
# 출력: 대주제별 관심사 카탈로그.
# 동작: 로그인 없이 선택 가능한 고정 관심사 목록을 반환한다.
@router.get("/v1/interests/catalog", response_model=CatalogResponse)
def catalog() -> CatalogResponse:
    """선택 가능한 관심사 15개를 대주제별로 알려 준다(로그인 불필요).

    입력: 없음
    출력: CatalogResponse (대주제 3개, 각 소주제의 code·name·group)
    기능: 가입 화면에서 로그인 전에도 보여 줘야 해서 공개한다. 개인 데이터는 없다.
    """
    return interest_service.get_catalog()


# 입력: 앱 설정과 인증된 사용자.
# 출력: 본인이 저장한 관심사 목록.
# 동작: access 토큰의 사용자 ID로 관심사만 조회한다.
@router.get("/v1/me/interests", response_model=MyInterestsResponse)
def my_interests(
    settings: Annotated[Settings, Depends(get_settings)],
    user: Annotated[UserRecord, Depends(get_current_user)],
) -> MyInterestsResponse:
    """내 관심사를 조회한다.

    입력: settings, user (Bearer 토큰으로 확인된 본인)
    출력: MyInterestsResponse (선택한 관심사, 없으면 빈 목록)
    기능: 토큰이 없으면 401.
    """
    return interest_service.get_my_interests(settings, user)


# 입력: 새 관심사 목록, 앱 설정, 인증된 사용자.
# 출력: 교체 후 저장된 관심사 목록.
# 동작: 본인의 관심사를 한 트랜잭션에서 전달받은 목록으로 교체한다.
@router.put("/v1/me/interests", response_model=MyInterestsResponse)
def replace_my_interests(
    body: InterestsUpdateRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    user: Annotated[UserRecord, Depends(get_current_user)],
) -> MyInterestsResponse:
    """내 관심사를 보낸 목록으로 통째로 교체한다.

    입력: body (코드 목록, 최대 15개, 빈 목록이면 선택 해제), settings, user (본인)
    출력: MyInterestsResponse (저장된 결과)
    기능: 모르는 코드·중복·16개 이상은 422, 토큰이 없으면 401.
    """
    return interest_service.replace_my_interests(settings, user, body.interests)

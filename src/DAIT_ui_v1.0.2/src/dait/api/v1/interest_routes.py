"""로그인 사용자의 관심 카테고리 선택·조회·저장."""
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from dait.auth import current_user
from dait.preferences import category_options, needs_interest_onboarding, update_interests, user_interests, selected_ui_interests
from dait.schemas import InterestSaved, InterestSelection, InterestState
from frontend.views import render_interests

router = APIRouter(tags=["관심 카테고리"])
CurrentUser = Annotated[str | None, Depends(current_user)]


# 기능: 로그인 여부에 따라 메인 또는 관심사 설정 경로로 이동시킨다.
# 입력:
#   user (CurrentUser): 현재 사용자 이름(비로그인은 None).
# 출력: HTTP 303 RedirectResponse.
@router.get("/interests", response_class=HTMLResponse, summary="관심 카테고리 선택 화면")
def interests_page(user: CurrentUser) -> Response:
    if user is None:
        return RedirectResponse("/", status_code=303)
    return RedirectResponse("/settings#interests", status_code=303)


# 기능: 현재 계정의 관심사와 선택 가능한 카테고리를 제공한다.
# 입력:
#   user (CurrentUser): 현재 사용자 이름(비로그인은 None).
# 출력: InterestState 객체 또는 HTTP 401 JSONResponse.
@router.get("/api/interests", response_model=InterestState)
def get_interests(user: CurrentUser):
    if user is None:
        return JSONResponse({"error": "로그인이 필요합니다."}, status_code=401)
    return InterestState(user=user, available=list(category_options()), selected=list(selected_ui_interests(user)))


# 기능: 현재 계정의 관심사 선택을 검증하고 저장한다.
# 입력:
#   data (InterestSelection): 처리할 요청 또는 결과 데이터.
#   user (CurrentUser): 현재 사용자 이름(비로그인은 None).
# 출력: InterestSaved 객체 또는 HTTP 400/401 JSONResponse.
@router.put("/api/interests", response_model=InterestSaved, summary="내 관심 카테고리 저장")
def put_interests(data: InterestSelection, user: CurrentUser):
    if user is None:
        return JSONResponse({"error": "로그인이 필요합니다."}, status_code=401)
    try:
        selected = update_interests(user, data.categories)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return InterestSaved(message="관심 카테고리를 저장했습니다.", selected=list(selected))


# 기능: 현재 관심사를 유지하고 초기 설정을 나중에 할 수 있다는 안내를 제공한다.
# 입력:
#   user (CurrentUser): 현재 사용자 이름(비로그인은 None).
# 출력: InterestSaved 객체 또는 HTTP 401 JSONResponse.
@router.post("/api/interests/skip", response_model=InterestSaved, summary="이번 로그인에서 관심 카테고리 설정 건너뛰기")
def skip_interests(user: CurrentUser):
    if user is None:
        return JSONResponse({"error": "로그인이 필요합니다."}, status_code=401)
    return InterestSaved(message="관심 카테고리는 나중에 설정할 수 있습니다.", selected=list(user_interests(user)))

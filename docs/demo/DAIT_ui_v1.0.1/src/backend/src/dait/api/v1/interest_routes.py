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


@router.get("/interests", response_class=HTMLResponse, summary="관심 카테고리 선택 화면")
def interests_page(user: CurrentUser) -> Response:
    if user is None:
        return RedirectResponse("/", status_code=303)
    return RedirectResponse("/settings#interests", status_code=303)


@router.get("/api/interests", response_model=InterestState)
def get_interests(user: CurrentUser):
    if user is None:
        return JSONResponse({"error": "로그인이 필요합니다."}, status_code=401)
    return InterestState(user=user, available=list(category_options()), selected=list(selected_ui_interests(user)))


@router.put("/api/interests", response_model=InterestSaved, summary="내 관심 카테고리 저장")
def put_interests(data: InterestSelection, user: CurrentUser):
    if user is None:
        return JSONResponse({"error": "로그인이 필요합니다."}, status_code=401)
    try:
        selected = update_interests(user, data.categories)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return InterestSaved(message="관심 카테고리를 저장했습니다.", selected=list(selected))


@router.post("/api/interests/skip", response_model=InterestSaved, summary="이번 로그인에서 관심 카테고리 설정 건너뛰기")
def skip_interests(user: CurrentUser):
    if user is None:
        return JSONResponse({"error": "로그인이 필요합니다."}, status_code=401)
    return InterestSaved(message="관심 카테고리는 나중에 설정할 수 있습니다.", selected=list(user_interests(user)))

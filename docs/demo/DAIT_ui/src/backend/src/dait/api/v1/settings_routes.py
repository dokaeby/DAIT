"""로그인 사용자 전용 설정 화면. 저장·예약 실행은 후속 단계입니다."""
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from dait.auth import current_user
from frontend.views import render_settings_entry
from dait.preferences import user_interests

router = APIRouter(tags=["설정"])


@router.get("/settings", response_class=HTMLResponse, summary="로그인 사용자 설정 화면")
def settings_page(user: Annotated[str | None, Depends(current_user)]) -> Response:
    if user is None:
        return RedirectResponse("/", status_code=303)
    return HTMLResponse(render_settings_entry(user, user_interests(user)))

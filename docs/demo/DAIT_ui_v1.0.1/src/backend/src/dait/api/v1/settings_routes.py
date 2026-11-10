"""로그인 사용자 전용 설정 화면. 저장·예약 실행은 후속 단계입니다."""
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, Response, JSONResponse
from pydantic import BaseModel, Field
from dait.repositories.user_repository import update_nickname, DuplicateNicknameError

from dait.auth import current_user
from frontend.views import render_settings_entry
from dait.preferences import selected_ui_interests, category_options

router = APIRouter(tags=["설정"])


@router.get("/settings", response_class=HTMLResponse, summary="로그인 사용자 설정 화면")
def settings_page(user: Annotated[str | None, Depends(current_user)]) -> Response:
    if user is None:
        return RedirectResponse("/", status_code=303)
    return HTMLResponse(render_settings_entry(user, selected_ui_interests(user), category_options()))


class NicknameRequest(BaseModel):
    nickname: str = Field(max_length=30)


@router.put("/api/settings/nickname")
def change_nickname(data: NicknameRequest, user: Annotated[str | None, Depends(current_user)]) -> Response:
    if user is None:
        return JSONResponse({"error": "로그인이 필요합니다."}, status_code=401)
    nickname = data.nickname.strip()
    if any(ord(char) < 32 for char in nickname):
        return JSONResponse({"error": "닉네임을 확인해주세요."}, status_code=400)
    try:
        if not update_nickname(user, nickname):
            return JSONResponse({"error": "회원 계정에서만 닉네임을 변경할 수 있습니다."}, status_code=400)
    except DuplicateNicknameError as exc:
        return JSONResponse({"error": str(exc)}, status_code=409)
    return JSONResponse({"nickname": nickname, "message": "닉네임을 변경했습니다."})

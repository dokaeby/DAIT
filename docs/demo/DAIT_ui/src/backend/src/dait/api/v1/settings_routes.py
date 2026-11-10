"""로그인 사용자 전용 설정 화면과 예약 소식함(KAN-10)."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from dait.api.v1.auth_routes import current_user
from dait.schemas import Digest, InboxState, SettingsState, UserSettings
from dait.services import settings_service
from dait.services.preference_service import user_interests
from frontend.views import render_inbox, render_settings_entry

router = APIRouter(tags=["설정"])
CurrentUser = Annotated[str | None, Depends(current_user)]
LOGIN_REQUIRED = {"error": "로그인이 필요합니다."}


def _now() -> datetime:
    return datetime.now(UTC)


@router.get("/settings", response_class=HTMLResponse, summary="로그인 사용자 설정 화면")
def settings_page(user: CurrentUser) -> Response:
    if user is None:
        return RedirectResponse("/", status_code=303)
    state = settings_service.settings_state(user, _now())
    prefs = settings_service.main_preferences(user)
    return HTMLResponse(
        render_settings_entry(user, user_interests(user), state, prefs.inbox_unseen if prefs else 0)
    )


@router.get("/api/settings", response_model=SettingsState, summary="내 설정 조회")
def get_settings(user: CurrentUser) -> Response | SettingsState:
    if user is None:
        return JSONResponse(LOGIN_REQUIRED, status_code=401)
    return settings_service.settings_state(user, _now())


@router.put("/api/settings", response_model=SettingsState, summary="내 설정 저장")
def put_settings(data: UserSettings, user: CurrentUser) -> Response | SettingsState:
    if user is None:
        return JSONResponse(LOGIN_REQUIRED, status_code=401)
    try:
        return settings_service.save_settings(user, data, _now())
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@router.get("/inbox", response_class=HTMLResponse, summary="예약 소식함 화면")
def inbox_page(user: CurrentUser) -> Response:
    if user is None:
        return RedirectResponse("/", status_code=303)
    state = settings_service.inbox(user)
    # 화면에는 이번에 새로 온 소식 표시를 남기고, 저장 상태는 읽음으로 바꿉니다.
    settings_service.mark_inbox_seen(user)
    return HTMLResponse(render_inbox(user, state))


@router.get("/api/inbox", response_model=InboxState, summary="예약 소식함 조회")
def get_inbox(user: CurrentUser) -> Response | InboxState:
    if user is None:
        return JSONResponse(LOGIN_REQUIRED, status_code=401)
    return settings_service.inbox(user)


@router.post("/api/inbox/seen", response_model=InboxState, summary="예약 소식 모두 읽음")
def post_inbox_seen(user: CurrentUser) -> Response | InboxState:
    if user is None:
        return JSONResponse(LOGIN_REQUIRED, status_code=401)
    settings_service.mark_inbox_seen(user)
    return settings_service.inbox(user)


@router.post(
    "/api/inbox/run", response_model=Digest, status_code=201, summary="지금 한 번 받아보기"
)
def post_inbox_run(user: CurrentUser) -> Response | Digest:
    if user is None:
        return JSONResponse(LOGIN_REQUIRED, status_code=401)
    digest = settings_service.run_now(user, _now())
    if digest is None:
        return JSONResponse(
            {"error": "예약 소식을 만들지 못했습니다. 다시 시도해주세요."}, status_code=409
        )
    return digest

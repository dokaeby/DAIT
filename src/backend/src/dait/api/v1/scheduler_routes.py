"""예약 검색 API.

- POST /v1/internal/scheduler/tick : 외부 cron이 부르는 내부 트리거(Bearer SCHEDULER_TICK_SECRET).
- GET  /v1/me/schedule-runs         : 로그인 사용자의 예약 검색 결과·실행 이력.
- POST /v1/me/schedule-runs/seen    : 결과를 확인했다고 표시.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Response

from dait.api.deps import get_current_user
from dait.core.config import Settings, get_settings
from dait.core.errors import SchedulerAuthError
from dait.core.logging import request_id_var
from dait.repositories.audit_repository import insert_audit
from dait.repositories.db import transaction
from dait.schemas.schedule_run import ScheduleRunListResponse, TickRequest, TickResponse
from dait.schemas.user import UserRecord
from dait.services import schedule_run_service
from dait.services.schedule_run_service import (
    DbNewsSearcher,
    KakaoMemoSender,
    NotConfiguredSender,
    ScheduleSearcher,
)

router = APIRouter(tags=["scheduler"])
SettingsDep = Annotated[Settings, Depends(get_settings)]
CurrentUser = Annotated[UserRecord, Depends(get_current_user)]


def get_searcher() -> ScheduleSearcher:
    """예약 검색기. 지훈님 검색 워커가 준비되면 이 의존성만 바꿔 끼운다."""
    return DbNewsSearcher()


def get_sender() -> KakaoMemoSender:
    """카카오 '나에게 보내기' 전송기. 카카오 앱 등록 전에는 '설정 전'으로 기록만 한다."""
    return NotConfiguredSender()


SearcherDep = Annotated[ScheduleSearcher, Depends(get_searcher)]
SenderDep = Annotated[KakaoMemoSender, Depends(get_sender)]


@router.post(
    "/v1/internal/scheduler/tick",
    response_model=TickResponse,
    summary="외부 cron tick 수신(내부 전용)",
    include_in_schema=False,
)
def scheduler_tick(
    settings: SettingsDep,
    background: BackgroundTasks,
    searcher: SearcherDep,
    sender: SenderDep,
    authorization: Annotated[str | None, Header()] = None,
    body: TickRequest | None = None,
) -> TickResponse:
    """실행할 예약 회차를 만들고, 검색·전송은 응답 뒤 백그라운드로 넘긴다.

    입력: Authorization: Bearer <SCHEDULER_TICK_SECRET>, 선택 본문 {"now": ...}
    출력: TickResponse (예약 수·생성·건너뜀)
    기능: 비밀값이 없거나 틀리면 401. 실행 대상이 없어도 200으로 응답한다.
          검색이 오래 걸려도 cron 응답이 늦어지지 않게 처리는 응답 후에 한다.
    """
    if not schedule_run_service.tick_secret_matches(settings, authorization):
        raise SchedulerAuthError
    now = body.now if body and body.now else datetime.now(UTC)
    result = schedule_run_service.plan_due_runs(settings, now)
    with transaction(settings.database_url) as conn:
        insert_audit(
            conn, None, "SCHEDULER_TICK", "scheduler", None, request_id_var.get(), datetime.now(UTC)
        )
    background.add_task(schedule_run_service.process_pending, settings, now, searcher, sender)
    return result


@router.get(
    "/v1/me/schedule-runs",
    response_model=ScheduleRunListResponse,
    summary="내 예약 검색 결과·실행 이력",
)
def list_my_schedule_runs(settings: SettingsDep, user: CurrentUser) -> ScheduleRunListResponse:
    """로그인하면 보여줄 예약 검색 결과(검색·카카오 상태 포함)를 최신순으로 돌려준다."""
    return schedule_run_service.list_runs(settings, user)


@router.post("/v1/me/schedule-runs/seen", status_code=204, summary="예약 검색 결과 확인 표시")
def mark_my_schedule_runs_seen(settings: SettingsDep, user: CurrentUser) -> Response:
    """새 결과 표시를 지운다."""
    schedule_run_service.mark_runs_seen(settings, user, datetime.now(UTC))
    return Response(status_code=204)

"""예약 검색 실행(tick)·실행 이력·결과 조회 계약 모델 (06_API 7.3절 + 예약 검색 업무 지시서)."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SearchStatus(StrEnum):
    """검색 단계 상태. 결과 없음과 실패를 구분한다."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    NO_RESULTS = "NO_RESULTS"
    FAILED = "FAILED"


class NotifyStatus(StrEnum):
    """카카오(나에게 보내기) 전송 단계 상태. 검색 상태와 따로 기록한다."""

    WAITING = "WAITING"  # 검색이 끝나기 전
    PENDING = "PENDING"  # 보낼 차례
    SENDING = "SENDING"  # 한 서버가 보내는 중(lease)
    SENT = "SENT"
    FAILED = "FAILED"  # 재시도 대상
    UNKNOWN = "UNKNOWN"  # 응답이 끊겨 전송 여부를 모름 → 자동 재호출하지 않음
    SKIPPED = "SKIPPED"  # 결과 없음 등 보낼 필요 없음
    NOT_CONFIGURED = "NOT_CONFIGURED"  # 카카오 연동 설정 전


class TickRequest(BaseModel):
    """POST /v1/internal/scheduler/tick 요청. 본문이 없으면 서버 시각을 쓴다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    now: datetime | None = None


class TickResponse(BaseModel):
    """tick 처리 요약. 기사 본문·사용자 정보는 넣지 않는다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: str = "ok"
    tick_at: datetime
    due_schedules: int
    jobs_created: int
    jobs_skipped: int
    notifications_created: int = 0


class ScheduleRunItem(BaseModel):
    """예약 검색으로 찾은 기사 한 건."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    news_id: str
    title: str
    source_name: str
    url: str
    published_at: datetime
    summary_lines: str | None = None


class ScheduleRunResponse(BaseModel):
    """실행 이력 한 회차. 검색 상태와 카카오 전송 상태를 따로 보여준다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    schedule_id: str | None
    scheduled_for: datetime
    search_status: SearchStatus
    search_error: str | None
    result_count: int | None
    started_at: datetime | None
    finished_at: datetime | None
    notify_status: NotifyStatus
    notify_error: str | None
    notified_at: datetime | None
    seen: bool
    items: list[ScheduleRunItem] = Field(default_factory=list[ScheduleRunItem])


class ScheduleRunListResponse(BaseModel):
    """GET /v1/me/schedule-runs 응답. 로그인하면 보여줄 예약 검색 결과."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    unseen: int
    items: list[ScheduleRunResponse]

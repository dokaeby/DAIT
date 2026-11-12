"""FR-SET-01 예약 수집: 생성·변경·삭제와 다음 실행 시각 계산을 조정한다."""

import json
import uuid
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dait.core.config import Settings
from dait.core.errors import ScheduleNotFoundError, ValidationFailedError
from dait.repositories import news_repository, schedule_repository
from dait.repositories.audit_repository import insert_audit
from dait.repositories.db import DbConnection, transaction
from dait.schemas.settings import (
    ScheduleCreateRequest,
    ScheduleCriteria,
    ScheduleListResponse,
    ScheduleRepeat,
    ScheduleResponse,
    ScheduleUpdateRequest,
    check_repeat,
    normalize_keywords,
)
from dait.schemas.user import UserRecord

MAX_SCHEDULES = 10


def compute_next_run(local_time: str, timezone_name: str, now: datetime) -> datetime:
    """다음 실행 시각을 UTC로 계산한다.

    입력: local_time ("HH:mm"), timezone_name (IANA 이름), now (현재 UTC 시각)
    출력: datetime (UTC, timezone-aware)
    기능: 사용자 로컬 시각의 다음 발생 시점을 UTC로 변환한다.
          존재하지 않는 시간(DST 공백)은 zoneinfo가 조정한 값으로 계산하고,
          모호한 시간은 fold=0(첫 번째 발생)을 따른다.
    """
    tz = ZoneInfo(timezone_name)  # 잘못된 이름이면 ZoneInfoNotFoundError
    hour, minute = (int(part) for part in local_time.split(":"))
    local_now = now.astimezone(tz)
    candidate = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= local_now:
        candidate += timedelta(days=1)
    return candidate.astimezone(UTC)


def compute_next_occurrence(
    local_time: str,
    timezone_name: str,
    now: datetime,
    repeat: str = "DAILY",
    weekdays: tuple[int, ...] = (),
    run_date: date | None = None,
) -> datetime | None:
    """반복 방식에 맞는 now 이후 다음 실행 시각(UTC). 더 실행할 회차가 없으면 None.

    입력: local_time ("HH:mm"), timezone_name, now (UTC), repeat (DAILY·WEEKLY·ONCE),
          weekdays (WEEKLY의 요일, 월=0…일=6), run_date (ONCE의 날짜)
    출력: datetime(UTC) 또는 None
    기능: DAILY는 매일, WEEKLY는 고른 요일만, ONCE는 그 날짜 그 시각 한 번만(지났으면 None).
    """
    tz = ZoneInfo(timezone_name)
    hour, minute = (int(part) for part in local_time.split(":"))
    local_now = now.astimezone(tz)
    if repeat == "ONCE":
        if run_date is None:
            return None
        once = datetime(run_date.year, run_date.month, run_date.day, hour, minute, tzinfo=tz)
        return once.astimezone(UTC) if once > local_now else None
    allowed = set(weekdays) if repeat == "WEEKLY" else set(range(7))
    if not allowed:
        return None
    for offset in range(8):
        day = local_now + timedelta(days=offset)
        candidate = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate > local_now and candidate.weekday() in allowed:
            return candidate.astimezone(UTC)
    return None


def _validate_timezone(name: str) -> None:
    """IANA 시간대 이름인지 확인한다.

    입력: name (사용자가 보낸 시간대)
    출력: 없음
    기능: 알 수 없는 이름이면 ValidationFailedError(422).
    """
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValidationFailedError from exc


def _validate_criteria_sources(conn: DbConnection, criteria: ScheduleCriteria) -> None:
    """예약 조건의 출처 ID가 활성 승인 출처인지 확인한다.

    입력: conn (연결), criteria (검증할 조건)
    출력: 없음
    기능: 미승인 출처가 하나라도 있으면 ValidationFailedError(422).
    """
    if not criteria.source_ids:
        return
    allowed = set(news_repository.list_enabled_source_ids(conn))
    if any(source_id not in allowed for source_id in criteria.source_ids):
        raise ValidationFailedError


def _normalized_criteria(criteria: ScheduleCriteria) -> ScheduleCriteria:
    """예약 조건을 정규화한다(키워드 정리·중복 제거).

    입력: criteria (요청 모델)
    출력: 정규화된 ScheduleCriteria
    기능: 저장 전에 한 형태로 맞춰 재진입 시 동일하게 복원되게 한다.
    """
    try:
        keywords = normalize_keywords([str(k) for k in criteria.keywords])
    except ValueError as exc:
        raise ValidationFailedError from exc
    return ScheduleCriteria(
        keywords=keywords,
        source_ids=list(dict.fromkeys(criteria.source_ids)),
        categories=list(dict.fromkeys(criteria.categories)),
    )


def _criteria_json(criteria: ScheduleCriteria) -> str:
    """조건을 JSON TEXT로 직렬화한다."""
    return json.dumps(
        {
            "keywords": criteria.keywords,
            "source_ids": criteria.source_ids,
            "categories": [c.value for c in criteria.categories],
        },
        ensure_ascii=False,
    )


def _parse_criteria(raw: str) -> ScheduleCriteria:
    """저장된 조건 JSON을 모델로 되돌린다.

    입력: raw (criteria_json TEXT)
    출력: ScheduleCriteria
    기능: 손상된 값은 빈 조건으로 수렴하지 않고 검증 오류로 드러낸다(데이터 이상).
    """
    return ScheduleCriteria.model_validate(json.loads(raw))


def _repeat(value: str) -> ScheduleRepeat:
    """DB의 반복 방식 문자열을 응답 타입으로 맞춘다(알 수 없는 값은 매일)."""
    if value == "WEEKLY":
        return "WEEKLY"
    if value == "ONCE":
        return "ONCE"
    return "DAILY"


def _to_response(row: schedule_repository.ScheduleRow) -> ScheduleResponse:
    """저장 행을 API 응답으로 변환한다."""
    return ScheduleResponse(
        id=row.id,
        local_time=row.local_time,
        timezone=row.timezone,
        enabled=row.enabled,
        criteria=_parse_criteria(row.criteria_json),
        next_run_at=row.next_run_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        repeat=_repeat(row.repeat),
        weekdays=list(row.weekdays),
        run_date=row.run_date,
    )


def _next_run_or_none(
    enabled: bool,
    local_time: str,
    timezone_name: str,
    now: datetime,
    repeat: str = "DAILY",
    weekdays: tuple[int, ...] = (),
    run_date: date | None = None,
) -> datetime | None:
    """활성 예약의 다음 실행 시각을 계산한다(비활성이면 None)."""
    if not enabled:
        return None
    return compute_next_occurrence(local_time, timezone_name, now, repeat, weekdays, run_date)


def list_schedules(settings: Settings, user: UserRecord) -> ScheduleListResponse:
    """본인의 예약 목록을 조회한다.

    입력: settings, user (본인)
    출력: ScheduleListResponse
    기능: user_id 조건이 항상 붙는다.
    """
    with transaction(settings.database_url) as conn:
        rows = schedule_repository.list_by_user(conn, user.id)
    return ScheduleListResponse(items=[_to_response(row) for row in rows])


def create_schedule(
    settings: Settings,
    user: UserRecord,
    request: ScheduleCreateRequest,
    request_id: str | None,
    now: datetime,
) -> ScheduleResponse:
    """예약을 생성하고 다음 실행 시각을 계산한다.

    입력: settings, user (본인), request (검증된 생성 요청),
          request_id (감사 추적용), now (UTC 시각)
    출력: ScheduleResponse (201)
    기능: 시간대·출처를 검증하고 예약 상한(10개)을 적용한다.
          같은 사용자·예약·실행 창의 중복 작업 방지는 jobs.dedupe_key가 담당한다(후속 단계).
    """
    _validate_timezone(request.timezone)
    criteria = _normalized_criteria(request.criteria)
    with transaction(settings.database_url) as conn:
        _validate_criteria_sources(conn, criteria)
        existing = schedule_repository.list_by_user(conn, user.id)
        if len(existing) >= MAX_SCHEDULES:
            raise ValidationFailedError
        weekdays = tuple(sorted(set(request.weekdays))) if request.repeat == "WEEKLY" else ()
        run_date = request.run_date if request.repeat == "ONCE" else None
        next_run = _next_run_or_none(
            request.enabled,
            request.local_time,
            request.timezone,
            now,
            request.repeat,
            weekdays,
            run_date,
        )
        if request.repeat == "ONCE" and request.enabled and next_run is None:
            raise ValidationFailedError  # 이미 지난 날짜·시각의 한 번만 예약
        row = schedule_repository.ScheduleRow(
            id=uuid.uuid4().hex,
            user_id=user.id,
            local_time=request.local_time,
            timezone=request.timezone,
            enabled=request.enabled,
            criteria_json=_criteria_json(criteria),
            next_run_at=next_run,
            created_at=now,
            updated_at=now,
            repeat=request.repeat,
            weekdays=weekdays,
            run_date=run_date,
        )
        schedule_repository.insert_schedule(conn, row)
        insert_audit(conn, user.id, "SCHEDULE_CREATED", "SCHEDULE", row.id, request_id, now)
    return _to_response(row)


def update_schedule(
    settings: Settings,
    user: UserRecord,
    schedule_id: str,
    request: ScheduleUpdateRequest,
    request_id: str | None,
    now: datetime,
) -> ScheduleResponse:
    """본인의 예약을 부분 수정한다.

    입력: settings, user, schedule_id (경로), request (보낸 필드만 변경),
          request_id, now
    출력: ScheduleResponse (변경된 전체 객체)
    기능: id+user_id로 조회해 타인 예약은 404. 시간·시간대·활성 변경 시
          다음 실행 시각을 다시 계산한다.
    """
    _validate_timezone(request.timezone) if request.timezone is not None else None
    with transaction(settings.database_url) as conn:
        row = schedule_repository.get_by_id_and_user(conn, user.id, schedule_id)
        if row is None:
            raise ScheduleNotFoundError
        criteria = (
            _normalized_criteria(request.criteria)
            if request.criteria is not None
            else _parse_criteria(row.criteria_json)
        )
        if request.criteria is not None:
            _validate_criteria_sources(conn, criteria)
        local_time = request.local_time if request.local_time is not None else row.local_time
        timezone_name = request.timezone if request.timezone is not None else row.timezone
        enabled = request.enabled if request.enabled is not None else row.enabled
        repeat = request.repeat if request.repeat is not None else row.repeat
        weekdays_list = (
            list(request.weekdays) if request.weekdays is not None else list(row.weekdays)
        )
        run_date = request.run_date if request.run_date is not None else row.run_date
        try:
            check_repeat(repeat, weekdays_list, run_date)
        except ValueError as exc:
            raise ValidationFailedError from exc
        weekdays = tuple(sorted(set(weekdays_list))) if repeat == "WEEKLY" else ()
        run_date = run_date if repeat == "ONCE" else None
        schedule_changed = (
            request.local_time is not None
            or request.timezone is not None
            or request.enabled is not None
            or request.repeat is not None
            or request.weekdays is not None
            or request.run_date is not None
        )
        next_run = (
            _next_run_or_none(enabled, local_time, timezone_name, now, repeat, weekdays, run_date)
            if schedule_changed
            else row.next_run_at
        )
        if repeat == "ONCE" and enabled and schedule_changed and next_run is None:
            raise ValidationFailedError  # 이미 지난 날짜·시각으로 바꾸려는 경우
        new_row = schedule_repository.ScheduleRow(
            id=row.id,
            user_id=user.id,
            local_time=local_time,
            timezone=timezone_name,
            enabled=enabled,
            criteria_json=_criteria_json(criteria),
            next_run_at=next_run,
            created_at=row.created_at,
            updated_at=now,
            repeat=repeat,
            weekdays=weekdays,
            run_date=run_date,
        )
        schedule_repository.update_schedule(conn, new_row)
        insert_audit(conn, user.id, "SCHEDULE_UPDATED", "SCHEDULE", row.id, request_id, now)
    return _to_response(new_row)


def delete_schedule(
    settings: Settings,
    user: UserRecord,
    schedule_id: str,
    request_id: str | None,
    now: datetime,
) -> None:
    """본인의 예약을 삭제하고 감사 로그를 남긴다.

    입력: settings, user, schedule_id, request_id, now
    출력: 없음
    기능: 멱등 — 이미 없는 예약이면 404를 반환해 재시도와 구분한다.
    """
    with transaction(settings.database_url) as conn:
        row = schedule_repository.get_by_id_and_user(conn, user.id, schedule_id)
        if row is None:
            raise ScheduleNotFoundError
        schedule_repository.delete_schedule(conn, user.id, schedule_id)
        insert_audit(conn, user.id, "SCHEDULE_DELETED", "SCHEDULE", row.id, request_id, now)

"""예약과 cron-job.org job 동기화.

예약 1건마다 cron-job.org job 1건을 만들고, 그 job이 Render의
POST /v1/internal/scheduler/tick을 예약 시각에 호출하게 한다.
DB의 next_run_at은 그대로 두어 tick이 도착했을 때 실행 회차를 만든다.
"""

import logging
from typing import Any

import httpx

from dait.core.config import Settings
from dait.core.errors import CronJobOrgUnavailableError
from dait.repositories import schedule_repository
from dait.repositories.db import transaction
from dait.repositories.schedule_repository import ScheduleRow
from dait.services.cron_job_org import CronJobOrgClient, CronJobOrgError

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT_SECONDS = 10.0
_JOB_REQUEST_TIMEOUT = 300  # Render cold start를 고려해 cron-job.org 요청 제한을 넉넉히 둔다.


def _configured(settings: Settings) -> bool:
    """외부 cron 등록에 필요한 설정이 모두 있는지 확인한다.

    입력: settings
    출력: bool
    기능: API 키·공개 주소·tick 비밀값이 모두 있을 때만 True.
    """
    return bool(
        settings.cron_job_org_api_key.get_secret_value()
        and settings.public_base_url
        and settings.scheduler_tick_secret.get_secret_value()
    )


def client_for_settings(
    settings: Settings, transport: httpx.BaseTransport | None = None
) -> CronJobOrgClient | None:
    """설정이 갖춰졌을 때만 cron-job.org 클라이언트를 만든다.

    입력: settings, transport (테스트용)
    출력: CronJobOrgClient 또는 None
    기능: 미설정(로컬/테스트)이면 None을 돌려 외부 호출을 건너뛴다.
    """
    if not _configured(settings):
        return None
    return CronJobOrgClient(
        api_key=settings.cron_job_org_api_key.get_secret_value(),
        api_url=settings.cron_job_org_api_url,
        timeout_seconds=_REQUEST_TIMEOUT_SECONDS,
        transport=transport,
    )


def _tick_url(settings: Settings) -> str:
    """cron job이 호출할 Render tick URL을 만든다."""
    return f"{(settings.public_base_url or '').rstrip('/')}/v1/internal/scheduler/tick"


def _job_payload(settings: Settings, row: ScheduleRow) -> dict[str, Any]:
    """cron-job.org DetailedJob 페이로드를 만든다.

    입력: settings, row (예약 행)
    출력: dict (PUT/PATCH /jobs의 job 객체)
    기능: 예약 로컬 시각을 cron-job.org schedule 필드로 바꾸고 tick 인증 헤더를 넣는다.
    """
    hour, minute = (int(part) for part in row.local_time.split(":"))
    return {
        "title": f"dait-schedule-{row.id}",
        "url": _tick_url(settings),
        "enabled": row.enabled,
        "requestMethod": 1,  # POST
        "requestTimeout": _JOB_REQUEST_TIMEOUT,
        "saveResponses": False,
        "schedule": {
            "timezone": row.timezone,
            "expiresAt": 0,
            "hours": [hour],
            "mdays": [-1],
            "minutes": [minute],
            "months": [-1],
            "wdays": [-1],
        },
        "extendedData": {
            "headers": {
                "Authorization": ("Bearer " + settings.scheduler_tick_secret.get_secret_value())
            }
        },
    }


def upsert_schedule_job(
    settings: Settings,
    row: ScheduleRow,
    client: CronJobOrgClient | None = None,
) -> str | None:
    """예약에 대응하는 cron-job.org job을 만들거나 갱신한다.

    입력: settings, row (동기화할 예약), client (테스트용 주입)
    출력: str | None (연결된 jobId, 비활성·미설정이면 None 또는 기존 id)
    기능: jobId가 없으면 생성, 있으면 갱신한다. 404는 stale id로 보고 재생성한다.
    """
    if not _configured(settings):
        return row.cron_job_id
    if not row.enabled and row.cron_job_id is None:
        return None
    owns_client = client is None
    client = client or client_for_settings(settings)
    if client is None:
        return row.cron_job_id
    payload = _job_payload(settings, row)
    try:
        if row.cron_job_id:
            job_id = int(row.cron_job_id)
            try:
                client.update_job(job_id, payload)
                return str(job_id)
            except CronJobOrgError as exc:
                if exc.status_code != 404:
                    raise
                return str(client.create_job(payload))
        return str(client.create_job(payload))
    except CronJobOrgError as exc:
        raise CronJobOrgUnavailableError() from exc
    finally:
        if owns_client:
            client.close()


def delete_schedule_job(
    settings: Settings,
    row: ScheduleRow,
    client: CronJobOrgClient | None = None,
) -> None:
    """예약에 연결된 cron-job.org job을 삭제한다.

    입력: settings, row (삭제할 예약), client (테스트용 주입)
    출력: 없음
    기능: 미설정이거나 jobId가 없으면 아무것도 하지 않는다. 404는 이미 삭제된 것으로 본다.
    """
    if not _configured(settings) or not row.cron_job_id:
        return
    owns_client = client is None
    client = client or client_for_settings(settings)
    if client is None:
        return
    try:
        client.delete_job(int(row.cron_job_id))
    except CronJobOrgError as exc:
        raise CronJobOrgUnavailableError() from exc
    finally:
        if owns_client:
            client.close()


def reconcile_all(settings: Settings, client: CronJobOrgClient | None = None) -> dict[str, int]:
    """DB 예약과 cron-job.org job을 맞춘다(배포/시작 시 1회 권장).

    입력: settings, client (테스트용 주입)
    출력: dict (schedules/synced/failed 건수)
    기능: cron_job_id가 없는 활성 예약은 만들고, 비활성 job은 끄고, stale id는 재생성한다.
    """
    if not _configured(settings):
        return {"schedules": 0, "synced": 0, "failed": 0}
    with transaction(settings.database_url) as conn:
        rows = schedule_repository.list_all(conn)
    synced = 0
    failed = 0
    owns_client = client is None
    client = client or client_for_settings(settings)
    for row in rows:
        if not row.enabled and row.cron_job_id is None:
            continue
        try:
            job_id = upsert_schedule_job(settings, row, client=client)
        except Exception:
            failed += 1
            logger.exception("cron-job.org schedule sync failed", extra={"schedule_id": row.id})
            continue
        if job_id and job_id != row.cron_job_id:
            with transaction(settings.database_url) as conn:
                schedule_repository.set_cron_job_id(conn, row.user_id, row.id, job_id)
        synced += 1
    if owns_client and client is not None:
        client.close()
    return {"schedules": len(rows), "synced": synced, "failed": failed}


def reconcile_all_safe(settings: Settings) -> dict[str, int]:
    """reconcile_all을 감싸 시작을 막지 않게 한다.

    입력: settings
    출력: dict (실패 시 빈 결과)
    기능: 외부 cron 장애가 앱 기동을 실패시키지 않게 로그만 남긴다.
    """
    try:
        return reconcile_all(settings)
    except Exception:
        logger.exception("cron-job.org reconcile failed")
        return {"schedules": 0, "synced": 0, "failed": 0}

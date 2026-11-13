"""cron-job.org 자동 등록/동기화 회귀 테스트."""

import json
from datetime import UTC, datetime
from typing import cast

import httpx
import pytest
from pydantic import SecretStr

from dait.core.config import Settings
from dait.repositories import schedule_repository, user_repository
from dait.repositories.db import transaction
from dait.repositories.schedule_repository import ScheduleRow
from dait.schemas.news import NewsCategory
from dait.schemas.settings import (
    ScheduleCreateRequest,
    ScheduleCriteria,
    ScheduleUpdateRequest,
)
from dait.schemas.user import UserRecord, UserRole, UserStatus
from dait.services import schedule_cron_service, schedule_service
from dait.services.cron_job_org import CronJobOrgClient, CronJobOrgError

TICK_SECRET = "tick-secret-for-cron-tests-0123456789"  # noqa: S105 - 테스트 전용 가짜 값
CRON_API_KEY = "cron-job-org-test-key"
PUBLIC_BASE_URL = "https://dait.onrender.com"
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _settings(db_url: str) -> Settings:
    return Settings(
        database_url=db_url,
        cron_job_org_api_key=SecretStr(CRON_API_KEY),
        cron_job_org_api_url="https://api.cron-job.org",
        public_base_url=PUBLIC_BASE_URL,
        scheduler_tick_secret=SecretStr(TICK_SECRET),
    )


def _user(db_url: str) -> UserRecord:
    user = UserRecord(
        id="user-cron-1",
        email="cron@example.com",
        password_hash=None,
        status=UserStatus.ACTIVE,
        role=UserRole.USER,
        created_at=NOW,
    )
    with transaction(db_url) as conn:
        user_repository.insert_user(conn, user)
    return user


def _criteria(keywords: list[str] | None = None) -> ScheduleCriteria:
    return ScheduleCriteria(categories=[NewsCategory.AI], source_ids=[], keywords=keywords or [])


def _row(cron_job_id: str | None = None, enabled: bool = True) -> ScheduleRow:
    return ScheduleRow(
        id="sched-1",
        user_id="user-cron-1",
        local_time="08:30",
        timezone="Asia/Seoul",
        enabled=enabled,
        criteria_json="{}",
        next_run_at=None,
        created_at=NOW,
        updated_at=NOW,
        cron_job_id=cron_job_id,
    )


class FakeCronClient:
    """cron-job.org 클라이언트 대역. 호출을 기록하고 jobId를 순서대로 돌려준다."""

    def __init__(self) -> None:
        self.created: list[dict[str, object]] = []
        self.updated: list[tuple[int, dict[str, object]]] = []
        self.deleted: list[int] = []
        self.update_error: CronJobOrgError | None = None

    def create_job(self, job: dict[str, object]) -> int:
        self.created.append(job)
        return 100 + len(self.created)

    def update_job(self, job_id: int, job: dict[str, object]) -> None:
        if self.update_error is not None:
            raise self.update_error
        self.updated.append((job_id, job))

    def delete_job(self, job_id: int) -> bool:
        self.deleted.append(job_id)
        return True

    def close(self) -> None:
        """실제 클라이언트와 같은 종료 메서드."""


def test_cron_job_org_client_sends_bearer_and_json_payload() -> None:
    """API 키는 Authorization 헤더에만 있고 job 본문에는 tick 비밀값만 들어간다."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"jobId": 123})

    client = CronJobOrgClient(
        api_key=CRON_API_KEY,
        api_url="https://api.cron-job.org",
        transport=httpx.MockTransport(handler),
    )
    try:
        assert client.create_job({"url": f"{PUBLIC_BASE_URL}/v1/internal/scheduler/tick"}) == 123
    finally:
        client.close()

    assert len(seen) == 1
    request = seen[0]
    assert request.method == "PUT"
    assert str(request.url) == "https://api.cron-job.org/jobs"
    assert request.headers["authorization"] == f"Bearer {CRON_API_KEY}"
    assert json.loads(request.content) == {
        "job": {"url": f"{PUBLIC_BASE_URL}/v1/internal/scheduler/tick"}
    }


def test_cron_job_org_delete_returns_false_on_404() -> None:
    """이미 없는 job 삭제는 실패가 아니라 False로 처리한다."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        assert str(request.url) == "https://api.cron-job.org/jobs/55"
        return httpx.Response(404, json={})

    client = CronJobOrgClient(
        api_key=CRON_API_KEY,
        api_url="https://api.cron-job.org",
        transport=httpx.MockTransport(handler),
    )
    try:
        assert client.delete_job(55) is False
    finally:
        client.close()


def test_upsert_creates_tick_job_for_schedule(db_url: str) -> None:
    """예약 생성 시각이 cron-job.org schedule로 변환되고 tick URL/인증 헤더가 들어간다."""
    settings = _settings(db_url)
    fake = FakeCronClient()

    job_id = schedule_cron_service.upsert_schedule_job(
        settings, _row(), client=cast(CronJobOrgClient, fake)
    )

    assert job_id == "101"
    assert len(fake.created) == 1
    payload = fake.created[0]
    assert payload["url"] == f"{PUBLIC_BASE_URL}/v1/internal/scheduler/tick"
    assert payload["enabled"] is True
    assert payload["requestMethod"] == 1
    schedule = payload["schedule"]
    assert isinstance(schedule, dict)
    assert schedule["timezone"] == "Asia/Seoul"
    assert schedule["hours"] == [8]
    assert schedule["minutes"] == [30]
    extended = payload["extendedData"]
    assert isinstance(extended, dict)
    headers = extended["headers"]
    assert isinstance(headers, dict)
    assert headers["Authorization"] == f"Bearer {TICK_SECRET}"
    assert CRON_API_KEY not in json.dumps(payload)


def test_upsert_updates_existing_job_and_recreates_on_404(db_url: str) -> None:
    """jobId가 있으면 PATCH하고, 404 stale id면 새로 만든다."""
    settings = _settings(db_url)
    fake = FakeCronClient()
    updated = schedule_cron_service.upsert_schedule_job(
        settings, _row(cron_job_id="55"), client=cast(CronJobOrgClient, fake)
    )
    assert updated == "55"
    assert fake.updated
    assert fake.updated[0][0] == 55
    assert not fake.created

    fake.update_error = CronJobOrgError(404)
    recreated = schedule_cron_service.upsert_schedule_job(
        settings, _row(cron_job_id="55"), client=cast(CronJobOrgClient, fake)
    )
    assert recreated == "101"
    assert len(fake.created) == 1
    assert len(fake.updated) == 1  # 404로 실패한 두 번째 update는 기록되지 않는다.


def test_disabled_schedule_without_job_is_noop(db_url: str) -> None:
    """비활성이면서 아직 jobId가 없는 예약은 외부 job을 만들지 않는다."""
    settings = _settings(db_url)
    fake = FakeCronClient()

    assert (
        schedule_cron_service.upsert_schedule_job(
            settings, _row(enabled=False), client=cast(CronJobOrgClient, fake)
        )
        is None
    )
    assert not fake.created
    assert not fake.updated


def test_create_update_delete_schedule_syncs_cron_job(
    db_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """예약 생성/시간 변경/삭제가 cron-job.org job 생성·수정·삭제로 이어진다."""
    settings = _settings(db_url)
    user = _user(db_url)
    fake = FakeCronClient()
    monkeypatch.setattr(
        schedule_cron_service,
        "client_for_settings",
        lambda _settings, transport=None: cast(CronJobOrgClient, fake),
    )

    created = schedule_service.create_schedule(
        settings,
        user,
        ScheduleCreateRequest(
            local_time="08:30", timezone="Asia/Seoul", enabled=True, criteria=_criteria()
        ),
        "req-create",
        NOW,
    )
    assert len(fake.created) == 1
    with transaction(db_url) as conn:
        stored = schedule_repository.get_by_id_and_user(conn, user.id, created.id)
    assert stored is not None
    assert stored.cron_job_id == "101"

    updated = schedule_service.update_schedule(
        settings,
        user,
        created.id,
        ScheduleUpdateRequest(local_time="09:15"),
        "req-update",
        NOW,
    )
    assert updated.local_time == "09:15"
    assert len(fake.updated) == 1
    assert fake.updated[0][0] == 101
    assert not fake.created[1:]

    schedule_service.delete_schedule(settings, user, created.id, "req-delete", NOW)
    assert fake.deleted == [101]


def test_criteria_only_update_does_not_touch_cron_job(
    db_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """관심 조건만 바뀌면 외부 cron job은 그대로 둔다."""
    settings = _settings(db_url)
    user = _user(db_url)
    fake = FakeCronClient()
    monkeypatch.setattr(
        schedule_cron_service,
        "client_for_settings",
        lambda _settings, transport=None: cast(CronJobOrgClient, fake),
    )
    created = schedule_service.create_schedule(
        settings,
        user,
        ScheduleCreateRequest(
            local_time="08:30", timezone="Asia/Seoul", enabled=True, criteria=_criteria()
        ),
        "req-create",
        NOW,
    )
    created_count = len(fake.created)
    updated_count = len(fake.updated)

    schedule_service.update_schedule(
        settings,
        user,
        created.id,
        ScheduleUpdateRequest(criteria=_criteria(keywords=["H100"])),
        "req-criteria",
        NOW,
    )

    assert len(fake.created) == created_count
    assert len(fake.updated) == updated_count


def test_reconcile_registers_legacy_schedule(db_url: str) -> None:
    """이미 DB에만 있던 활성 예약도 시작 동기화에서 cron job을 만든다."""
    settings = _settings(db_url)
    user = _user(db_url)
    legacy = ScheduleRow(
        id="legacy-1",
        user_id=user.id,
        local_time="07:45",
        timezone="Asia/Seoul",
        enabled=True,
        criteria_json="{}",
        next_run_at=None,
        created_at=NOW,
        updated_at=NOW,
    )
    with transaction(db_url) as conn:
        schedule_repository.insert_schedule(conn, legacy)
    fake = FakeCronClient()

    result = schedule_cron_service.reconcile_all(settings, client=cast(CronJobOrgClient, fake))

    assert result == {"schedules": 1, "synced": 1, "failed": 0}
    assert len(fake.created) == 1
    schedule = fake.created[0]["schedule"]
    assert isinstance(schedule, dict)
    assert schedule["minutes"] == [45]
    with transaction(db_url) as conn:
        stored = schedule_repository.get_by_id_and_user(conn, user.id, legacy.id)
    assert stored is not None
    assert stored.cron_job_id == "101"

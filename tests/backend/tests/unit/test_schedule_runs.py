"""예약 검색 tick·실행 이력·카카오 전송 단계 테스트 (예약 검색 업무 지시서 완료 기준)."""

import sqlite3
import threading
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import SecretStr

from dait.api.v1.scheduler_routes import get_searcher, get_sender
from dait.core.config import Settings
from dait.main import create_app
from dait.repositories.db import DbConnection
from dait.schemas.schedule_run import ScheduleRunListResponse, TickResponse
from dait.schemas.settings import ScheduleCriteria
from dait.services import schedule_run_service
from dait.services.schedule_run_service import (
    DbNewsSearcher,
    SearchHit,
    SendOutcome,
    SendResult,
)
from support import HttpClient, as_client

TICK_SECRET = "tick-secret-for-unit-tests-0123456789"  # noqa: S105 - 테스트 전용 가짜 값
PASSWORD = "Str0ng!Passw0rd-xyz"  # noqa: S105 - 테스트 전용 가짜 비밀번호
NOW = datetime(2026, 1, 1, tzinfo=UTC).isoformat()
DROPPED = "connection dropped"
WORKER_DOWN = "search worker down"


class FakeSender:
    """카카오 전송기 가짜. 정해 둔 결과를 차례로 돌려주고 호출을 기록한다."""

    def __init__(self, outcomes: list[SendOutcome] | None = None, raises: bool = False) -> None:
        self.outcomes = outcomes or []
        self.raises = raises
        self.calls: list[tuple[str, str]] = []

    def send(self, user_id: str, text: str, link_url: str | None) -> SendOutcome:
        self.calls.append((user_id, text))
        if self.raises:
            raise TimeoutError(DROPPED)
        return self.outcomes.pop(0) if self.outcomes else SendOutcome(SendResult.SENT)


class FlakySearcher:
    """처음 n번은 실패하는 검색기."""

    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.inner = DbNewsSearcher()

    def search(self, conn: DbConnection, criteria: ScheduleCriteria, limit: int) -> list[SearchHit]:
        if self.failures:
            self.failures -= 1
            raise RuntimeError(WORKER_DOWN)
        return self.inner.search(conn, criteria, limit)


@pytest.fixture
def tick_settings(db_url: str) -> Settings:
    return Settings(database_url=db_url, scheduler_tick_secret=SecretStr(TICK_SECRET))


def _seed_news(db_url: str) -> None:
    conn = sqlite3.connect(db_url.removeprefix("sqlite:///"))
    try:
        conn.execute(
            "INSERT INTO sources (id, name, kind, base_url, priority, enabled, created_at, "
            "updated_at) VALUES ('src1', '테스트통신', 'RSS', 'https://example.com/feed', "
            "10, 1, ?, ?)",
            (NOW, NOW),
        )
        for index, title in enumerate(["HBM 증산 경쟁", "AI 에이전트 공개", "클라우드 요금"]):
            news_id = f"news{index:02d}"
            conn.execute(
                "INSERT INTO news (id, source_id, title, canonical_url, published_at, "
                "collected_at, category, original_language, created_at) "
                "VALUES (?, 'src1', ?, ?, ?, ?, 'AI', 'ko', ?)",
                (
                    news_id,
                    title,
                    f"https://example.com/a{index}",
                    f"2026-01-0{index + 1}T00:00:00+00:00",
                    NOW,
                    NOW,
                ),
            )
            conn.execute(
                "INSERT INTO content_results (news_id, summary_lines, status, updated_at) "
                "VALUES (?, '[\"요약\"]', 'READY', ?)",
                (news_id, NOW),
            )
        conn.commit()
    finally:
        conn.close()


def _client(
    settings: Settings, sender: FakeSender | None = None, searcher: object = None
) -> HttpClient:
    app = create_app(settings)
    if sender is not None:
        app.dependency_overrides[get_sender] = lambda: sender
    if searcher is not None:
        app.dependency_overrides[get_searcher] = lambda: searcher
    return as_client(app)


def _signup(client: HttpClient, email: str = "tick@example.com") -> Mapping[str, str]:
    body = {
        "email": email,
        "password": PASSWORD,
        "password_confirm": PASSWORD,
        "terms_accepted": True,
    }
    response = client.request("POST", "/v1/auth/signup", json=body)
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['tokens']['access_token']}"}


def _schedule(
    client: HttpClient, auth: Mapping[str, str], keywords: list[str], enabled: bool = True
) -> datetime:
    body: dict[str, object] = {
        "local_time": "08:30",
        "timezone": "Asia/Seoul",
        "enabled": enabled,
        "criteria": {"keywords": keywords, "categories": ["AI"]},
    }
    response = client.request("POST", "/v1/me/schedules", json=body, headers=auth)
    assert response.status_code == 201, response.text
    next_run = response.json()["next_run_at"]
    return datetime.fromisoformat(next_run) if next_run else datetime.now(UTC)


def _tick(client: HttpClient, now: datetime, secret: str | None = TICK_SECRET) -> TickResponse:
    headers = {"Authorization": f"Bearer {secret}"} if secret else {}
    response = client.request(
        "POST", "/v1/internal/scheduler/tick", json={"now": now.isoformat()}, headers=headers
    )
    assert response.status_code == 200, response.text
    return TickResponse.model_validate(response.json())


def _runs(client: HttpClient, auth: Mapping[str, str]) -> ScheduleRunListResponse:
    response = client.request("GET", "/v1/me/schedule-runs", headers=auth)
    assert response.status_code == 200
    return ScheduleRunListResponse.model_validate(response.json())


# ---- 인증 ----


@pytest.mark.parametrize("header", [None, "Bearer wrong-secret", f"Token {TICK_SECRET}", "Bearer "])
def test_tick_rejects_missing_or_wrong_secret(tick_settings: Settings, header: str | None) -> None:
    client = _client(tick_settings)
    headers = {"Authorization": header} if header is not None else {}
    response = client.request("POST", "/v1/internal/scheduler/tick", headers=headers)
    assert response.status_code == 401
    assert response.json()["code"] == "AUTHENTICATION_FAILED"


def test_tick_is_disabled_when_secret_not_configured(settings: Settings) -> None:
    client = _client(settings)
    response = client.request(
        "POST", "/v1/internal/scheduler/tick", headers={"Authorization": "Bearer "}
    )
    assert response.status_code == 401


def test_tick_with_nothing_due_returns_ok(tick_settings: Settings) -> None:
    result = _tick(_client(tick_settings), datetime.now(UTC))
    assert result.status == "ok"
    assert result.due_schedules == 0
    assert result.jobs_created == 0


# ---- 실행·이력 ----


def test_due_schedule_runs_once_and_result_is_stored(tick_settings: Settings, db_url: str) -> None:
    _seed_news(db_url)
    sender = FakeSender()
    client = _client(tick_settings, sender)
    auth = _signup(client)
    due = _schedule(client, auth, ["HBM"])

    first = _tick(client, due)
    second = _tick(client, due)  # 같은 tick을 두 번 보내도
    assert first.jobs_created == 1
    assert second.jobs_created == 0  # 검색은 한 번만

    runs = _runs(client, auth)
    assert runs.unseen == 1
    run = runs.items[0]
    assert run.search_status == "SUCCEEDED"
    assert run.result_count == 1
    assert run.items[0].title == "HBM 증산 경쟁"
    assert run.notify_status == "SENT"
    assert len(sender.calls) == 1
    assert "HBM 증산 경쟁" in sender.calls[0][1]

    assert client.request("POST", "/v1/me/schedule-runs/seen", headers=auth).status_code == 204
    assert _runs(client, auth).unseen == 0


def test_disabled_and_not_yet_due_schedules_are_not_run(
    tick_settings: Settings, db_url: str
) -> None:
    _seed_news(db_url)
    client = _client(tick_settings, FakeSender())
    auth = _signup(client)
    due = _schedule(client, auth, ["HBM"], enabled=False)
    assert _tick(client, due + timedelta(days=1)).due_schedules == 0
    other = _signup(client, "other@example.com")
    future = _schedule(client, other, ["HBM"])
    assert _tick(client, future - timedelta(minutes=1)).due_schedules == 0


def test_no_results_skips_kakao(tick_settings: Settings, db_url: str) -> None:
    _seed_news(db_url)
    sender = FakeSender()
    client = _client(tick_settings, sender)
    auth = _signup(client)
    _tick(client, _schedule(client, auth, ["존재하지않는단어"]))
    run = _runs(client, auth).items[0]
    assert run.search_status == "NO_RESULTS"
    assert run.notify_status == "SKIPPED"
    assert sender.calls == []


def test_missed_runs_are_executed_after_server_restart(
    tick_settings: Settings, db_url: str
) -> None:
    _seed_news(db_url)
    client = _client(tick_settings, FakeSender())
    auth = _signup(client)
    due = _schedule(client, auth, ["HBM"])
    result = _tick(client, due + timedelta(days=2, minutes=1))  # 이틀 동안 서버가 꺼져 있었다
    assert result.jobs_created == 3
    schedules = client.request("GET", "/v1/me/schedules", headers=auth).json()["items"]
    assert datetime.fromisoformat(schedules[0]["next_run_at"]) > due + timedelta(days=2)


def test_concurrent_ticks_create_one_run(tick_settings: Settings, db_url: str) -> None:
    _seed_news(db_url)
    client = _client(tick_settings, FakeSender())
    auth = _signup(client)
    due = _schedule(client, auth, ["HBM"])
    totals: list[int] = []

    def tick() -> None:
        totals.append(schedule_run_service.plan_due_runs(tick_settings, due).jobs_created)

    threads = [threading.Thread(target=tick) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sum(totals) == 1


def test_search_failure_is_recorded_and_retried_without_blocking_others(
    tick_settings: Settings, db_url: str
) -> None:
    _seed_news(db_url)
    client = _client(tick_settings, FakeSender(), FlakySearcher(failures=1))
    auth = _signup(client)
    due = _schedule(client, auth, ["HBM"])
    other = _signup(client, "second@example.com")
    _schedule(client, other, ["AI 에이전트"])
    _tick(client, due)

    first = _runs(client, auth).items[0]
    second = _runs(client, other).items[0]
    statuses = {first.search_status, second.search_status}
    assert statuses == {"FAILED", "SUCCEEDED"}  # 한 예약이 실패해도 다른 예약은 처리됨
    failed = first if first.search_status == "FAILED" else second
    assert WORKER_DOWN in (failed.search_error or "")

    schedule_run_service.process_pending(
        tick_settings, due, DbNewsSearcher(), FakeSender()
    )  # 다음 tick의 재시도
    retried = _runs(client, auth).items + _runs(client, other).items
    assert all(r.search_status == "SUCCEEDED" for r in retried)


def test_kakao_failure_retries_only_send_and_unknown_is_not_resent(
    tick_settings: Settings, db_url: str
) -> None:
    _seed_news(db_url)
    sender = FakeSender([SendOutcome(SendResult.FAILED, "HTTP 500")])
    client = _client(tick_settings, sender)
    auth = _signup(client)
    due = _schedule(client, auth, ["HBM"])
    _tick(client, due)
    run = _runs(client, auth).items[0]
    assert run.search_status == "SUCCEEDED"
    assert run.notify_status == "FAILED"

    searcher = FlakySearcher(
        failures=99
    )  # 검색을 다시 하면 실패하게 해서, 재전송 때 검색이 안 불리는지 확인
    schedule_run_service.process_pending(
        tick_settings, due + timedelta(seconds=30), searcher, sender
    )
    assert len(sender.calls) == 1  # 1분이 지나기 전에는 다시 보내지 않음
    schedule_run_service.process_pending(
        tick_settings, due + timedelta(minutes=2), searcher, sender
    )
    run = _runs(client, auth).items[0]
    assert run.notify_status == "SENT"
    assert run.search_status == "SUCCEEDED"
    assert len(sender.calls) == 2

    lost = FakeSender(raises=True)
    other = _signup(client, "lost@example.com")
    due2 = _schedule(client, other, ["AI 에이전트"])
    schedule_run_service.plan_due_runs(tick_settings, due2)
    schedule_run_service.process_pending(tick_settings, due2, DbNewsSearcher(), lost)
    schedule_run_service.process_pending(
        tick_settings, due2 + timedelta(hours=1), DbNewsSearcher(), lost
    )
    run2 = _runs(client, other).items[0]
    assert run2.notify_status == "UNKNOWN"
    assert len(lost.calls) == 1  # 응답이 끊긴 전송은 자동으로 다시 부르지 않는다


def test_runs_are_private_to_owner(tick_settings: Settings, db_url: str) -> None:
    _seed_news(db_url)
    client = _client(tick_settings, FakeSender())
    auth = _signup(client)
    _tick(client, _schedule(client, auth, ["HBM"]))
    stranger = _signup(client, "stranger@example.com")
    assert _runs(client, stranger).items == []
    assert client.request("GET", "/v1/me/schedule-runs").status_code == 401


def test_message_fits_kakao_text_limit() -> None:
    from dait.repositories.schedule_run_repository import RunItemRow

    item = RunItemRow("n", "가" * 300, "출처", "https://example.com/a", datetime.now(UTC), None)
    text, link = schedule_run_service.build_message([item] * 5, None)
    assert len(text) <= 200
    assert link == "https://example.com/a"

"""예약 검색 유스케이스.

흐름: tick 수신 → 실행할 회차 만들기 → 검색 → 결과 저장 → 카카오 전송 → 이력 기록.

외부 의존(검색 워커, 카카오)은 Protocol 뒤에 둔다. 검색은 지훈님 워커가 완성되면 그 함수를 연결하고,
그 전까지는 이미 수집된 뉴스를 DB에서 찾는 DbNewsSearcher를 쓴다.
"""

import hmac
import json
import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Protocol

from dait.core.config import Settings
from dait.repositories import interest_repository, news_repository, schedule_run_repository
from dait.repositories.db import DB_ERRORS, DB_INTEGRITY_ERRORS, DbConnection, transaction
from dait.repositories.interest_matching import GROUPS
from dait.repositories.schedule_run_repository import RunItemRow, RunRow
from dait.schemas.interest import InterestCode
from dait.schemas.schedule_run import (
    NotifyStatus,
    ScheduleRunItem,
    ScheduleRunListResponse,
    ScheduleRunResponse,
    SearchStatus,
    TickResponse,
)
from dait.schemas.settings import ScheduleCriteria
from dait.schemas.user import UserRecord
from dait.services.news_search_service import normalize_query
from dait.services.schedule_service import compute_next_run

logger = logging.getLogger(__name__)

_INTEREST_VALUES = {code.value for code in InterestCode}

MAX_DUE_PER_TICK = 200  # 한 tick에서 살펴볼 예약 수 상한
MAX_CATCHUP_PER_SCHEDULE = 20  # 서버가 오래 꺼져 있었을 때 한 예약에서 되살릴 회차 수 상한
MAX_SEARCH_ATTEMPTS = 3
SEARCH_RESULT_LIMIT = 10
LEASE = timedelta(minutes=5)  # 한 서버가 회차를 붙잡고 있는 최대 시간
RUN_LIST_LIMIT = 30


# ---- 외부 의존 인터페이스 ----


@dataclass(frozen=True)
class SearchHit:
    """검색 결과 기사 한 건(검색 구현과 무관한 공통 형태)."""

    news_id: str
    title: str
    source_name: str
    url: str
    published_at: datetime
    summary_lines: str | None


class ScheduleSearcher(Protocol):
    """예약 조건으로 기사를 찾는다. 지훈님 검색 워커가 이 형태로 연결된다."""

    def search(self, conn: DbConnection, criteria: ScheduleCriteria, limit: int) -> list[SearchHit]:
        """조건에 맞는 기사를 최신순으로 limit건까지 돌려준다. 실패하면 예외를 올린다."""
        ...


class SendResult(StrEnum):
    """카카오 전송 결과. UNKNOWN은 '갔는지 모름'이라 자동으로 다시 보내지 않는다."""

    SENT = "SENT"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    NOT_CONFIGURED = "NOT_CONFIGURED"


@dataclass(frozen=True)
class SendOutcome:
    """전송 결과와 실패 이유(로그·이력용, 비밀값 없음)."""

    result: SendResult
    error: str | None = None


class KakaoMemoSender(Protocol):
    """카카오톡 '나에게 보내기'. 실제 구현은 카카오 앱 등록 후 연결한다."""

    def send(self, user_id: str, text: str, link_url: str | None) -> SendOutcome:
        """사용자 본인 카톡으로 text를 보낸다."""
        ...


class DbNewsSearcher:
    """이미 수집·요약된 뉴스에서 예약 조건으로 찾는 임시 검색기.

    키워드가 여러 개면 하나라도 제목·요약에 들어 있는 기사를 모은다(OR).
    관심사(interests)가 있으면 관심사별 최신 기사를 번갈아 먼저 채우고
    남은 자리는 카테고리 스캔으로 채운다. 영문(en.*) 관심사는 언어 조건이
    붙어 영문 기사만 매칭된다. 출처(source_ids) 조건은 현재 뉴스 조회 SQL이
    출처 ID를 돌려주지 않아 아직 적용하지 않는다.
    """

    def search(self, conn: DbConnection, criteria: ScheduleCriteria, limit: int) -> list[SearchHit]:
        """예약 조건으로 기사를 찾는다."""
        queries = [normalize_query(k) for k in criteria.keywords] or [""]
        interests = criteria.interests or []
        hits: list[SearchHit] = []
        seen: set[str] = set()
        if interests:
            buckets = [
                self._interest_hits(conn, code, queries, limit)
                for code in _ordered_interest_codes(interests)
            ]
            hits = _round_robin(buckets, limit)
            seen = {hit.news_id for hit in hits}
        remaining = limit - len(hits)
        if remaining > 0:
            found: dict[str, SearchHit] = {}
            for category in criteria.categories:
                for query in queries:
                    rows = news_repository.list_public_news(
                        conn, str(category), query, "latest", limit, 0
                    )
                    for row in rows:
                        if row.id in seen:
                            continue
                        found.setdefault(
                            row.id,
                            SearchHit(
                                news_id=row.id,
                                title=row.title,
                                source_name=row.source_name,
                                url=row.canonical_url,
                                published_at=row.published_at,
                                summary_lines=row.summary_lines,
                            ),
                        )
            extra = sorted(
                found.values(), key=lambda h: (h.published_at, h.news_id), reverse=True
            )[:remaining]
            hits.extend(extra)
        hits.sort(key=lambda h: (h.published_at, h.news_id), reverse=True)
        return hits[:limit]

    def _interest_hits(
        self,
        conn: DbConnection,
        code: InterestCode,
        queries: list[str],
        limit: int,
    ) -> list[SearchHit]:
        """관심사 코드 하나에 맞는 기사를 최신순으로 모은다(키워드는 AND 조건)."""
        base = code.value.removeprefix("en.")
        category = GROUPS[base.split(".")[0]]
        found: dict[str, SearchHit] = {}
        for query in queries:
            rows = news_repository.list_public_news(
                conn,
                category,
                query,
                "latest",
                limit,
                0,
                interests=(code.value,),
            )
            for row in rows:
                found.setdefault(
                    row.id,
                    SearchHit(
                        news_id=row.id,
                        title=row.title,
                        source_name=row.source_name,
                        url=row.canonical_url,
                        published_at=row.published_at,
                        summary_lines=row.summary_lines,
                    ),
                )
        return sorted(found.values(), key=lambda h: (h.published_at, h.news_id), reverse=True)[:limit]


def _ordered_interest_codes(codes: list[InterestCode]) -> list[InterestCode]:
    """관심사 코드를 en.*와 한국어 코드가 번갈아 오도록 정렬한다.

    영문 기사는 수집량이 적어 최신순 경쟁에서 항상 밀린다. 슬롯을 관심사별로
    나눌 때 영문 관심사가 한쪽으로 몰리지 않게 두 언어를 교차 배치한다.
    """
    english = sorted((c for c in codes if c.value.startswith("en.")), key=lambda c: c.value)
    korean = sorted((c for c in codes if not c.value.startswith("en.")), key=lambda c: c.value)
    ordered: list[InterestCode] = []
    while english or korean:
        if english:
            ordered.append(english.pop(0))
        if korean:
            ordered.append(korean.pop(0))
    return ordered


def _round_robin(buckets: list[list[SearchHit]], limit: int) -> list[SearchHit]:
    """관심사별 버킷을 한 건씩 번갈아 뽑아 limit까지 채운다(중복 기사 제외)."""
    result: list[SearchHit] = []
    seen: set[str] = set()
    pointers = [0] * len(buckets)
    while len(result) < limit:
        added = False
        for index, bucket in enumerate(buckets):
            while pointers[index] < len(bucket) and bucket[pointers[index]].news_id in seen:
                pointers[index] += 1
            if pointers[index] < len(bucket):
                hit = bucket[pointers[index]]
                pointers[index] += 1
                result.append(hit)
                seen.add(hit.news_id)
                added = True
                if len(result) >= limit:
                    break
        if not added:
            break
    return result


class NotConfiguredSender:
    """카카오 연동 전 기본값: 보내지 않고 '설정 전'으로 기록한다."""

    def send(self, user_id: str, text: str, link_url: str | None) -> SendOutcome:
        """아무것도 보내지 않는다."""
        return SendOutcome(SendResult.NOT_CONFIGURED, "kakao sender is not configured")


# ---- 인증 ----


def tick_secret_matches(settings: Settings, authorization: str | None) -> bool:
    """tick 요청의 Authorization: Bearer 값이 약속된 비밀값과 같은지 확인한다.

    입력: settings (SCHEDULER_TICK_SECRET), authorization (요청 헤더 원문)
    출력: bool
    기능: 비밀값이 설정되지 않았으면 항상 거절한다. 비교는 시간차 공격을 막는 compare_digest로 한다.
    """
    secret = settings.scheduler_tick_secret.get_secret_value()
    if not secret or not authorization or not authorization.startswith("Bearer "):
        return False
    return hmac.compare_digest(authorization.removeprefix("Bearer ").encode(), secret.encode())


# ---- tick: 실행할 회차 만들기 ----


def _utc(moment: datetime) -> datetime:
    """시간대가 없는 값은 UTC로 보고, 모든 비교를 UTC로 맞춘다."""
    return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment.astimezone(UTC)


def plan_due_runs(settings: Settings, now: datetime) -> TickResponse:
    """실행 시각이 된 예약마다 회차 기록을 만들고 다음 실행 시각을 옮긴다.

    입력: settings, now (tick 기준 시각)
    출력: TickResponse (조회·생성·건너뜀 수)
    기능: 서버가 꺼져 있어 놓친 회차도 하나씩 만들어 실행되게 한다
          (팀장님 결정: 놓친 예약은 서버가 살아나면 실행).
          같은 회차는 dedupe_key UNIQUE로, 같은 예약의 동시 처리는
          next_run_at 조건부 갱신으로 한 번만 만든다.
          한 예약이 실패해도 다른 예약은 계속 처리한다.
    """
    now = _utc(now)
    with transaction(settings.database_url) as conn:
        due = schedule_run_repository.list_due_schedules(conn, now, MAX_DUE_PER_TICK)
    created = 0
    skipped = 0
    for schedule in due:
        try:
            made = _plan_one(settings, schedule, now)
        except DB_ERRORS:
            logger.exception("schedule tick failed", extra={"schedule_id": schedule.id})
            skipped += 1
            continue
        if made:
            created += made
        else:
            skipped += 1
    return TickResponse(
        tick_at=now, due_schedules=len(due), jobs_created=created, jobs_skipped=skipped
    )


def _plan_one(
    settings: Settings, schedule: schedule_run_repository.ScheduleRow, now: datetime
) -> int:
    """예약 하나의 놓친 회차들을 만들고 next_run_at을 미래로 옮긴다. 만든 회차 수를 돌려준다."""
    if schedule.next_run_at is None:
        return 0
    expected = _utc(schedule.next_run_at)
    occurrence = expected
    occurrences: list[datetime] = []
    while occurrence <= now and len(occurrences) < MAX_CATCHUP_PER_SCHEDULE:
        occurrences.append(occurrence)
        occurrence = compute_next_run(schedule.local_time, schedule.timezone, occurrence)
    while occurrence <= now:  # 상한을 넘은 오래된 회차는 건너뛰고 다음 미래 시각으로 맞춘다.
        occurrence = compute_next_run(schedule.local_time, schedule.timezone, occurrence)
    made = 0
    with transaction(settings.database_url) as conn:
        if not schedule_run_repository.advance_schedule(
            conn, schedule.id, expected, occurrence, now
        ):
            return 0  # 다른 서버(또는 같은 tick의 중복 호출)가 이미 처리했다.
        for when in occurrences:
            if _insert_run_once(conn, schedule, when, now):
                made += 1
    return made


def _insert_run_once(
    conn: DbConnection, schedule: schedule_run_repository.ScheduleRow, when: datetime, now: datetime
) -> bool:
    """회차를 넣되, 이미 있으면(같은 회차 중복) 조용히 건너뛴다."""
    savepoint = f"run_{uuid.uuid4().hex}"
    conn.execute(f"SAVEPOINT {savepoint}")
    try:
        schedule_run_repository.insert_run(conn, str(uuid.uuid4()), schedule, when, now)
    except DB_INTEGRITY_ERRORS:
        conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
        return False
    conn.execute(f"RELEASE SAVEPOINT {savepoint}")
    return True


# ---- 백그라운드: 검색 → 저장 → 전송 ----


def notify_backoff(settings: Settings, attempt: int) -> timedelta:
    """attempt번째 실패 뒤 다음 재시도까지 기다릴 시간(설정값, 기본 1분·5분·15분)."""
    steps = settings.kakao_retry_backoff_seconds or [60]
    return timedelta(seconds=steps[min(attempt, len(steps)) - 1])


def process_pending(
    settings: Settings,
    now: datetime,
    searcher: ScheduleSearcher,
    sender: KakaoMemoSender,
    limit: int = 50,
) -> dict[str, int]:
    """남아 있는 검색·전송을 처리한다. tick 응답 뒤 백그라운드에서, 그리고 재시도 때 불린다.

    입력: settings, now, searcher (검색기), sender (카카오 전송기), limit (한 번에 처리할 최대 회차)
    출력: {"searched": n, "notified": n}
    기능: 회차마다 먼저 선점(claim)해 여러 서버가 같은 회차를 동시에 처리하지 않게 하고,
          한 회차의 실패가 다른 회차에 영향을 주지 않게 따로 처리한다.
    """
    now = _utc(now)
    with transaction(settings.database_url) as conn:
        schedule_run_repository.mark_stale_sending_unknown(conn, now)
        search_ids = schedule_run_repository.list_search_candidates(
            conn, now, MAX_SEARCH_ATTEMPTS, limit
        )
    searched = sum(1 for run_id in search_ids if _search_one(settings, run_id, now, searcher))
    with transaction(settings.database_url) as conn:
        notify_ids = schedule_run_repository.list_notify_candidates(
            conn, now, settings.kakao_max_attempts, limit
        )
    notified = sum(1 for run_id in notify_ids if _notify_one(settings, run_id, now, sender))
    return {"searched": searched, "notified": notified}


def _search_one(settings: Settings, run_id: str, now: datetime, searcher: ScheduleSearcher) -> bool:
    """회차 하나를 검색하고 결과를 저장한다. 처리했으면 True."""
    with transaction(settings.database_url) as conn:
        if not schedule_run_repository.claim_search(
            conn, run_id, now, now + LEASE, MAX_SEARCH_ATTEMPTS
        ):
            return False
        run = schedule_run_repository.get_run(conn, run_id)
    if run is None:
        return False
    try:
        criteria = ScheduleCriteria.model_validate(json.loads(run.criteria_json))
        if criteria.interests is None:
            # 관심사를 명시하지 않은 예약은 검색 시점의 저장 관심사(한국어 코드)를 따른다.
            with transaction(settings.database_url) as conn:
                saved = interest_repository.list_codes(conn, run.user_id)
            criteria = criteria.model_copy(
                update={
                    "interests": [
                        InterestCode(code)
                        for code in saved
                        if code in _INTEREST_VALUES and not code.startswith("en.")
                    ]
                }
            )
        with transaction(settings.database_url) as conn:
            hits = searcher.search(conn, criteria, SEARCH_RESULT_LIMIT)
    except Exception as exc:  # noqa: BLE001 - 검색 실패 원인을 이력에 남기고 다른 회차는 계속한다.
        logger.warning("schedule search failed", extra={"run_id": run_id})
        with transaction(settings.database_url) as conn:
            schedule_run_repository.finish_search(
                conn,
                run_id,
                SearchStatus.FAILED,
                None,
                _short_error(exc),
                NotifyStatus.WAITING,
                now,
            )
        return True
    items = [
        RunItemRow(h.news_id, h.title, h.source_name, h.url, h.published_at, h.summary_lines)
        for h in hits
    ]
    # 결과가 없으면 요약·번역·전송이 의미 없으므로 카카오는 건너뛴다(팀장님 결정).
    status = SearchStatus.SUCCEEDED if items else SearchStatus.NO_RESULTS
    notify = NotifyStatus.PENDING if items else NotifyStatus.SKIPPED
    with transaction(settings.database_url) as conn:
        schedule_run_repository.replace_items(conn, run_id, items)
        schedule_run_repository.finish_search(conn, run_id, status, len(items), None, notify, now)
    return True


def _notify_one(settings: Settings, run_id: str, now: datetime, sender: KakaoMemoSender) -> bool:
    """회차 하나의 검색 결과를 카카오로 보낸다. 검색은 다시 하지 않는다."""
    with transaction(settings.database_url) as conn:
        if not schedule_run_repository.claim_notify(
            conn, run_id, now, now + LEASE, settings.kakao_max_attempts
        ):
            return False
        run = schedule_run_repository.get_run(conn, run_id)
        items = schedule_run_repository.list_items(conn, run_id)
    if run is None:
        return False
    text, link = build_message(items, settings.public_base_url)
    try:
        outcome = sender.send(run.user_id, text, link)
    except Exception as exc:  # noqa: BLE001 - 응답 전에 끊기면 전송 여부를 알 수 없다.
        outcome = SendOutcome(SendResult.UNKNOWN, _short_error(exc))
    next_at = None
    if outcome.result is SendResult.FAILED and run.notify_attempts < settings.kakao_max_attempts:
        next_at = now + notify_backoff(settings, run.notify_attempts)
    with transaction(settings.database_url) as conn:
        schedule_run_repository.finish_notify(
            conn, run_id, outcome.result.value, outcome.error, next_at, now
        )
    return True


def build_message(items: Sequence[RunItemRow], base_url: str | None) -> tuple[str, str | None]:
    """카카오 기본 텍스트 템플릿(최대 200자)에 맞춰 보낼 문장을 만든다."""
    lines = [f"[DAIT] 예약 검색 결과 {len(items)}건"]
    for index, item in enumerate(items[:3], 1):
        lines.append(f"{index}. {item.title}")
    text = "\n".join(lines)
    if len(text) > 200:
        text = text[:197] + "..."
    link = items[0].url if items else base_url
    return text, link


def _short_error(exc: BaseException) -> str:
    """이력에 남길 짧은 실패 이유(예외 종류와 앞부분만, 비밀값이 섞이지 않게 200자 제한)."""
    return f"{type(exc).__name__}: {exc}"[:200]


# ---- 사용자 화면용 조회 ----


def list_runs(settings: Settings, user: UserRecord) -> ScheduleRunListResponse:
    """로그인한 사용자의 예약 검색 결과(최신 30회차)를 돌려준다."""
    with transaction(settings.database_url) as conn:
        runs = schedule_run_repository.list_runs_for_user(conn, user.id, RUN_LIST_LIMIT)
        unseen = schedule_run_repository.count_unseen(conn, user.id)
        responses = [
            _to_response(run, schedule_run_repository.list_items(conn, run.id)) for run in runs
        ]
    return ScheduleRunListResponse(unseen=unseen, items=responses)


def mark_runs_seen(settings: Settings, user: UserRecord, now: datetime) -> None:
    """사용자가 결과를 확인했음을 기록한다."""
    with transaction(settings.database_url) as conn:
        schedule_run_repository.mark_seen(conn, user.id, _utc(now))


def _to_response(run: RunRow, items: list[RunItemRow]) -> ScheduleRunResponse:
    return ScheduleRunResponse(
        id=run.id,
        schedule_id=run.schedule_id,
        scheduled_for=run.scheduled_for,
        search_status=SearchStatus(run.search_status),
        search_error=run.search_error,
        result_count=run.result_count,
        started_at=run.started_at,
        finished_at=run.finished_at,
        notify_status=NotifyStatus(run.notify_status),
        notify_error=run.notify_error,
        notified_at=run.notified_at,
        seen=run.seen_at is not None,
        items=[
            ScheduleRunItem(
                news_id=i.news_id,
                title=i.title,
                source_name=i.source_name,
                url=i.url,
                published_at=i.published_at,
                summary_lines=i.summary_lines,
            )
            for i in items
        ],
    )

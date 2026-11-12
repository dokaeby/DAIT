"""schedule_runs·schedule_run_items 접근.

회차 중복 방지와 서버 간 작업 선점(lease)을 SQL 조건으로 보장한다.
"""

from datetime import datetime
from typing import NamedTuple

from dait.repositories import schedule_repository
from dait.repositories.db import DbConnection
from dait.repositories.schedule_repository import ScheduleRow


class RunRow(NamedTuple):
    """schedule_runs 한 행."""

    id: str
    schedule_id: str | None
    user_id: str
    scheduled_for: datetime
    criteria_json: str
    search_status: str
    search_attempts: int
    search_error: str | None
    result_count: int | None
    started_at: datetime | None
    finished_at: datetime | None
    notify_status: str
    notify_attempts: int
    notify_error: str | None
    notify_next_at: datetime | None
    notified_at: datetime | None
    seen_at: datetime | None


class RunItemRow(NamedTuple):
    """schedule_run_items 한 행."""

    news_id: str
    title: str
    source_name: str
    url: str
    published_at: datetime
    summary_lines: str | None


_RUN_COLUMNS = (
    "id, schedule_id, user_id, scheduled_for, criteria_json, search_status, search_attempts, "
    "search_error, result_count, started_at, finished_at, notify_status, notify_attempts, "
    "notify_error, notify_next_at, notified_at, seen_at"
)


_MISSING_SCHEDULED_FOR = "scheduled_for is required"


def _dt(value: object) -> datetime | None:
    """DB 값(문자열 또는 datetime)을 datetime으로 바꾼다. 없으면 None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _iso(value: datetime | None) -> str | None:
    """datetime을 저장용 ISO 문자열로 바꾼다."""
    return value.isoformat() if value else None


def _to_run(row: tuple[object, ...]) -> RunRow:
    """SELECT 결과 한 줄을 RunRow로 바꾼다."""
    scheduled_for = _dt(row[3])
    if scheduled_for is None:
        raise ValueError(_MISSING_SCHEDULED_FOR)
    return RunRow(
        id=str(row[0]),
        schedule_id=None if row[1] is None else str(row[1]),
        user_id=str(row[2]),
        scheduled_for=scheduled_for,
        criteria_json=str(row[4]),
        search_status=str(row[5]),
        search_attempts=int(str(row[6])),
        search_error=None if row[7] is None else str(row[7]),
        result_count=None if row[8] is None else int(str(row[8])),
        started_at=_dt(row[9]),
        finished_at=_dt(row[10]),
        notify_status=str(row[11]),
        notify_attempts=int(str(row[12])),
        notify_error=None if row[13] is None else str(row[13]),
        notify_next_at=_dt(row[14]),
        notified_at=_dt(row[15]),
        seen_at=_dt(row[16]),
    )


def list_due_schedules(conn: DbConnection, now: datetime, limit: int) -> list[ScheduleRow]:
    """실행 시각이 된 활성 예약을 오래된 순으로 읽는다.

    입력: conn (연결), now (기준 UTC 시각), limit (한 tick에서 볼 최대 개수)
    출력: ScheduleRow 목록
    기능: 비활성 예약과 아직 시간이 안 된 예약은 SQL 조건에서 바로 빠진다.
    """
    rows = conn.execute(
        f"SELECT {schedule_repository.COLUMNS} FROM schedules "  # noqa: S608 - 상수 컬럼 목록
        "WHERE enabled AND next_run_at IS NOT NULL AND next_run_at <= ? "
        "ORDER BY next_run_at, id LIMIT ?",
        (now.isoformat(), limit),
    ).fetchall()
    return [schedule_repository.row_from_db(tuple(row)) for row in rows]


def advance_schedule(
    conn: DbConnection,
    schedule_id: str,
    expected: datetime,
    next_run_at: datetime | None,
    now: datetime,
) -> bool:
    """예약의 다음 실행 시각을 옮긴다. 다른 서버가 먼저 옮겼다면 바꾸지 않는다.

    입력: conn, schedule_id, expected (읽을 때의 next_run_at), next_run_at (새 값, 없으면 None), now
    출력: bool (이번 호출이 옮겼으면 True)
    기능: WHERE next_run_at = expected 조건으로, 동시에 들어온 tick 중 하나만 성공한다.
          다음 회차가 없으면(한 번만 예약 실행 완료) 예약을 끈다.
    """
    cursor = conn.execute(
        "UPDATE schedules SET next_run_at = ?, enabled = ?, updated_at = ? "
        "WHERE id = ? AND next_run_at = ?",
        (
            next_run_at.isoformat() if next_run_at else None,
            next_run_at is not None,
            now.isoformat(),
            schedule_id,
            expected.isoformat(),
        ),
    )
    return cursor.rowcount == 1


def insert_run(
    conn: DbConnection,
    run_id: str,
    schedule: ScheduleRow,
    scheduled_for: datetime,
    now: datetime,
) -> None:
    """회차 실행 기록을 QUEUED로 만든다.

    입력: conn, run_id, schedule (예약), scheduled_for (회차 시각), now
    출력: 없음
    기능: dedupe_key(예약 ID + 회차 시각)가 UNIQUE라, 같은 회차를 두 번 넣으면 무결성 오류가 난다.
          예약 조건은 그 시점 값으로 복사해 둬 나중에 예약을 고쳐도 이력이 바뀌지 않게 한다.
    """
    conn.execute(
        "INSERT INTO schedule_runs (id, schedule_id, user_id, dedupe_key, scheduled_for, "
        "criteria_json, search_status, search_attempts, notify_status, notify_attempts, "
        "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'QUEUED', 0, 'WAITING', 0, ?, ?)",
        (
            run_id,
            schedule.id,
            schedule.user_id,
            f"{schedule.id}@{scheduled_for.isoformat()}",
            scheduled_for.isoformat(),
            schedule.criteria_json,
            now.isoformat(),
            now.isoformat(),
        ),
    )


def claim_search(
    conn: DbConnection, run_id: str, now: datetime, lease_until: datetime, max_attempts: int
) -> bool:
    """검색할 회차 하나를 선점한다. 여러 서버가 동시에 불러도 한 곳만 성공한다.

    입력: conn, run_id, now, lease_until (선점 만료 시각), max_attempts (최대 시도 횟수)
    출력: bool (선점했으면 True)
    기능: QUEUED·FAILED(재시도)이거나, RUNNING인데 선점이 만료된(서버가 중간에 죽은) 회차만 잡는다.
    """
    cursor = conn.execute(
        "UPDATE schedule_runs SET search_status = 'RUNNING', "
        "search_attempts = search_attempts + 1, lease_until = ?, started_at = ?, updated_at = ? "
        "WHERE id = ? AND search_attempts < ? AND ("
        "search_status IN ('QUEUED', 'FAILED') OR "
        "(search_status = 'RUNNING' AND lease_until < ?))",
        (
            lease_until.isoformat(),
            now.isoformat(),
            now.isoformat(),
            run_id,
            max_attempts,
            now.isoformat(),
        ),
    )
    return cursor.rowcount == 1


def list_search_candidates(
    conn: DbConnection, now: datetime, max_attempts: int, limit: int
) -> list[str]:
    """검색을 시작하거나 다시 해야 하는 회차 ID 목록.

    입력: conn, now, max_attempts, limit
    출력: run id 목록 (회차 시각 오름차순)
    기능: 서버가 꺼졌다 켜져서 남은 QUEUED·FAILED·만료된 RUNNING 회차도 다시 잡힌다.
    """
    rows = conn.execute(
        "SELECT id FROM schedule_runs WHERE search_attempts < ? AND ("
        "search_status IN ('QUEUED', 'FAILED') OR "
        "(search_status = 'RUNNING' AND lease_until < ?)) "
        "ORDER BY scheduled_for, id LIMIT ?",
        (max_attempts, now.isoformat(), limit),
    ).fetchall()
    return [str(row[0]) for row in rows]


def finish_search(
    conn: DbConnection,
    run_id: str,
    status: str,
    result_count: int | None,
    error: str | None,
    notify_status: str,
    now: datetime,
) -> None:
    """검색 단계 결과를 기록하고 다음 단계(카카오 전송) 상태를 정한다."""
    conn.execute(
        "UPDATE schedule_runs SET search_status = ?, result_count = ?, search_error = ?, "
        "finished_at = ?, notify_status = ?, lease_until = NULL, updated_at = ? WHERE id = ?",
        (status, result_count, error, now.isoformat(), notify_status, now.isoformat(), run_id),
    )


def replace_items(conn: DbConnection, run_id: str, items: list[RunItemRow]) -> None:
    """회차의 검색 결과를 저장한다(재시도로 다시 저장해도 한 벌만 남게 먼저 지운다)."""
    conn.execute("DELETE FROM schedule_run_items WHERE run_id = ?", (run_id,))
    for position, item in enumerate(items):
        conn.execute(
            "INSERT INTO schedule_run_items (run_id, position, news_id, title, source_name, url, "
            "published_at, summary_lines) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_id,
                position,
                item.news_id,
                item.title,
                item.source_name,
                item.url,
                item.published_at.isoformat(),
                item.summary_lines,
            ),
        )


def list_notify_candidates(
    conn: DbConnection, now: datetime, max_attempts: int, limit: int
) -> list[str]:
    """카카오로 보낼(또는 다시 보낼) 회차 ID 목록.

    기능: PENDING과, 재시도 시각이 된 FAILED만 고른다. UNKNOWN은 자동으로 다시 보내지 않는다.
    """
    rows = conn.execute(
        "SELECT id FROM schedule_runs WHERE notify_attempts < ? AND ("
        "notify_status = 'PENDING' OR "
        "(notify_status = 'FAILED' AND (notify_next_at IS NULL OR notify_next_at <= ?))) "
        "ORDER BY scheduled_for, id LIMIT ?",
        (max_attempts, now.isoformat(), limit),
    ).fetchall()
    return [str(row[0]) for row in rows]


def claim_notify(
    conn: DbConnection, run_id: str, now: datetime, lease_until: datetime, max_attempts: int
) -> bool:
    """전송할 회차를 선점한다. 같은 회차를 두 서버가 동시에 보내지 않게 한다."""
    cursor = conn.execute(
        "UPDATE schedule_runs SET notify_status = 'SENDING', "
        "notify_attempts = notify_attempts + 1, lease_until = ?, updated_at = ? "
        "WHERE id = ? AND notify_attempts < ? AND ("
        "notify_status = 'PENDING' OR "
        "(notify_status = 'FAILED' AND (notify_next_at IS NULL OR notify_next_at <= ?)))",
        (lease_until.isoformat(), now.isoformat(), run_id, max_attempts, now.isoformat()),
    )
    return cursor.rowcount == 1


def mark_stale_sending_unknown(conn: DbConnection, now: datetime) -> int:
    """전송 중(SENDING)에 서버가 죽어 선점이 만료된 회차를 UNKNOWN으로 바꾼다.

    기능: 실제로 카톡이 갔는지 알 수 없으므로 자동 재전송하지 않고, 사람이 확인하게 남긴다.
    """
    cursor = conn.execute(
        "UPDATE schedule_runs SET notify_status = 'UNKNOWN', "
        "notify_error = 'interrupted while sending', lease_until = NULL, updated_at = ? "
        "WHERE notify_status = 'SENDING' AND lease_until < ?",
        (now.isoformat(), now.isoformat()),
    )
    return cursor.rowcount


def finish_notify(
    conn: DbConnection,
    run_id: str,
    status: str,
    error: str | None,
    next_at: datetime | None,
    now: datetime,
) -> None:
    """카카오 전송 결과를 기록한다."""
    conn.execute(
        "UPDATE schedule_runs SET notify_status = ?, notify_error = ?, notify_next_at = ?, "
        "notified_at = CASE WHEN ? = 'SENT' THEN ? ELSE notified_at END, "
        "lease_until = NULL, updated_at = ? WHERE id = ?",
        (status, error, _iso(next_at), status, now.isoformat(), now.isoformat(), run_id),
    )


def get_run(conn: DbConnection, run_id: str) -> RunRow | None:
    """회차 하나를 읽는다."""
    row = conn.execute(
        f"SELECT {_RUN_COLUMNS} FROM schedule_runs WHERE id = ?",  # noqa: S608 - 상수 컬럼 목록
        (run_id,),
    ).fetchone()
    return None if row is None else _to_run(tuple(row))


def list_runs_for_user(conn: DbConnection, user_id: str, limit: int) -> list[RunRow]:
    """사용자의 최근 회차 목록(최신순). 항상 user_id로 묶어 다른 사람 결과는 보이지 않는다."""
    rows = conn.execute(
        f"SELECT {_RUN_COLUMNS} FROM schedule_runs WHERE user_id = ? "  # noqa: S608 - 상수 컬럼
        "ORDER BY scheduled_for DESC, id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    return [_to_run(tuple(row)) for row in rows]


def list_items(conn: DbConnection, run_id: str) -> list[RunItemRow]:
    """회차의 검색 결과 기사 목록."""
    rows = conn.execute(
        "SELECT news_id, title, source_name, url, published_at, summary_lines "
        "FROM schedule_run_items WHERE run_id = ? ORDER BY position",
        (run_id,),
    ).fetchall()
    result: list[RunItemRow] = []
    for row in rows:
        published = _dt(row[4])
        if published is None:
            continue
        result.append(
            RunItemRow(
                news_id=str(row[0]),
                title=str(row[1]),
                source_name=str(row[2]),
                url=str(row[3]),
                published_at=published,
                summary_lines=None if row[5] is None else str(row[5]),
            )
        )
    return result


def count_unseen(conn: DbConnection, user_id: str) -> int:
    """아직 보지 않은 완료 회차 수(검색이 끝난 것만)."""
    row = conn.execute(
        "SELECT COUNT(*) FROM schedule_runs WHERE user_id = ? AND seen_at IS NULL "
        "AND search_status IN ('SUCCEEDED', 'NO_RESULTS')",
        (user_id,),
    ).fetchone()
    return 0 if row is None else int(str(row[0]))


def mark_seen(conn: DbConnection, user_id: str, now: datetime) -> None:
    """사용자의 완료 회차를 모두 본 것으로 표시한다."""
    conn.execute(
        "UPDATE schedule_runs SET seen_at = ? WHERE user_id = ? AND seen_at IS NULL "
        "AND search_status IN ('SUCCEEDED', 'NO_RESULTS')",
        (now.isoformat(), user_id),
    )

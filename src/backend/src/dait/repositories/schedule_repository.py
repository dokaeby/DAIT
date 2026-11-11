"""schedules 테이블 접근. 예약은 항상 user_id와 함께 조회해 소유권을 지킨다."""

from datetime import datetime
from typing import NamedTuple

from dait.repositories.db import DbConnection


class ScheduleRow(NamedTuple):
    """schedules 한 행. criteria_json은 TEXT 원문이다."""

    id: str
    user_id: str
    local_time: str
    timezone: str
    enabled: bool
    criteria_json: str
    next_run_at: datetime | None
    created_at: datetime
    updated_at: datetime


_COLUMNS = (
    "id, user_id, local_time, timezone, enabled, criteria_json, next_run_at, created_at, updated_at"
)


def _to_row(
    row: tuple[str, str, str, str, int, str, str | None, str, str],
) -> ScheduleRow:
    """DB 행을 ScheduleRow로 바꾼다.

    입력: row (컬럼 순서대로 읽은 행)
    출력: ScheduleRow
    기능: next_run_at은 비어 있을 수 있어 None을 허용한다.
    """
    return ScheduleRow(
        id=row[0],
        user_id=row[1],
        local_time=row[2],
        timezone=row[3],
        enabled=bool(row[4]),
        criteria_json=row[5],
        next_run_at=datetime.fromisoformat(row[6]) if row[6] else None,
        created_at=datetime.fromisoformat(row[7]),
        updated_at=datetime.fromisoformat(row[8]),
    )


def list_by_user(conn: DbConnection, user_id: str) -> list[ScheduleRow]:
    """사용자의 예약 목록을 읽는다.

    입력: conn (연결), user_id (본인 id)
    출력: ScheduleRow 목록 (생성 순)
    기능: user_id 조건이 항상 붙는다.
    """
    rows = conn.execute(
        f"SELECT {_COLUMNS} FROM schedules WHERE user_id = ? ORDER BY created_at, id",  # noqa: S608 - _COLUMNS는 모듈 상수
        (user_id,),
    ).fetchall()
    return [_to_row(row) for row in rows]


def get_by_id_and_user(conn: DbConnection, user_id: str, schedule_id: str) -> ScheduleRow | None:
    """본인의 예약 한 건을 읽는다.

    입력: conn (연결), user_id (본인 id), schedule_id (경로의 예약 ID)
    출력: ScheduleRow 또는 None
    기능: id만으로 조회하지 않고 user_id를 함께 묶어 IDOR을 막는다.
    """
    row = conn.execute(
        f"SELECT {_COLUMNS} FROM schedules WHERE id = ? AND user_id = ?",  # noqa: S608 - _COLUMNS는 모듈 상수
        (schedule_id, user_id),
    ).fetchone()
    return None if row is None else _to_row(row)


def insert_schedule(conn: DbConnection, row: ScheduleRow) -> None:
    """예약 한 건을 저장한다.

    입력: conn (트랜잭션 연결), row (저장할 값)
    출력: 없음
    기능: enabled는 bool을 정수로 바꿔 저장한다.
    """
    conn.execute(
        "INSERT INTO schedules (id, user_id, local_time, timezone, enabled, "
        "criteria_json, next_run_at, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            row.id,
            row.user_id,
            row.local_time,
            row.timezone,
            row.enabled,
            row.criteria_json,
            row.next_run_at.isoformat() if row.next_run_at else None,
            row.created_at.isoformat(),
            row.updated_at.isoformat(),
        ),
    )


def update_schedule(conn: DbConnection, row: ScheduleRow) -> bool:
    """본인의 예약을 새 값으로 갱신한다.

    입력: conn (트랜잭션 연결), row (갱신할 전체 값)
    출력: bool (갱신된 행이 있었으면 True)
    기능: WHERE에 user_id를 함께 걸어 다른 사용자의 행은 절대 바꾸지 않는다.
    """
    cursor = conn.execute(
        "UPDATE schedules SET local_time = ?, timezone = ?, enabled = ?, "
        "criteria_json = ?, next_run_at = ?, updated_at = ? "
        "WHERE id = ? AND user_id = ?",
        (
            row.local_time,
            row.timezone,
            row.enabled,
            row.criteria_json,
            row.next_run_at.isoformat() if row.next_run_at else None,
            row.updated_at.isoformat(),
            row.id,
            row.user_id,
        ),
    )
    return cursor.rowcount == 1


def delete_schedule(conn: DbConnection, user_id: str, schedule_id: str) -> bool:
    """본인의 예약을 삭제한다.

    입력: conn (트랜잭션 연결), user_id (본인 id), schedule_id (예약 ID)
    출력: bool (삭제됐으면 True)
    기능: WHERE에 user_id를 함께 걸어 타인 예약 삭제를 막는다.
    """
    cursor = conn.execute(
        "DELETE FROM schedules WHERE id = ? AND user_id = ?", (schedule_id, user_id)
    )
    return cursor.rowcount == 1

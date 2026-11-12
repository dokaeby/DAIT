"""schedules 테이블 접근. 예약은 항상 user_id와 함께 조회해 소유권을 지킨다."""

import json
from datetime import date, datetime
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
    # 반복 방식: DAILY(매일) · WEEKLY(요일 선택, weekdays 월=0…일=6) · ONCE(run_date 하루)
    repeat: str = "DAILY"
    weekdays: tuple[int, ...] = ()
    run_date: date | None = None


_COLUMNS = (
    "id, user_id, local_time, timezone, enabled, criteria_json, next_run_at, created_at, "
    "updated_at, repeat, weekdays, run_date"
)
COLUMNS = _COLUMNS  # 다른 저장소(예약 실행)가 같은 컬럼 순서로 읽을 때 쓴다.


def _weekdays_json(values: tuple[int, ...]) -> str:
    """요일 목록을 저장용 JSON으로 바꾼다."""
    return json.dumps(sorted(set(values)))


def _opt(value: object) -> str | None:
    """비어 있을 수 있는 DB 값을 문자열 또는 None으로 맞춘다."""
    return None if value is None else str(value)


def row_from_db(row: tuple[object, ...]) -> ScheduleRow:
    """다른 저장소에서 SELECT {COLUMNS} 결과를 ScheduleRow로 바꿀 때 쓰는 공개 함수.

    입력: row (COLUMNS 순서의 DB 행, 드라이버마다 값 타입이 다를 수 있음)
    출력: ScheduleRow
    기능: 값을 문자열·정수로 맞춘 뒤 _to_row와 같은 규칙으로 변환한다.
    """
    return _to_row(
        (
            str(row[0]),
            str(row[1]),
            str(row[2]),
            str(row[3]),
            int(bool(row[4])),
            str(row[5]),
            _opt(row[6]),
            str(row[7]),
            str(row[8]),
            str(row[9] or "DAILY"),
            str(row[10] or "[]"),
            _opt(row[11]),
        )
    )


def _to_row(
    row: tuple[str, str, str, str, int, str, str | None, str, str, str, str, str | None],
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
        next_run_at=datetime.fromisoformat(str(row[6])) if row[6] else None,
        created_at=datetime.fromisoformat(str(row[7])),
        updated_at=datetime.fromisoformat(str(row[8])),
        repeat=str(row[9] or "DAILY"),
        weekdays=tuple(int(d) for d in json.loads(str(row[10] or "[]"))),
        run_date=date.fromisoformat(str(row[11])) if row[11] else None,
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
        "criteria_json, next_run_at, created_at, updated_at, repeat, weekdays, run_date) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
            row.repeat,
            _weekdays_json(row.weekdays),
            row.run_date.isoformat() if row.run_date else None,
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
        "criteria_json = ?, next_run_at = ?, updated_at = ?, repeat = ?, weekdays = ?, "
        "run_date = ? WHERE id = ? AND user_id = ?",
        (
            row.local_time,
            row.timezone,
            row.enabled,
            row.criteria_json,
            row.next_run_at.isoformat() if row.next_run_at else None,
            row.updated_at.isoformat(),
            row.repeat,
            _weekdays_json(row.weekdays),
            row.run_date.isoformat() if row.run_date else None,
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

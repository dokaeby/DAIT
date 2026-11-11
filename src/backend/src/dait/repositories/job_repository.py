"""jobs·job_attempts 테이블 접근. dedupe_key unique와 단계별 시도 기록을 담당한다."""

import uuid
from datetime import datetime
from typing import NamedTuple

from dait.repositories.db import DbConnection


class JobRow(NamedTuple):
    """jobs 한 행."""

    id: str
    schedule_id: str | None
    kind: str
    dedupe_key: str
    status: str
    scheduled_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


_COLUMNS = (
    "id, schedule_id, kind, dedupe_key, status, scheduled_at, started_at, finished_at, created_at"
)


def _to_row(row: tuple[str | None, ...]) -> JobRow:
    """DB 행을 JobRow로 바꾼다."""
    return JobRow(
        id=str(row[0]),
        schedule_id=str(row[1]) if row[1] is not None else None,
        kind=str(row[2]),
        dedupe_key=str(row[3]),
        status=str(row[4]),
        scheduled_at=datetime.fromisoformat(str(row[5])),
        started_at=datetime.fromisoformat(str(row[6])) if row[6] else None,
        finished_at=datetime.fromisoformat(str(row[7])) if row[7] else None,
        created_at=datetime.fromisoformat(str(row[8])),
    )


def get_by_dedupe_key(conn: DbConnection, dedupe_key: str) -> JobRow | None:
    """dedupe_key로 기존 작업을 찾는다.

    입력: conn (연결), dedupe_key (예: collect:src1:20261110)
    출력: JobRow 또는 None
    기능: 같은 키의 작업이 있으면 새 작업을 만들지 않는다(중복 수집 방지).
    """
    row = conn.execute(
        f"SELECT {_COLUMNS} FROM jobs WHERE dedupe_key = ?",  # noqa: S608 - _COLUMNS는 모듈 상수
        (dedupe_key,),
    ).fetchone()
    return None if row is None else _to_row(row)


def create_job(
    conn: DbConnection,
    schedule_id: str | None,
    kind: str,
    dedupe_key: str,
    scheduled_at: datetime,
    created_at: datetime,
) -> JobRow | None:
    """작업을 등록한다. dedupe_key 충돌이면 None을 돌려준다.

    입력: conn (트랜잭션 연결), schedule_id (예약 발이면 ID, 수동이면 None),
          kind, dedupe_key, scheduled_at·created_at (UTC)
    출력: 생성된 JobRow 또는 None (이미 같은 키의 작업이 있음)
    기능: INSERT ... ON CONFLICT DO NOTHING으로 동시 실행 경쟁에서도 한 건만 만든다.
    """
    job_id = uuid.uuid4().hex
    cursor = conn.execute(
        "INSERT INTO jobs (id, schedule_id, kind, dedupe_key, status, scheduled_at, "
        "created_at) VALUES (?, ?, ?, ?, 'PENDING', ?, ?) "
        "ON CONFLICT(dedupe_key) DO NOTHING",
        (job_id, schedule_id, kind, dedupe_key, scheduled_at.isoformat(), created_at.isoformat()),
    )
    if cursor.rowcount != 1:
        return None
    return JobRow(
        id=job_id,
        schedule_id=schedule_id,
        kind=kind,
        dedupe_key=dedupe_key,
        status="PENDING",
        scheduled_at=scheduled_at,
        started_at=None,
        finished_at=None,
        created_at=created_at,
    )


def update_status(
    conn: DbConnection,
    job_id: str,
    status: str,
    started_at: datetime | None,
    finished_at: datetime | None,
) -> None:
    """작업 상태를 갱신한다.

    입력: conn, job_id, status (허용 Enum 문자열), started_at·finished_at
    출력: 없음
    기능: 허용 상태 전이는 호출부(서비스)가 Enum으로 제한한다.
    """
    conn.execute(
        "UPDATE jobs SET status = ?, started_at = COALESCE(?, started_at), "
        "finished_at = ? WHERE id = ?",
        (
            status,
            started_at.isoformat() if started_at else None,
            finished_at.isoformat() if finished_at else None,
            job_id,
        ),
    )


def count_attempts(conn: DbConnection, job_id: str, step: str) -> int:
    """특정 단계의 누적 시도 횟수를 센다.

    입력: conn, job_id, step (예: COLLECT)
    출력: int
    기능: 최대 재시도 횟수 판정에 쓴다.
    """
    row = conn.execute(
        "SELECT COUNT(*) FROM job_attempts WHERE job_id = ? AND step = ?",
        (job_id, step),
    ).fetchone()
    return int(row[0]) if row else 0


def record_attempt(
    conn: DbConnection,
    job_id: str,
    step: str,
    attempt_no: int,
    error_code: str | None,
    created_at: datetime,
) -> None:
    """단계별 시도 결과를 기록한다.

    입력: conn, job_id, step, attempt_no, error_code (성공이면 None), created_at
    출력: 없음
    기능: (job_id, step, attempt_no) unique라 같은 번호 재기록은 실패로 드러난다.
    """
    conn.execute(
        "INSERT INTO job_attempts (id, job_id, step, attempt_no, error_code, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (uuid.uuid4().hex, job_id, step, attempt_no, error_code, created_at.isoformat()),
    )

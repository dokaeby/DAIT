"""sources 테이블 접근. 수집 대상은 enabled=1인 승인 출처뿐이다."""

import sqlite3
from datetime import datetime
from typing import NamedTuple


class SourceRow(NamedTuple):
    """sources 한 행."""

    id: str
    name: str
    kind: str
    base_url: str
    priority: int
    enabled: bool


def list_enabled(conn: sqlite3.Connection) -> list[SourceRow]:
    """활성화된 출처를 우선순위 순으로 읽는다.

    입력: conn (연결)
    출력: SourceRow 목록
    기능: 수집기는 이 목록만 대상으로 하므로 비활성 출처는 절대 읽지 않는다.
    """
    rows = conn.execute(
        "SELECT id, name, kind, base_url, priority, enabled FROM sources "
        "WHERE enabled = 1 ORDER BY priority, id"
    ).fetchall()
    return [
        SourceRow(
            id=row[0],
            name=row[1],
            kind=row[2],
            base_url=row[3],
            priority=int(row[4]),
            enabled=bool(row[5]),
        )
        for row in rows
    ]


def get_by_id(conn: sqlite3.Connection, source_id: str) -> SourceRow | None:
    """출처 한 건을 읽는다(수동 수집 지정용).

    입력: conn (연결), source_id (sources.id)
    출력: SourceRow 또는 None
    기능: enabled 여부와 무관하게 읽되 호출부가 enabled를 판단한다.
    """
    row = conn.execute(
        "SELECT id, name, kind, base_url, priority, enabled FROM sources WHERE id = ?",
        (source_id,),
    ).fetchone()
    if row is None:
        return None
    return SourceRow(
        id=row[0],
        name=row[1],
        kind=row[2],
        base_url=row[3],
        priority=int(row[4]),
        enabled=bool(row[5]),
    )


def touch_robots_checked(conn: sqlite3.Connection, source_id: str, now: datetime) -> None:
    """robots 확인 시각을 갱신한다.

    입력: conn (연결), source_id, now (UTC 시각)
    출력: 없음
    기능: 다음 수집 주기의 robots 재확인 기준 시각으로 쓴다.
    """
    conn.execute(
        "UPDATE sources SET robots_checked_at = ?, updated_at = ? WHERE id = ?",
        (now.isoformat(), now.isoformat(), source_id),
    )

"""user_settings 테이블 접근. 사용자당 1행이며 항상 user_id로 범위를 제한한다."""

import json
import sqlite3
from datetime import datetime
from typing import NamedTuple, cast


class SettingsRow(NamedTuple):
    """user_settings 한 행. JSON 컬럼은 TEXT 원문 그대로 둔다."""

    user_id: str
    default_count: int
    categories: str
    keywords: str
    source_ids: str
    in_app_notice: bool
    email_notice: bool
    created_at: datetime
    updated_at: datetime


_COLUMNS = (
    "user_id, default_count, categories, keywords, source_ids, "
    "in_app_notice, email_notice, created_at, updated_at"
)


def _to_row(
    row: tuple[str, int, str, str, str, int, int, str, str],
) -> SettingsRow:
    """DB 행을 SettingsRow로 바꾼다.

    입력: row (컬럼 순서대로 읽은 행)
    출력: SettingsRow
    기능: 시각 문자열을 datetime으로, 정수를 bool로 되돌린다.
    """
    return SettingsRow(
        user_id=row[0],
        default_count=int(row[1]),
        categories=row[2],
        keywords=row[3],
        source_ids=row[4],
        in_app_notice=bool(row[5]),
        email_notice=bool(row[6]),
        created_at=datetime.fromisoformat(row[7]),
        updated_at=datetime.fromisoformat(row[8]),
    )


def get_row(conn: sqlite3.Connection, user_id: str) -> SettingsRow | None:
    """사용자의 설정 행을 읽는다.

    입력: conn (연결), user_id (인증된 본인 id)
    출력: SettingsRow 또는 None (아직 설정을 만든 적 없을 때)
    기능: user_id 조건이 항상 붙어 타인 행은 읽지 않는다.
    """
    row = conn.execute(
        f"SELECT {_COLUMNS} FROM user_settings WHERE user_id = ?",  # noqa: S608 - _COLUMNS는 모듈 상수
        (user_id,),
    ).fetchone()
    return None if row is None else _to_row(row)


def save_row(conn: sqlite3.Connection, row: SettingsRow) -> None:
    """설정 행을 만들거나 통째로 갱신한다.

    입력: conn (트랜잭션 연결), row (저장할 전체 값)
    출력: 없음
    기능: user_id 충돌 시 UPDATE로 처리해 사용자당 1행을 유지한다.
          목록 값은 JSON 문자열로 직렬화해 TEXT 컬럼에 넣는다.
    """
    conn.execute(
        "INSERT INTO user_settings (user_id, default_count, categories, keywords, "
        "source_ids, in_app_notice, email_notice, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET "
        "default_count = excluded.default_count, "
        "categories = excluded.categories, "
        "keywords = excluded.keywords, "
        "source_ids = excluded.source_ids, "
        "in_app_notice = excluded.in_app_notice, "
        "email_notice = excluded.email_notice, "
        "updated_at = excluded.updated_at",
        (
            row.user_id,
            row.default_count,
            row.categories,
            row.keywords,
            row.source_ids,
            int(row.in_app_notice),
            int(row.email_notice),
            row.created_at.isoformat(),
            row.updated_at.isoformat(),
        ),
    )


def dumps_list(values: list[str]) -> str:
    """문자열 목록을 JSON TEXT로 직렬화한다.

    입력: values (코드·키워드·출처 ID 목록)
    출력: str (JSON 배열 문자열)
    기능: SQLite/PostgreSQL 공통으로 TEXT 컬럼에 저장하기 위한 변환이다.
    """
    return json.dumps(values, ensure_ascii=False)


def loads_list(raw: str | None) -> list[str]:
    """JSON TEXT를 문자열 목록으로 되돌린다.

    입력: raw (저장된 TEXT, None 가능)
    출력: str 목록 (파싱 실패·비목록이면 빈 목록)
    기능: 손상된 값이 응답을 깨지 않게 빈 목록으로 수렴한다.
    """
    if not raw:
        return []
    try:
        value: object = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(value, list):
        return []
    items = cast("list[object]", value)
    return [str(item) for item in items]

"""users 테이블 접근. SQL은 파라미터 바인딩(?)만 쓰고 문자열을 이어 붙이지 않는다."""

import sqlite3
from datetime import datetime

from dait.schemas.user import UserRecord, UserRole, UserStatus


class DuplicateEmailError(Exception):
    """이미 같은 이메일의 사용자가 있을 때(유니크 제약 위반)."""


def insert_user(conn: sqlite3.Connection, user: UserRecord) -> None:
    """사용자 한 명을 저장한다.

    입력: conn (열려 있는 트랜잭션 연결), user (저장할 사용자 레코드)
    출력: 없음
    기능: 이메일 유니크 제약을 어기면 DuplicateEmailError. 그 밖의 DB 오류는 그대로 올린다.
    """
    try:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, status, role, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                user.id,
                user.email,
                user.password_hash,
                user.status.value,
                user.role.value,
                user.created_at.isoformat(),
            ),
        )
    except sqlite3.IntegrityError as exc:
        if "users.email" in str(exc):
            raise DuplicateEmailError from exc
        raise


def _to_record(row: tuple[str, str, str, str, str, str]) -> UserRecord:
    """DB 행을 사용자 레코드로 바꾼다.

    입력: row (users 테이블의 컬럼 순서대로 읽은 행)
    출력: UserRecord (검증된 모델)
    기능: 저장된 문자열을 Enum과 UTC 시각으로 되돌린다.
    """
    return UserRecord(
        id=row[0],
        email=row[1],
        password_hash=row[2],
        status=UserStatus(row[3]),
        role=UserRole(row[4]),
        created_at=datetime.fromisoformat(row[5]),
    )


def find_by_email(conn: sqlite3.Connection, email: str) -> UserRecord | None:
    """이메일로 사용자를 찾는다.

    입력: conn (열려 있는 연결), email (소문자로 맞춘 이메일)
    출력: UserRecord 또는 None (없을 때)
    기능: 이메일은 저장할 때 소문자로 통일하므로 같은 형태로 비교한다.
    """
    row = conn.execute(
        "SELECT id, email, password_hash, status, role, created_at FROM users WHERE email = ?",
        (email,),
    ).fetchone()
    return None if row is None else _to_record(row)


def find_by_id(conn: sqlite3.Connection, user_id: str) -> UserRecord | None:
    """id로 사용자를 찾는다.

    입력: conn (열려 있는 연결), user_id (토큰에서 꺼낸 사용자 id)
    출력: UserRecord 또는 None (탈퇴했거나 없을 때)
    기능: 탈퇴한 사용자의 남은 access 토큰을 거부하는 데 쓴다.
    """
    row = conn.execute(
        "SELECT id, email, password_hash, status, role, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    return None if row is None else _to_record(row)


def delete_user(conn: sqlite3.Connection, user_id: str) -> bool:
    """사용자를 실제로 삭제한다.

    입력: conn (열려 있는 트랜잭션 연결), user_id (삭제할 사용자 id)
    출력: bool (지웠으면 True)
    기능: 외래키 CASCADE로 refresh 토큰도 함께 지워진다. 비식별화가 아니라 행 삭제다.
    """
    return conn.execute("DELETE FROM users WHERE id = ?", (user_id,)).rowcount == 1

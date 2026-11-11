"""refresh_tokens 테이블 접근. 토큰 원문은 받지도 저장하지도 않는다."""

import sqlite3
from datetime import datetime

from dait.schemas.token import RefreshTokenRecord, StoredRefreshToken


def insert_refresh_token(conn: sqlite3.Connection, record: RefreshTokenRecord) -> None:
    """refresh 토큰 해시 한 건을 저장한다.

    입력: conn (열려 있는 트랜잭션 연결), record (해시와 만료 시각을 담은 레코드)
    출력: 없음
    기능: user_id가 users에 없으면 외래키 위반으로 sqlite3.IntegrityError가 올라간다.
    """
    conn.execute(
        "INSERT INTO refresh_tokens (id, user_id, family_id, token_hash, expires_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            record.id,
            record.user_id,
            record.family_id,
            record.token_hash,
            record.expires_at.isoformat(),
            record.created_at.isoformat(),
        ),
    )


def find_by_hash(conn: sqlite3.Connection, token_hash: str) -> StoredRefreshToken | None:
    """토큰 해시로 저장된 refresh 토큰을 찾는다.

    입력: conn (열려 있는 연결), token_hash (요청으로 받은 토큰의 SHA-256)
    출력: StoredRefreshToken 또는 None (없을 때)
    기능: token_hash 컬럼에 유니크 인덱스가 있어 한 번에 찾는다.
    """
    row = conn.execute(
        "SELECT id, user_id, family_id, expires_at, revoked_at FROM refresh_tokens "
        "WHERE token_hash = ?",
        (token_hash,),
    ).fetchone()
    if row is None:
        return None
    return StoredRefreshToken(
        id=row[0],
        user_id=row[1],
        family_id=row[2],
        expires_at=datetime.fromisoformat(row[3]),
        revoked_at=datetime.fromisoformat(row[4]) if row[4] else None,
    )


def revoke_if_active(conn: sqlite3.Connection, token_id: str, now: datetime) -> bool:
    """아직 폐기되지 않은 토큰 하나를 폐기한다.

    입력: conn (열려 있는 트랜잭션 연결), token_id (토큰 행 id), now (UTC 시각)
    출력: bool (이 호출이 폐기했으면 True, 이미 폐기돼 있었으면 False)
    기능: 조건부 UPDATE라 같은 토큰으로 동시에 요청해도 한 번만 성공한다.
    """
    cursor = conn.execute(
        "UPDATE refresh_tokens SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL",
        (now.isoformat(), token_id),
    )
    return cursor.rowcount == 1


def revoke_family(conn: sqlite3.Connection, family_id: str, now: datetime) -> int:
    """같은 로그인 계열(family)의 살아 있는 토큰을 모두 폐기한다.

    입력: conn (열려 있는 트랜잭션 연결), family_id (계열 id), now (UTC 시각)
    출력: int (새로 폐기한 개수)
    기능: 폐기된 토큰이 재사용되면 도난으로 보고 그 계열 전체를 막는다.
    """
    cursor = conn.execute(
        "UPDATE refresh_tokens SET revoked_at = ? WHERE family_id = ? AND revoked_at IS NULL",
        (now.isoformat(), family_id),
    )
    return cursor.rowcount


def revoke_all_for_user(conn: sqlite3.Connection, user_id: str, now: datetime) -> int:
    """한 사용자의 살아 있는 refresh 토큰을 모두 폐기한다.

    입력: conn (열려 있는 트랜잭션 연결), user_id (사용자 id), now (UTC 시각)
    출력: int (새로 폐기한 개수, 이미 없으면 0)
    기능: 로그아웃에서 쓴다. 두 번 불러도 오류 없이 0을 돌려준다(멱등).
    """
    cursor = conn.execute(
        "UPDATE refresh_tokens SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
        (now.isoformat(), user_id),
    )
    return cursor.rowcount

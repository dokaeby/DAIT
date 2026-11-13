"""users 테이블 접근. SQL은 파라미터 바인딩(?)만 쓰고 문자열을 이어 붙이지 않는다."""

from datetime import datetime

from psycopg.errors import UniqueViolation

from dait.repositories.db import DB_INTEGRITY_ERRORS, DbConnection
from dait.schemas.user import UserRecord, UserRole, UserStatus


class DuplicateEmailError(Exception):
    """이미 같은 이메일의 사용자가 있을 때(유니크 제약 위반)."""


class DuplicateNicknameError(Exception):
    """중복 확인 이후 동시에 같은 닉네임으로 가입한 경우도 차단한다."""


# 입력: 열린 DB 연결과 정규화된 닉네임.
# 출력: 같은 닉네임의 존재 여부.
# 동작: 대소문자를 구분하지 않는 비교 키로 중복 닉네임을 조회한다.
def nickname_exists(conn: DbConnection, nickname: str) -> bool:
    """정규화된 닉네임을 대소문자 구분 없이 비교한다.

    입력: conn (열린 DB 연결), nickname (정규화된 닉네임)
    출력: bool (같은 닉네임이 있으면 True)
    기능: nickname_key를 기준으로 중복 닉네임을 조회한다.
    """
    return (
        conn.execute(
            "SELECT 1 FROM users WHERE nickname_key = ?", (nickname.casefold(),)
        ).fetchone()
        is not None
    )


# 입력: 열린 DB 연결, 사용자 ID, 새 닉네임.
# 출력: 반환값 없음.
# 동작: 닉네임과 비교 키를 함께 갱신하고 중복 오류를 도메인 예외로 변환한다.
def update_nickname(conn: DbConnection, user_id: str, nickname: str | None) -> None:
    """닉네임과 비교 키를 함께 갱신한다.

    입력: conn (열린 DB 연결), user_id (사용자 ID), nickname (새 닉네임 또는 None)
    출력: 없음
    기능: 유니크 제약 위반을 DuplicateNicknameError로 변환한다.
    """
    try:
        conn.execute(
            "UPDATE users SET nickname = ?, nickname_key = ? WHERE id = ?",
            (nickname, nickname.casefold() if nickname else None, user_id),
        )
    except DB_INTEGRITY_ERRORS as exc:
        if "nickname_key" in str(exc):
            raise DuplicateNicknameError from exc
        raise


# 입력: 열린 DB 연결과 저장할 사용자 레코드.
# 출력: 반환값 없음.
# 동작: 사용자를 저장하고 이메일·닉네임 고유 제약 오류를 도메인 예외로 변환한다.
def insert_user(conn: DbConnection, user: UserRecord) -> None:
    """사용자 한 명을 저장한다.

    입력: conn (열려 있는 트랜잭션 연결), user (저장할 사용자 레코드)
    출력: 없음
    기능: 이메일 유니크 제약을 어기면 DuplicateEmailError. 그 밖의 DB 오류는 그대로 올린다.
    """
    try:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, status, role, created_at, "
            "nickname, nickname_key) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user.id,
                user.email,
                user.password_hash,
                user.status.value,
                user.role.value,
                user.created_at.isoformat(),
                user.nickname,
                user.nickname.casefold() if user.nickname else None,
            ),
        )
    except DB_INTEGRITY_ERRORS as exc:
        if "nickname_key" in str(exc):
            raise DuplicateNicknameError from exc
        # PostgreSQL은 제약 이름을, SQLite는 오류 문자열을 제공하므로 각 드라이버의 정보를 쓴다.
        email_conflict = (
            exc.diag.constraint_name == "users_email_key"
            if isinstance(exc, UniqueViolation)
            else "users.email" in str(exc)
        )
        if email_conflict:
            raise DuplicateEmailError from exc
        raise


# 입력: users 테이블에서 조회한 행.
# 출력: 검증된 사용자 레코드.
# 동작: 문자열 상태·역할·시각 값을 도메인 타입으로 변환한다.
def _to_record(row: tuple[str, str, str | None, str, str, str, str | None]) -> UserRecord:
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
        nickname=row[6],
    )


# 입력: 열린 DB 연결과 정규화된 이메일.
# 출력: 사용자 레코드 또는 없음.
# 동작: 이메일이 일치하는 사용자 한 명을 조회한다.
def find_by_email(conn: DbConnection, email: str) -> UserRecord | None:
    """이메일로 사용자를 찾는다.

    입력: conn (열려 있는 연결), email (소문자로 맞춘 이메일)
    출력: UserRecord 또는 None (없을 때)
    기능: 이메일은 저장할 때 소문자로 통일하므로 같은 형태로 비교한다.
    """
    row = conn.execute(
        "SELECT id, email, password_hash, status, role, created_at, nickname "
        "FROM users WHERE email = ?",
        (email,),
    ).fetchone()
    return None if row is None else _to_record(row)


# 입력: 열린 DB 연결과 사용자 ID.
# 출력: 사용자 레코드 또는 없음.
# 동작: ID가 일치하는 사용자 한 명을 조회한다.
def find_by_id(conn: DbConnection, user_id: str) -> UserRecord | None:
    """id로 사용자를 찾는다.

    입력: conn (열려 있는 연결), user_id (토큰에서 꺼낸 사용자 id)
    출력: UserRecord 또는 None (탈퇴했거나 없을 때)
    기능: 탈퇴한 사용자의 남은 access 토큰을 거부하는 데 쓴다.
    """
    row = conn.execute(
        "SELECT id, email, password_hash, status, role, created_at, nickname "
        "FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    return None if row is None else _to_record(row)


# 입력: 열린 DB 연결과 삭제할 사용자 ID.
# 출력: 사용자 삭제 성공 여부.
# 동작: 사용자와 삭제를 막는 예약 작업을 정리하고 사용자 행을 삭제한다.
def delete_user(conn: DbConnection, user_id: str) -> bool:
    """사용자를 실제로 삭제한다.

    입력: conn (열려 있는 트랜잭션 연결), user_id (삭제할 사용자 id)
    출력: bool (지웠으면 True)
    기능: 외래키 CASCADE로 refresh 토큰도 함께 지워진다. 비식별화가 아니라 행 삭제다.
    """
    # 예약 작업의 외래키는 RESTRICT이므로 해당 사용자의 작업을 먼저 정리한다.
    conn.execute(
        "DELETE FROM jobs WHERE schedule_id IN (SELECT id FROM schedules WHERE user_id = ?)",
        (user_id,),
    )
    return conn.execute("DELETE FROM users WHERE id = ?", (user_id,)).rowcount == 1

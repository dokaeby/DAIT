"""social_identities 테이블 접근. SQL은 파라미터 바인딩(?)만 쓴다."""

from dait.repositories.db import DB_INTEGRITY_ERRORS, DbConnection
from dait.schemas.social import SocialIdentityRecord, SocialProvider


class DuplicateIdentityError(Exception):
    """같은 (공급자, subject)가 이미 연결돼 있을 때(동시 최초 가입 경합 포함)."""


# 입력: 열린 DB 연결과 저장할 연결 레코드.
# 출력: 반환값 없음.
# 동작: 연결을 저장하고 유니크 제약 위반을 도메인 예외로 바꾼다.
def insert_identity(conn: DbConnection, record: SocialIdentityRecord) -> None:
    """소셜 연결 한 건을 저장한다.

    입력: conn (열려 있는 트랜잭션 연결), record (저장할 연결 레코드)
    출력: 없음
    기능: (provider, subject) 또는 (user_id, provider) 중복이면 DuplicateIdentityError.
    """
    try:
        conn.execute(
            "INSERT INTO social_identities (id, user_id, provider, subject, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                record.id,
                record.user_id,
                record.provider.value,
                record.subject,
                record.created_at.isoformat(),
            ),
        )
    except DB_INTEGRITY_ERRORS as exc:
        if "social_identities" in str(exc):
            raise DuplicateIdentityError from exc
        raise


# 입력: 열린 DB 연결, 공급자, 공급자가 준 사용자 고유값(subject).
# 출력: 연결된 사용자 ID 또는 없음.
# 동작: (provider, subject)로 연결된 사용자를 한 번에 조회한다.
def find_user_id(conn: DbConnection, provider: SocialProvider, subject: str) -> str | None:
    """공급자 계정에 연결된 우리 사용자 id를 찾는다.

    입력: conn (열려 있는 연결), provider (공급자), subject (구글 sub 값)
    출력: str 또는 None (연결이 없을 때)
    기능: 이메일이 아니라 불변 값인 sub로만 계정을 찾는다(이메일 자동 병합 금지).
    """
    row = conn.execute(
        "SELECT user_id FROM social_identities WHERE provider = ? AND subject = ?",
        (provider.value, subject),
    ).fetchone()
    return None if row is None else str(row[0])


# 입력: 열린 DB 연결, 사용자 ID, 공급자.
# 출력: 이미 그 공급자 계정이 연결돼 있는지 여부.
# 동작: (user_id, provider)로 연결 존재를 조회한다.
def has_identity(conn: DbConnection, user_id: str, provider: SocialProvider) -> bool:
    """사용자에게 해당 공급자 계정이 이미 연결돼 있는지 확인한다.

    입력: conn (열려 있는 연결), user_id (사용자 id), provider (공급자)
    출력: bool (연결돼 있으면 True)
    기능: 다른 구글 계정이 이미 붙은 사용자에게 새 연결 표를 주지 않기 위해 쓴다.
    """
    row = conn.execute(
        "SELECT 1 FROM social_identities WHERE user_id = ? AND provider = ?",
        (user_id, provider.value),
    ).fetchone()
    return row is not None

"""신규 계정의 첫 로그인 안내를 트랜잭션 안에서 한 번만 소비한다."""

from dait.repositories.db import DbConnection


def enroll(conn: DbConnection, user_id: str) -> None:
    """계정 생성과 함께 안내 대상을 등록한다."""
    conn.execute("INSERT INTO pending_interest_onboarding (user_id) VALUES (?)", (user_id,))


def consume(conn: DbConnection, user_id: str) -> bool:
    """동시 로그인에서도 한 응답만 안내를 받도록 원자적으로 삭제한다."""
    row = conn.execute(
        "DELETE FROM pending_interest_onboarding WHERE user_id = ? RETURNING user_id", (user_id,)
    ).fetchone()
    return row is not None

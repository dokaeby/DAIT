"""신규 계정의 첫 로그인 안내를 트랜잭션 안에서 한 번만 소비한다."""

from dait.repositories.db import DbConnection


# 입력: 열린 DB 연결과 신규 사용자 ID.
# 출력: 반환값 없음.
# 동작: 신규 사용자를 관심사 선택 안내 대상으로 등록한다.
def enroll(conn: DbConnection, user_id: str) -> None:
    """신규 사용자를 관심사 안내 대상으로 등록한다.

    입력: conn (열린 DB 연결), user_id (신규 사용자 ID)
    출력: 없음
    기능: 계정 생성 트랜잭션에서 일회성 안내 대상을 저장한다.
    """
    conn.execute("INSERT INTO pending_interest_onboarding (user_id) VALUES (?)", (user_id,))


# 입력: 열린 DB 연결과 로그인 사용자 ID.
# 출력: 이번 로그인에서 안내를 표시할지 여부.
# 동작: 안내 대상을 원자적으로 삭제해 최초 로그인 한 번만 참을 반환한다.
def consume(conn: DbConnection, user_id: str) -> bool:
    """로그인 사용자의 일회성 관심사 안내를 소비한다.

    입력: conn (열린 DB 연결), user_id (로그인 사용자 ID)
    출력: bool (이번 응답에 안내가 필요하면 True)
    기능: 동시 로그인에서도 DELETE RETURNING으로 한 응답만 안내받게 한다.
    """
    row = conn.execute(
        "DELETE FROM pending_interest_onboarding WHERE user_id = ? RETURNING user_id", (user_id,)
    ).fetchone()
    return row is not None

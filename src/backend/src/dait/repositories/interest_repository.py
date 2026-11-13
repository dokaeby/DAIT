"""user_interests 테이블 접근. 코드 값 검증은 호출하는 쪽의 Pydantic 모델이 끝낸 상태다."""

from dait.repositories.db import DbConnection


# 입력: 열린 DB 연결과 사용자 ID.
# 출력: 사용자가 선택한 관심사 코드 목록.
# 동작: 해당 사용자에게 속한 관심사 코드만 조회한다.
def list_codes(conn: DbConnection, user_id: str) -> list[str]:
    """한 사용자의 관심사 코드를 읽는다.

    입력: conn (열려 있는 연결), user_id (토큰에서 얻은 본인 id)
    출력: list[str] (코드 문자열, 순서는 보장하지 않음)
    기능: 항상 user_id 조건이 붙어 다른 사용자의 행은 읽지 않는다.
    """
    rows = conn.execute(
        "SELECT interest_code FROM user_interests WHERE user_id = ?", (user_id,)
    ).fetchall()
    return [row[0] for row in rows]


# 입력: 열린 DB 연결, 사용자 ID, 새 관심사 코드 목록.
# 출력: 반환값 없음.
# 동작: 트랜잭션 안에서 기존 관심사를 새 목록으로 교체한다.
def replace_codes(conn: DbConnection, user_id: str, codes: list[str]) -> None:
    """한 사용자의 관심사를 주어진 목록으로 통째로 바꾼다.

    입력: conn (열려 있는 트랜잭션 연결), user_id (본인 id),
          codes (중복 없는 코드 목록, 빈 목록 가능)
    출력: 없음
    기능: 기존 행을 지우고 새로 넣는다. 호출하는 쪽의 트랜잭션 안에서 실행되므로
          중간에 실패하면 이전 값이 그대로 남는다.
    """
    conn.execute("DELETE FROM user_interests WHERE user_id = ?", (user_id,))
    conn.executemany(
        "INSERT INTO user_interests (user_id, interest_code) VALUES (?, ?)",
        [(user_id, code) for code in codes],
    )

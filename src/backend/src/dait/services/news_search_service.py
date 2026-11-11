"""FR-SEARCH-01 검색어 정규화. DB 접근은 하지 않는 순수 규칙만 둔다."""

MAX_QUERY_LENGTH = 100


def normalize_query(raw: str) -> str:
    """검색어를 정규화한다.

    입력: raw (사용자가 입력한 검색어)
    출력: str (앞뒤 공백 제거·연속 공백을 하나로 줄인 문자열, 빈 값이면 "")
    기능: 빈 문자열은 전체 목록 조회로 처리하기 위해 서비스가 구분한다.
          길이 상한은 라우트의 Query(max_length=100)가 먼저 강제한다.
    """
    return " ".join(raw.split())

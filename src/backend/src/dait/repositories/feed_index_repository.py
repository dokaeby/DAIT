"""news_topics·news_classified 저장소: 기사 주제 분류 결과의 읽기·쓰기.

분류 자체(키워드 매칭)는 services/feed_index_service가 담당하고,
이 모듈은 후보 조회와 결과 저장만 담당한다.
"""

from dait.repositories.db import DbConnection
from dait.schemas.news import ACTIVE_CATEGORIES, PUBLIC_STATUSES

_STATUS_VALUES = tuple(sorted(status.value for status in PUBLIC_STATUSES))
_CATEGORY_VALUES = tuple(sorted(category.value for category in ACTIVE_CATEGORIES))


def _in_clause(values: tuple[str, ...]) -> str:
    return "(" + ", ".join("?" for _ in values) + ")"


def list_classification_candidates(
    conn: DbConnection, limit: int
) -> list[tuple[str, str, str | None, str]]:
    """분류가 없거나 콘텐츠 갱신 이후 재분류가 필요한 공개 기사를 읽는다.

    입력: conn (연결), limit (한 번에 가져올 최대 건수)
    출력: (news_id, title, summary_lines 원문, content_updated_at) 목록
    기능: 공개 상태·활성 카테고리·https URL 조건은 목록 조회와 동일하게 적용한다.
          최신 기사부터 처리해 화면에 먼저 보이는 기사가 우선 분류된다.
    """
    # content_updated_at은 varchar로 저장하므로 timestamptz 컬럼과 직접 비교할 수
    # 없다(PostgreSQL은 varchar < timestamptz 연산자가 없다). 비교·저장 모두
    # 같은 TEXT 표현으로 맞춘다.
    rows = conn.execute(
        "SELECT n.id, n.title, c.summary_lines, CAST(c.updated_at AS TEXT) "  # noqa: S608 - 상수 절만 결합
        "FROM news n "
        "JOIN content_results c ON c.news_id = n.id "
        "LEFT JOIN news_classified nc ON nc.news_id = n.id "
        f"WHERE c.status IN {_in_clause(_STATUS_VALUES)} "
        "AND n.canonical_url LIKE 'https://%' "
        f"AND n.category IN {_in_clause(_CATEGORY_VALUES)} "
        "AND (nc.news_id IS NULL OR nc.content_updated_at < CAST(c.updated_at AS TEXT)) "
        "ORDER BY n.published_at DESC LIMIT ?",
        (*_STATUS_VALUES, *_CATEGORY_VALUES, limit),
    ).fetchall()
    return [(row[0], row[1], row[2], row[3]) for row in rows]


def apply_classification(
    conn: DbConnection,
    news_id: str,
    topic_codes: tuple[str, ...],
    content_updated_at: str,
    classified_at: str,
) -> None:
    """한 기사의 분류 결과를 저장한다(기존 결과는 교체).

    입력: conn, news_id, topic_codes (매칭된 주제 코드),
          content_updated_at (분류 기준이 된 content_results.updated_at),
          classified_at (분류 시각 ISO 문자열)
    출력: 없음
    기능: 주제가 하나도 없는 기사도 news_classified에 기록해
          다음 스윕에서 다시 훑지 않게 한다.
    """
    conn.execute("DELETE FROM news_topics WHERE news_id = ?", (news_id,))
    for code in topic_codes:
        conn.execute(
            "INSERT INTO news_topics (news_id, topic_code) VALUES (?, ?) ON CONFLICT DO NOTHING",
            (news_id, code),
        )
    conn.execute(
        "INSERT INTO news_classified (news_id, content_updated_at, classified_at) "
        "VALUES (?, ?, ?) "
        "ON CONFLICT(news_id) DO UPDATE SET "
        "content_updated_at = excluded.content_updated_at, "
        "classified_at = excluded.classified_at",
        (news_id, content_updated_at, classified_at),
    )

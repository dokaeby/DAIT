"""FR-PIPE-03 관련 뉴스: 저장된 관계를 API 계약으로 변환한다.

관계 생성(키워드·유사도 규칙)은 수집 파이프라인 단계에서 수행하고,
여기서는 이미 저장된 `news_relations`만 읽는다.
"""

from dait.repositories import news_repository
from dait.repositories.db import DbConnection
from dait.schemas.news import RelatedNewsItem

MAX_RELATED = 5


def list_related(conn: DbConnection, news_id: str) -> list[RelatedNewsItem]:
    """기준 뉴스의 관련 뉴스를 점수 순으로 돌려준다.

    입력: conn (연결), news_id (상세를 보는 뉴스 ID)
    출력: RelatedNewsItem 목록 (최대 5건)
    기능: 저장소가 자기 자신·비공개 기사를 이미 제외한다.
          score는 0~1로 클램프해 계약 범위를 지킨다.
    """
    rows = news_repository.list_related_news(conn, news_id, MAX_RELATED)
    return [
        RelatedNewsItem(
            id=row.id,
            title=row.title,
            source_name=row.source_name,
            published_at=row.published_at,
            reason=row.reason,
            score=min(max(row.score, 0.0), 1.0),
        )
        for row in rows
    ]

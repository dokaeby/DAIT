"""서버 시작 준비 단계에서 기존 공용 결과를 통합 DB에 연결한다."""

from dait.core.config import Settings
from dait.repositories.db import transaction
from dait.repositories.legacy_news_repository import insert_result, read_results


def import_saved_news(settings: Settings) -> None:
    """원본이 있을 때만 처리한다. 조회 요청에서는 수집·LLM을 호출하지 않는다."""
    if not settings.legacy_news_db.is_file():
        return
    with transaction(settings.database_url) as conn:
        for item in read_results(settings.legacy_news_db):
            insert_result(conn, item)

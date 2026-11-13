"""기사 주제 분류를 1회 계산해 news_topics에 저장한다.

배경: 관심사·주제 메뉴를 선택할 때마다 요청 경로에서 키워드 LIKE 검색을
다시 실행하면 카테고리 수 x 관심사 수만큼 무거운 질의가 발생한다.
대신 로그인 세션 확인과 파이프라인 동기화 시 request_classify가
백그라운드로 아직 분류되지 않은 기사를 한 번 분류해 DB에 저장하고,
이후 카테고리·주제 조회는 저장된 결과만 읽는다.
"""

import logging
import threading
import time
from datetime import UTC, datetime

from dait.core.config import Settings
from dait.repositories import feed_index_repository
from dait.repositories.db import DbConnection, transaction
from dait.repositories.interest_matching import matching_codes

logger = logging.getLogger(__name__)

_CLASSIFY_INTERVAL_SECONDS = 60.0
_BATCH_SIZE = 500
_MAX_BATCHES = 50

_lock = threading.Lock()
_state = {"last_classify_monotonic": 0.0}
_workers: list[threading.Thread] = []


def request_classify(settings: Settings) -> None:
    """분류 스윕을 백그라운드로 예약한다(요청 경로를 막지 않는다).

    입력: settings (데이터베이스 URL)
    출력: 없음
    기능: 간격이 지나지 않았거나 이미 워커가 돌고 있으면 즉시 반환한다.
          분류 실패는 로그만 남기고 API 응답에 영향을 주지 않는다.
    """
    now = time.monotonic()
    if now - _state["last_classify_monotonic"] < _CLASSIFY_INTERVAL_SECONDS:
        return
    with _lock:
        now = time.monotonic()
        if now - _state["last_classify_monotonic"] < _CLASSIFY_INTERVAL_SECONDS:
            return
        if _workers and _workers[0].is_alive():
            return
        _state["last_classify_monotonic"] = now
        _workers[:] = [threading.Thread(target=_run_classification, args=(settings,), daemon=True)]
        _workers[0].start()


def classify_pending(conn: DbConnection) -> int:
    """분류가 필요 없는 기사가 없어질 때까지 배치로 분류한다.

    입력: conn (호출자가 연 트랜잭션 연결)
    출력: 이번 호출에서 분류한 기사 수
    기능: content_results.updated_at이 마지막 분류 이후 바뀐 기사는
          주제 결과를 교체해 재처리 결과가 반영되게 한다.
    """
    processed = 0
    classified_at = datetime.now(UTC).isoformat()
    for _ in range(_MAX_BATCHES):
        rows = feed_index_repository.list_classification_candidates(conn, _BATCH_SIZE)
        if not rows:
            break
        for news_id, title, summary_lines, content_updated_at in rows:
            text = f"{title or ''}\n{summary_lines or ''}"
            feed_index_repository.apply_classification(
                conn, news_id, matching_codes(text), content_updated_at, classified_at
            )
        processed += len(rows)
        if len(rows) < _BATCH_SIZE:
            break
    return processed


def _run_classification(settings: Settings) -> None:
    try:
        with transaction(settings.database_url) as conn:
            processed = classify_pending(conn)
        if processed:
            logger.info("뉴스 주제 분류 완료: %d건", processed)
    except Exception:
        logger.warning("뉴스 주제 분류 실패", exc_info=True)

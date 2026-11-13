"""FR-HOME-01 랭킹 카드: 저장된 공개 결과를 목록 계약으로 조립한다.

화면 요청 경로에서 크롤링·LLM을 호출하지 않고 DB의 저장 결과만 읽는다.
"""

import re
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from dait.core.config import Settings
from dait.core.errors import ValidationFailedError
from dait.repositories import news_repository
from dait.repositories.db import transaction
from dait.repositories.interest_matching import MATCHING_VERSION
from dait.schemas.news import (
    ContentStatus,
    NewsCategory,
    NewsListItem,
    NewsListMeta,
    NewsListResponse,
    PageInfo,
    ProcessingStatus,
    SortOrder,
    decode_cursor,
    encode_cursor,
)
from dait.services import (
    cache_retry_service,
    feed_index_service,
    news_search_service,
    pipeline_sync_service,
)

_PARTIAL_WINDOW = timedelta(hours=24)
_PARTIAL_MESSAGE = "일부 출처의 수집이 지연되고 있습니다."
# rank도 최신→과거가 최우선이다. 품질·출처 우선순위는 동률 보조 정렬이다.
_RANK_BASIS = ["published_at", "quality", "source_priority", "id"]
_LATEST_BASIS = ["published_at", "id"]


def _processing_status(raw: str) -> ProcessingStatus:
    """DB 상태 문자열을 API 처리 상태로 변환한다.

    입력: raw (content_results.status)
    출력: ProcessingStatus
    기능: 공개 필터를 통과한 값만 들어오지만 알 수 없는 값은 PENDING으로 수렴한다.
    """
    try:
        status = ContentStatus(raw)
    except ValueError:
        return "PENDING"
    if status is ContentStatus.READY:
        return "READY"
    if status is ContentStatus.INSUFFICIENT:
        return "INSUFFICIENT"
    return "PENDING"


def _to_item(row: news_repository.NewsListRow, rank: int) -> NewsListItem | None:
    """조회 행을 카드 모델로 바꾼다.

    입력: row (저장소 행), rank (전체 결과 기준 순위)
    출력: NewsListItem 또는 None (공개 URL이 https가 아니면 제외)
    기능: 계약상 원문은 HTTPS만 허용하므로 어긋난 행은 목록에서 뺀다.
    """
    if not row.canonical_url.startswith("https://"):
        return None
    status = _processing_status(row.status)
    return NewsListItem(
        original_language=row.original_language,
        author_name=_author_name(row.author_text),
        id=row.id,
        rank=rank,
        title=row.title.split("|||", 1)[0].strip() if row.original_language != "ko" else row.title,
        source_name=row.source_name,
        published_at=row.published_at,
        category=NewsCategory(row.category),
        summary_lines=news_repository.parse_summary_lines(row.summary_lines),
        processing_status=status,
        original_url=row.canonical_url,
        is_partial=status != "READY",
    )


def list_news(
    settings: Settings,
    category: NewsCategory | None,
    query: str,
    sort: SortOrder,
    page_size: int,
    cursor: str | None,
    now: datetime | None = None,
    interests: tuple[str, ...] | None = None,
    language: str | None = None,
    refresh: bool = False,
) -> NewsListResponse:
    """뉴스 목록을 조회한다(캐시 우선).

    입력: settings (앱 설정), category·query·sort·page_size·cursor (검증된 요청 값),
          now (테스트용 현재 시각, None이면 UTC 현재)
    출력: NewsListResponse (items, page, meta)
    기능: 커서는 불투명 offset 문자열이다. 형식이 어긋나면 422.
          목록·상세 조회는 저장 결과만 읽고 AI 작업을 만들지 않는다.
          Redis(또는 메모리 fallback) 캐시 5분+jitter, 락으로 stampede를 막는다.
    """
    pipeline_sync_service.request_sync(settings)
    feed_index_service.request_classify(settings)
    normalized = news_search_service.normalize_query(query)
    scope_key = sha256(
        repr((MATCHING_VERSION, settings.database_url, language, interests)).encode()
    ).hexdigest()[:24]
    cache_key = cache_retry_service.list_cache_key(
        scope_key + ":" + (category.value if category is not None else "ALL"),
        normalized,
        sort,
        page_size,
        cursor,
    )
    hit = cache_retry_service.load_cached(settings, cache_key, NewsListResponse)
    if hit is not None and not refresh:
        return hit
    with cache_retry_service.locked(settings, cache_key, cache_key) as acquired:
        if not acquired:
            hit = cache_retry_service.load_cached(settings, cache_key, NewsListResponse)
            if hit is not None and not refresh:
                return hit
        response = _list_news_uncached(
            settings, category, normalized, sort, page_size, cursor, now, interests, language
        )
        cache_retry_service.cache_set(
            settings, cache_key, response.model_dump_json(), cache_retry_service.list_ttl()
        )
        return response


def _list_news_uncached(
    settings: Settings,
    category: NewsCategory | None,
    normalized: str,
    sort: SortOrder,
    page_size: int,
    cursor: str | None,
    now: datetime | None,
    interests: tuple[str, ...] | None = None,
    language: str | None = None,
) -> NewsListResponse:
    """캐시를 거치지 않는 실제 목록 조회 본체."""
    try:
        offset = decode_cursor(cursor) if cursor else 0
    except ValueError as exc:
        raise ValidationFailedError from exc
    current = now if now is not None else datetime.now(UTC)
    since_iso = (current - _PARTIAL_WINDOW).isoformat()

    with transaction(settings.database_url) as conn:
        rows = news_repository.list_public_news(
            conn,
            category.value if category is not None else None,
            normalized,
            sort,
            page_size + 1,
            offset,
            interests,
            language,
        )
        total = news_repository.count_public_news(
            conn, category.value if category is not None else None, normalized, interests, language
        )
        partial = news_repository.has_recent_job_failures(conn, since_iso)

    has_more = len(rows) > page_size
    page_rows = rows[:page_size]
    items = [
        item
        for item in (_to_item(row, offset + index + 1) for index, row in enumerate(page_rows))
        if item is not None
    ]
    next_offset = offset + len(page_rows)
    return NewsListResponse(
        items=items,
        page=PageInfo(
            next_cursor=encode_cursor(next_offset) if has_more else None,
            has_more=has_more,
        ),
        meta=NewsListMeta(
            total_visible=total,
            partial=partial,
            message=_PARTIAL_MESSAGE if partial else None,
            rank_basis=list(_RANK_BASIS if sort == "rank" else _LATEST_BASIS),
        ),
    )


def _author_name(text: str | None) -> str | None:
    """Display only an explicit byline; never infer a reporter from article entities."""
    if not text:
        return None
    match = re.search(r"(?:^|[\n\r\[(])\s*([가-힣]{2,5})\s*기자(?:[\s\]):]|$)", text[:2000])
    if match:
        return match.group(1) + " 기자"
    match = re.search(r"(?im)^by\s+([A-Z][a-z]+(?:[ -][A-Z][a-z]+){1,3})\b", text[:2000])
    return match.group(1) if match else None

"""FR-DETAIL-01 뉴스 상세: 저장된 기사·콘텐츠·관계 결과를 계약으로 조립한다."""

from dait.core.article_language import needs_translation
from dait.core.config import Settings
from dait.core.errors import NewsNotFoundError
from dait.repositories import news_repository
from dait.repositories.db import transaction
from dait.schemas.news import (
    ArticleInfo,
    ContentInfo,
    NewsCategory,
    NewsDetailResponse,
    ProcessingInfo,
    ProcessingStatus,
    SourceInfo,
)
from dait.services import cache_retry_service, ranking_relation_service

_READ_MINUTES_PER_CHARS = 400  # 분당 대략적 독서량. 실제 계산값이 있을 때만 노출한다.


def _estimate_read_minutes(extracted_text: str | None) -> int | None:
    """정제 본문 길이로 읽기 시간(분)을 어림한다.

    입력: extracted_text (정제된 기사 텍스트, 없을 수 있음)
    출력: int 또는 None (본문이 없으면 None)
    기능: 화면의 표시용 추정치이며 원문 전체를 노출하지 않는다.
    """
    if not extracted_text:
        return None
    return max(1, len(extracted_text) // _READ_MINUTES_PER_CHARS + 1)


def _content_status(raw: str) -> ProcessingStatus:
    """content_results.status를 API 상태로 변환한다."""
    if raw == "READY":
        return "READY"
    if raw == "INSUFFICIENT":
        return "INSUFFICIENT"
    return "PENDING"


def _processing_info(raw: str) -> ProcessingInfo:
    """상세의 처리 단계 상태를 만든다.

    입력: raw (content_results.status)
    출력: ProcessingInfo
    기능: 공개 목록에 오른 기사만 오므로 collection은 성공으로 본다.
          본문 부족(INSUFFICIENT)은 LLM 호출 없이 끝난 정상 상태라 SKIPPED로 표시한다.
    """
    if raw == "READY":
        return ProcessingInfo(
            collection_status="SUCCEEDED",
            translation_status="SUCCEEDED",
            summary_status="SUCCEEDED",
        )
    return ProcessingInfo(
        collection_status="SUCCEEDED",
        translation_status="SKIPPED",
        summary_status="SKIPPED",
    )


def get_news_detail(settings: Settings, news_id: str) -> NewsDetailResponse:
    """뉴스 상세를 조회한다(캐시 우선).

    입력: settings (앱 설정), news_id (경로의 불투명 ID)
    출력: NewsDetailResponse
    기능: 없거나 공개 불가 상태면 NewsNotFoundError(404)로 존재 여부를 숨긴다.
          조회는 저장 결과만 읽고 AI 작업을 만들지 않는다.
          상세 캐시 30분+jitter, 락으로 stampede를 막는다.
    """
    if not news_id or len(news_id) > 64:
        raise NewsNotFoundError
    cache_key = cache_retry_service.detail_cache_key(news_id)
    cached = cache_retry_service.cache_get(settings, cache_key)
    if cached is not None:
        return NewsDetailResponse.model_validate_json(cached)
    with cache_retry_service.locked(settings, cache_key, cache_key) as acquired:
        if not acquired:
            cached = cache_retry_service.cache_get(settings, cache_key)
            if cached is not None:
                return NewsDetailResponse.model_validate_json(cached)
        response = _detail_uncached(settings, news_id)
        cache_retry_service.cache_set(
            settings, cache_key, response.model_dump_json(), cache_retry_service.detail_ttl()
        )
        return response


def _detail_uncached(settings: Settings, news_id: str) -> NewsDetailResponse:
    """캐시를 거치지 않는 실제 상세 조회 본체."""
    with transaction(settings.database_url) as conn:
        row = news_repository.get_public_news(conn, news_id)
        if row is None:
            raise NewsNotFoundError
        related = ranking_relation_service.list_related(conn, news_id)

    translation_required = needs_translation(row.original_language, row.source_name)
    processing = _processing_info(row.status)
    if not translation_required:
        processing = processing.model_copy(update={"translation_status": "SKIPPED"})
    return NewsDetailResponse(
        article=ArticleInfo(
            id=row.id,
            title=row.title,
            source_name=row.source_name,
            published_at=row.published_at,
            original_language=row.original_language,
            translation_required=translation_required,
            category=NewsCategory(row.category),
            estimated_read_minutes=_estimate_read_minutes(row.extracted_text),
        ),
        content=ContentInfo(
            summary_lines=news_repository.parse_summary_lines(row.summary_lines),
            translated_text=row.translated_text if translation_required else None,
            processed_at=row.processed_at,
            content_status=_content_status(row.status),
            summary_model_version=row.prompt_version or row.model_id,
        ),
        source=SourceInfo(
            original_url=row.canonical_url,
            url_verified=row.canonical_url.startswith("https://"),
            source_type=row.source_kind,
        ),
        related_news=related,
        processing=processing,
    )

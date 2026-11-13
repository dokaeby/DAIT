"""FR-HOME-01/02, FR-SEARCH-01, FR-DETAIL-01~02 뉴스 API.

목록·검색·상세는 저장 결과만 반환하며 조회 시 크롤링·LLM을 호출하지 않는다.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from dait.api.deps import get_current_user, get_optional_user
from dait.core.config import Settings, get_settings
from dait.core.errors import ValidationFailedError
from dait.repositories.interest_matching import KEYWORDS
from dait.schemas.news import (
    ACTIVE_CATEGORIES,
    NewsActivity,
    NewsCategory,
    NewsDetailResponse,
    NewsListResponse,
    SortOrder,
    decode_cursor,
)
from dait.schemas.user import UserRecord
from dait.services import news_activity_service, news_detail_service, news_feed_service
from dait.services.interest_service import list_interests

router = APIRouter(prefix="/v1/news", tags=["news"])
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get("", response_model=NewsListResponse, summary="뉴스 목록·검색·정렬")
def list_news(
    settings: SettingsDep,
    user: Annotated[UserRecord | None, Depends(get_optional_user)],
    language: Annotated[str | None, Query(pattern="^(ko|en)$")] = None,
    topic: Annotated[str | None, Query(max_length=50)] = None,
    personalized: bool = False,
    interest: Annotated[str | None, Query(max_length=50)] = None,
    category: Annotated[NewsCategory | None, Query()] = None,
    q: Annotated[str, Query(max_length=100)] = "",
    sort: Annotated[SortOrder, Query()] = "rank",
    page_size: Annotated[int, Query(ge=1, le=50)] = 10,
    cursor: Annotated[str | None, Query(max_length=500)] = None,
) -> NewsListResponse:
    """공개 가능한 기사를 랭킹순/최신순으로 조회한다.

    입력: category(AI만 활성), q(제목+검증된 요약 검색), sort, page_size, cursor
    출력: NewsListResponse (items, page, meta)
    기능: MVP는 단일 AI 카테고리만 허용한다. 목록은 저장 결과만 읽는다.
    """
    if category is not None and category not in ACTIVE_CATEGORIES:
        raise ValidationFailedError
    if cursor is not None:
        try:
            decode_cursor(cursor)  # 형식 검증은 service에서도 하지만 여기서 먼저 422를 만든다.
        except ValueError as exc:
            raise ValidationFailedError from exc
    if user is None:
        if cursor is not None:
            raise ValidationFailedError
        response = news_feed_service.list_news(
            settings, None, q, "latest", min(page_size, 10), None
        )
        return response.model_copy(
            update={
                "page": response.page.model_copy(update={"has_more": False, "next_cursor": None}),
                "meta": response.meta.model_copy(update={"total_visible": len(response.items)}),
            }
        )
    scope = None
    if personalized:
        saved = tuple(i.code.value for i in list_interests(settings, user.id).interests)
        if interest is not None and (interest not in saved or interest not in KEYWORDS):
            raise ValidationFailedError
        if language:
            saved_for_language = tuple(
                c for c in saved if c.startswith("en.") == (language == "en")
            )
            scope = (interest,) if interest else (saved_for_language if saved else None)
        else:
            scope = (interest,) if interest else (saved or None)
    if topic:
        if topic not in KEYWORDS:
            raise ValidationFailedError
        scope = (topic,)
    return news_feed_service.list_news(
        settings, category, q, sort, page_size, cursor, interests=scope, language=language
    )


@router.get("/activity", response_model=NewsActivity)
def news_activity(
    settings: SettingsDep,
    user: Annotated[UserRecord, Depends(get_current_user)],
    response: Response,
    q: Annotated[str, Query(max_length=100)] = "",
    ids: Annotated[list[str] | None, Query(max_length=50)] = None,
    language: Annotated[str | None, Query(pattern="^(ko|en)$")] = None,
    personalized: bool = False,
) -> NewsActivity:
    """Fresh filtered counts and private read state, never publicly cached."""
    if ids and any(not identifier or len(identifier) > 64 for identifier in ids):
        raise ValidationFailedError
    response.headers["Cache-Control"] = "no-store"
    return news_activity_service.activity(settings, user.id, q, ids or [], personalized, language)


@router.get("/read-state", response_model=list[str])
def news_read_state(
    settings: SettingsDep,
    user: Annotated[UserRecord, Depends(get_current_user)],
    response: Response,
    ids: Annotated[list[str] | None, Query(max_length=50)] = None,
) -> list[str]:
    """Fetch private read receipts independently of public topic counts."""
    if ids and any(not identifier or len(identifier) > 64 for identifier in ids):
        raise ValidationFailedError
    response.headers["Cache-Control"] = "no-store"
    return news_activity_service.read_state(settings, user.id, ids or [])


@router.put("/{news_id}/read", status_code=204)
def mark_news_read(
    news_id: str,
    settings: SettingsDep,
    user: Annotated[UserRecord, Depends(get_current_user)],
) -> Response:
    """Idempotent authenticated read receipt."""
    if not news_id or len(news_id) > 64:
        raise ValidationFailedError
    news_activity_service.mark_read(settings, user.id, news_id)
    return Response(status_code=204)


@router.get("/{news_id}", response_model=NewsDetailResponse, summary="뉴스 상세")
def news_detail(news_id: str, settings: SettingsDep) -> NewsDetailResponse:
    """기사 헤더·3줄 요약·번역·처리 정보·원본 정보·관련 뉴스를 반환한다.

    입력: news_id (불투명 뉴스 ID, 경로)
    출력: NewsDetailResponse
    기능: 없거나 공개 불가 ID는 404 NEWS_NOT_FOUND로 존재 여부를 숨긴다.
    """
    return news_detail_service.get_news_detail(settings, news_id)

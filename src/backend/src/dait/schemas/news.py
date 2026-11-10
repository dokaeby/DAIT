"""뉴스 목록·검색·상세 API 계약 모델 (06_API_설계서 4~5절)."""

import base64
import json
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_SUMMARY_LINES = 3
MAX_TITLE_LENGTH = 500
MAX_RELATED = 10
_CURSOR_MAX_OFFSET = 100_000
_HTTPS_ONLY = "original_url must be https"
_INVALID_CURSOR = "invalid cursor"


class NewsCategory(StrEnum):
    """카테고리 Enum. MVP에서 수집·노출하는 것은 AI뿐이다."""

    AI = "AI"
    WEATHER = "WEATHER"
    ECONOMY = "ECONOMY"
    POLITICS = "POLITICS"


ACTIVE_CATEGORIES: frozenset[NewsCategory] = frozenset({NewsCategory.AI})


class ContentStatus(StrEnum):
    """content_results.status 값. API의 processing_status로 변환해 노출한다."""

    PENDING = "PENDING"
    COLLECTED = "COLLECTED"
    TRANSLATED = "TRANSLATED"
    SUMMARIZED = "SUMMARIZED"
    READY = "READY"
    INSUFFICIENT = "INSUFFICIENT"
    FAILED = "FAILED"


# 공개 목록에 노출할 수 있는 처리 상태. FAILED·PENDING은 공개하지 않는다.
PUBLIC_STATUSES: frozenset[ContentStatus] = frozenset(
    {ContentStatus.READY, ContentStatus.INSUFFICIENT}
)

ProcessingStatus = Literal["READY", "INSUFFICIENT", "FAILED", "PENDING"]
SortOrder = Literal["rank", "latest"]


class NewsListItem(BaseModel):
    """목록 카드 한 건. 화면의 rank·제목·출처·시각·요약·상태·원문에 대응한다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1, max_length=64)
    rank: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    source_name: str = Field(min_length=1, max_length=200)
    published_at: datetime
    category: NewsCategory
    summary_lines: list[Annotated[str, Field(max_length=500)]] = Field(max_length=MAX_SUMMARY_LINES)
    processing_status: ProcessingStatus
    original_url: str = Field(min_length=1, max_length=2000)
    is_partial: bool

    @field_validator("original_url")
    @classmethod
    def _https_only(cls, value: str) -> str:
        """원문 URL은 검증된 HTTPS만 허용한다.

        입력: value (저장된 canonical_url)
        출력: 같은 문자열
        기능: http·기타 scheme이면 ValueError로 응답 생성을 막는다.
        """
        if not value.startswith("https://"):
            raise ValueError(_HTTPS_ONLY)
        return value


class PageInfo(BaseModel):
    """커서 페이지네이션 메타."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    next_cursor: str | None = Field(default=None, max_length=500)
    has_more: bool


class NewsListMeta(BaseModel):
    """목록 부가 정보: 부분 실패 여부와 랭킹 기준 설명."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    total_visible: int = Field(ge=0)
    partial: bool
    message: str | None = Field(default=None, max_length=200)
    rank_basis: list[str] = Field(max_length=10)


class NewsListResponse(BaseModel):
    """GET /v1/news 응답."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    items: list[NewsListItem] = Field(max_length=50)
    page: PageInfo
    meta: NewsListMeta


class ArticleInfo(BaseModel):
    """상세 상단의 기사 메타."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str = Field(max_length=MAX_TITLE_LENGTH)
    source_name: str = Field(max_length=200)
    published_at: datetime
    original_language: str = Field(min_length=2, max_length=8)
    category: NewsCategory
    estimated_read_minutes: int | None = Field(default=None, ge=1)


class ContentInfo(BaseModel):
    """상세 본문의 AI 처리 결과."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    summary_lines: list[Annotated[str, Field(max_length=500)]] = Field(max_length=MAX_SUMMARY_LINES)
    translated_text: str | None = Field(default=None, max_length=20000)
    processed_at: datetime | None = None
    content_status: ProcessingStatus
    summary_model_version: str | None = Field(default=None, max_length=80)


class SourceInfo(BaseModel):
    """원본 정보: 검증된 HTTPS 원문과 출처 유형."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    original_url: str = Field(min_length=1, max_length=2000)
    url_verified: bool
    source_type: str = Field(min_length=1, max_length=20)

    @field_validator("original_url")
    @classmethod
    def _https_only(cls, value: str) -> str:
        """원문 URL은 검증된 HTTPS만 노출한다."""
        if not value.startswith("https://"):
            raise ValueError(_HTTPS_ONLY)
        return value


class RelatedNewsItem(BaseModel):
    """관련 뉴스 한 건. reason·score로 관련 근거를 설명한다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str = Field(max_length=MAX_TITLE_LENGTH)
    source_name: str = Field(max_length=200)
    published_at: datetime
    reason: str = Field(min_length=1, max_length=500)
    score: float = Field(ge=0.0, le=1.0)


class ProcessingInfo(BaseModel):
    """수집·번역·요약 각 단계의 상태."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    collection_status: Literal["SUCCEEDED", "FAILED", "PENDING"]
    translation_status: Literal["SUCCEEDED", "FAILED", "SKIPPED", "PENDING"]
    summary_status: Literal["SUCCEEDED", "FAILED", "SKIPPED", "PENDING"]


class NewsDetailResponse(BaseModel):
    """GET /v1/news/{news_id} 응답."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    article: ArticleInfo
    content: ContentInfo
    source: SourceInfo
    related_news: list[RelatedNewsItem] = Field(max_length=MAX_RELATED)
    processing: ProcessingInfo


def encode_cursor(offset: int) -> str:
    """다음 페이지 위치를 불투명 문자열로 만든다.

    입력: offset (다음에 읽을 행 위치)
    출력: str (base64url JSON)
    기능: 클라이언트가 내부 정렬 키를 알지 못하게 한다.
    """
    return base64.urlsafe_b64encode(json.dumps({"o": offset}).encode()).decode()


def decode_cursor(cursor: str) -> int:
    """커서 문자열을 행 위치로 되돌린다.

    입력: cursor (클라이언트가 돌려준 문자열)
    출력: int (0 이상 _CURSOR_MAX_OFFSET 이하)
    기능: 형식이 어긋나면 ValueError → 라우트에서 422로 변환한다.
    """
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        offset = int(payload["o"])
    except (ValueError, KeyError, TypeError, UnicodeDecodeError) as exc:
        raise ValueError(_INVALID_CURSOR) from exc
    if offset < 0 or offset > _CURSOR_MAX_OFFSET:
        raise ValueError(_INVALID_CURSOR)
    return offset

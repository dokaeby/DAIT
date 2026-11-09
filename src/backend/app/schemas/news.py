"""Confirmed v1.0.1 news API contracts; unavailable provenance is explicitly null."""

from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator
from src.backend.app.core.taxonomy import CategoryType
from src.backend.app.schemas.collector import CollectedArticle
from src.backend.app.schemas.content import GeneratedContent

INVALID_QUERY = "Invalid news query"
INVALID_RESPONSE = "Invalid news API response"
RANK_BASIS = "ready>published_at_desc>source_priority_asc>id_asc"
LATEST_BASIS = "published_at_desc>id_asc"


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class NewsQuery(ApiModel):
    category: CategoryType = "AI"
    q: str | None = Field(default=None, max_length=200)
    sort: Literal["rank", "latest"] = "rank"
    page_size: int = Field(default=10, ge=1, le=50)
    cursor: str | None = Field(default=None, min_length=1, max_length=2048)

    @field_validator("page_size", mode="before")
    @classmethod
    def integer_page_size(cls, value: object) -> object:
        if type(value) is int or (isinstance(value, str) and value.isascii() and value.isdigit()):
            return value
        raise ValueError(INVALID_QUERY)

    @field_validator("q")
    @classmethod
    def normalize_search(cls, value: str | None) -> str | None:
        return (" ".join(value.casefold().split()) or None) if value is not None else None


class NewsListItem(ApiModel):
    id: str = Field(min_length=1, max_length=200)
    rank: int = Field(strict=True, ge=1)
    title: str = Field(min_length=1, max_length=2000)
    source_name: str = Field(min_length=1, max_length=200)
    published_at: datetime
    category: CategoryType = "AI"
    summary_lines: tuple[str, str, str]
    processing_status: Literal["READY"] = "READY"
    original_url: HttpUrl
    is_partial: bool = False

    @field_validator("title", "source_name")
    @classmethod
    def nonblank(cls, value: str) -> str:
        return CollectedArticle.nonblank(value)

    @field_validator("published_at")
    @classmethod
    def utc_time(cls, value: datetime) -> datetime:
        return CollectedArticle.normalize_timestamp(value)

    @field_validator("original_url")
    @classmethod
    def safe_url(cls, value: HttpUrl) -> HttpUrl:
        return CollectedArticle.normalize_url(value)

    @field_validator("summary_lines")
    @classmethod
    def three_sentences(cls, value: tuple[str, str, str]) -> tuple[str, str, str]:
        return GeneratedContent.validate_sentences(value)


class NewsPage(ApiModel):
    next_cursor: str | None
    has_more: bool

    @model_validator(mode="after")
    def consistent_cursor(self) -> Self:
        if self.has_more != bool(self.next_cursor):
            raise ValueError(INVALID_RESPONSE)
        return self


class NewsMeta(ApiModel):
    total_visible: int = Field(strict=True, ge=0)
    partial: bool
    message: str | None
    rank_basis: Literal[
        "ready>published_at_desc>source_priority_asc>id_asc", "published_at_desc>id_asc"
    ]


class NewsListResponse(ApiModel):
    items: list[NewsListItem]
    page: NewsPage
    meta: NewsMeta

    @model_validator(mode="after")
    def unique_items(self) -> Self:
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError(INVALID_RESPONSE)
        if self.meta.total_visible < len(self.items):
            raise ValueError(INVALID_RESPONSE)
        return self


class NewsArticle(ApiModel):
    id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=2000)
    source_name: str = Field(min_length=1, max_length=200)
    published_at: datetime
    original_language: str | None
    category: CategoryType = "AI"
    estimated_read_minutes: int | None = Field(ge=1)

    @field_validator("published_at")
    @classmethod
    def utc_time(cls, value: datetime) -> datetime:
        return CollectedArticle.normalize_timestamp(value)


class NewsContent(ApiModel):
    summary_lines: tuple[str, str, str] | tuple[()]
    translated_text: str | None
    processed_at: datetime | None
    content_status: Literal["READY", "INSUFFICIENT"]
    summary_model_version: str | None

    @field_validator("processed_at")
    @classmethod
    def utc_time(cls, value: datetime | None) -> datetime | None:
        return None if value is None else CollectedArticle.normalize_timestamp(value)

    @model_validator(mode="after")
    def valid_content(self) -> Self:
        if self.content_status == "READY":
            if (
                len(self.summary_lines) != 3
                or not self.translated_text
                or not self.translated_text.strip()
            ):
                raise ValueError(INVALID_RESPONSE)
            GeneratedContent(
                summary_lines=(
                    self.summary_lines[0],
                    self.summary_lines[1],
                    self.summary_lines[2],
                ),
                translated_text=self.translated_text,
            )
        elif self.summary_lines or self.translated_text is not None:
            raise ValueError(INVALID_RESPONSE)
        return self


class NewsSource(ApiModel):
    original_url: HttpUrl
    url_verified: bool
    source_type: Literal["RSS", "HTML", "UNKNOWN"]

    @field_validator("original_url")
    @classmethod
    def safe_url(cls, value: HttpUrl) -> HttpUrl:
        return CollectedArticle.normalize_url(value)


class NewsProcessing(ApiModel):
    collection_status: Literal["COLLECTED"]
    translation_status: Literal["SUCCESS", "INSUFFICIENT"]
    summary_status: Literal["SUCCESS", "INSUFFICIENT"]


class NewsDetailResponse(ApiModel):
    article: NewsArticle
    content: NewsContent
    source: NewsSource
    related_news: list[NewsListItem]
    processing: NewsProcessing

    @model_validator(mode="after")
    def consistent_processing(self) -> Self:
        ready = self.content.content_status == "READY"
        if ready != (self.processing.translation_status == "SUCCESS") or ready != (
            self.processing.summary_status == "SUCCESS"
        ):
            raise ValueError(INVALID_RESPONSE)
        ids = tuple(item.id for item in self.related_news)
        if self.article.id in ids or len(set(ids)) != len(ids):
            raise ValueError(INVALID_RESPONSE)
        return self


type ApiErrorCode = Literal["NEWS_NOT_FOUND", "INVALID_REQUEST", "INVALID_CURSOR", "INTERNAL_ERROR"]


class ApiError(ApiModel):
    code: ApiErrorCode
    message: str


class ApiErrorResponse(ApiModel):
    error: ApiError
    request_id: str = Field(min_length=1, max_length=64)

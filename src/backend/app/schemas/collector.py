"""Validated contracts for the shared AI news collection pipeline."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from src.backend.app.core.taxonomy import CategoryType


class _Messages:
    INVALID_APPROVED_HOST: str = "Invalid approved host"
    TEXT_MUST_NOT_BE_BLANK: str = "Text must not be blank"
    URL_CREDENTIALS_ARE_FORBIDDEN: str = "URL credentials are forbidden"
    PUBLICATION_TIME_MUST_BE_TIMEZONE_AWARE: str = "Publication time must be timezone-aware"


class CollectorModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CollectorSource(CollectorModel):
    """Operator-approved source configuration, never supplied by an end user."""

    source_name: str = Field(min_length=1, max_length=200)
    feed_url: HttpUrl
    allowed_hosts: tuple[str, ...] = Field(min_length=1)
    category: CategoryType = "AI"

    @field_validator("allowed_hosts")
    @classmethod
    def normalize_hosts(cls, hosts: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(host.encode("idna").decode("ascii").lower() for host in hosts)
        if any(not host or "/" in host or "*" in host or host.endswith(".") for host in normalized):
            raise ValueError(_Messages.INVALID_APPROVED_HOST)
        return normalized


class CollectedArticle(CollectorModel):
    source_name: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=2000)
    canonical_url: HttpUrl
    published_at: datetime
    raw_text: str | None
    category: CategoryType = "AI"

    @field_validator("source_name", "title")
    @classmethod
    def nonblank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError(_Messages.TEXT_MUST_NOT_BE_BLANK)
        return cleaned

    @field_validator("canonical_url")
    @classmethod
    def normalize_url(cls, value: HttpUrl) -> HttpUrl:
        if value.username is not None or value.password is not None:
            raise ValueError(_Messages.URL_CREDENTIALS_ARE_FORBIDDEN)
        return HttpUrl(str(value).split("#", 1)[0])

    @field_validator("published_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(_Messages.PUBLICATION_TIME_MUST_BE_TIMEZONE_AWARE)
        return value.astimezone(UTC)


class CollectionResult(CollectorModel):
    source_name: str
    category: CategoryType = "AI"
    articles: tuple[CollectedArticle, ...]
    rejected_count: int = Field(default=0, ge=0)

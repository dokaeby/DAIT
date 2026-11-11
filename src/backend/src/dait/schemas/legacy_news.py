"""기존 수집 결과를 통합 저장소로 옮기는 검증 모델."""

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

_HTTPS_REQUIRED = "https required"


class LegacyNews(BaseModel):
    """기존 DB의 성공 결과만 받는다. 기존 SQLite의 UTC 시각을 명시한다."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(min_length=1, max_length=36)
    canonical_url: HttpUrl
    source_name: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=500)
    category: Literal["AI", "ECONOMY", "SOCIETY"]
    published_at: datetime
    translated_text: str | None = Field(default=None, max_length=20000)
    summary_lines: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(
        min_length=3, max_length=3
    )

    @field_validator("published_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        """기존 수집 DB의 naive UTC 저장 형식을 복원한다."""
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    @field_validator("canonical_url")
    @classmethod
    def https_only(cls, value: HttpUrl) -> HttpUrl:
        """통합 API의 HTTPS 공개 조건을 유지한다."""
        if value.scheme != "https":
            raise ValueError(_HTTPS_REQUIRED)
        return value

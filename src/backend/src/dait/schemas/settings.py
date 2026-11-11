"""설정·예약 API 계약 모델 (06_API_설계서 6절, FR-SET-01~03)."""

import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from dait.schemas.news import ACTIVE_CATEGORIES, NewsCategory

MAX_KEYWORDS = 20
MAX_KEYWORD_LENGTH = 50
MAX_SOURCE_IDS = 50
MAX_SCHEDULES = 10
_TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_BAD_KEYWORD = "keyword contains control characters"
_INACTIVE_CATEGORY = "category is not active"
_BAD_TIME = "local_time must be HH:mm"
_EMPTY_UPDATE = "empty update"
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")

Keyword = Annotated[str, Field(min_length=1, max_length=MAX_KEYWORD_LENGTH)]
SourceId = Annotated[str, Field(min_length=1, max_length=64)]


def normalize_keywords(values: list[str]) -> list[str]:
    """키워드 목록을 정규화한다: 앞뒤 공백 제거, 빈 값 제거, 중복 제거(순서 유지).

    입력: values (사용자가 보낸 문자열 목록)
    출력: 정규화된 문자열 목록
    기능: 제어문자가 있으면 ValueError. 대소문자만 다른 중복은 별개로 둔다(한국어 중심).
    """
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in values:
        item = raw.strip()
        if not item:
            continue
        if _CONTROL_CHARS.search(item):
            raise ValueError(_BAD_KEYWORD)
        if item not in seen:
            seen.add(item)
            normalized.append(item)
    return normalized


class SettingsResponse(BaseModel):
    """GET/PATCH /v1/me/settings 응답. 서버가 정규화해 저장한 값을 그대로 돌려준다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    default_count: Literal[5, 10]
    keywords: list[Keyword] = Field(max_length=MAX_KEYWORDS)
    source_ids: list[SourceId] = Field(max_length=MAX_SOURCE_IDS)
    categories: list[NewsCategory] = Field(max_length=10)
    in_app_notice: bool
    email_notice: bool
    updated_at: datetime


class SettingsUpdateRequest(BaseModel):
    """PATCH /v1/me/settings 요청. 보내지 않은 필드는 유지한다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    default_count: Literal[5, 10] | None = None
    keywords: list[Annotated[str, Field(max_length=MAX_KEYWORD_LENGTH)]] | None = Field(
        default=None, max_length=MAX_KEYWORDS
    )
    source_ids: list[SourceId] | None = Field(default=None, max_length=MAX_SOURCE_IDS)
    categories: list[NewsCategory] | None = Field(default=None, max_length=10)
    in_app_notice: bool | None = None
    email_notice: bool | None = None

    @field_validator("keywords")
    @classmethod
    def _check_keywords(cls, value: list[str] | None) -> list[str] | None:
        """키워드 목록의 형식·제어문자를 검사한다(정규화는 service에서)."""
        if value is None:
            return value
        for item in value:
            if _CONTROL_CHARS.search(item):
                raise ValueError(_BAD_KEYWORD)
        return value

    @field_validator("categories")
    @classmethod
    def _check_categories(cls, value: list[NewsCategory] | None) -> list[NewsCategory] | None:
        """활성 카테고리(AI)만 허용한다."""
        if value is None:
            return value
        inactive = [c for c in value if c not in ACTIVE_CATEGORIES]
        if inactive:
            raise ValueError(_INACTIVE_CATEGORY)
        return value


class ScheduleCriteria(BaseModel):
    """예약에 저장하는 관심 조건. settings의 관심 조건과 같은 검증을 거친다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    keywords: list[Keyword] = Field(default_factory=list, max_length=MAX_KEYWORDS)
    source_ids: list[SourceId] = Field(default_factory=list, max_length=MAX_SOURCE_IDS)
    categories: list[NewsCategory] = Field(min_length=1, max_length=10)

    @field_validator("keywords")
    @classmethod
    def _check_keywords(cls, value: list[str]) -> list[str]:
        for item in value:
            if _CONTROL_CHARS.search(item):
                raise ValueError(_BAD_KEYWORD)
        return value

    @field_validator("categories")
    @classmethod
    def _check_categories(cls, value: list[NewsCategory]) -> list[NewsCategory]:
        inactive = [c for c in value if c not in ACTIVE_CATEGORIES]
        if inactive:
            raise ValueError(_INACTIVE_CATEGORY)
        return value


class ScheduleResponse(BaseModel):
    """예약 한 건의 응답."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1, max_length=64)
    local_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    timezone: str = Field(min_length=1, max_length=64)
    enabled: bool
    criteria: ScheduleCriteria
    next_run_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ScheduleListResponse(BaseModel):
    """GET /v1/me/schedules 응답."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    items: list[ScheduleResponse] = Field(max_length=MAX_SCHEDULES)


class ScheduleCreateRequest(BaseModel):
    """POST /v1/me/schedules 요청."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    local_time: str = Field(min_length=4, max_length=5)
    timezone: str = Field(min_length=1, max_length=64)
    enabled: bool = True
    criteria: ScheduleCriteria

    @field_validator("local_time")
    @classmethod
    def _check_time(cls, value: str) -> str:
        """HH:mm 24시간 형식인지 확인한다."""
        if not _TIME_PATTERN.fullmatch(value):
            raise ValueError(_BAD_TIME)
        return value


class ScheduleUpdateRequest(BaseModel):
    """PATCH /v1/me/schedules/{id} 요청. 보내지 않은 필드는 유지한다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    local_time: str | None = Field(default=None, min_length=4, max_length=5)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    enabled: bool | None = None
    criteria: ScheduleCriteria | None = None

    @field_validator("local_time")
    @classmethod
    def _check_time(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not _TIME_PATTERN.fullmatch(value):
            raise ValueError(_BAD_TIME)
        return value

    @model_validator(mode="after")
    def _not_empty(self) -> "ScheduleUpdateRequest":
        """모든 필드가 비어 있는 부분 변경은 의미가 없어 거부한다."""
        if (
            self.local_time is None
            and self.timezone is None
            and self.enabled is None
            and self.criteria is None
        ):
            raise ValueError(_EMPTY_UPDATE)
        return self

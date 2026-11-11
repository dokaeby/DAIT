"""파이프라인 내부 Pydantic 모델: 수집 피드 항목·작업 상태·수집 요약 (FR-PIPE-01~04)."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_FEED_ENTRIES = 100
MAX_SUMMARY_TEXT = 4000

_HTTPS_ONLY = "url must be https"


class JobStatus(StrEnum):
    """jobs.status 허용 값."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    DEAD_LETTER = "DEAD_LETTER"


class JobKind(StrEnum):
    """jobs.kind 허용 값."""

    COLLECT = "COLLECT"
    PROCESS = "PROCESS"


class StepName(StrEnum):
    """job_attempts.step 허용 값."""

    COLLECT = "COLLECT"
    TRANSLATE = "TRANSLATE"
    SUMMARIZE = "SUMMARIZE"
    RANK = "RANK"
    NOTIFY = "NOTIFY"


class FeedEntry(BaseModel):
    """피드 한 항목의 정규화 모델. 외부 입력 경계라 엄격하게 검증한다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str = Field(min_length=1, max_length=500)
    url: str = Field(min_length=8, max_length=2000)
    published_at: datetime | None = None
    summary: str | None = Field(default=None, max_length=MAX_SUMMARY_TEXT)

    @field_validator("url")
    @classmethod
    def _check_https(cls, value: str) -> str:
        """원문 링크는 HTTPS만 허용한다."""
        if not value.lower().startswith("https://"):
            raise ValueError(_HTTPS_ONLY)
        return value


class CollectionSummary(BaseModel):
    """한 출처의 수집 실행 결과 요약."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    status: Literal["SUCCEEDED", "FAILED", "SKIPPED"]
    fetched: int = Field(ge=0)
    inserted: int = Field(ge=0)
    duplicates: int = Field(ge=0)
    rejected: int = Field(ge=0)
    error_code: str | None = Field(default=None, max_length=64)


def now_utc_iso() -> str:
    """UTC 현재 시각의 ISO 문자열. 테스트에서 now를 주입할 수 있게 함수로 둔다."""
    return datetime.now().astimezone().isoformat()

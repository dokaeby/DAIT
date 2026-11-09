"""Deterministic AI news ranking combining recency, source priority, keywords, and popularity.

Priority: READY first, deterministic weighted score (when keyword_frequency or
popularity_index is supplied), publication time descending, source priority
ascending, normalized UUID ascending. No wall clock, random numbers, network
calls or database access are involved.
"""

from datetime import UTC, datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from src.backend.app.core.taxonomy import SUBTOPIC_GROUPS, CategoryType
from src.backend.app.schemas.content import CONTENT_RESULT_ADAPTER, ContentResult, SuccessContent

INVALID_TIME = "Publication time must be timezone-aware"
INVALID_LIMIT = "Display limit must be the integer 5 or 10"
DUPLICATE_ID = "Ranking candidates must have unique IDs"


class RankingModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class RankingWeights(RankingModel):
    """Deterministic weights for recency, source priority, keyword frequency, and popularity."""

    recency_weight: float = Field(default=40.0, ge=0.0, allow_inf_nan=False)
    source_priority_weight: float = Field(default=25.0, ge=0.0, allow_inf_nan=False)
    keyword_frequency_weight: float = Field(default=20.0, ge=0.0, allow_inf_nan=False)
    popularity_weight: float = Field(default=15.0, ge=0.0, allow_inf_nan=False)


class RankingCandidate(RankingModel):
    id: UUID
    category: CategoryType = "AI"
    published_at: datetime
    source_priority: int = Field(strict=True, ge=0)
    keyword_frequency: int = Field(default=0, strict=True, ge=0)
    popularity_index: int = Field(default=0, strict=True, ge=0)
    content: ContentResult

    @field_validator("published_at")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(INVALID_TIME)
        return value.astimezone(UTC)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: ContentResult) -> ContentResult:
        # Existing content models must also be checked after model_construct/model_copy.
        return CONTENT_RESULT_ADAPTER.validate_json(value.model_dump_json(warnings=False))

    @property
    def ready(self) -> bool:
        """READY requires the existing successful three-sentence/translation contract."""
        return isinstance(self.content, SuccessContent)

    @property
    def ranking_key(self) -> tuple[bool, datetime, int, str]:
        """Factual ranking components; directions follow the module's priority rule."""
        return self.ready, self.published_at, self.source_priority, str(self.id)


class RankingRequest(RankingModel):
    candidates: tuple[RankingCandidate, ...]
    limit: Literal[5, 10] = 5

    @field_validator("limit", mode="before")
    @classmethod
    def strict_limit(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError(INVALID_LIMIT)
        return value

    @model_validator(mode="after")
    def unique_ids(self) -> Self:
        ids = tuple(candidate.id for candidate in self.candidates)
        if len(set(ids)) != len(ids):
            raise ValueError(DUPLICATE_ID)
        return self


class RankedNews(RankingModel):
    rank: int = Field(strict=True, ge=1)
    news: RankingCandidate


def compute_keyword_and_popularity(
    title: str,
    summary_lines: tuple[str, ...],
    raw_text: str | None = None,
    source_priority: int = 0,
) -> tuple[int, int]:
    """Compute deterministic keyword_frequency and popularity_index (조회수/반응도) from article."""
    combined = f"{title} {' '.join(summary_lines)} {raw_text or ''}".casefold()
    title_lower = title.casefold()
    keyword_hits = 0
    for group in SUBTOPIC_GROUPS:
        for kw in group.keywords:
            token = kw.casefold()
            if token in title_lower:
                keyword_hits += 2
            elif token in combined:
                keyword_hits += 1

    # Deterministic popularity index (0..100) from keyword buzz, content richness, and tier
    body_len = len(raw_text or "")
    richness_points = min(35, body_len // 40)
    keyword_buzz = min(40, keyword_hits * 4)
    tier_bonus = max(0, 25 - source_priority)
    popularity_idx = min(100, richness_points + keyword_buzz + tier_bonus)
    return keyword_hits, popularity_idx


class RankingService:
    @staticmethod
    def calculate_weighted_score(
        candidate: RankingCandidate,
        *,
        reference_time: datetime | None = None,
        weights: RankingWeights | None = None,
    ) -> float:
        """Calculate deterministic weighted ranking score from recency, source, and popularity."""
        active_weights = weights or RankingWeights()
        ref = reference_time or candidate.published_at
        delta_seconds = max(0.0, (ref - candidate.published_at).total_seconds())
        age_hours = delta_seconds / 3600.0
        recency_ratio = max(0.0, 1.0 - (age_hours / 168.0))
        source_ratio = max(0.0, (20.0 - float(min(candidate.source_priority, 20))) / 20.0)
        keyword_ratio = min(float(candidate.keyword_frequency), 10.0) / 10.0
        popularity_ratio = min(float(candidate.popularity_index), 100.0) / 100.0

        total = (
            recency_ratio * active_weights.recency_weight
            + source_ratio * active_weights.source_priority_weight
            + keyword_ratio * active_weights.keyword_frequency_weight
            + popularity_ratio * active_weights.popularity_weight
        )
        return round(total, 6)

    @staticmethod
    def rank(request: RankingRequest) -> tuple[RankedNews, ...]:
        """Validate, fully sort, then slice without modifying the supplied candidates.

        Stable passes run from least to most significant criterion. Datetimes
        retain microsecond precision; no platform-dependent float timestamp is used.
        """
        validated = RankingRequest.model_validate(request)
        ordered = RankingService.order(validated.candidates)
        return tuple(
            RankedNews(rank=index, news=news)
            for index, news in enumerate(ordered[: validated.limit], start=1)
        )

    @staticmethod
    def order(candidates: tuple[RankingCandidate, ...]) -> tuple[RankingCandidate, ...]:
        """Share the exact ranking rule with API pagination without a premature 5/10 cap."""
        validated = RankingRequest(candidates=candidates, limit=10)
        if not validated.candidates:
            return ()
        ordered = sorted(validated.candidates, key=lambda news: str(news.id))
        ordered.sort(key=lambda news: news.source_priority)
        ordered.sort(key=lambda news: news.published_at, reverse=True)
        has_weighted_signals = any(
            news.keyword_frequency > 0 or news.popularity_index > 0 for news in validated.candidates
        )
        if has_weighted_signals:
            latest_time = max(news.published_at for news in validated.candidates)
            ordered.sort(
                key=lambda news: RankingService.calculate_weighted_score(
                    news, reference_time=latest_time
                ),
                reverse=True,
            )
        ordered.sort(key=lambda news: news.ready, reverse=True)
        return tuple(ordered)

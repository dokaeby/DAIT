"""Shared collection-to-AI worker, invoked by a scheduler/queue consumer.

Production supplies a durable repository with a canonical_url UNIQUE constraint,
atomic claims and fenced commits. No process-local set is used as durable history.
Failed items remain retryable; queue callers must inspect failed_count/busy_count.
Provider failures, expired AI cache and process crashes can cause later retries:
external LLM execution is not guaranteed exactly once across such failures.
"""

import asyncio
import logging
from typing import Literal, Protocol, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator
from src.backend.app.core.taxonomy import CategoryType
from src.backend.app.schemas.collector import CollectedArticle, CollectionResult, CollectorSource
from src.backend.app.schemas.content import (
    CONTENT_RESULT_ADAPTER,
    ContentResult,
    InsufficientContent,
)

logger = logging.getLogger(__name__)
INVALID_STATE = "Invalid pipeline state"
COLLECTION_FAILED = "Pipeline collection failed safely"
type Outcome = Literal["STORED", "INSUFFICIENT", "DUPLICATE", "BUSY", "FAILED"]


class WorkerError(ValueError):
    """Fixed diagnostic without source, provider, database or credential details."""


class WorkerModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ProcessingClaim(WorkerModel):
    canonical_url: HttpUrl
    token: UUID

    @field_validator("canonical_url")
    @classmethod
    def normalize_url(cls, value: HttpUrl) -> HttpUrl:
        return CollectedArticle.normalize_url(value)


class ClaimDecision(WorkerModel):
    status: Literal["ACQUIRED", "COMPLETED", "BUSY"]
    claim: ProcessingClaim | None = None

    @model_validator(mode="after")
    def validate_claim(self) -> Self:
        if (self.status == "ACQUIRED") != (self.claim is not None):
            raise ValueError(INVALID_STATE)
        return self


class PipelineRecord(WorkerModel):
    article: CollectedArticle
    content: ContentResult


class WorkerPolicy(WorkerModel):
    processing_timeout_seconds: float = Field(default=45, gt=0, le=600, allow_inf_nan=False)
    cleanup_timeout_seconds: float = Field(default=5, gt=0, le=30, allow_inf_nan=False)


class PipelineReport(WorkerModel):
    source_name: str
    category: CategoryType = "AI"
    collected_count: int = Field(ge=0)
    stored_count: int = Field(ge=0)
    insufficient_count: int = Field(ge=0)
    duplicate_count: int = Field(ge=0)
    busy_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_totals(self) -> Self:
        if (
            self.collected_count
            != self.stored_count + self.duplicate_count + self.busy_count + self.failed_count
            or self.insufficient_count > self.stored_count
        ):
            raise ValueError(INVALID_STATE)
        return self


class NewsCollector(Protocol):
    async def collect(self, source: CollectorSource) -> CollectionResult: ...


class ContentProcessor(Protocol):
    async def process(self, article: CollectedArticle) -> ContentResult: ...


class PipelineRepository(Protocol):
    """Durable cross-worker contract; all operations must be asynchronous.

    claim atomically returns COMPLETED, BUSY for an unexpired owner's claim, or
    ACQUIRED with a fresh token. Failure/expiry permits a new owner. Completed
    URLs remain completed independently of AI cache TTL and worker restarts.
    complete atomically verifies URL, token and unexpired lease, persists the
    article/content pair under a UNIQUE canonical_url and marks completion.
    release is idempotent and token-fenced: it cannot remove another owner's
    claim or a completed record. Neither completion nor release trusts a token
    merely because the caller supplied one; the repository verifies ownership.
    """

    async def claim(self, canonical_url: HttpUrl, lease_seconds: float) -> ClaimDecision: ...
    async def complete(self, claim: ProcessingClaim, record: PipelineRecord) -> None: ...
    async def release(self, claim: ProcessingClaim) -> None: ...


def _owned_claim(decision: ClaimDecision, canonical_url: HttpUrl) -> ProcessingClaim:
    if decision.claim is None or decision.claim.canonical_url != canonical_url:
        raise WorkerError(INVALID_STATE)
    return decision.claim


def _validated_collection(source: CollectorSource, collected: CollectionResult) -> CollectionResult:
    validated = CollectionResult.model_validate_json(collected.model_dump_json())
    if validated.source_name != source.source_name:
        raise WorkerError(INVALID_STATE)
    return validated


class CollectorWorker:
    def __init__(
        self,
        *,
        collector: NewsCollector,
        processor: ContentProcessor,
        repository: PipelineRepository,
        policy: WorkerPolicy | None = None,
    ) -> None:
        self.collector = collector
        self.processor = processor
        self.repository = repository
        self.policy = WorkerPolicy.model_validate_json((policy or WorkerPolicy()).model_dump_json())

    async def _process(self, article: CollectedArticle) -> Outcome:
        claim: ProcessingClaim | None = None
        committed = False
        try:
            async with asyncio.timeout(self.policy.processing_timeout_seconds):
                decision = await self.repository.claim(
                    article.canonical_url,
                    self.policy.processing_timeout_seconds
                    + self.policy.cleanup_timeout_seconds
                    + 5,
                )
                decision = ClaimDecision.model_validate_json(decision.model_dump_json())
                if decision.status == "COMPLETED":
                    return "DUPLICATE"
                if decision.status == "BUSY":
                    return "BUSY"
                claim = _owned_claim(decision, article.canonical_url)
                content = await self.processor.process(article)
                content = CONTENT_RESULT_ADAPTER.validate_json(content.model_dump_json())
                record = PipelineRecord(article=article, content=content)
                await self.repository.complete(claim, record)
                committed = True
                return "INSUFFICIENT" if isinstance(content, InsufficientContent) else "STORED"
        except Exception:  # noqa: BLE001 -- isolate untrusted adapter diagnostics per item
            logger.warning("Pipeline article processing failed")
            return "FAILED"
        finally:
            if claim is not None and not committed:
                try:
                    async with asyncio.timeout(self.policy.cleanup_timeout_seconds):
                        await self.repository.release(claim)
                except Exception:  # noqa: BLE001 -- lease expiry remains the recovery path
                    logger.warning("Pipeline claim cleanup failed; lease expiry required")

    async def run_once(self, source: CollectorSource) -> PipelineReport:
        """Run one scheduled batch; completed URLs skip AI even if body changed.

        Source-local RSS duplicates may already be removed by the collector;
        duplicate_count counts only duplicates observed at this worker boundary.
        Processing errors are counted for retry; collection errors raise WorkerError.
        Cancellation propagates and releases an acquired claim when possible.
        """
        try:
            source = CollectorSource.model_validate_json(source.model_dump_json())
            collected = await self.collector.collect(source)
            collected = _validated_collection(source, collected)
        except Exception:  # noqa: BLE001 -- do not expose source/validation payloads
            logger.warning("Pipeline collection failed")
            raise WorkerError(COLLECTION_FAILED) from None
        seen: set[str] = set()
        outcomes: list[Outcome] = []
        for article in collected.articles:
            key = str(article.canonical_url)
            if key in seen:
                outcomes.append("DUPLICATE")
                continue
            seen.add(key)
            outcomes.append(await self._process(article))
        report = PipelineReport(
            source_name=source.source_name,
            category=source.category,
            collected_count=len(collected.articles),
            stored_count=outcomes.count("STORED") + outcomes.count("INSUFFICIENT"),
            insufficient_count=outcomes.count("INSUFFICIENT"),
            duplicate_count=outcomes.count("DUPLICATE"),
            busy_count=outcomes.count("BUSY"),
            failed_count=outcomes.count("FAILED"),
            rejected_count=collected.rejected_count,
        )
        logger.info(
            "Pipeline batch completed; stored=%d duplicate=%d busy=%d failed=%d",
            report.stored_count,
            report.duplicate_count,
            report.busy_count,
            report.failed_count,
        )
        return report

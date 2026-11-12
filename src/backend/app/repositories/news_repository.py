"""Async SQLite/PostgreSQL persistence implementing PipelineRepository.

Use sqlite+aiosqlite:///... locally and postgresql+psycopg://... in production.
initialize() creates tables for local/tests; production schema changes require
migrations. Each call owns a separate short transaction, never spanning an LLM
call. PostgreSQL uses row locks; SQLite serializes transactions with BEGIN
IMMEDIATE. Lease times use the database clock (one-second precision margin).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from functools import wraps
from types import CoroutineType
from typing import Literal, Protocol, cast
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, SecretStr, field_validator
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    delete,
    event,
    func,
    inspect,
    or_,
    select,
    type_coerce,
    update,
)
from sqlalchemy.engine import Connection, CursorResult, Dialect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator
from src.backend.app.core.taxonomy import CategoryType
from src.backend.app.schemas.collector import CollectedArticle
from src.backend.app.schemas.content import (
    CONTENT_RESULT_ADAPTER,
    ContentResult,
    SuccessContent,
)
from src.backend.app.workers.collector_worker import ClaimDecision, PipelineRecord, ProcessingClaim

logger = logging.getLogger(__name__)
DB_FAILED = "News repository operation failed safely"
CLAIM_INVALID = "Processing claim is stale or invalid"
INVALID_TIME = "Database timestamps must be timezone-aware"
INVALID_DRIVER = "Unsupported database driver"


class RepositoryError(ValueError):
    """Sanitized failure; SQL, bound values and DSNs must never escape this boundary."""


class ClaimOwnershipError(RepositoryError):
    """The claim has expired, is completed, or belongs to another worker."""


def _safe_operation[**P, R](
    function: Callable[P, Awaitable[R]],
) -> Callable[P, CoroutineType[object, object, R]]:
    @wraps(function)
    async def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return await function(*args, **kwargs)
        except ClaimOwnershipError:
            raise ClaimOwnershipError(CLAIM_INVALID) from None
        except Exception:  # noqa: BLE001 -- suppress DB parameters/validation payloads
            logger.warning("News repository operation failed")
            raise RepositoryError(DB_FAILED) from None

    return wrapped


class RepositorySettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")
    database_url: SecretStr


class StoredNews(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: UUID
    record: PipelineRecord

    @field_validator("record")
    @classmethod
    def validate_record(cls, value: PipelineRecord) -> PipelineRecord:
        return PipelineRecord.model_validate_json(value.model_dump_json(warnings=False))


class NewsIdentifier(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: UUID


class ReadyInvalidator(Protocol):
    async def invalidate_lists(self) -> None: ...


class NewsKey(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    canonical_url: HttpUrl

    @field_validator("canonical_url")
    @classmethod
    def normalize_url(cls, value: HttpUrl) -> HttpUrl:
        return CollectedArticle.normalize_url(value)


class ClaimRequest(NewsKey):
    lease_seconds: float = Field(gt=0, le=3600, allow_inf_nan=False)


class UTCDateTime(TypeDecorator[datetime]):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(INVALID_TIME)
        value = value.astimezone(UTC)
        return value.replace(tzinfo=None) if dialect.name == "sqlite" else value

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if dialect.name == "sqlite" and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(INVALID_TIME)
        return value.astimezone(UTC)


class Base(DeclarativeBase):
    pass


class NewsRow(Base):
    __tablename__ = "news"
    __table_args__ = (
        CheckConstraint("category IN ('AI', 'ECONOMY', 'SOCIETY')", name="ck_news_category"),
        Index("ix_news_category_published", "category", "published_at"),
        Index("ix_news_published_at", "published_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    canonical_url: Mapped[str] = mapped_column(String(2083), unique=True, nullable=False)
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(2000), nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    published_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text)


class ContentResultRow(Base):
    __tablename__ = "content_results"
    __table_args__ = (
        CheckConstraint(
            "(status = 'SUCCESS' AND line_1 IS NOT NULL AND line_2 IS NOT NULL "
            "AND line_3 IS NOT NULL AND translated_text IS NOT NULL) OR "
            "(status = 'INSUFFICIENT' AND line_1 IS NULL AND line_2 IS NULL "
            "AND line_3 IS NULL AND translated_text IS NULL)",
            name="ck_content_status",
        ),
        CheckConstraint("length(content_hash) = 64", name="ck_content_hash"),
    )
    # A non-null shared primary key enforces at most one result per news article.
    news_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("news.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(12), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    line_1: Mapped[str | None] = mapped_column(Text)
    line_2: Mapped[str | None] = mapped_column(Text)
    line_3: Mapped[str | None] = mapped_column(Text)
    translated_text: Mapped[str | None] = mapped_column(Text)
    engine: Mapped[str] = mapped_column(String(50), nullable=False, server_default="")
    model_id: Mapped[str] = mapped_column(String(200), nullable=False, server_default="")
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False, server_default="")

    @property
    def summary_lines(self) -> tuple[str, ...]:
        return tuple(line for line in (self.line_1, self.line_2, self.line_3) if line is not None)

    @property
    def category(self) -> CategoryType:
        return "AI"


class ProcessingClaimRow(Base):
    __tablename__ = "news_processing_claims"
    __table_args__ = (
        CheckConstraint(
            "(token IS NULL AND expires_at IS NULL) OR "
            "(token IS NOT NULL AND expires_at IS NOT NULL)",
            name="ck_claim_lease",
        ),
    )
    canonical_url: Mapped[str] = mapped_column(String(2083), primary_key=True)
    token: Mapped[str | None] = mapped_column(String(36))
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class _SQLiteCursor(Protocol):
    def execute(self, statement: str) -> object: ...
    def close(self) -> None: ...


class _SQLiteConnection(Protocol):
    isolation_level: str | None

    def cursor(self) -> _SQLiteCursor: ...


def _setup_sqlite(connection: _SQLiteConnection, record: object) -> None:
    connection.isolation_level = None
    cursor = connection.cursor()
    try:
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


def _begin_sqlite(connection: Connection) -> None:
    connection.exec_driver_sql("BEGIN IMMEDIATE")


async def _db_now(session: AsyncSession) -> datetime:
    # PostgreSQL CURRENT_TIMESTAMP is fixed at transaction start; a lock wait
    # must not give a newly acquired lease an already-expired timestamp.
    clock = (
        type_coerce(func.clock_timestamp(), DateTime(timezone=True))
        if session.get_bind().dialect.name == "postgresql"
        else func.current_timestamp()
    )
    value = (await session.execute(select(clock))).scalar_one()
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


async def _locked_claim(session: AsyncSession, key: str) -> ProcessingClaimRow:
    query = (
        select(ProcessingClaimRow).where(ProcessingClaimRow.canonical_url == key).with_for_update()
    )
    row = (await session.scalars(query)).one_or_none()
    if row is None:
        try:
            async with session.begin_nested():
                session.add(ProcessingClaimRow(canonical_url=key, completed=False))
                await session.flush()
        except IntegrityError:
            # Another transaction inserted the same URL; its UNIQUE key is the arbiter.
            pass
        row = (await session.scalars(query)).one_or_none()
    if row is None:
        raise RepositoryError(DB_FAILED)
    return row


def _require_owner(row: ProcessingClaimRow, claim: ProcessingClaim, now: datetime) -> None:
    if (
        row.completed
        or row.token != str(claim.token)
        or row.expires_at is None
        or row.expires_at <= now
    ):
        raise ClaimOwnershipError(CLAIM_INVALID)


def _ensure_content_columns(connection: Connection) -> None:
    """Add engine/model_id columns to pre-existing content_results tables."""
    existing = {
        column["name"] for column in inspect(connection).get_columns("content_results")
    }
    for name, ddl in (
        ("engine", "VARCHAR(50) NOT NULL DEFAULT ''"),
        ("model_id", "VARCHAR(200) NOT NULL DEFAULT ''"),
        ("prompt_version", "VARCHAR(50) NOT NULL DEFAULT ''"),
    ):
        if name not in existing:
            connection.exec_driver_sql(
                f"ALTER TABLE content_results ADD COLUMN {name} {ddl}"
            )


def _ensure_indexes(connection: Connection) -> None:
    """Create query indexes on pre-existing tables (IF NOT EXISTS is dialect-safe)."""
    connection.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_news_category_published "
        "ON news (category, published_at)"
    )
    connection.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_news_published_at ON news (published_at)"
    )


def _configure_engine(engine: AsyncEngine) -> None:
    if engine.dialect.name not in {"sqlite", "postgresql"}:
        raise RepositoryError(INVALID_DRIVER)
    # These drivers log raw bound parameters at DEBUG; keep sensitive payloads out.
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("psycopg").setLevel(logging.WARNING)
    if engine.dialect.name == "sqlite":
        event.listen(engine.sync_engine, "connect", _setup_sqlite)
        event.listen(engine.sync_engine, "begin", _begin_sqlite)


class NewsRepository:
    """Owns its engine; create one per application lifecycle and close at shutdown."""

    def __init__(self, settings: RepositorySettings) -> None:
        try:
            settings = RepositorySettings.model_validate(settings)
            self.engine = create_async_engine(
                settings.database_url.get_secret_value(), echo=False, hide_parameters=True
            )
            _configure_engine(self.engine)
            self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
            self._ready_invalidators: list[ReadyInvalidator] = []
            # SQLite(:memory: 포함)는 커넥션을 공유하므로 겹친 BEGIN IMMEDIATE가
            # "cannot start a transaction within a transaction"으로 실패한다.
            # 방언이 sqlite일 때만 세션 트랜잭션을 직렬화한다.
            self._serialize = self.engine.dialect.name == "sqlite"
            self._tx_lock = asyncio.Lock()
        except Exception:  # noqa: BLE001 -- invalid DSNs can contain credentials
            raise RepositoryError(DB_FAILED) from None

    def add_ready_invalidator(self, invalidator: ReadyInvalidator) -> None:
        """Register once at application startup; callbacks run after a READY commit.

        Notification is best effort, not an outbox: failures/crashes can leave
        previously cached lists alive until their TTL. DB commits remain durable.
        """
        if not any(existing is invalidator for existing in self._ready_invalidators):
            self._ready_invalidators.append(invalidator)

    @_safe_operation
    async def initialize(self) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            await connection.run_sync(_ensure_content_columns)
            await connection.run_sync(_ensure_indexes)

    @_safe_operation
    async def close(self) -> None:
        await self.engine.dispose()

    @asynccontextmanager
    async def _session(self) -> AsyncGenerator[AsyncSession]:
        """SQLite에서는 단일 커넥션 보호를 위해 트랜잭션을 직렬화한다."""
        if self._serialize:
            async with self._tx_lock, self.sessions.begin() as session:
                yield session
        else:
            async with self.sessions.begin() as session:
                yield session

    @_safe_operation
    async def claim(self, canonical_url: HttpUrl, lease_seconds: float) -> ClaimDecision:
        request = ClaimRequest(canonical_url=canonical_url, lease_seconds=lease_seconds)
        key = str(request.canonical_url)
        async with self._session() as session:
            row = await _locked_claim(session, key)
            if (
                row.completed
                or (await session.scalar(select(NewsRow.id).where(NewsRow.canonical_url == key)))
                is not None
            ):
                return ClaimDecision(status="COMPLETED")
            now = await _db_now(session)
            token = uuid4()
            acquired = await session.scalar(
                update(ProcessingClaimRow)
                .where(
                    ProcessingClaimRow.canonical_url == key,
                    ProcessingClaimRow.completed.is_(False),
                    or_(ProcessingClaimRow.token.is_(None), ProcessingClaimRow.expires_at <= now),
                )
                .values(
                    token=str(token), expires_at=now + timedelta(seconds=request.lease_seconds + 1)
                )
                .returning(ProcessingClaimRow.canonical_url)
            )
            if acquired is None:
                return ClaimDecision(status="BUSY")
            return ClaimDecision(
                status="ACQUIRED",
                claim=ProcessingClaim(canonical_url=request.canonical_url, token=token),
            )

    @_safe_operation
    async def complete(self, claim: ProcessingClaim, record: PipelineRecord) -> None:
        claim = ProcessingClaim.model_validate_json(claim.model_dump_json())
        record = PipelineRecord.model_validate_json(record.model_dump_json())
        if claim.canonical_url != record.article.canonical_url:
            raise ClaimOwnershipError(CLAIM_INVALID)
        async with self._session() as session:
            row = await _locked_claim(session, str(claim.canonical_url))
            _require_owner(row, claim, await _db_now(session))
            article = record.article
            news = NewsRow(
                id=str(uuid4()),
                canonical_url=str(article.canonical_url),
                source_name=article.source_name,
                title=article.title,
                category=article.category,
                published_at=article.published_at,
                raw_text=article.raw_text,
            )
            session.add(news)
            await session.flush()  # Both inserts and claim completion share this transaction.
            content = record.content
            lines = content.summary_lines if isinstance(content, SuccessContent) else None
            session.add(
                ContentResultRow(
                    news_id=news.id,
                    status=content.status,
                    content_hash=content.content_hash,
                    line_1=lines[0] if lines is not None else None,
                    line_2=lines[1] if lines is not None else None,
                    line_3=lines[2] if lines is not None else None,
                    translated_text=content.translated_text,
                    engine=content.engine,
                    model_id=content.model_id,
                    prompt_version=content.prompt_version,
                )
            )
            await session.flush()
            row.completed = True
            row.token = None
            row.expires_at = None
        # Transaction has committed. Cache failures must never turn a durable save into failure.
        if isinstance(record.content, SuccessContent):
            for invalidator in tuple(self._ready_invalidators):
                try:
                    async with asyncio.timeout(1):
                        await invalidator.invalidate_lists()
                except Exception:  # noqa: BLE001 -- cache diagnostics may include credentials
                    logger.warning("READY cache notification failed; DB commit retained")

    @_safe_operation
    async def release(self, claim: ProcessingClaim) -> None:
        claim = ProcessingClaim.model_validate_json(claim.model_dump_json())
        async with self._session() as session:
            await session.execute(
                update(ProcessingClaimRow)
                .where(
                    ProcessingClaimRow.canonical_url == str(claim.canonical_url),
                    ProcessingClaimRow.token == str(claim.token),
                    ProcessingClaimRow.completed.is_(False),
                )
                .values(token=None, expires_at=None)
            )

    @_safe_operation
    async def get(self, canonical_url: HttpUrl) -> PipelineRecord | None:
        key = str(NewsKey(canonical_url=canonical_url).canonical_url)
        async with self._session() as session:
            news = (
                await session.scalars(select(NewsRow).where(NewsRow.canonical_url == key))
            ).one_or_none()
            if news is None:
                return None
            content = await session.get(ContentResultRow, news.id)
            if content is None:
                raise RepositoryError(DB_FAILED)
            return PipelineRecord(
                article=CollectedArticle.model_validate(news, from_attributes=True),
                content=CONTENT_RESULT_ADAPTER.validate_python(content, from_attributes=True),
            )

    @_safe_operation
    async def list_candidates(
        self,
        *,
        category: CategoryType,
        cutoff: datetime | None,
        like: str | None,
        search_scope: Literal["title", "content", "all"],
    ) -> tuple[StoredNews, ...]:
        """DB-level pre-filter for list queries: category, freshness, SUCCESS, LIKE.

        `like` must be a pre-escaped lowercase fragment (caller guarantees it is a
        safe superset of the Python-side matcher). The service re-checks every row,
        so false positives are fine but false negatives are not.
        """
        conditions = [
            NewsRow.category == category,
            ContentResultRow.status == "SUCCESS",
        ]
        if cutoff is not None:
            conditions.append(NewsRow.published_at >= cutoff)
        if like is not None:
            pattern = f"%{like}%"
            scope_columns = {
                "title": (NewsRow.title,),
                "content": (
                    NewsRow.raw_text,
                    ContentResultRow.line_1,
                    ContentResultRow.line_2,
                    ContentResultRow.line_3,
                    ContentResultRow.translated_text,
                ),
                "all": (
                    NewsRow.title,
                    NewsRow.source_name,
                    NewsRow.raw_text,
                    ContentResultRow.line_1,
                    ContentResultRow.line_2,
                    ContentResultRow.line_3,
                    ContentResultRow.translated_text,
                ),
            }[search_scope]
            conditions.append(
                or_(
                    *(
                        func.lower(column).like(pattern, escape="\\")
                        for column in scope_columns
                    )
                )
            )
        async with self._session() as session:
            rows = await session.execute(
                select(NewsRow, ContentResultRow)
                .join(ContentResultRow, ContentResultRow.news_id == NewsRow.id)
                .where(*conditions)
            )
            return tuple(_stored_news(news, content) for news, content in rows.all())

    @_safe_operation
    async def count_news(self) -> int:
        """저장된 뉴스 총건수 — 상태 폴링처럼 건수만 필요한 경로용."""
        async with self._session() as session:
            return int(
                await session.scalar(select(func.count()).select_from(NewsRow)) or 0
            )

    @_safe_operation
    async def list_news(self) -> tuple[StoredNews, ...]:
        """Return all completed records so READY ranking happens before slicing."""
        async with self._session() as session:
            rows = await session.execute(
                select(NewsRow, ContentResultRow).outerjoin(
                    ContentResultRow, ContentResultRow.news_id == NewsRow.id
                )
            )
            return tuple(_stored_news(news, content) for news, content in rows.all())

    @_safe_operation
    async def update_content(self, canonical_url: str, content: ContentResult) -> bool:
        """Reprocess path: replace the stored result for an existing article."""
        key = NewsKey(canonical_url=HttpUrl(canonical_url)).canonical_url
        async with self._session() as session:
            news = (
                await session.scalars(
                    select(NewsRow).where(NewsRow.canonical_url == str(key))
                )
            ).one_or_none()
            if news is None:
                return False
            row = await session.get(ContentResultRow, news.id)
            if row is None:
                raise RepositoryError(DB_FAILED)
            lines = content.summary_lines if isinstance(content, SuccessContent) else None
            row.status = content.status
            row.content_hash = content.content_hash
            row.line_1 = lines[0] if lines is not None else None
            row.line_2 = lines[1] if lines is not None else None
            row.line_3 = lines[2] if lines is not None else None
            row.translated_text = content.translated_text
            row.engine = content.engine
            row.model_id = content.model_id
            row.prompt_version = content.prompt_version
            return True

    @_safe_operation
    async def delete_records(self, canonical_urls: tuple[str, ...]) -> int:
        """Delete stored articles and their processing claims so feeds re-collect them.

        ContentResultRow rows cascade via the news_id foreign key. Claim rows must
        be removed too: a completed claim would otherwise block re-processing.
        """
        if not canonical_urls:
            return 0
        async with self._session() as session:
            result = await session.execute(
                delete(NewsRow).where(NewsRow.canonical_url.in_(canonical_urls))
            )
            await session.execute(
                delete(ProcessingClaimRow).where(
                    ProcessingClaimRow.canonical_url.in_(canonical_urls)
                )
            )
            cursor_result = cast(CursorResult[object], result)
            return cursor_result.rowcount

    @_safe_operation
    async def get_by_id(self, news_id: UUID) -> StoredNews | None:
        key = NewsIdentifier(id=news_id)
        async with self._session() as session:
            rows = await session.execute(
                select(NewsRow, ContentResultRow)
                .outerjoin(ContentResultRow, ContentResultRow.news_id == NewsRow.id)
                .where(NewsRow.id == str(key.id))
            )
            row = rows.one_or_none()
            return None if row is None else _stored_news(row[0], row[1])


def _stored_news(news: NewsRow, content: ContentResultRow | None) -> StoredNews:
    if content is None:
        raise RepositoryError(DB_FAILED)
    return StoredNews(
        id=UUID(news.id),
        record=PipelineRecord(
            article=CollectedArticle.model_validate(news, from_attributes=True),
            content=CONTENT_RESULT_ADAPTER.validate_python(content, from_attributes=True),
        ),
    )

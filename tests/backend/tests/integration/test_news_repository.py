"""Real temporary SQLite integration tests; PostgreSQL tests compile SQL only."""

import asyncio
import hashlib
import socket
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import pytest
import pytest_asyncio
from pydantic import HttpUrl, SecretStr, ValidationError
from sqlalchemy import delete, event, func, select, update
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.engine import URL, Connection
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateTable
from src.backend.app.repositories.news_repository import (
    Base,
    ClaimOwnershipError,
    ContentResultRow,
    NewsRepository,
    NewsRow,
    ProcessingClaimRow,
    RepositoryError,
    RepositorySettings,
    StoredNews,
    UTCDateTime,
)
from src.backend.app.schemas.collector import CollectedArticle, CollectionResult, CollectorSource
from src.backend.app.schemas.content import (
    ContentPolicy,
    GeneratedContent,
    InsufficientContent,
    LLMRequest,
    PrivacyDecision,
    SuccessContent,
)
from src.backend.app.workers.ai_processor import AIProcessor
from src.backend.app.workers.collector_worker import (
    CollectorWorker,
    PipelineRecord,
    PipelineRepository,
    ProcessingClaim,
)

BODY = "Acme released an AI model with 3.5 billion parameters. It achieved 90% accuracy."
LINES = ("Acme가 모델을 발표했다.", "매개변수는 3.5 billion이다.", "정확도는 90%이다.")
TRANSLATION = "Acme는 3.5 billion 매개변수 모델을 발표했다. 정확도는 90%이다."
URL_TEXT = "https://news.example/article"
ROLLBACK_ERROR = "secret-token simulated database failure"


@pytest.fixture(autouse=True)
def no_external_connections(monkeypatch: pytest.MonkeyPatch) -> None:
    def deny(*args: object, **kwargs: object) -> None:
        pytest.fail("Repository tests must not connect to external services")

    async def deny_async(*args: object, **kwargs: object) -> None:
        deny()

    monkeypatch.setattr(socket, "getaddrinfo", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(asyncio.BaseEventLoop, "create_connection", deny_async)


def settings(path: Path) -> RepositorySettings:
    url = URL.create("sqlite+aiosqlite", database=path.as_posix())
    return RepositorySettings(database_url=SecretStr(str(url)))


@pytest.fixture
def database_path() -> Generator[Path]:
    # The managed environment permits writes in the workspace, not the OS temp root.
    workspace = Path(__file__).resolve().parents[2]
    cache = workspace / ".pytest_cache"
    cache.mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="news-repository-", dir=cache) as directory:
        yield Path(directory) / "news.sqlite3"


@pytest_asyncio.fixture
async def repository(database_path: Path) -> AsyncGenerator[NewsRepository]:
    repo = NewsRepository(settings(database_path))
    try:
        await repo.initialize()
        yield repo
    finally:
        await repo.close()


def record(url: str = URL_TEXT, *, insufficient: bool = False) -> PipelineRecord:
    article = CollectedArticle(
        source_name="Approved AI",
        title="AI update",
        canonical_url=HttpUrl(url),
        published_at=datetime(2026, 11, 8, tzinfo=UTC),
        raw_text=None if insufficient else BODY,
    )
    digest = hashlib.sha256((article.raw_text or "").encode()).hexdigest()
    content = (
        InsufficientContent(content_hash=digest)
        if insufficient
        else SuccessContent(content_hash=digest, summary_lines=LINES, translated_text=TRANSLATION)
    )
    return PipelineRecord(article=article, content=content)


async def counts(repo: NewsRepository) -> tuple[int, int]:
    async with repo.sessions.begin() as session:
        news = (await session.execute(select(func.count()).select_from(NewsRow))).scalar_one()
        content = (
            await session.execute(select(func.count()).select_from(ContentResultRow))
        ).scalar_one()
        return news, content


async def save(repo: NewsRepository, data: PipelineRecord) -> None:
    decision = await repo.claim(data.article.canonical_url, 60)
    assert decision.claim is not None
    await repo.complete(decision.claim, data)


def news_row(data: PipelineRecord) -> NewsRow:
    article = data.article
    return NewsRow(
        id=str(uuid4()),
        canonical_url=str(article.canonical_url),
        source_name=article.source_name,
        title=article.title,
        category=article.category,
        published_at=article.published_at,
        raw_text=article.raw_text,
    )


async def insert_rows(repo: NewsRepository, *rows: Base) -> None:
    async with repo.sessions.begin() as session:
        for row in rows:
            session.add(row)
            await session.flush()


@pytest.mark.asyncio
@pytest.mark.parametrize("insufficient", [False, True])
async def test_atomic_roundtrip_and_utc(repository: NewsRepository, insufficient: bool) -> None:
    data = record(insufficient=insufficient)
    await save(repository, data)
    loaded = await repository.get(HttpUrl("https://NEWS.example:443/article#fragment"))
    assert loaded == data
    assert loaded is not None
    assert loaded.article.published_at.tzinfo is UTC
    assert await counts(repository) == (1, 1)
    assert (await repository.claim(data.article.canonical_url, 60)).status == "COMPLETED"


@pytest.mark.asyncio
async def test_missing_news(repository: NewsRepository) -> None:
    assert await repository.get(HttpUrl(URL_TEXT)) is None


@pytest.mark.asyncio
async def test_db_unique_canonical_url(repository: NewsRepository) -> None:
    data = record()
    await save(repository, data)
    with pytest.raises(IntegrityError):
        await insert_rows(repository, news_row(data))
    assert await counts(repository) == (1, 1)


@pytest.mark.asyncio
async def test_db_one_to_one_constraint(repository: NewsRepository) -> None:
    await save(repository, record())
    async with repository.sessions.begin() as session:
        news_id = (await session.execute(select(NewsRow.id))).scalar_one()
    duplicate = ContentResultRow(news_id=news_id, status="INSUFFICIENT", content_hash="a" * 64)
    with pytest.raises(IntegrityError):
        await insert_rows(repository, duplicate)
    assert await counts(repository) == (1, 1)


@pytest.mark.asyncio
async def test_foreign_key_and_delete_cascade(repository: NewsRepository) -> None:
    orphan = ContentResultRow(news_id=str(uuid4()), status="INSUFFICIENT", content_hash="a" * 64)
    with pytest.raises(IntegrityError):
        await insert_rows(repository, orphan)
    assert await counts(repository) == (0, 0)
    await save(repository, record())
    async with repository.sessions.begin() as session:
        await session.execute(delete(NewsRow))
    assert await counts(repository) == (0, 0)


@pytest.mark.asyncio
async def test_db_rejects_incomplete_success(repository: NewsRepository) -> None:
    news = news_row(record())
    incomplete = ContentResultRow(news_id=news.id, status="SUCCESS", content_hash="a" * 64)
    with pytest.raises(IntegrityError):
        await insert_rows(repository, news, incomplete)
    assert await counts(repository) == (0, 0)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_table", ["content_results", "news_processing_claims"])
async def test_transaction_rolls_back_both_rows_and_completion(
    repository: NewsRepository,
    failure_table: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    data = record()
    decision = await repository.claim(data.article.canonical_url, 60)
    assert decision.claim is not None

    def fail_statement(
        connection: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        if (
            failure_table == "content_results"
            and statement.startswith("INSERT INTO content_results")
        ) or (
            failure_table == "news_processing_claims"
            and statement.startswith("UPDATE news_processing_claims")
        ):
            raise RuntimeError(ROLLBACK_ERROR)

    event.listen(repository.engine.sync_engine, "before_cursor_execute", fail_statement)
    try:
        with pytest.raises(RepositoryError, match="safely") as caught:
            await repository.complete(decision.claim, data)
    finally:
        event.remove(repository.engine.sync_engine, "before_cursor_execute", fail_statement)
    assert "secret-token" not in str(caught.value)
    assert "secret-token" not in caplog.text
    assert await counts(repository) == (0, 0)
    assert (await repository.claim(data.article.canonical_url, 60)).status == "BUSY"
    # The original token remains valid after transaction rollback; a retry is safe.
    await repository.complete(decision.claim, data)
    assert await counts(repository) == (1, 1)


@pytest.mark.asyncio
async def test_concurrent_claims_across_independent_engines(repository: NewsRepository) -> None:
    other = NewsRepository(RepositorySettings(database_url=SecretStr(str(repository.engine.url))))
    try:
        results = await asyncio.gather(
            *(
                (repository if index % 2 else other).claim(HttpUrl(URL_TEXT), 60)
                for index in range(12)
            )
        )
        owners = [decision.claim for decision in results if decision.status == "ACQUIRED"]
        assert len(owners) == 1
        assert sum(decision.status == "BUSY" for decision in results) == 11
        owner = owners[0]
        assert owner is not None
        await repository.complete(owner, record())
        assert (await other.claim(HttpUrl(URL_TEXT), 60)).status == "COMPLETED"
        assert await other.get(HttpUrl(URL_TEXT)) == record()
        assert await counts(other) == (1, 1)
    finally:
        await other.close()


@pytest.mark.asyncio
async def test_release_is_idempotent_and_token_fenced(repository: NewsRepository) -> None:
    first = (await repository.claim(HttpUrl(URL_TEXT), 60)).claim
    assert first is not None
    await repository.release(first)
    await repository.release(first)
    second = (await repository.claim(HttpUrl(URL_TEXT), 60)).claim
    assert second is not None
    assert second.token != first.token
    await repository.release(first)
    assert (await repository.claim(HttpUrl(URL_TEXT), 60)).status == "BUSY"
    with pytest.raises(ClaimOwnershipError):
        await repository.complete(first, record())
    await repository.complete(second, record())
    await repository.release(second)
    assert (await repository.claim(HttpUrl(URL_TEXT), 60)).status == "COMPLETED"


@pytest.mark.asyncio
async def test_expired_claim_is_replaced(repository: NewsRepository) -> None:
    first = (await repository.claim(HttpUrl(URL_TEXT), 60)).claim
    assert first is not None
    async with repository.sessions.begin() as session:
        await session.execute(
            update(ProcessingClaimRow).values(expires_at=datetime(2000, 1, 1, tzinfo=UTC))
        )
    with pytest.raises(ClaimOwnershipError):
        await repository.complete(first, record())
    assert await counts(repository) == (0, 0)
    second = (await repository.claim(HttpUrl(URL_TEXT), 60)).claim
    assert second is not None
    assert second.token != first.token
    await repository.release(first)
    assert (await repository.claim(HttpUrl(URL_TEXT), 60)).status == "BUSY"
    await repository.complete(second, record())


@pytest.mark.asyncio
async def test_mismatched_url_rejected(repository: NewsRepository) -> None:
    owner = (await repository.claim(HttpUrl(URL_TEXT), 60)).claim
    assert owner is not None
    with pytest.raises(ClaimOwnershipError):
        await repository.complete(owner, record("https://news.example/different"))
    assert await counts(repository) == (0, 0)


@pytest.mark.asyncio
async def test_reopen_preserves_records_and_claims(database_path: Path) -> None:
    config = settings(database_path)
    first = NewsRepository(config)
    await first.initialize()
    waiting = HttpUrl("https://news.example/waiting")
    try:
        await save(first, record())
        assert (await first.claim(waiting, 60)).status == "ACQUIRED"
    finally:
        await first.close()
    reopened = NewsRepository(config)
    try:
        assert await reopened.get(HttpUrl(URL_TEXT)) == record()
        assert (await reopened.claim(HttpUrl(URL_TEXT), 60)).status == "COMPLETED"
        assert (await reopened.claim(waiting, 60)).status == "BUSY"
    finally:
        await reopened.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("lease", [0.0, -1.0, float("nan"), float("inf")])
async def test_invalid_claim_inputs_do_not_write(repository: NewsRepository, lease: float) -> None:
    with pytest.raises(RepositoryError):
        await repository.claim(HttpUrl(URL_TEXT), lease)
    async with repository.sessions.begin() as session:
        assert (
            await session.execute(select(func.count()).select_from(ProcessingClaimRow))
        ).scalar_one() == 0


@pytest.mark.asyncio
async def test_boundary_rejects_corrupted_input_and_output(repository: NewsRepository) -> None:
    data = record()
    owner = (await repository.claim(data.article.canonical_url, 60)).claim
    assert owner is not None
    # A deliberately bypassed model must be revalidated at the repository boundary.
    forged_content = SuccessContent.model_construct(
        content_hash="invalid", summary_lines=LINES, translated_text=TRANSLATION
    )
    forged = PipelineRecord.model_construct(article=data.article, content=forged_content)
    with pytest.raises(RepositoryError):
        await repository.complete(owner, forged)
    assert await counts(repository) == (0, 0)
    await repository.complete(owner, data)
    async with repository.sessions.begin() as session:
        await session.execute(update(ContentResultRow).values(line_1="Not a sentence"))
    with pytest.raises(RepositoryError):
        await repository.get(data.article.canonical_url)


@pytest.mark.asyncio
async def test_parameterized_text_and_safe_logs(
    repository: NewsRepository, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("DEBUG")
    data = record()
    # Literal text must be stored as data, never executable SQL or a log argument.
    article = CollectedArticle(
        source_name=data.article.source_name,
        title="secret-token '; DROP TABLE news; --",
        canonical_url=data.article.canonical_url,
        published_at=data.article.published_at,
        raw_text="private-body secret-token",
    )
    saved = PipelineRecord(article=article, content=data.content)
    await save(repository, saved)
    assert await repository.get(article.canonical_url) == saved
    assert "secret-token" not in caplog.text
    assert "private-body" not in caplog.text
    assert "Traceback" not in caplog.text


class FakeCollector:
    async def collect(self, source: CollectorSource) -> CollectionResult:
        return CollectionResult(source_name=source.source_name, articles=(record().article,))


class FakeLLM:
    def __init__(self) -> None:
        self.calls = 0
        self.fail = False
        self.started = asyncio.Event()
        self.hold: asyncio.Event | None = None

    async def generate(self, request: LLMRequest) -> str:
        self.calls += 1
        self.started.set()
        if self.hold is not None:
            await self.hold.wait()
        if self.fail:
            raise RuntimeError(ROLLBACK_ERROR)
        return GeneratedContent(summary_lines=LINES, translated_text=TRANSLATION).model_dump_json()


class FakeGuard:
    async def sanitize(self, text: str) -> PrivacyDecision:
        return PrivacyDecision(approved=True, sanitized_text=text, protected_terms=("Acme",))


class FakeCache:
    def __init__(self) -> None:
        self.entries: list[tuple[str, str]] = []
        self.gate = asyncio.Lock()

    async def get(self, key: str) -> str | None:
        return next((value for saved, value in self.entries if saved == key), None)

    async def put(self, key: str, value: str, ttl_seconds: int) -> None:
        self.entries.append((key, value))

    @asynccontextmanager
    async def lock(self, key: str, lease_seconds: float) -> AsyncGenerator[None]:
        async with self.gate:
            yield


@pytest.mark.asyncio
async def test_worker_and_real_ai_processor_use_sqlite_repository(
    repository: NewsRepository,
) -> None:
    llm = FakeLLM()
    processor = AIProcessor(
        llm=llm,
        cache=FakeCache(),
        privacy_guard=FakeGuard(),
        policy=ContentPolicy(
            model_version="fake-v1", privacy_version="fixture-v1", min_body_chars=20
        ),
    )
    # This assignment checks structural compatibility with the Worker's actual protocol.
    contract: PipelineRepository = repository
    worker = CollectorWorker(collector=FakeCollector(), processor=processor, repository=contract)
    source = CollectorSource(
        source_name="Approved AI",
        feed_url=HttpUrl("https://news.example/rss"),
        allowed_hosts=("news.example",),
    )
    llm.fail = True
    assert (await worker.run_once(source)).failed_count == 1
    assert await counts(repository) == (0, 0)
    llm.fail = False
    assert (await worker.run_once(source)).stored_count == 1
    assert (await worker.run_once(source)).duplicate_count == 1
    assert llm.calls == 2  # One failed attempt, one successful call, no call for the replay.
    assert await counts(repository) == (1, 1)
    loaded = await repository.get(HttpUrl(URL_TEXT))
    assert loaded is not None
    assert isinstance(loaded.content, SuccessContent)
    assert loaded.content.summary_lines == LINES


def test_postgresql_and_sqlite_ddl_compile_without_connections() -> None:
    for dialect in (sqlite.dialect(), postgresql.dialect()):
        ddl = "\n".join(
            str(CreateTable(table).compile(dialect=dialect))
            for table in Base.metadata.sorted_tables
        )
        assert "UNIQUE (canonical_url)" in ddl
        assert "FOREIGN KEY(news_id)" in ddl
        assert "PRIMARY KEY (news_id)" in ddl
        assert "CHECK" in ddl
        statement = (
            update(ProcessingClaimRow)
            .where(ProcessingClaimRow.completed.is_(False))
            .values(token=str(uuid4()))
            .returning(ProcessingClaimRow.canonical_url)
        )
        assert "RETURNING" in str(statement.compile(dialect=dialect))


@pytest.mark.asyncio
async def test_postgresql_async_driver_constructs_without_connecting() -> None:
    repo = NewsRepository(
        RepositorySettings(
            database_url=SecretStr("postgresql+psycopg://fixture:secret-token@invalid.example/dait")
        )
    )
    try:
        assert repo.engine.dialect.name == "postgresql"
        assert repo.engine.dialect.is_async
    finally:
        await repo.close()


def test_settings_secret_and_utc_validation() -> None:
    config = RepositorySettings(
        database_url=SecretStr("postgresql+psycopg://user:secret-token@host/db")
    )
    assert "secret-token" not in repr(config)
    with pytest.raises(ValidationError):
        config.database_url = SecretStr("other")
    naive = datetime(2026, 11, 8, tzinfo=UTC).replace(tzinfo=None)
    with pytest.raises(ValueError, match="timezone-aware"):
        UTCDateTime().process_bind_param(naive, sqlite.dialect())


@pytest.mark.asyncio
async def test_unowned_complete_leaves_no_claim_or_partial_rows(repository: NewsRepository) -> None:
    unowned = ProcessingClaim(canonical_url=HttpUrl(URL_TEXT), token=uuid4())
    with pytest.raises(ClaimOwnershipError):
        await repository.complete(unowned, record())
    assert await counts(repository) == (0, 0)
    async with repository.sessions.begin() as session:
        assert (
            await session.execute(select(func.count()).select_from(ProcessingClaimRow))
        ).scalar_one() == 0
    assert (await repository.claim(HttpUrl(URL_TEXT), 60)).status == "ACQUIRED"


@pytest.mark.asyncio
async def test_concurrent_completion_commits_only_once(repository: NewsRepository) -> None:
    owner = (await repository.claim(HttpUrl(URL_TEXT), 60)).claim
    assert owner is not None
    results = await asyncio.gather(
        repository.complete(owner, record()),
        repository.complete(owner, record()),
        return_exceptions=True,
    )
    assert sum(result is None for result in results) == 1
    assert sum(isinstance(result, ClaimOwnershipError) for result in results) == 1
    assert await counts(repository) == (1, 1)


@pytest.mark.asyncio
async def test_independent_workers_sqlite_claim_prevents_concurrent_llm(
    repository: NewsRepository,
) -> None:
    other = NewsRepository(RepositorySettings(database_url=SecretStr(str(repository.engine.url))))
    llm = FakeLLM()
    llm.hold = asyncio.Event()
    source = CollectorSource(
        source_name="Approved AI",
        feed_url=HttpUrl("https://news.example/rss"),
        allowed_hosts=("news.example",),
    )
    policy = ContentPolicy(model_version="fake-v1", privacy_version="fixture-v1", min_body_chars=20)
    first = CollectorWorker(
        collector=FakeCollector(),
        repository=repository,
        processor=AIProcessor(llm=llm, cache=FakeCache(), privacy_guard=FakeGuard(), policy=policy),
    )
    second = CollectorWorker(
        collector=FakeCollector(),
        repository=other,
        processor=AIProcessor(llm=llm, cache=FakeCache(), privacy_guard=FakeGuard(), policy=policy),
    )
    task = asyncio.create_task(first.run_once(source))
    try:
        await asyncio.wait_for(llm.started.wait(), timeout=2)
        assert (await second.run_once(source)).busy_count == 1
        llm.hold.set()
        assert (await task).stored_count == 1
        assert (await second.run_once(source)).duplicate_count == 1
        assert llm.calls == 1
        assert await counts(repository) == (1, 1)
    finally:
        llm.hold.set()
        if not task.done():
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        await other.close()


@pytest.mark.asyncio
async def test_id_and_list_reads_preserve_validated_models(repository: NewsRepository) -> None:
    data = record()
    await save(repository, data)
    listed = await repository.list_news()
    assert len(listed) == 1
    assert listed[0].record == data
    assert await repository.get_by_id(listed[0].id) == listed[0]
    assert await repository.get_by_id(uuid4()) is None
    assert await repository.get(data.article.canonical_url) == data
    with pytest.raises(ValidationError):
        listed[0].id = uuid4()


@pytest.mark.asyncio
async def test_ready_notification_runs_after_atomic_commit_and_only_on_success(
    repository: NewsRepository,
) -> None:
    observed: list[tuple[StoredNews, ...]] = []

    class Observer:
        async def invalidate_lists(self) -> None:
            # A new independent transaction can see the committed news/content pair.
            observed.append(await repository.list_news())

    observer = Observer()
    repository.add_ready_invalidator(observer)
    repository.add_ready_invalidator(observer)
    data = record()
    owner = (await repository.claim(data.article.canonical_url, 60)).claim
    assert owner is not None
    await repository.complete(owner, data)
    assert len(observed) == 1
    assert observed[0][0].record == data
    with pytest.raises(ClaimOwnershipError):
        await repository.complete(owner, data)
    await save(repository, record("https://news.example/insufficient", insufficient=True))
    assert len(observed) == 1


@pytest.mark.asyncio
async def test_failed_notification_keeps_committed_rows(
    repository: NewsRepository, caplog: pytest.LogCaptureFixture
) -> None:
    class UnavailableCache:
        async def invalidate_lists(self) -> None:
            raise ConnectionError(ROLLBACK_ERROR)

    repository.add_ready_invalidator(UnavailableCache())
    data = record()
    await save(repository, data)
    assert await repository.get(data.article.canonical_url) == data
    assert await counts(repository) == (1, 1)
    assert "secret-token" not in caplog.text


@pytest.mark.asyncio
async def test_real_repository_news_service_fallback_without_redis(
    repository: NewsRepository,
) -> None:
    from src.backend.app.services.news_service import NewsService, NewsServicePolicy, SourcePriority

    class UnavailableCache:
        async def generation(self) -> str:
            raise ConnectionError(ROLLBACK_ERROR)

        async def get_list(self, key: str, generation: str) -> str | None:
            raise ConnectionError(ROLLBACK_ERROR)

        async def put_list(self, key: str, generation: str, value: str, ttl_seconds: int) -> bool:
            raise ConnectionError(ROLLBACK_ERROR)

        async def get_detail(self, key: str) -> str | None:
            raise ConnectionError(ROLLBACK_ERROR)

        async def put_detail(self, key: str, value: str, ttl_seconds: int) -> None:
            raise ConnectionError(ROLLBACK_ERROR)

        async def invalidate_lists(self) -> None:
            raise ConnectionError(ROLLBACK_ERROR)

    app = NewsService(
        repository=repository,
        cache=UnavailableCache(),
        policy=NewsServicePolicy(
            source_priorities=(SourcePriority(source_name="Approved AI", priority=0),)
        ),
    )
    await save(repository, record())
    listed = await app.list_news(5)
    assert len(listed.items) == 1
    assert listed.items[0].status == "READY"
    assert await app.get_detail(listed.items[0].id) == listed.items[0]

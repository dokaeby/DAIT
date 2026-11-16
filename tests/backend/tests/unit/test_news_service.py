"""Fake/Mock news service tests; no real Redis, DB, source or LLM connections."""

import asyncio
import socket
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

import pytest
from pydantic import HttpUrl, ValidationError
from redis.asyncio import Redis
from src.backend.app.core.taxonomy import CategoryType
from src.backend.app.repositories.news_repository import (
    ReadyInvalidator,
    RepositoryError,
    StoredNews,
)
from src.backend.app.schemas.collector import CollectedArticle
from src.backend.app.schemas.content import InsufficientContent, SuccessContent
from src.backend.app.schemas.news import NewsQuery
from src.backend.app.services.news_service import (
    DETAIL_TTL_SECONDS,
    GENERATION_KEY,
    GET_LIST_SCRIPT,
    LIST_TTL_SECONDS,
    PUT_LIST_SCRIPT,
    NewsListResponse,
    NewsService,
    NewsServiceError,
    NewsServicePolicy,
    RedisNewsCache,
    SourcePriority,
)
from src.backend.app.services.ranking_service import RankedNews, RankingRequest, RankingService
from src.backend.app.workers.collector_worker import PipelineRecord

TIME = datetime(2026, 11, 8, tzinfo=UTC)
LINES = ("AI 뉴스가 발표됐다.", "새 모델을 소개했다.", "연구 결과를 공개했다.")
ADAPTER_ERROR = "secret-token cache failure"
DB_ERROR = "Database unavailable"


@pytest.fixture(autouse=True)
def no_external_connections(monkeypatch: pytest.MonkeyPatch) -> None:
    def deny(*args: object, **kwargs: object) -> None:
        pytest.fail("NewsService unit tests must not use real network services")

    async def deny_async(*args: object, **kwargs: object) -> None:
        deny()

    monkeypatch.setattr(socket, "getaddrinfo", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(asyncio.BaseEventLoop, "create_connection", deny_async)
    monkeypatch.setattr(Redis, "execute_command", deny_async)


def news(
    identifier: int = 1,
    *,
    ready: bool = True,
    source: str = "Source A",
    published_at: datetime = TIME,
) -> StoredNews:
    content = (
        SuccessContent(
            content_hash="a" * 64,
            summary_lines=LINES,
            translated_text="새 모델의 연구 결과를 공개했다.",
        )
        if ready
        else InsufficientContent(content_hash="b" * 64)
    )
    article = CollectedArticle(
        source_name=source,
        title=f"AI news {identifier}",
        canonical_url=HttpUrl(f"https://news.example/{identifier}"),
        published_at=published_at,
        raw_text="private-body",
    )
    return StoredNews(
        id=UUID(int=identifier), record=PipelineRecord(article=article, content=content)
    )


class FakeRepository:
    def __init__(self, entries: tuple[StoredNews, ...] = ()) -> None:
        self.entries = entries
        self.list_calls = 0
        self.detail_calls = 0
        self.listeners: list[ReadyInvalidator] = []
        self.fail = False
        self.after_list: Callable[[], Awaitable[None]] | None = None

    def add_ready_invalidator(self, invalidator: ReadyInvalidator) -> None:
        if not any(existing is invalidator for existing in self.listeners):
            self.listeners.append(invalidator)

    async def list_news(self) -> tuple[StoredNews, ...]:
        self.list_calls += 1
        if self.fail:
            raise RepositoryError(DB_ERROR)
        snapshot = self.entries
        if self.after_list is not None:
            await self.after_list()
        return snapshot

    async def list_candidates(
        self,
        *,
        category: CategoryType,
        cutoff: datetime | None,
        like: str | None,
        search_scope: Literal["title", "content", "all"],
    ) -> tuple[StoredNews, ...]:
        # Fake는 필터를 적용하지 않고 전체를 반환한다 — 서비스의 Python 재검증이
        # 최종 결과를 결정하므로 superset 반환으로 충분하다.
        return await self.list_news()

    async def get_by_id(self, news_id: UUID) -> StoredNews | None:
        self.detail_calls += 1
        if self.fail:
            raise RepositoryError(DB_ERROR)
        return next((entry for entry in self.entries if entry.id == news_id), None)

    async def commit(self, entry: StoredNews) -> None:
        if self.fail:
            raise RepositoryError(DB_ERROR)
        self.entries += (entry,)
        if isinstance(entry.record.content, SuccessContent):
            for listener in self.listeners:
                await listener.invalidate_lists()


class FakeCache:
    def __init__(self) -> None:
        self.version = 1
        self.now = 0.0
        self.entries: list[tuple[str, str, float]] = []
        self.list_writes: list[tuple[str, str, int]] = []
        self.detail_writes: list[tuple[str, int]] = []
        self.invalidations = 0
        self.fail_operations: set[str] = set()
        self.slow_operations: set[str] = set()
        self.invalidate_before_get = False
        self.invalidate_before_put = False
        self.rejected_writes = 0

    async def check(self, operation: str) -> None:
        if operation in self.slow_operations:
            await asyncio.sleep(0.05)
        if operation in self.fail_operations:
            raise ConnectionError(ADAPTER_ERROR)

    def lookup(self, key: str) -> str | None:
        return next(
            (
                value
                for stored, value, expiry in self.entries
                if stored == key and expiry > self.now
            ),
            None,
        )

    def store(self, key: str, value: str, ttl: int) -> None:
        self.entries = [
            (stored, old, expiry) for stored, old, expiry in self.entries if stored != key
        ]
        self.entries.append((key, value, self.now + ttl))

    async def generation(self) -> str:
        await self.check("generation")
        return str(self.version)

    async def get_list(self, key: str, generation: str) -> str | None:
        await self.check("get_list")
        if self.invalidate_before_get:
            self.version += 1
            self.invalidate_before_get = False
        return self.lookup(key) if generation == str(self.version) else None

    async def put_list(self, key: str, generation: str, value: str, ttl_seconds: int) -> bool:
        await self.check("put_list")
        if self.invalidate_before_put:
            self.version += 1
            self.invalidate_before_put = False
        if generation != str(self.version):
            self.rejected_writes += 1
            return False
        self.store(key, value, ttl_seconds)
        self.list_writes.append((key, generation, ttl_seconds))
        return True

    async def get_detail(self, key: str) -> str | None:
        await self.check("get_detail")
        return self.lookup(key)

    async def put_detail(self, key: str, value: str, ttl_seconds: int) -> None:
        await self.check("put_detail")
        self.store(key, value, ttl_seconds)
        self.detail_writes.append((key, ttl_seconds))

    async def invalidate_lists(self) -> None:
        await self.check("invalidate_lists")
        self.version += 1
        self.invalidations += 1


class SpyRanking:
    calls: list[RankingRequest]

    def __init__(self) -> None:
        self.calls = []

    def rank(self, request: RankingRequest) -> tuple[RankedNews, ...]:
        self.calls.append(request)
        return RankingService.rank(request)


def policy(timeout: float = 0.01) -> NewsServicePolicy:
    return NewsServicePolicy(
        source_priorities=(
            SourcePriority(source_name="Source A", priority=1),
            SourcePriority(source_name="Source B", priority=0),
        ),
        cache_timeout_seconds=timeout,
    )


def service(repository: FakeRepository, cache: FakeCache) -> NewsService:
    return NewsService(repository=repository, cache=cache, policy=policy())


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [5, 10])
async def test_ranked_list_slicing_and_cache_hit(limit: int) -> None:
    repository = FakeRepository(
        tuple(news(i, published_at=TIME + timedelta(minutes=i)) for i in range(1, 16))
    )
    cache, ranking = FakeCache(), SpyRanking()
    app = NewsService(repository=repository, cache=cache, policy=policy(), ranking=ranking)
    request_limit = 5 if limit == 5 else 10
    first = await app.list_news(request_limit)
    second = await app.list_news(request_limit)
    assert first == second
    assert tuple(item.id.int for item in first.items) == tuple(range(15, 15 - limit, -1))
    assert len(ranking.calls) == 1
    assert repository.list_calls == 1
    assert cache.list_writes[0][2] == LIST_TTL_SECONDS == 300
    assert len(ranking.calls[0].candidates) == 15
    assert "private-body" not in first.model_dump_json()


@pytest.mark.asyncio
async def test_ready_and_configured_source_priority_are_used() -> None:
    repository = FakeRepository(
        (
            news(1, ready=False, published_at=TIME + timedelta(days=10)),
            news(2),
            news(3, source="Source B"),
        )
    )
    result = await service(repository, FakeCache()).list_news()
    assert tuple(item.id.int for item in result.items) == (3, 2, 1)
    assert tuple(item.status for item in result.items) == ("READY", "READY", "INSUFFICIENT")


@pytest.mark.asyncio
async def test_detail_cache_hit_and_ttl() -> None:
    repository, cache = FakeRepository((news(),)), FakeCache()
    app = service(repository, cache)
    first = await app.get_detail(UUID(int=1))
    assert first is not None
    assert first.status == "READY"
    assert first.content.summary_lines == LINES
    assert await app.get_detail(UUID(int=1)) == first
    assert repository.detail_calls == 1
    assert cache.detail_writes[0][1] == DETAIL_TTL_SECONDS == 1800


@pytest.mark.asyncio
async def test_detail_missing_is_not_negative_cached() -> None:
    repository, cache = FakeRepository(), FakeCache()
    app = service(repository, cache)
    assert await app.get_detail(UUID(int=1)) is None
    assert not cache.detail_writes
    await repository.commit(news())
    assert await app.get_detail(UUID(int=1)) is not None
    assert repository.detail_calls == 2


@pytest.mark.asyncio
async def test_empty_list_and_insufficient_detail() -> None:
    repository, cache = FakeRepository(), FakeCache()
    app = service(repository, cache)
    assert (await app.list_news()).items == ()
    await repository.commit(news(ready=False))
    result = await app.get_detail(UUID(int=1))
    assert result is not None
    assert result.status == "INSUFFICIENT"
    assert result.content.summary_lines == ()


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["generation", "get_list", "put_list"])
async def test_list_redis_failures_fall_back_to_db(
    operation: str, caplog: pytest.LogCaptureFixture
) -> None:
    repository, cache = FakeRepository((news(),)), FakeCache()
    cache.fail_operations.add(operation)
    result = await service(repository, cache).list_news()
    assert len(result.items) == 1
    assert repository.list_calls == 1
    assert "secret-token" not in caplog.text
    assert "Traceback" not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["get_detail", "put_detail"])
async def test_detail_redis_failures_fall_back_to_db(operation: str) -> None:
    repository, cache = FakeRepository((news(),)), FakeCache()
    cache.fail_operations.add(operation)
    assert await service(repository, cache).get_detail(UUID(int=1)) is not None
    assert repository.detail_calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operation", ["generation", "get_list", "put_list", "get_detail", "put_detail"]
)
async def test_redis_timeouts_are_bounded_and_do_not_fail_response(operation: str) -> None:
    repository, cache = FakeRepository((news(),)), FakeCache()
    cache.slow_operations.add(operation)
    app = service(repository, cache)
    async with asyncio.timeout(1):
        if "detail" in operation:
            assert await app.get_detail(UUID(int=1)) is not None
        else:
            assert len((await app.list_news()).items) == 1


@pytest.mark.asyncio
async def test_new_ready_commit_invalidates_all_list_variants() -> None:
    repository, cache = FakeRepository((news(),)), FakeCache()
    app = service(repository, cache)
    await app.list_news(5)
    await app.list_news(10)
    await app.get_detail(UUID(int=1))
    old_version = cache.version
    await repository.commit(news(2, published_at=TIME + timedelta(days=1)))
    assert cache.version != old_version
    assert tuple(item.id.int for item in (await app.list_news(5)).items) == (2, 1)
    assert tuple(item.id.int for item in (await app.list_news(10)).items) == (2, 1)
    assert await app.get_detail(UUID(int=1)) is not None
    assert repository.list_calls == 4
    assert repository.detail_calls == 1


@pytest.mark.asyncio
async def test_invalidating_during_fill_rejects_stale_cache_write() -> None:
    repository, cache = FakeRepository((news(),)), FakeCache()
    app = service(repository, cache)
    cache.invalidate_before_put = True
    assert len((await app.list_news()).items) == 1
    assert cache.rejected_writes == 1
    assert not cache.list_writes
    await app.list_news()
    assert repository.list_calls == 2
    assert len(cache.list_writes) == 1


@pytest.mark.asyncio
async def test_invalidation_between_generation_and_cached_read_cannot_return_old_entry() -> None:
    repository, cache = FakeRepository((news(),)), FakeCache()
    app = service(repository, cache)
    await app.list_news()
    repository.entries += (news(2),)
    cache.invalidate_before_get = True
    result = await app.list_news()
    assert len(result.items) == 2
    assert repository.list_calls == 2
    assert cache.rejected_writes == 1


@pytest.mark.asyncio
async def test_db_snapshot_preceding_commit_cannot_refill_invalidated_generation() -> None:
    repository, cache = FakeRepository((news(),)), FakeCache()
    app = service(repository, cache)

    async def commit_after_read() -> None:
        repository.after_list = None
        await repository.commit(news(2))

    repository.after_list = commit_after_read
    assert len((await app.list_news()).items) == 1
    assert cache.rejected_writes == 1
    assert len((await app.list_news()).items) == 2


@pytest.mark.asyncio
async def test_invalidation_failure_does_not_rollback_commit_and_old_cache_expires() -> None:
    repository, cache = FakeRepository((news(),)), FakeCache()
    app = service(repository, cache)
    await app.list_news()
    cache.fail_operations.add("invalidate_lists")
    await repository.commit(news(2))
    assert len(repository.entries) == 2
    assert len((await app.list_news()).items) == 1  # Best effort invalidation, bounded by TTL.
    cache.now += 301
    assert len((await app.list_news()).items) == 2


@pytest.mark.asyncio
async def test_only_successful_ready_commit_invalidates() -> None:
    repository, cache = FakeRepository(), FakeCache()
    service(repository, cache)
    await repository.commit(news(ready=False))
    assert cache.invalidations == 0
    repository.fail = True
    with pytest.raises(RepositoryError):
        await repository.commit(news(2))
    assert cache.invalidations == 0


@pytest.mark.asyncio
async def test_list_and_detail_ttl_expiry_use_virtual_clock() -> None:
    repository, cache = FakeRepository((news(),)), FakeCache()
    app = service(repository, cache)
    await app.list_news()
    await app.get_detail(UUID(int=1))
    cache.now = 299
    await app.list_news()
    await app.get_detail(UUID(int=1))
    assert repository.list_calls == repository.detail_calls == 1
    cache.now = 300
    await app.list_news()
    await app.get_detail(UUID(int=1))
    assert repository.list_calls == 2
    assert repository.detail_calls == 1
    cache.now = 1800
    await app.get_detail(UUID(int=1))
    assert repository.detail_calls == 2


@pytest.mark.asyncio
async def test_config_order_shares_cache_but_priority_change_isolated() -> None:
    repository, cache = FakeRepository((news(1), news(2, source="Source B"))), FakeCache()
    app = service(repository, cache)
    assert (await app.list_news()).items[0].id.int == 2
    reverse_policy = NewsServicePolicy(
        source_priorities=tuple(reversed(policy().source_priorities))
    )
    equivalent = NewsService(repository=repository, cache=cache, policy=reverse_policy)
    await equivalent.list_news()
    assert repository.list_calls == 1
    changed = NewsService(
        repository=repository,
        cache=cache,
        policy=NewsServicePolicy(
            source_priorities=(
                SourcePriority(source_name="Source A", priority=0),
                SourcePriority(source_name="Source B", priority=1),
            )
        ),
    )
    assert (await changed.list_news()).items[0].id.int == 1
    assert repository.list_calls == 2


@pytest.mark.asyncio
async def test_corrupt_and_wrong_limit_list_cache_are_ignored() -> None:
    repository, cache = FakeRepository((news(),)), FakeCache()
    app = service(repository, cache)
    valid = await app.list_news()
    key = cache.list_writes[0][0]
    for payload in ("broken-json", valid.model_dump_json().replace('"limit":5', '"limit":10')):
        cache.store(key, payload, 300)
        assert await app.list_news() == valid
    assert repository.list_calls == 3


@pytest.mark.asyncio
async def test_corrupt_wrong_id_and_invalid_summary_detail_cache_are_ignored() -> None:
    repository, cache = FakeRepository((news(),)), FakeCache()
    app = service(repository, cache)
    valid = await app.get_detail(UUID(int=1))
    assert valid is not None
    key = cache.detail_writes[0][0]
    for payload in (
        "broken",
        valid.model_dump_json().replace(str(UUID(int=1)), str(UUID(int=2))),
        valid.model_dump_json().replace(LINES[0], "Not a sentence"),
    ):
        cache.store(key, payload, 1800)
        assert await app.get_detail(UUID(int=1)) == valid
    assert repository.detail_calls == 4


@pytest.mark.asyncio
async def test_db_failure_propagates_instead_of_returning_fake_empty_list() -> None:
    repository, cache = FakeRepository(), FakeCache()
    repository.fail = True
    app = service(repository, cache)
    with pytest.raises(RepositoryError):
        await app.list_news()
    with pytest.raises(RepositoryError):
        await app.get_detail(UUID(int=1))


@pytest.mark.asyncio
async def test_missing_source_priority_is_not_invented() -> None:
    with pytest.raises(NewsServiceError, match="configuration"):
        await service(FakeRepository((news(source="Unconfigured"),)), FakeCache()).list_news()


def test_models_are_frozen_and_reject_unknown_or_conflicting_values() -> None:
    config = policy()
    with pytest.raises(ValidationError):
        config.cache_timeout_seconds = 1
    with pytest.raises(ValidationError):
        NewsServicePolicy(
            source_priorities=(
                SourcePriority(source_name="A", priority=0),
                SourcePriority(source_name="A", priority=1),
            )
        )
    with pytest.raises(ValidationError):
        NewsListResponse.model_validate_json('{"limit":true,"items":[]}')


class FakeRedisWire:
    """Mock the command boundary, not a real Redis interpreter or server."""

    def __init__(self) -> None:
        self.entries: list[tuple[str, str]] = []
        self.sets: list[tuple[str, int | None, bool]] = []
        self.evals: list[tuple[str, int, tuple[str, ...]]] = []
        self.return_bytes = True
        self.invalid_result = False

    async def get(self, key: str) -> bytes | str | None:
        value = next((value for stored, value in self.entries if stored == key), None)
        return value.encode() if self.return_bytes and value is not None else value

    async def set(
        self, key: str, value: str, *, ex: int | None = None, nx: bool = False
    ) -> bool | None:
        self.sets.append((key, ex, nx))
        if nx and any(stored == key for stored, _ in self.entries):
            return None
        self.entries = [(stored, old) for stored, old in self.entries if stored != key]
        self.entries.append((key, value))
        return True

    async def eval(self, script: str, numkeys: int, *args: str) -> object:
        self.evals.append((script, numkeys, args))
        assert numkeys == 2
        assert "{AI}" in args[0]
        assert "{AI}" in args[1]
        if self.invalid_result:
            return 1.5
        generation = await self.get(args[0])
        text = generation.decode() if isinstance(generation, bytes) else generation
        if text != args[2]:
            return None if script == GET_LIST_SCRIPT else 0
        if script == GET_LIST_SCRIPT:
            return await self.get(args[1])
        assert script == PUT_LIST_SCRIPT
        await self.set(args[1], args[3], ex=int(args[4]))
        return 1


@pytest.mark.asyncio
async def test_redis_adapter_wire_contract_ttls_generation_and_atomic_scripts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wire, client = FakeRedisWire(), Redis()
    monkeypatch.setattr(client, "get", wire.get)
    monkeypatch.setattr(client, "set", wire.set)
    monkeypatch.setattr(client, "eval", wire.eval)
    adapter = RedisNewsCache(client)
    try:
        generation = await adapter.generation()
        assert len(generation) == 32
        assert wire.sets[0] == (GENERATION_KEY, None, True)
        key = "dait:news:v1:{AI}:list:fixture:5:" + generation
        assert await adapter.put_list(key, generation, "payload", 300)
        assert await adapter.get_list(key, generation) == "payload"
        await adapter.put_detail("detail-key", "detail", 1800)
        assert await adapter.get_detail("detail-key") == "detail"
        assert ("detail-key", 1800, False) in wire.sets
        await adapter.invalidate_lists()
        assert await adapter.generation() != generation
        assert await adapter.get_list(key, generation) is None
        assert not await adapter.put_list(key, generation, "stale", 300)
        assert wire.evals[0][0] == PUT_LIST_SCRIPT
        assert wire.evals[1][0] == GET_LIST_SCRIPT
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_evicted_generation_is_not_reused_and_invalid_wire_reply_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wire, client = FakeRedisWire(), Redis()
    monkeypatch.setattr(client, "get", wire.get)
    monkeypatch.setattr(client, "set", wire.set)
    monkeypatch.setattr(client, "eval", wire.eval)
    adapter = RedisNewsCache(client)
    try:
        first = await adapter.generation()
        wire.entries.clear()
        second = await adapter.generation()
        assert first != second
        wire.invalid_result = True
        with pytest.raises(NewsServiceError):
            await adapter.put_list("dait:{AI}:list", second, "value", 300)
        with pytest.raises(NewsServiceError):
            await adapter.get_list("dait:{AI}:list", second)
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_invalidation_timeout_preserves_saved_article() -> None:
    repository, cache = FakeRepository((news(),)), FakeCache()
    app = service(repository, cache)
    await app.list_news()
    cache.slow_operations.add("invalidate_lists")
    async with asyncio.timeout(1):
        await repository.commit(news(2))
    assert len(repository.entries) == 2
    assert cache.invalidations == 0
    assert await app.get_detail(UUID(int=2)) is not None


@pytest.mark.asyncio
async def test_invalid_generation_falls_back_without_cache_write() -> None:
    class MalformedGeneration(FakeCache):
        async def generation(self) -> str:
            return "invalid:generation"

    repository, cache = FakeRepository((news(),)), MalformedGeneration()
    assert len((await service(repository, cache).list_news()).items) == 1
    assert repository.list_calls == 1
    assert not cache.list_writes


def _stored_midterms_mistranslation() -> StoredNews:
    original = news()
    article = CollectedArticle(
        source_name=original.record.article.source_name,
        title=(
            "After the midterms, things look rocky for data centers"
            " ||| 중간고사 이후 상황이 험난하다"
        ),
        canonical_url=original.record.article.canonical_url,
        published_at=original.record.article.published_at,
        raw_text="Public article excerpt.",
    )
    content = SuccessContent(
        content_hash="a" * 64,
        summary_lines=(
            "이번 중간선거에서 민주당이 승리했습니다.",
            "유권자는 데이터 센터 건설을 거부했습니다.",
            "새 주지사가 규제 강화를 약속했습니다.",
        ),
        translated_text="이번 중간선거에서 민주당이 승리했습니다.",
    )
    return StoredNews(id=original.id, record=PipelineRecord(article=article, content=content))


@pytest.mark.asyncio
async def test_existing_db_title_is_corrected_using_stored_summary_without_retranslation() -> None:
    stored = _stored_midterms_mistranslation()
    repository, cache = FakeRepository((stored,)), FakeCache()
    app = service(repository, cache)
    listed = await app.query_news(NewsQuery(fresh_hours=0))
    assert "중간선거 이후" in listed.items[0].title
    assert "중간고사" not in listed.items[0].title
    detail = await app.get_api_detail(str(stored.id))
    assert detail is not None
    assert detail.article.title == listed.items[0].title
    # Repair only the response: no destructive DB reset or external translator invocation.
    assert "중간고사" in repository.entries[0].record.article.title
    assert detail.content.summary_lines == stored.record.content.summary_lines


@pytest.mark.asyncio
async def test_old_list_and_detail_cache_titles_are_corrected_on_cache_hit() -> None:
    stored = _stored_midterms_mistranslation()
    repository, cache = FakeRepository((stored,)), FakeCache()
    app = service(repository, cache)
    listed = await app.list_news()
    corrected_title = listed.items[0].title
    old_title = stored.record.article.title
    cache.store(
        cache.list_writes[0][0],
        listed.model_dump_json().replace(corrected_title, old_title, 1),
        300,
    )
    assert (await app.list_news()).items[0].title == corrected_title
    assert repository.list_calls == 1
    detail = await app.get_detail(stored.id)
    assert detail is not None
    cache.store(
        cache.detail_writes[0][0],
        detail.model_dump_json().replace(corrected_title, old_title, 1),
        1800,
    )
    assert await app.get_detail(stored.id) == detail
    assert repository.detail_calls == 1

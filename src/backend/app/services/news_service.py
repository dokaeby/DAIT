"""Cache-first news reads; requests never crawl sources or invoke an LLM.

Create one service per application lifecycle: it registers a post-commit READY
invalidation hook on its repository. Redis failures are bounded and optional;
DB failures remain errors. Failed invalidation/crashes can leave old lists until
TTL expiry (no distributed transactional outbox is claimed here).
"""

import asyncio
import base64
import binascii
import hashlib
import hmac
import logging
import secrets
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Literal, Protocol, Self
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    SecretStr,
    ValidationError,
    field_validator,
    model_validator,
)
from redis.asyncio import Redis
from src.backend.app.core.taxonomy import (
    CategoryType,
    matches_subtopic_or_query,
    OFFICIAL_SOURCE_NAMES,
)
from src.backend.app.core.title_translation import repair_contextual_title
from src.backend.app.repositories.news_repository import (
    NewsIdentifier,
    ReadyInvalidator,
    StoredNews,
)
from src.backend.app.schemas.collector import CollectedArticle
from src.backend.app.schemas.content import CONTENT_RESULT_ADAPTER, ContentResult, SuccessContent
from src.backend.app.schemas.news import (
    LATEST_BASIS,
    RANK_BASIS,
    NewsArticle,
    NewsContent,
    NewsListItem,
    NewsMeta,
    NewsPage,
    NewsProcessing,
    NewsQuery,
    NewsSource,
)
from src.backend.app.schemas.news import (
    NewsDetailResponse as ApiNewsDetail,
)
from src.backend.app.schemas.news import (
    NewsListResponse as ApiNewsList,
)
from src.backend.app.services.ranking_service import (
    RankedNews,
    RankingCandidate,
    RankingRequest,
    RankingService,
    compute_keyword_and_popularity,
)

logger = logging.getLogger(__name__)
LIST_TTL_SECONDS = 300
DETAIL_TTL_SECONDS = 1800
GENERATION_KEY = "dait:news:v1:{AI}:generation"
INVALID_RESPONSE = "Invalid news response"
INVALID_CONFIGURATION = "Invalid source priority configuration"
CACHE_FAILED = "Invalid cache response"
# KEYS share a Redis Cluster hash tag; Lua atomically checks generation and accesses the list.
GET_LIST_SCRIPT = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return nil end
return redis.call('GET', KEYS[2])
"""
PUT_LIST_SCRIPT = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end
redis.call('SET', KEYS[2], ARGV[2], 'EX', ARGV[3])
return 1
"""


class NewsServiceError(ValueError):
    """Fixed diagnostic; no cached payloads, URLs or private content in logs."""


class NewsModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class SourcePriority(NewsModel):
    source_name: str = Field(min_length=1, max_length=200)
    priority: int = Field(strict=True, ge=0)

    @field_validator("source_name")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError(INVALID_CONFIGURATION)
        return value.strip()


class NewsServicePolicy(NewsModel):
    source_priorities: tuple[SourcePriority, ...] = Field(min_length=1)
    cursor_signing_key: SecretStr | None = None
    cache_timeout_seconds: float = Field(default=0.25, gt=0, le=1, allow_inf_nan=False)

    @field_validator("cursor_signing_key")
    @classmethod
    def strong_key(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and len(value.get_secret_value().encode()) < 32:
            raise ValueError(INVALID_CONFIGURATION)
        return value

    @model_validator(mode="after")
    def unique_sources(self) -> Self:
        names = tuple(entry.source_name for entry in self.source_priorities)
        if len(set(names)) != len(names):
            raise ValueError(INVALID_CONFIGURATION)
        return self


class ListRequest(NewsModel):
    limit: Literal[5, 10] = 5

    @field_validator("limit", mode="before")
    @classmethod
    def strict_limit(cls, value: object) -> object:
        return RankingRequest.strict_limit(value)


class CacheGeneration(NewsModel):
    value: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9-]+$")


class NewsDetailResponse(NewsModel):
    id: UUID
    category: CategoryType = "AI"
    source_name: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=2000)
    canonical_url: HttpUrl
    published_at: datetime
    status: Literal["READY", "INSUFFICIENT"]
    content: ContentResult

    @field_validator("source_name", "title")
    @classmethod
    def nonblank(cls, value: str) -> str:
        return CollectedArticle.nonblank(value)

    @field_validator("published_at")
    @classmethod
    def utc_time(cls, value: datetime) -> datetime:
        return CollectedArticle.normalize_timestamp(value)

    @field_validator("canonical_url")
    @classmethod
    def canonical(cls, value: HttpUrl) -> HttpUrl:
        return CollectedArticle.normalize_url(value)

    @field_validator("content")
    @classmethod
    def valid_content(cls, value: ContentResult) -> ContentResult:
        return CONTENT_RESULT_ADAPTER.validate_json(value.model_dump_json(warnings=False))

    @model_validator(mode="after")
    def valid_status(self) -> Self:
        if (self.status == "READY") != isinstance(self.content, SuccessContent):
            raise ValueError(INVALID_RESPONSE)
        return self


class NewsListResponse(NewsModel):
    category: CategoryType = "AI"
    limit: Literal[5, 10]
    items: tuple[NewsDetailResponse, ...]

    @field_validator("limit", mode="before")
    @classmethod
    def strict_limit(cls, value: object) -> object:
        return RankingRequest.strict_limit(value)

    @model_validator(mode="after")
    def valid_items(self) -> Self:
        if len(self.items) > self.limit or len({item.id for item in self.items}) != len(self.items):
            raise ValueError(INVALID_RESPONSE)
        return self


class NewsReader(Protocol):
    async def list_news(self) -> tuple[StoredNews, ...]: ...
    async def get_by_id(self, news_id: UUID) -> StoredNews | None: ...
    def add_ready_invalidator(self, invalidator: ReadyInvalidator) -> None: ...


class NewsRanker(Protocol):
    def rank(self, request: RankingRequest) -> tuple[RankedNews, ...]: ...


class NewsCache(Protocol):
    async def generation(self) -> str: ...
    async def get_list(self, key: str, generation: str) -> str | None: ...
    async def put_list(self, key: str, generation: str, value: str, ttl_seconds: int) -> bool: ...
    async def get_detail(self, key: str) -> str | None: ...
    async def put_detail(self, key: str, value: str, ttl_seconds: int) -> None: ...
    async def invalidate_lists(self) -> None: ...


def _text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, str):
        return value
    raise NewsServiceError(CACHE_FAILED)


class RedisNewsCache:
    """Caller owns the Redis client; NewsService bounds all cache operations.

    A missing generation is initialized with a fresh UUID, not a recycled zero,
    preventing stale list resurrection if the generation key is evicted.
    """

    def __init__(self, client: Redis) -> None:
        self.client = client

    async def generation(self) -> str:
        value = await self.client.get(GENERATION_KEY)
        if value is None:
            await self.client.set(GENERATION_KEY, uuid4().hex, nx=True)
            value = await self.client.get(GENERATION_KEY)
        text = _text(value)
        if text is None:
            raise NewsServiceError(CACHE_FAILED)
        return CacheGeneration(value=text).value

    async def get_list(self, key: str, generation: str) -> str | None:
        value: object = await self.client.eval(GET_LIST_SCRIPT, 2, GENERATION_KEY, key, generation)
        return _text(value)

    async def put_list(self, key: str, generation: str, value: str, ttl_seconds: int) -> bool:
        result: object = await self.client.eval(
            PUT_LIST_SCRIPT, 2, GENERATION_KEY, key, generation, value, str(ttl_seconds)
        )
        if type(result) is not int or result not in (0, 1):
            raise NewsServiceError(CACHE_FAILED)
        return result == 1

    async def get_detail(self, key: str) -> str | None:
        return _text(await self.client.get(key))

    async def put_detail(self, key: str, value: str, ttl_seconds: int) -> None:
        await self.client.set(key, value, ex=ttl_seconds)

    async def invalidate_lists(self) -> None:
        await self.client.set(GENERATION_KEY, uuid4().hex)


def _response(stored: StoredNews) -> NewsDetailResponse:
    stored = StoredNews.model_validate_json(stored.model_dump_json(warnings=False))
    article, content = stored.record.article, stored.record.content
    return NewsDetailResponse(
        id=stored.id,
        category=article.category,
        source_name=article.source_name,
        title=repair_contextual_title(
            article.title,
            (article.raw_text or "")
            + " "
            + (content.translated_text or "")
            + " "
            + " ".join(content.summary_lines),
        ),
        canonical_url=article.canonical_url,
        published_at=article.published_at,
        status="READY" if isinstance(content, SuccessContent) else "INSUFFICIENT",
        content=content,
    )


def _repair_cached_detail(detail: NewsDetailResponse) -> NewsDetailResponse:
    title = repair_contextual_title(
        detail.title,
        (detail.content.translated_text or "") + " " + " ".join(detail.content.summary_lines),
    )
    if title == detail.title:
        return detail
    return NewsDetailResponse(
        id=detail.id,
        category=detail.category,
        source_name=detail.source_name,
        title=title,
        canonical_url=detail.canonical_url,
        published_at=detail.published_at,
        status=detail.status,
        content=detail.content,
    )


class InvalidNewsCursorError(ValueError):
    """Malformed, tampered or query-mismatched cursor; never expose its payload."""


class _QueryBinding(NewsModel):
    category: CategoryType
    q: str | None
    sort: Literal["rank", "latest"]
    page_size: int
    priorities: str


class _NewsCursor(NewsModel):
    version: Literal[1] = 1
    binding: str = Field(pattern=r"^[0-9a-f]{64}$")
    last_id: UUID
    published_at: datetime
    source_priority: int | None = Field(ge=0)

    @field_validator("published_at")
    @classmethod
    def utc_time(cls, value: datetime) -> datetime:
        return CollectedArticle.normalize_timestamp(value)


def _api_item(stored: StoredNews, rank: int) -> NewsListItem:
    article, content = stored.record.article, stored.record.content
    if not isinstance(content, SuccessContent):
        raise NewsServiceError(INVALID_RESPONSE)
    return NewsListItem(
        id=str(stored.id),
        rank=rank,
        title=repair_contextual_title(
            article.title,
            (article.raw_text or "")
            + " "
            + (content.translated_text or "")
            + " "
            + " ".join(content.summary_lines),
        ),
        category=article.category,
        source_name=article.source_name,
        published_at=article.published_at,
        summary_lines=content.summary_lines,
        original_url=article.canonical_url,
    )


class NewsService:
    def __init__(
        self,
        *,
        repository: NewsReader,
        cache: NewsCache,
        policy: NewsServicePolicy,
        ranking: NewsRanker | None = None,
    ) -> None:
        self.repository = repository
        self.cache = cache
        self.policy = NewsServicePolicy.model_validate(policy)
        self.ranking = ranking or RankingService()
        priorities = tuple(
            sorted(self.policy.source_priorities, key=lambda entry: entry.source_name)
        )
        self._priority_fingerprint = hashlib.sha256(
            "\n".join(entry.model_dump_json() for entry in priorities).encode()
        ).hexdigest()
        self._cursor_key = (
            self.policy.cursor_signing_key.get_secret_value().encode()
            if self.policy.cursor_signing_key is not None
            else secrets.token_bytes(32)
        )
        repository.add_ready_invalidator(self)

    async def _cache_call[R](self, operation: Callable[[], Awaitable[R]]) -> R | None:
        try:
            async with asyncio.timeout(self.policy.cache_timeout_seconds):
                return await operation()
        except Exception:  # noqa: BLE001 -- Redis payloads/credentials never reach diagnostics
            logger.warning("News cache unavailable; DB response remains available")
            return None

    async def invalidate_lists(self) -> None:
        await self._cache_call(self.cache.invalidate_lists)

    def _source_priority(self, source_name: str) -> int:
        for entry in self.policy.source_priorities:
            if entry.source_name == source_name:
                return entry.priority
        raise NewsServiceError(INVALID_CONFIGURATION)

    async def _list_from_db(self, limit: Literal[5, 10]) -> NewsListResponse:
        stored = await self.repository.list_news()
        records = tuple(
            StoredNews.model_validate_json(entry.model_dump_json(warnings=False))
            for entry in stored
        )
        candidates = tuple(
            RankingCandidate(
                id=entry.id,
                category=entry.record.article.category,
                published_at=entry.record.article.published_at,
                source_priority=self._source_priority(entry.record.article.source_name),
                content=entry.record.content,
            )
            for entry in records
        )
        ranked = self.ranking.rank(RankingRequest(candidates=candidates, limit=limit))
        return NewsListResponse(
            limit=limit,
            items=tuple(
                _response(next(entry for entry in records if entry.id == item.news.id))
                for item in ranked
            ),
        )

    async def list_news(self, limit: Literal[5, 10] = 5) -> NewsListResponse:
        request = ListRequest(limit=limit)
        generation = await self._cache_call(self.cache.generation)
        key: str | None = None
        if generation is not None:
            try:
                generation = CacheGeneration(value=generation).value
            except ValidationError:
                generation = None
            if generation is not None:
                key = (
                    f"dait:news:v1:{{AI}}:list:{self._priority_fingerprint}:"
                    f"{request.limit}:{generation}"
                )
                payload = await self._cache_call(
                    lambda: self.cache.get_list(key or "", generation or "")
                )
                if payload is not None:
                    try:
                        cached = NewsListResponse.model_validate_json(payload)
                        if cached.limit == request.limit:
                            return NewsListResponse(
                                category=cached.category,
                                limit=cached.limit,
                                items=tuple(_repair_cached_detail(item) for item in cached.items),
                            )
                    except ValidationError:
                        logger.warning("Invalid news list cache ignored")
        response = await self._list_from_db(request.limit)
        if key is not None and generation is not None:
            await self._cache_call(
                lambda: self.cache.put_list(
                    key or "", generation or "", response.model_dump_json(), LIST_TTL_SECONDS
                )
            )
        return response

    async def get_detail(self, news_id: UUID) -> NewsDetailResponse | None:
        identifier = NewsIdentifier(id=news_id)
        key = f"dait:news:v1:{{AI}}:detail:{identifier.id}"
        payload = await self._cache_call(lambda: self.cache.get_detail(key))
        if payload is not None:
            try:
                cached = NewsDetailResponse.model_validate_json(payload)
                if cached.id == identifier.id:
                    return _repair_cached_detail(cached)
            except ValidationError:
                logger.warning("Invalid news detail cache ignored")
        stored = await self.repository.get_by_id(identifier.id)
        if stored is None:
            return None  # No negative caching: a subsequently committed article stays visible.
        response = _response(stored)
        if response.id != identifier.id:
            raise NewsServiceError(INVALID_RESPONSE)
        await self._cache_call(
            lambda: self.cache.put_detail(key, response.model_dump_json(), DETAIL_TTL_SECONDS)
        )
        return response

    def _query_binding(self, query: NewsQuery) -> str:
        binding = _QueryBinding(
            category=query.category,
            q=query.q,
            sort=query.sort,
            page_size=query.page_size,
            priorities=self._priority_fingerprint,
        )
        return hashlib.sha256(binding.model_dump_json().encode()).hexdigest()

    def _decode_cursor(self, token: str, binding: str) -> _NewsCursor:
        try:
            encoded, signature = token.split(".")
            expected = hmac.new(
                self._cursor_key, encoded.encode("ascii"), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise InvalidNewsCursorError(INVALID_RESPONSE)
            data = base64.b64decode(
                encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True
            )
            cursor = _NewsCursor.model_validate_json(data)
            if not hmac.compare_digest(cursor.binding, binding):
                raise InvalidNewsCursorError(INVALID_RESPONSE)
        except ValueError, UnicodeError, binascii.Error:
            raise InvalidNewsCursorError(INVALID_RESPONSE) from None
        return cursor

    def _encode_cursor(self, cursor: _NewsCursor) -> str:
        encoded = base64.urlsafe_b64encode(cursor.model_dump_json().encode()).decode().rstrip("=")
        signature = hmac.new(self._cursor_key, encoded.encode(), hashlib.sha256).hexdigest()
        return encoded + "." + signature

    async def _api_records(self, query: NewsQuery) -> tuple[tuple[StoredNews, ...], bool]:
        stored = await self.repository.list_news()
        records = tuple(
            StoredNews.model_validate_json(entry.model_dump_json(warnings=False))
            for entry in stored
        )
        matched = tuple(
            entry
            for entry in records
            if entry.record.article.category == query.category
            and matches_subtopic_or_query(
                query.category,
                query.q,
                (
                    entry.record.article.title
                    + " "
                    + entry.record.article.source_name
                    + " "
                    + " ".join(entry.record.content.summary_lines)
                    + " "
                    + (entry.record.content.translated_text or "")
                ),
            )
        )
        visible = tuple(
            entry
            for entry in matched
            if isinstance(entry.record.content, SuccessContent)
            and not any(
                dummy in line
                for line in entry.record.content.summary_lines
                for dummy in (
                    "에서 보도한",
                    "원문 보기 링크를 통해",
                    "원문 링크를 통해",
                    "원문 보기를 통해",
                    "전체 본문을 확인할 수 있습니다",
                    "상세 본문을 확인할 수 있습니다",
                    "섹션에 보도된 실제 원문 기사입니다",
                )
            )
        )
        if len({entry.id for entry in visible}) != len(visible):
            raise NewsServiceError(INVALID_RESPONSE)
        if query.sort == "rank":
            candidate_list: list[RankingCandidate] = []
            for entry in visible:
                priority = self._source_priority(entry.record.article.source_name)
                if entry.record.article.source_name in OFFICIAL_SOURCE_NAMES:
                    kw_freq, pop_idx = compute_keyword_and_popularity(
                        entry.record.article.title,
                        entry.record.content.summary_lines,
                        entry.record.article.raw_text,
                        priority,
                    )
                else:
                    kw_freq, pop_idx = 0, 0
                candidate_list.append(
                    RankingCandidate(
                        id=entry.id,
                        category=entry.record.article.category,
                        published_at=entry.record.article.published_at,
                        source_priority=priority,
                        keyword_frequency=kw_freq,
                        popularity_index=pop_idx,
                        content=entry.record.content,
                    )
                )
            ordered = RankingService.order(tuple(candidate_list))
            result = tuple(
                next(entry for entry in visible if entry.id == item.id) for item in ordered
            )
        else:
            by_id = sorted(visible, key=lambda entry: str(entry.id))
            result = tuple(
                sorted(by_id, key=lambda entry: entry.record.article.published_at, reverse=True)
            )
        return result, len(visible) != len(matched)

    def _after_cursor(self, entry: StoredNews, cursor: _NewsCursor, sort: str) -> bool:
        date = entry.record.article.published_at
        if date != cursor.published_at:
            return date < cursor.published_at
        if sort == "rank":
            priority = self._source_priority(entry.record.article.source_name)
            if cursor.source_priority is None:
                raise InvalidNewsCursorError(INVALID_RESPONSE)
            if priority != cursor.source_priority:
                return priority > cursor.source_priority
        return str(entry.id) > str(cursor.last_id)

    async def query_news(self, query: NewsQuery) -> ApiNewsList:
        """API pagination is separate from the legacy 5/10 home cache contract.

        Query all candidates before filtering/sorting/slicing; keyset cursors are
        HMAC-bound to category/query/sort/page size/priority config. A stable
        cursor_signing_key must be injected across workers and restarts.
        """
        query = NewsQuery.model_validate(query)
        binding = self._query_binding(query)
        cursor = self._decode_cursor(query.cursor, binding) if query.cursor is not None else None
        records, partial = await self._api_records(query)
        remaining = [
            (index, entry)
            for index, entry in enumerate(records, start=1)
            if cursor is None or self._after_cursor(entry, cursor, query.sort)
        ]
        selected = remaining[: query.page_size]
        has_more = len(remaining) > query.page_size
        next_cursor: str | None = None
        if has_more:
            last = selected[-1][1]
            next_cursor = self._encode_cursor(
                _NewsCursor(
                    binding=binding,
                    last_id=last.id,
                    published_at=last.record.article.published_at,
                    source_priority=self._source_priority(last.record.article.source_name)
                    if query.sort == "rank"
                    else None,
                )
            )
        return ApiNewsList(
            items=[_api_item(entry, rank) for rank, entry in selected],
            page=NewsPage(next_cursor=next_cursor, has_more=has_more),
            meta=NewsMeta(
                total_visible=len(records),
                partial=partial,
                message="요약이 완료되지 않은 일부 기사는 목록에서 제외되었습니다."
                if partial
                else None,
                rank_basis=RANK_BASIS if query.sort == "rank" else LATEST_BASIS,
            ),
        )

    async def get_api_detail(self, news_id: str) -> ApiNewsDetail | None:
        """Opaque external IDs currently map to stored UUIDs; unknown strings are missing.

        Provenance is not persisted yet: report null/UNKNOWN/false, never invent
        language, processing time, model version, verification or reading time.
        Related means other READY articles in the same category in deterministic rank order (max 3).
        """
        try:
            identifier = UUID(news_id)
        except ValueError:
            return None
        detail = await self.get_detail(identifier)
        if detail is None:
            return None
        ordered, _ = await self._api_records(NewsQuery(category=detail.category))
        related = [
            _api_item(entry, index)
            for index, entry in enumerate(ordered, start=1)
            if entry.id != identifier
        ][:3]
        content = detail.content
        ready = isinstance(content, SuccessContent)
        return ApiNewsDetail(
            article=NewsArticle(
                id=str(detail.id),
                title=detail.title,
                category=detail.category,
                source_name=detail.source_name,
                published_at=detail.published_at,
                original_language=None,
                estimated_read_minutes=None,
            ),
            content=NewsContent(
                summary_lines=content.summary_lines,
                translated_text=content.translated_text,
                processed_at=None,
                content_status=detail.status,
                summary_model_version=None,
            ),
            source=NewsSource(
                original_url=detail.canonical_url, url_verified=False, source_type="UNKNOWN"
            ),
            related_news=related,
            processing=NewsProcessing(
                collection_status="COLLECTED",
                translation_status="SUCCESS" if ready else "INSUFFICIENT",
                summary_status="SUCCESS" if ready else "INSUFFICIENT",
            ),
        )

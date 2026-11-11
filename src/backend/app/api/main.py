"""FastAPI application entrypoint for uvicorn (src.backend.app.api.main:app)."""

import asyncio
import logging
import os
import re
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field, SecretStr
from redis.asyncio import Redis
from src.backend.app.api.v1.news import NewsApiService, get_news_service, router
from src.backend.app.collectors.rss_collector import RSSCollector
from src.backend.app.core.taxonomy import GLOBAL_SOURCE_NAMES, OFFICIAL_MEDIA_SOURCES
from src.backend.app.repositories.news_repository import Base, NewsRepository, RepositorySettings
from src.backend.app.schemas.collector import CollectorSource
from src.backend.app.schemas.news import ApiModel, NewsDetailResponse, NewsListResponse, NewsQuery
from src.backend.app.services.news_service import (
    NewsCache,
    NewsService,
    NewsServicePolicy,
    RedisNewsCache,
    SourcePriority,
)
from src.backend.app.workers.ai_processor import (
    GoogleTranslateContentProcessor,
    TranslatingNewsCollector,
)
from src.backend.app.workers.cloud_llm import (
    CloudLLMContentProcessor,
    CloudLLMSettings,
)
from src.backend.app.workers.collector_worker import CollectorWorker, NewsCollector, WorkerPolicy

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
MOCKUP_DIR = PROJECT_ROOT / "src" / "frontend" / "public"
MOCKUP_INDEX = MOCKUP_DIR / "index.html"
MOCKUP_DETAIL = MOCKUP_DIR / "detail.html"
DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./dait.db"
_HANGUL_CHECK = re.compile(r"[가-힣]")
_LEGACY_DUMMY_PATTERNS: tuple[str, ...] = (
    "에서 보도한",
    "원문 보기 링크를 통해",
    "원문 링크를 통해",
    "원문 보기를 통해",
    "전체 본문을 확인할 수 있습니다",
    "상세 본문을 확인할 수 있습니다",
    "섹션에 보도된 실제 원문 기사입니다",
)

_LEGACY_SOURCE_NAMES: tuple[str, ...] = (
    "Approved AI",
    "OpenAI",
    "DeepMind",
    "Anthropic",
    "Fake Source",
)
DEFAULT_PRIORITIES: tuple[SourcePriority, ...] = tuple(
    SourcePriority(source_name=spec.source_name, priority=index)
    for index, spec in enumerate(OFFICIAL_MEDIA_SOURCES)
) + tuple(
    SourcePriority(
        source_name=name,
        priority=len(OFFICIAL_MEDIA_SOURCES) + offset,
    )
    for offset, name in enumerate(_LEGACY_SOURCE_NAMES)
)

OFFICIAL_COLLECTOR_SOURCES: tuple[CollectorSource, ...] = tuple(
    CollectorSource(
        source_name=spec.source_name,
        category=spec.default_category,
        feed_url=spec.feed_url,
        allowed_hosts=spec.allowed_hosts,
    )
    for spec in OFFICIAL_MEDIA_SOURCES
)


class HealthResponse(ApiModel):
    """Health check response contract."""

    status: Literal["ok"] = "ok"


class AppSettings(ApiModel):
    """Validated runtime settings for the API process."""

    database_url: SecretStr = SecretStr(DEFAULT_DATABASE_URL)
    redis_host: str | None = Field(default=None, min_length=1, max_length=255)
    redis_port: int = Field(default=6379, ge=1, le=65535)
    cursor_signing_key: SecretStr | None = None
    source_priorities: tuple[SourcePriority, ...] = DEFAULT_PRIORITIES
    enable_live_rss: bool = True
    max_items_per_feed: int = Field(default=4, ge=1, le=50)

    @classmethod
    def from_env(cls) -> "AppSettings":
        db_url = os.getenv("DAIT_DATABASE_URL", DEFAULT_DATABASE_URL)
        redis_host = os.getenv("DAIT_REDIS_HOST")
        redis_port_raw = os.getenv("DAIT_REDIS_PORT", "6379")
        redis_port = int(redis_port_raw) if redis_port_raw.isdigit() else 6379
        cursor_raw = os.getenv("DAIT_CURSOR_SIGNING_KEY")
        live_rss = os.getenv("DAIT_ENABLE_LIVE_RSS", "true").lower() in {"1", "true", "yes"}
        return cls(
            database_url=SecretStr(db_url),
            redis_host=redis_host if redis_host else None,
            redis_port=redis_port,
            cursor_signing_key=SecretStr(cursor_raw) if cursor_raw else None,
            enable_live_rss=live_rss,
        )


class _NullNewsCache:
    """In-process no-op cache used when Redis is not configured."""

    async def generation(self) -> str:
        return uuid4().hex

    async def get_list(self, key: str, generation: str) -> str | None:
        return None

    async def put_list(self, key: str, generation: str, value: str, ttl_seconds: int) -> bool:
        return False

    async def get_detail(self, key: str) -> str | None:
        return None

    async def put_detail(self, key: str, value: str, ttl_seconds: int) -> None:
        return None

    async def invalidate_lists(self) -> None:
        return None


class _ManagedRuntime(NewsApiService):
    """Owns repository, optional Redis client, and live RSS CollectorWorker execution."""

    def __init__(
        self,
        settings: AppSettings,
        *,
        collector: NewsCollector | None = None,
        enable_network_translation: bool = True,
    ) -> None:
        self.settings = AppSettings.model_validate(settings)
        self.repository = NewsRepository(
            RepositorySettings(database_url=self.settings.database_url)
        )
        self.redis_client: Redis | None = (
            Redis(host=self.settings.redis_host, port=self.settings.redis_port)
            if self.settings.redis_host is not None
            else None
        )
        cache: NewsCache = (
            RedisNewsCache(self.redis_client) if self.redis_client is not None else _NullNewsCache()
        )
        self.service = NewsService(
            repository=self.repository,
            cache=cache,
            policy=NewsServicePolicy(
                source_priorities=self.settings.source_priorities,
                cursor_signing_key=self.settings.cursor_signing_key,
            ),
        )
        base_collector: NewsCollector = collector or RSSCollector(
            OFFICIAL_COLLECTOR_SOURCES,
            timeout_seconds=8.0,
            max_items_per_feed=self.settings.max_items_per_feed,
        )
        self._collector: NewsCollector = TranslatingNewsCollector(
            base_collector,
            enable_network=enable_network_translation,
        )
        self._cloud_settings = CloudLLMSettings.from_env() if enable_network_translation else None
        if self._cloud_settings is not None:
            self._processor: GoogleTranslateContentProcessor | CloudLLMContentProcessor = (
                CloudLLMContentProcessor(self._cloud_settings)
            )
        else:
            self._processor = GoogleTranslateContentProcessor(
                enable_network_translation=enable_network_translation
            )
        self._enable_network_translation = enable_network_translation
        self._init_lock = asyncio.Lock()
        self._initialized = False

    async def _reset_schema_and_data(self) -> None:
        async with self.repository.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)

    async def _crawl_official_rss_feeds(self) -> None:
        worker = CollectorWorker(
            collector=self._collector,
            processor=self._processor,
            repository=self.repository,
            policy=WorkerPolicy(processing_timeout_seconds=20, cleanup_timeout_seconds=3),
        )
        for source in OFFICIAL_COLLECTOR_SOURCES:
            try:
                await worker.run_once(source)
            except Exception:  # noqa: BLE001 -- isolate individual RSS feed failures safely
                logger.warning("RSS feed collection skipped for source=%s", source.source_name)

    async def _bootstrap_if_empty(self) -> None:
        try:
            stored = await self.repository.list_news()
        except Exception:  # noqa: BLE001 -- rebuild incompatible legacy sqlite schema cleanly
            await self._reset_schema_and_data()
            stored = ()

        if len(stored) > 0:
            has_legacy_dummy = any(
                any(
                    pattern in line
                    for line in item.record.content.summary_lines
                    for pattern in _LEGACY_DUMMY_PATTERNS
                )
                for item in stored
            )
            has_untranslated_global = self._enable_network_translation and any(
                item.record.article.source_name in GLOBAL_SOURCE_NAMES
                and (
                    " ||| " not in item.record.article.title
                    or not bool(_HANGUL_CHECK.search(item.record.article.title))
                    or not all(
                        _HANGUL_CHECK.search(line) for line in item.record.content.summary_lines
                    )
                )
                for item in stored
            )
            if has_legacy_dummy or has_untranslated_global:
                await self._reset_schema_and_data()
                await self.service.invalidate_lists()
                stored = ()

        if len(stored) > 0:
            return
        if self.settings.enable_live_rss:
            await self._crawl_official_rss_feeds()

    async def startup(self) -> None:
        async with self._init_lock:
            if not self._initialized:
                await self.repository.initialize()
                await self._bootstrap_if_empty()
                self._initialized = True

    async def shutdown(self) -> None:
        async with self._init_lock:
            if self.redis_client is not None:
                await self.redis_client.aclose()
            if isinstance(self._processor, CloudLLMContentProcessor):
                await self._processor.aclose()
            await self.repository.close()
            self._initialized = False

    async def query_news(self, query: NewsQuery) -> NewsListResponse:
        await self.startup()
        return await self.service.query_news(query)

    async def get_api_detail(self, news_id: str) -> NewsDetailResponse | None:
        await self.startup()
        return await self.service.get_api_detail(news_id)


def create_application(
    service: NewsApiService | None = None,
    settings: AppSettings | None = None,
    *,
    collector: NewsCollector | None = None,
    enable_network_translation: bool = True,
) -> FastAPI:
    """Create the FastAPI application with /, /healthz, /v1/news, and static mockup mount."""
    runtime: _ManagedRuntime | None = None
    if service is None:
        runtime = _ManagedRuntime(
            settings or AppSettings.from_env(),
            collector=collector,
            enable_network_translation=enable_network_translation,
        )
        active_service: NewsApiService = runtime
    else:
        active_service = service

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
        if runtime is not None:
            await runtime.startup()
        try:
            yield
        finally:
            if runtime is not None:
                await runtime.shutdown()

    application = FastAPI(
        title="DAIT News API",
        version="1.0.1",
        lifespan=lifespan,
    )
    application.dependency_overrides[get_news_service] = lambda: active_service
    application.include_router(router, prefix="/v1")
    if MOCKUP_DIR.is_dir():
        application.mount("/mockup", StaticFiles(directory=str(MOCKUP_DIR)), name="mockup")

    @application.get("/", include_in_schema=False)
    async def index_page() -> FileResponse:
        return FileResponse(path=str(MOCKUP_INDEX), media_type="text/html")

    @application.get("/detail.html", include_in_schema=False)
    async def detail_page() -> FileResponse:
        return FileResponse(path=str(MOCKUP_DETAIL), media_type="text/html")

    @application.get("/healthz", response_model=HealthResponse, tags=["health"])
    async def healthz() -> HealthResponse:
        return HealthResponse()

    return application


app: FastAPI = create_application()

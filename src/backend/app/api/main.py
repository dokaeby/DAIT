"""FastAPI application entrypoint for uvicorn (src.backend.app.api.main:app)."""

import asyncio
import json
import logging
import os
import re
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import Field, SecretStr
from redis.asyncio import Redis
from src.backend.app.api.v1.news import NewsApiService, get_news_service, router
from src.backend.app.collectors.rss_collector import RSSCollector
from src.backend.app.core.taxonomy import GLOBAL_SOURCE_NAMES, OFFICIAL_MEDIA_SOURCES
from src.backend.app.repositories.news_repository import (
    Base,
    NewsRepository,
    RepositorySettings,
    StoredNews,
)
from src.backend.app.schemas.collector import CollectorSource
from src.backend.app.schemas.content import SuccessContent
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
    is_korean_text,
    looks_foreign_text,
)
from src.backend.app.workers.cloud_llm import (
    PROMPT_VERSION,
    CloudLLMContentProcessor,
    CloudLLMSettings,
    GrokClient,
    llm_translate_title,
)
from src.backend.app.workers.collector_worker import CollectorWorker, NewsCollector, WorkerPolicy

load_dotenv()

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
MOCKUP_DIR = PROJECT_ROOT / "src" / "frontend" / "public"
MOCKUP_INDEX = MOCKUP_DIR / "index.html"
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
    news_stale_hours: int = Field(default=24, ge=1, le=24 * 30)
    collect_interval_seconds: int = Field(default=6 * 3600, ge=0)
    crawl_on_startup: bool = True

    @classmethod
    def from_env(cls) -> "AppSettings":
        db_url = os.getenv("DAIT_DATABASE_URL", DEFAULT_DATABASE_URL)
        redis_host = os.getenv("DAIT_REDIS_HOST")
        redis_port_raw = os.getenv("DAIT_REDIS_PORT", "6379")
        redis_port = int(redis_port_raw) if redis_port_raw.isdigit() else 6379
        cursor_raw = os.getenv("DAIT_CURSOR_SIGNING_KEY")
        live_rss = os.getenv("DAIT_ENABLE_LIVE_RSS", "true").lower() in {"1", "true", "yes"}
        stale_hours = int(os.getenv("DAIT_NEWS_STALE_HOURS", "24"))
        interval = int(os.getenv("DAIT_COLLECT_INTERVAL_SECONDS", str(6 * 3600)))
        max_items = int(os.getenv("DAIT_MAX_ITEMS_PER_FEED", "4"))
        crawl_on_start = os.getenv("DAIT_CRAWL_ON_STARTUP", "true").lower() in {
            "1",
            "true",
            "yes",
        }
        return cls(
            database_url=SecretStr(db_url),
            redis_host=redis_host if redis_host else None,
            redis_port=redis_port,
            cursor_signing_key=SecretStr(cursor_raw) if cursor_raw else None,
            enable_live_rss=live_rss,
            news_stale_hours=stale_hours,
            collect_interval_seconds=interval,
            max_items_per_feed=max_items,
            crawl_on_startup=crawl_on_start,
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
        self._cloud_settings = CloudLLMSettings.from_env() if enable_network_translation else None
        self._title_llm_client: GrokClient | None = None
        title_translator = None
        if self._cloud_settings is not None:
            title_client = GrokClient.from_settings(self._cloud_settings)
            if title_client is not None:
                self._title_llm_client = title_client

                async def _translate_title(title: str, raw_text: str | None) -> str | None:
                    return await llm_translate_title(title_client, title, raw_text)

                title_translator = _translate_title
        self._collector: NewsCollector = TranslatingNewsCollector(
            base_collector,
            enable_network=enable_network_translation,
            title_translator=title_translator,
        )
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
        self._crawl_lock = asyncio.Lock()
        self._collect_task: asyncio.Task[None] | None = None
        self._crawl_task: asyncio.Task[None] | None = None
        self._is_collecting = False
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

    def _is_invalid_record(self, item: StoredNews) -> bool:
        """레거시 더미 요약 또는 미번역 해외 기사를 판별한다."""
        content = item.record.content
        if any(
            pattern in line for line in content.summary_lines for pattern in _LEGACY_DUMMY_PATTERNS
        ):
            return True
        if not self._enable_network_translation:
            return False
        if not isinstance(content, SuccessContent):
            # INSUFFICIENT 기사는 summary_lines가 비어 번역 여부를 판별할 수 없다.
            # 삭제하면 본문 추출이 계속 실패하는 기사가 시작 때마다 재수집된다.
            return False
        article = item.record.article
        foreign = article.source_name in GLOBAL_SOURCE_NAMES or looks_foreign_text(
            f"{article.title} {article.raw_text or ''}"
        )
        if not foreign:
            return False
        original_title = article.title.split(" ||| ", 1)[0].strip()
        title_needs_translation = looks_foreign_text(original_title) and not _HANGUL_CHECK.search(
            original_title
        )
        return (
            (title_needs_translation and " ||| " not in article.title)
            or not _HANGUL_CHECK.search(article.title)
            or not all(is_korean_text(line) for line in content.summary_lines)
        )

    async def _bootstrap_if_empty(self) -> None:
        try:
            stored = await self.repository.list_news()
        except Exception:  # noqa: BLE001 -- rebuild incompatible legacy sqlite schema cleanly
            await self._reset_schema_and_data()
            stored = ()

        if len(stored) > 0:
            bad_urls = tuple(
                str(item.record.article.canonical_url)
                for item in stored
                if self._is_invalid_record(item)
            )
            if bad_urls:
                removed = await self.repository.delete_records(bad_urls)
                await self.service.invalidate_lists()
                logger.warning("Removed %d invalid stored news records", removed)
                dropped = set(bad_urls)
                stored = tuple(
                    item for item in stored if str(item.record.article.canonical_url) not in dropped
                )

        newest = (
            max((item.record.article.published_at for item in stored), default=None)
            if stored
            else None
        )
        needs_crawl = (
            len(stored) == 0
            or self.settings.crawl_on_startup
            or newest is None
            or (datetime.now(UTC) - newest).total_seconds() > self.settings.news_stale_hours * 3600
        )
        if needs_crawl and self.settings.enable_live_rss:
            self._schedule_crawl()

    def _schedule_crawl(self) -> None:
        """백그라운드 수집을 예약한다 — 시작을 막지 않아 첫 화면이 바로 열린다."""
        if self._crawl_task is not None and not self._crawl_task.done():
            return
        self._crawl_task = asyncio.create_task(self._crawl_and_invalidate())
        self._crawl_task.add_done_callback(
            lambda t: (
                logger.warning("news crawl failed", exc_info=t.exception())
                if not t.cancelled() and t.exception() is not None
                else None
            )
        )

    async def _reprocess_fallbacks(self, limit: int = 10) -> None:
        """regex-fallback으로 저장된 기사를 LLM 복구 후 재처리한다.

        저장된 raw_text가 있으므로 피드 재수집 없이 재처리 가능하다.
        실행당 limit건만 처리해 LLM 토큰 사용량을 제한한다.
        """
        if not isinstance(self._processor, CloudLLMContentProcessor):
            return
        stored = await self.repository.list_news()
        # regex-fallback 재시도는 최근 기사로 제한한다 — 24시간 신선도 필터 밖의
        # 오래된 기사를 매 주기 재처리하면 화면에 안 보이는 기사에 LLM 토큰만
        # 소모한다. 해외 prompt_version 백필은 처리되면 자연 종료되므로 기간 제한 없음.
        fallback_cutoff = datetime.now(UTC) - timedelta(hours=72)
        targets = [
            item
            for item in stored
            if isinstance(item.record.content, SuccessContent)
            and (
                (
                    item.record.content.engine == "regex-fallback"
                    and item.record.article.published_at >= fallback_cutoff
                )
                # 프롬프트가 오래된 해외 기사: translated_body 도입 이전 결과라 재처리한다.
                or (
                    item.record.article.source_name in GLOBAL_SOURCE_NAMES
                    and item.record.content.prompt_version != PROMPT_VERSION
                )
                # 국내 매체 영문 기사 등 외국어 본문인데 한국어 요약이 아닌 결과를 복구한다.
                or self._is_invalid_record(item)
            )
        ][:limit]
        if not targets:
            return
        updated = 0
        for item in targets:
            try:
                result = await self._processor.process(item.record.article)
                if await self.repository.update_content(
                    str(item.record.article.canonical_url), result
                ):
                    updated += 1
            except Exception:  # noqa: BLE001 -- 개별 기사 실패는 건너뛰고 계속 진행
                logger.warning("Fallback reprocess skipped for one article")
        if updated:
            await self.service.invalidate_lists()
            logger.info("Reprocessed %d fallback news records", updated)

    async def _crawl_and_invalidate(self) -> None:
        async with self._crawl_lock:
            self._is_collecting = True
            try:
                await self._crawl_official_rss_feeds()
                await self._reprocess_fallbacks()
                await self.service.invalidate_lists()
            finally:
                self._is_collecting = False

    @property
    def is_collecting(self) -> bool:
        return self._is_collecting

    async def refresh(self) -> None:
        """수동 재수집 — 주기 작업과 동일한 경로를 lock으로 직렬화한다."""
        if self.settings.enable_live_rss:
            await self._crawl_and_invalidate()

    async def _collect_loop(self) -> None:
        interval = self.settings.collect_interval_seconds
        while True:
            await asyncio.sleep(interval)
            try:
                await self.refresh()
            except Exception:  # keep the periodic loop alive
                logger.warning("periodic news collection failed", exc_info=True)

    async def startup(self) -> None:
        async with self._init_lock:
            if not self._initialized:
                await self.repository.initialize()
                await self._bootstrap_if_empty()
                self._initialized = True
                if self.settings.collect_interval_seconds > 0 and self._collect_task is None:
                    self._collect_task = asyncio.create_task(self._collect_loop())

    async def shutdown(self) -> None:
        async with self._init_lock:
            if self._collect_task is not None:
                self._collect_task.cancel()
                self._collect_task = None
            if self._crawl_task is not None:
                self._crawl_task.cancel()
                self._crawl_task = None
            if self.redis_client is not None:
                await self.redis_client.aclose()
            if isinstance(self._processor, CloudLLMContentProcessor):
                await self._processor.aclose()
            if self._title_llm_client is not None:
                await self._title_llm_client.aclose()
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

    @application.get("/app.js", include_in_schema=False)
    async def app_js() -> FileResponse:
        return FileResponse(path=str(MOCKUP_DIR / "app.js"), media_type="text/javascript")

    @application.get("/healthz", response_model=HealthResponse, tags=["health"])
    async def healthz() -> HealthResponse:
        return HealthResponse()

    if runtime is not None:

        @application.post("/v1/news/refresh", include_in_schema=False)
        async def refresh_news(request: Request) -> Response:
            """DAIT_REFRESH_TOKEN 헤더가 일치할 때만 수동 재수집을 허용한다."""
            expected = os.getenv("DAIT_REFRESH_TOKEN", "")
            if not expected or request.headers.get("x-refresh-token") != expected:
                return Response(status_code=404)
            await runtime.startup()
            task = asyncio.create_task(runtime.refresh())

            def _log_refresh_failure(t: asyncio.Task[None]) -> None:
                if not t.cancelled() and t.exception() is not None:
                    logger.warning("manual news refresh failed", exc_info=t.exception())

            task.add_done_callback(_log_refresh_failure)
            return Response(status_code=202)

        @application.get("/v1/collection/status", include_in_schema=False)
        async def news_status() -> Response:
            """수집 진행 여부와 저장 건수를 반환한다 — 프론트 로딩 표시용."""
            await runtime.startup()
            stored_count = await runtime.repository.count_news()
            return Response(
                content=json.dumps(
                    {"collecting": runtime.is_collecting, "stored": stored_count},
                    ensure_ascii=False,
                ),
                media_type="application/json",
            )

    return application


app: FastAPI = create_application()

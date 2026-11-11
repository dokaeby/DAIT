"""뉴스 수집 오케스트레이션 — RSS fetch → 중복 제거 → AI 처리 → 저장.

- `collect_category`: 특정 분류 피드만 수집·처리한다.
- `collect_all`: 등록된 모든 피드를 수집·처리한다.
- 이미 처리된 기사는 `summary_lines`가 비어있지 않으면 건너뛴다(재처리 방지).
"""

from __future__ import annotations

import logging

import httpx
from dait.collectors.rss import FEED_SOURCES, FeedSource, fetch_feed
from dait.repositories.news_repository import NewsRepository
from dait.workers.ai_processor import AIProcessor, ArticleContent

logger = logging.getLogger(__name__)

_MAX_ENTRIES_PER_FEED = 10


class CollectionService:
    def __init__(
        self,
        repository: NewsRepository,
        processor: AIProcessor,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._repo = repository
        self._processor = processor
        self._client = client

    async def _process_articles(
        self, articles: list[dict[str, object]]
    ) -> None:
        """저장된 PENDING 기사를 AIProcessor로 처리해 결과를 기록한다."""
        contents = [
            ArticleContent(
                title=str(a["title"]),
                body_text=str(a["body_text"]),
                is_foreign=bool(a["is_foreign"]),
            )
            for a in articles
        ]
        import asyncio

        results = await asyncio.gather(
            *(self._processor.process(c) for c in contents)
        )
        for article, result in zip(articles, results, strict=True):
            self._repo.save_processed(
                str(article["url"]),
                status=result.status.value,
                summary_lines=list(result.summary_lines),
                translated_title=result.translated_title,
                engine=result.engine,
                model_id=result.model_id,
            )

    async def _collect_sources(
        self, sources: list[FeedSource]
    ) -> tuple[int, int]:
        """피드 수집 → 신규 저장 → AI 처리. (수집 건수, 처리 건수) 반환."""
        collected = 0
        client = self._client or httpx.AsyncClient()
        try:
            for source in sources:
                articles = await fetch_feed(
                    client,
                    source,
                    max_entries=_MAX_ENTRIES_PER_FEED,
                    known_urls=self._repo.existing_urls,
                )
                collected += len(articles)
                if not articles:
                    continue
                inserted = self._repo.insert_articles(
                    [
                        {
                            "url": a.url,
                            "title": a.title,
                            "body_text": a.body_text,
                            "category": a.category,
                            "is_foreign": a.is_foreign,
                            "published_at": a.published_at,
                        }
                        for a in articles
                    ]
                )
                if inserted == 0:
                    continue
                # 이번 수집으로 새로 들어온(PENDING) 기사만 처리
                pending_urls = self._repo.pending_urls([a.url for a in articles])
                pending = [a for a in articles if a.url in pending_urls]
                await self._process_articles(
                    [
                        {
                            "url": a.url,
                            "title": a.title,
                            "body_text": a.body_text,
                            "is_foreign": a.is_foreign,
                        }
                        for a in pending
                    ]
                )
        finally:
            if self._client is None:
                await client.aclose()
        return collected, collected

    async def collect_category(self, category: str) -> dict[str, int]:
        sources = [s for s in FEED_SOURCES if s.category == category]
        if not sources:
            return {"collected": 0, "processed": 0}
        collected, processed = await self._collect_sources(sources)
        return {"collected": collected, "processed": processed}

    async def collect_all(self) -> dict[str, int]:
        collected, processed = await self._collect_sources(list(FEED_SOURCES))
        return {"collected": collected, "processed": processed}

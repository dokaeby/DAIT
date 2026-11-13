# _ManagedRuntime

> God node · 39 connections · `src/backend/app/api/main.py`

**Community:** [_ManagedRuntime](_ManagedRuntime.md)

## Connections by Relation

### calls
- create_application() `EXTRACTED`

### contains
- api/main.py `EXTRACTED`

### inherits
- [NewsApiService](NewsApiService.md) `EXTRACTED`

### method
- .__init__() `EXTRACTED`
- ._is_invalid_record() `EXTRACTED`
- ._bootstrap_if_empty() `EXTRACTED`
- ._reprocess_fallbacks() `EXTRACTED`
- ._crawl_and_invalidate() `EXTRACTED`
- .startup() `EXTRACTED`
- ._crawl_official_rss_feeds() `EXTRACTED`
- ._schedule_crawl() `EXTRACTED`
- .refresh() `EXTRACTED`
- .query_news() `EXTRACTED`
- ._collect_loop() `EXTRACTED`
- .get_api_detail() `EXTRACTED`
- ._reset_schema_and_data() `EXTRACTED`
- .is_collecting() `EXTRACTED`
- .shutdown() `EXTRACTED`

### rationale_for
- Owns repository, optional Redis client, and live RSS CollectorWorker execution. `EXTRACTED`

### uses
- [NewsRepository](NewsRepository.md) `INFERRED`
- [SuccessContent](SuccessContent.md) `INFERRED`
- [NewsService](NewsService.md) `INFERRED`
- [StoredNews](StoredNews.md) `INFERRED`
- RSSCollector `INFERRED`
- NewsQuery `INFERRED`
- NewsListResponse `INFERRED`
- [NewsDetailResponse](NewsDetailResponse.md) `INFERRED`
- [CloudLLMSettings](CloudLLMSettings.md) `INFERRED`
- GoogleTranslateContentProcessor `INFERRED`
- CloudLLMContentProcessor `INFERRED`
- CollectorWorker `INFERRED`
- TranslatingNewsCollector `INFERRED`
- [RedisNewsCache](RedisNewsCache.md) `INFERRED`
- NewsServicePolicy `INFERRED`
- RepositorySettings `INFERRED`
- [NewsCache](NewsCache.md) `INFERRED`
- NewsCollector `INFERRED`
- Base `INFERRED`
- WorkerPolicy `INFERRED`

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
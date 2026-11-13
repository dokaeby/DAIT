# NewsService

> God node · 41 connections · `src/backend/app/services/news_service.py`

**Community:** [news_service.py](news_service.py.md)

## Connections by Relation

### calls
- service() `EXTRACTED`
- .__init__() `EXTRACTED`

### contains
- [news_service.py](news_service.py.md) `EXTRACTED`

### imports
- [test_news_repository.py](test_news_repository.py.md) `EXTRACTED`
- [test_news_service.py](test_news_service.py.md) `EXTRACTED`
- api/main.py `EXTRACTED`

### method
- ._api_records() `EXTRACTED`
- .query_news() `EXTRACTED`
- .get_api_detail() `EXTRACTED`
- .get_detail() `EXTRACTED`
- ._list_from_db() `EXTRACTED`
- .list_news() `EXTRACTED`
- .__init__() `EXTRACTED`
- ._source_priority() `EXTRACTED`
- ._search_like() `EXTRACTED`
- ._after_cursor() `EXTRACTED`
- ._cache_call() `EXTRACTED`
- ._query_binding() `EXTRACTED`
- ._decode_cursor() `EXTRACTED`
- ._encode_cursor() `EXTRACTED`
- .invalidate_lists() `EXTRACTED`

### references
- 3.1 개별 기사 상세 URL(`canonical_url` / `original_url`) 정상화 및 더미 데이터 영구 제거 `INFERRED`

### uses
- [SuccessContent](SuccessContent.md) `INFERRED`
- [_ManagedRuntime](_ManagedRuntime.md) `INFERRED`
- RankingRequest `INFERRED`
- [StoredNews](StoredNews.md) `INFERRED`
- RankingService `INFERRED`
- NewsQuery `INFERRED`
- RankingCandidate `INFERRED`
- NewsListResponse `INFERRED`
- [NewsDetailResponse](NewsDetailResponse.md) `INFERRED`
- test_real_repository_news_service_fallback_without_redis() `INFERRED`
- NewsContent `INFERRED`
- NewsPage `INFERRED`
- test_config_order_shares_cache_but_priority_change_isolated() `INFERRED`
- NewsArticle `INFERRED`
- NewsSource `INFERRED`
- test_ranked_list_slicing_and_cache_hit() `INFERRED`
- NewsMeta `INFERRED`
- NewsProcessing `INFERRED`
- NewsIdentifier `INFERRED`

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
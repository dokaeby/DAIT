# RedisNewsCache

> 15 nodes

## Key Concepts

- **RedisNewsCache** (15 connections) — `src/backend/app/services/news_service.py`
- **NewsServiceError** (13 connections) — `src/backend/app/services/news_service.py`
- **_text()** (5 connections) — `src/backend/app/services/news_service.py`
- **CacheGeneration** (4 connections) — `src/backend/app/services/news_service.py`
- **.generation()** (4 connections) — `src/backend/app/services/news_service.py`
- **.get_detail()** (2 connections) — `src/backend/app/services/news_service.py`
- **.get_list()** (2 connections) — `src/backend/app/services/news_service.py`
- **.__init__()** (2 connections) — `src/backend/app/services/news_service.py`
- **.put_list()** (2 connections) — `src/backend/app/services/news_service.py`
- **ValueError** (2 connections)
- **.invalidate_lists()** (1 connections) — `src/backend/app/services/news_service.py`
- **.put_detail()** (1 connections) — `src/backend/app/services/news_service.py`
- **Redis** (1 connections)
- **Caller owns the Redis client; NewsService bounds all cache operations. A…** (1 connections) — `src/backend/app/services/news_service.py`
- **Fixed diagnostic; no cached payloads, URLs or private content in logs.** (1 connections) — `src/backend/app/services/news_service.py`

## Relationships

- [news_service.py](news_service.py.md) (9 shared connections)
- [test_news_service.py](test_news_service.py.md) (3 shared connections)
- [FakeRedisWire](FakeRedisWire.md) (3 shared connections)
- [repair_contextual_title](repair_contextual_title.md) (1 shared connections)
- [NewsDetailResponse](NewsDetailResponse.md) (1 shared connections)
- [test_taxonomy_and_categories.py](test_taxonomy_and_categories.py.md) (1 shared connections)
- [ai_processor.py](ai_processor.py.md) (1 shared connections)
- [_ManagedRuntime](_ManagedRuntime.md) (1 shared connections)

## Source Files

- `src/backend/app/services/news_service.py`

## Audit Trail

- EXTRACTED: 33 (87%)
- INFERRED: 5 (13%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
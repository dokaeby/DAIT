# NewsCache

> 16 nodes

## Key Concepts

- **NewsCache** (11 connections) — `src/backend/app/services/news_service.py`
- **NewsReader** (10 connections) — `src/backend/app/services/news_service.py`
- **NewsRanker** (6 connections) — `src/backend/app/services/news_service.py`
- **.__init__()** (6 connections) — `src/backend/app/services/news_service.py`
- **.list_candidates()** (4 connections) — `src/backend/app/services/news_service.py`
- **.get_by_id()** (3 connections) — `src/backend/app/services/news_service.py`
- **Protocol** (3 connections)
- **UUID** (3 connections)
- **.list_news()** (2 connections) — `src/backend/app/services/news_service.py`
- **.generation()** (1 connections) — `src/backend/app/services/news_service.py`
- **.get_detail()** (1 connections) — `src/backend/app/services/news_service.py`
- **.get_list()** (1 connections) — `src/backend/app/services/news_service.py`
- **.invalidate_lists()** (1 connections) — `src/backend/app/services/news_service.py`
- **.put_detail()** (1 connections) — `src/backend/app/services/news_service.py`
- **.put_list()** (1 connections) — `src/backend/app/services/news_service.py`
- **CategoryType** (1 connections)

## Relationships

- [news_service.py](news_service.py.md) (6 shared connections)
- [test_ranking_service.py](test_ranking_service.py.md) (4 shared connections)
- [StoredNews](StoredNews.md) (4 shared connections)
- [ReadyInvalidator](ReadyInvalidator.md) (2 shared connections)
- [NewsDetailResponse](NewsDetailResponse.md) (2 shared connections)
- [ai_processor.py](ai_processor.py.md) (1 shared connections)
- [_ManagedRuntime](_ManagedRuntime.md) (1 shared connections)
- [test_news_service.py](test_news_service.py.md) (1 shared connections)

## Source Files

- `src/backend/app/services/news_service.py`

## Audit Trail

- EXTRACTED: 32 (84%)
- INFERRED: 6 (16%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
# StoredNews

> 37 nodes

## Key Concepts

- **StoredNews** (32 connections) — `src/backend/app/repositories/news_repository.py`
- **PipelineRecord** (24 connections) — `src/backend/app/workers/collector_worker.py`
- **_safe_operation()** (17 connections) — `src/backend/app/repositories/news_repository.py`
- **._session()** (14 connections) — `src/backend/app/repositories/news_repository.py`
- **.complete()** (12 connections) — `src/backend/app/repositories/news_repository.py`
- **.claim()** (11 connections) — `src/backend/app/repositories/news_repository.py`
- **_stored_news()** (10 connections) — `src/backend/app/repositories/news_repository.py`
- **.list_candidates()** (9 connections) — `src/backend/app/repositories/news_repository.py`
- **.update_content()** (8 connections) — `src/backend/app/repositories/news_repository.py`
- **NewsKey** (7 connections) — `src/backend/app/repositories/news_repository.py`
- **.get()** (7 connections) — `src/backend/app/repositories/news_repository.py`
- **.get_by_id()** (7 connections) — `src/backend/app/repositories/news_repository.py`
- **NewsIdentifier** (6 connections) — `src/backend/app/repositories/news_repository.py`
- **_locked_claim()** (6 connections) — `src/backend/app/repositories/news_repository.py`
- **.delete_records()** (6 connections) — `src/backend/app/repositories/news_repository.py`
- **.list_news()** (6 connections) — `src/backend/app/repositories/news_repository.py`
- **_db_now()** (5 connections) — `src/backend/app/repositories/news_repository.py`
- **.count_news()** (5 connections) — `src/backend/app/repositories/news_repository.py`
- **.release()** (5 connections) — `src/backend/app/repositories/news_repository.py`
- **.normalize_url()** (4 connections) — `src/backend/app/repositories/news_repository.py`
- **BaseModel** (4 connections)
- **ClaimRequest** (3 connections) — `src/backend/app/repositories/news_repository.py`
- **.validate_record()** (3 connections) — `src/backend/app/repositories/news_repository.py`
- **AsyncSession** (3 connections)
- **HttpUrl** (3 connections)
- *... and 12 more nodes in this community*

## Relationships

- [test_news_repository.py](test_news_repository.py.md) (28 shared connections)
- [app/repositories/news_repository.py](app-repositories-news_repository.py.md) (24 shared connections)
- [test_news_service.py](test_news_service.py.md) (9 shared connections)
- [ProcessingClaim](ProcessingClaim.md) (9 shared connections)
- [news_service.py](news_service.py.md) (7 shared connections)
- [ai_processor.py](ai_processor.py.md) (5 shared connections)
- [NewsCache](NewsCache.md) (4 shared connections)
- [_ManagedRuntime](_ManagedRuntime.md) (4 shared connections)
- [NewsDetailResponse](NewsDetailResponse.md) (2 shared connections)
- [.list_candidates](list_candidates.md) (2 shared connections)
- [withdraw](withdraw.md) (2 shared connections)
- [repair_contextual_title](repair_contextual_title.md) (1 shared connections)

## Source Files

- `src/backend/app/repositories/news_repository.py`
- `src/backend/app/workers/collector_worker.py`

## Audit Trail

- EXTRACTED: 137 (83%)
- INFERRED: 29 (17%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
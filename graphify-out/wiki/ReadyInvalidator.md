# ReadyInvalidator

> 6 nodes

## Key Concepts

- **ReadyInvalidator** (10 connections) — `src/backend/app/repositories/news_repository.py`
- **.add_ready_invalidator()** (3 connections) — `src/backend/app/repositories/news_repository.py`
- **.add_ready_invalidator()** (2 connections) — `src/backend/app/services/news_service.py`
- **.add_ready_invalidator()** (2 connections) — `tests/backend/tests/unit/test_news_service.py`
- **.invalidate_lists()** (1 connections) — `src/backend/app/repositories/news_repository.py`
- **Register once at application startup; callbacks run after a READY commit.…** (1 connections) — `src/backend/app/repositories/news_repository.py`

## Relationships

- [test_news_service.py](test_news_service.py.md) (3 shared connections)
- [app/repositories/news_repository.py](app-repositories-news_repository.py.md) (2 shared connections)
- [NewsCache](NewsCache.md) (2 shared connections)
- [news_service.py](news_service.py.md) (1 shared connections)
- [test_news_repository.py](test_news_repository.py.md) (1 shared connections)

## Source Files

- `src/backend/app/repositories/news_repository.py`
- `src/backend/app/services/news_service.py`
- `tests/backend/tests/unit/test_news_service.py`

## Audit Trail

- EXTRACTED: 12 (86%)
- INFERRED: 2 (14%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
# test_worker_and_real_ai_processor_use_sqlite_repository

> 13 nodes

## Key Concepts

- **test_worker_and_real_ai_processor_use_sqlite_repository()** (14 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **test_independent_workers_sqlite_claim_prevents_concurrent_llm()** (13 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **FakeCollector** (8 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **FakeCache** (7 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **FakeLLM** (7 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **FakeGuard** (5 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **.collect()** (4 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **.sanitize()** (2 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **.get()** (1 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **.__init__()** (1 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **.lock()** (1 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **.put()** (1 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **.__init__()** (1 connections) — `tests/backend/tests/integration/test_news_repository.py`

## Relationships

- [test_news_repository.py](test_news_repository.py.md) (13 shared connections)
- [test_pipeline_flow.py](test_pipeline_flow.py.md) (8 shared connections)
- [CollectionResult](CollectionResult.md) (4 shared connections)
- [CollectorSource](CollectorSource.md) (4 shared connections)
- [test_ai_processor.py](test_ai_processor.py.md) (3 shared connections)
- [app/repositories/news_repository.py](app-repositories-news_repository.py.md) (1 shared connections)
- [ProcessingClaim](ProcessingClaim.md) (1 shared connections)
- [ai_processor.py](ai_processor.py.md) (1 shared connections)

## Source Files

- `tests/backend/tests/integration/test_news_repository.py`

## Audit Trail

- EXTRACTED: 30 (60%)
- INFERRED: 20 (40%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
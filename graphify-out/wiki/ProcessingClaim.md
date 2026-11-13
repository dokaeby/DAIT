# ProcessingClaim

> 29 nodes

## Key Concepts

- **ProcessingClaim** (21 connections) — `src/backend/app/workers/collector_worker.py`
- **ClaimDecision** (12 connections) — `src/backend/app/workers/collector_worker.py`
- **FakeRepository** (11 connections) — `tests/backend/tests/integration/test_pipeline_flow.py`
- **PipelineRepository** (9 connections) — `src/backend/app/workers/collector_worker.py`
- **WorkerModel** (7 connections) — `src/backend/app/workers/collector_worker.py`
- **._process()** (6 connections) — `src/backend/app/workers/collector_worker.py`
- **_owned_claim()** (6 connections) — `src/backend/app/workers/collector_worker.py`
- **.claim()** (5 connections) — `tests/backend/tests/integration/test_pipeline_flow.py`
- **.normalize_url()** (4 connections) — `src/backend/app/workers/collector_worker.py`
- **.complete()** (4 connections) — `tests/backend/tests/integration/test_pipeline_flow.py`
- **test_worker_models_are_frozen_and_forbid_invalid_state()** (4 connections) — `tests/backend/tests/integration/test_pipeline_flow.py`
- **.validate_claim()** (3 connections) — `src/backend/app/workers/collector_worker.py`
- **.validate_totals()** (3 connections) — `src/backend/app/workers/collector_worker.py`
- **.claim()** (3 connections) — `src/backend/app/workers/collector_worker.py`
- **.complete()** (3 connections) — `src/backend/app/workers/collector_worker.py`
- **.now()** (3 connections) — `tests/backend/tests/integration/test_pipeline_flow.py`
- **HttpUrl** (3 connections)
- **Protocol** (3 connections)
- **.release()** (2 connections) — `src/backend/app/workers/collector_worker.py`
- **.release()** (2 connections) — `tests/backend/tests/integration/test_pipeline_flow.py`
- **model_validator** (2 connections)
- **Self** (2 connections)
- **.__init__()** (1 connections) — `tests/backend/tests/integration/test_pipeline_flow.py`
- **Outcome** (1 connections)
- **BaseModel** (1 connections)
- *... and 4 more nodes in this community*

## Relationships

- [test_pipeline_flow.py](test_pipeline_flow.py.md) (13 shared connections)
- [StoredNews](StoredNews.md) (9 shared connections)
- [ai_processor.py](ai_processor.py.md) (8 shared connections)
- [test_news_repository.py](test_news_repository.py.md) (5 shared connections)
- [app/repositories/news_repository.py](app-repositories-news_repository.py.md) (3 shared connections)
- [test_worker_and_real_ai_processor_use_sqlite_repository](test_worker_and_real_ai_processor_use_sqlite_repository.md) (1 shared connections)
- [NewsListItem](NewsListItem.md) (1 shared connections)
- [test_taxonomy_and_categories.py](test_taxonomy_and_categories.py.md) (1 shared connections)

## Source Files

- `src/backend/app/workers/collector_worker.py`
- `tests/backend/tests/integration/test_pipeline_flow.py`

## Audit Trail

- EXTRACTED: 74 (89%)
- INFERRED: 9 (11%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
# test_pipeline_flow.py

> 85 nodes

## Key Concepts

- **test_pipeline_flow.py** (56 connections) — `tests/backend/tests/integration/test_pipeline_flow.py`
- **AIProcessor** (25 connections) — `src/backend/app/workers/ai_processor.py`
- **Pipeline** (23 connections) — `tests/backend/tests/integration/test_pipeline_flow.py`
- **ContentPolicy** (19 connections) — `src/backend/app/schemas/content.py`
- **PrivacyDecision** (19 connections) — `src/backend/app/schemas/content.py`
- **CollectorWorker** (18 connections) — `src/backend/app/workers/collector_worker.py`
- **.__init__()** (9 connections) — `tests/backend/tests/integration/test_pipeline_flow.py`
- **WorkerError** (8 connections) — `src/backend/app/workers/collector_worker.py`
- **WorkerPolicy** (8 connections) — `src/backend/app/workers/collector_worker.py`
- **FakeCache** (8 connections) — `tests/backend/tests/integration/test_pipeline_flow.py`
- **ContentModel** (7 connections) — `src/backend/app/schemas/content.py`
- **.run_once()** (7 connections) — `src/backend/app/workers/collector_worker.py`
- **ContentCache** (6 connections) — `src/backend/app/workers/ai_processor.py`
- **PrivacyGuard** (6 connections) — `src/backend/app/workers/ai_processor.py`
- **PipelineReport** (6 connections) — `src/backend/app/workers/collector_worker.py`
- **.make_processor()** (6 connections) — `tests/backend/tests/integration/test_pipeline_flow.py`
- **test_worker_filters_duplicate_items_at_its_boundary()** (6 connections) — `tests/backend/tests/integration/test_pipeline_flow.py`
- **6. 최근 수정: midterms 제목 번역 문맥 보정** (6 connections) — `HANDOVER.md`
- **LLMClient** (5 connections) — `src/backend/app/workers/ai_processor.py`
- **FakeSource** (5 connections) — `tests/backend/tests/integration/test_pipeline_flow.py`
- **.__init__()** (5 connections) — `src/backend/app/workers/ai_processor.py`
- **.__init__()** (5 connections) — `src/backend/app/workers/collector_worker.py`
- **_validated_collection()** (5 connections) — `src/backend/app/workers/collector_worker.py`
- **rss_item()** (5 connections) — `tests/backend/tests/integration/test_pipeline_flow.py`
- **test_insufficient_is_completed_without_llm()** (5 connections) — `tests/backend/tests/integration/test_pipeline_flow.py`
- *... and 60 more nodes in this community*

## Relationships

- [ai_processor.py](ai_processor.py.md) (42 shared connections)
- [test_ai_processor.py](test_ai_processor.py.md) (21 shared connections)
- [ProcessingClaim](ProcessingClaim.md) (13 shared connections)
- [test_worker_and_real_ai_processor_use_sqlite_repository](test_worker_and_real_ai_processor_use_sqlite_repository.md) (8 shared connections)
- [CollectorSource](CollectorSource.md) (8 shared connections)
- [CollectionResult](CollectionResult.md) (7 shared connections)
- [_ManagedRuntime](_ManagedRuntime.md) (5 shared connections)
- [test_news_repository.py](test_news_repository.py.md) (4 shared connections)
- [unit/test_collector.py](unit-test_collector.py.md) (3 shared connections)
- [test_taxonomy_and_categories.py](test_taxonomy_and_categories.py.md) (2 shared connections)
- [collections_abc](collections_abc.md) (2 shared connections)
- [datetime](datetime.md) (2 shared connections)

## Source Files

- `HANDOVER.md`
- `src/backend/app/schemas/content.py`
- `src/backend/app/workers/ai_processor.py`
- `src/backend/app/workers/collector_worker.py`
- `tests/backend/tests/integration/test_pipeline_flow.py`
- `tests/backend/tests/unit/test_ai_processor.py`

## Audit Trail

- EXTRACTED: 216 (83%)
- INFERRED: 43 (17%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
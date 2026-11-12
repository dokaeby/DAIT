# test_news_repository.py

> 45 nodes

## Key Concepts

- **test_news_repository.py** (89 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **NewsRepository** (54 connections) — `src/backend/app/repositories/news_repository.py`
- **record()** (25 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **asyncio** (25 connections)
- **counts()** (19 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **save()** (13 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **ContentResultRow** (12 connections) — `src/backend/app/repositories/news_repository.py`
- **Base** (10 connections) — `src/backend/app/repositories/news_repository.py`
- **test_boundary_rejects_corrupted_input_and_output()** (10 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **test_foreign_key_and_delete_cascade()** (10 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **NewsRow** (9 connections) — `src/backend/app/repositories/news_repository.py`
- **ProcessingClaimRow** (9 connections) — `src/backend/app/repositories/news_repository.py`
- **test_db_one_to_one_constraint()** (9 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **test_transaction_rolls_back_both_rows_and_completion()** (9 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **test_db_rejects_incomplete_success()** (8 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **test_db_unique_canonical_url()** (8 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **test_expired_claim_is_replaced()** (8 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **test_failed_notification_keeps_committed_rows()** (8 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **test_parameterized_text_and_safe_logs()** (8 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **test_ready_notification_runs_after_atomic_commit_and_only_on_success()** (8 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **test_unowned_complete_leaves_no_claim_or_partial_rows()** (8 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **insert_rows()** (7 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **test_atomic_roundtrip_and_utc()** (7 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **test_reopen_preserves_records_and_claims()** (7 connections) — `tests/backend/tests/integration/test_news_repository.py`
- **update()** (6 connections) — `docs/demo/DAIT_ui_v1.0.1/src/backend/src/dait/services/search_lab_service.py`
- *... and 20 more nodes in this community*

## Relationships

- [app/repositories/news_repository.py](app-repositories-news_repository.py.md) (28 shared connections)
- [StoredNews](StoredNews.md) (28 shared connections)
- [ai_processor.py](ai_processor.py.md) (17 shared connections)
- [test_worker_and_real_ai_processor_use_sqlite_repository](test_worker_and_real_ai_processor_use_sqlite_repository.md) (13 shared connections)
- [no_external_connections](no_external_connections.md) (6 shared connections)
- [datetime](datetime.md) (6 shared connections)
- [test_real_repository_news_service_fallback_without_redis](test_real_repository_news_service_fallback_without_redis.md) (5 shared connections)
- [ProcessingClaim](ProcessingClaim.md) (5 shared connections)
- [test_pipeline_flow.py](test_pipeline_flow.py.md) (4 shared connections)
- [_ManagedRuntime](_ManagedRuntime.md) (2 shared connections)
- [test_ai_processor.py](test_ai_processor.py.md) (2 shared connections)
- [collections_abc](collections_abc.md) (2 shared connections)

## Source Files

- `docs/demo/DAIT_ui_v1.0.1/src/backend/src/dait/services/search_lab_service.py`
- `src/backend/app/repositories/news_repository.py`
- `tests/backend/tests/integration/test_news_repository.py`

## Audit Trail

- EXTRACTED: 216 (74%)
- INFERRED: 75 (26%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
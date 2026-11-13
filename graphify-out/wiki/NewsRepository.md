# NewsRepository

> God node · 54 connections · `src/backend/app/repositories/news_repository.py`

**Community:** [test_news_repository.py](test_news_repository.py.md)

## Connections by Relation

### calls
- .__init__() `EXTRACTED`

### contains
- [app/repositories/news_repository.py](app-repositories-news_repository.py.md) `EXTRACTED`

### imports
- [test_news_repository.py](test_news_repository.py.md) `EXTRACTED`
- api/main.py `EXTRACTED`

### method
- ._session() `EXTRACTED`
- .complete() `EXTRACTED`
- .claim() `EXTRACTED`
- .list_candidates() `EXTRACTED`
- .update_content() `EXTRACTED`
- .get() `EXTRACTED`
- .get_by_id() `EXTRACTED`
- .list_news() `EXTRACTED`
- .delete_records() `EXTRACTED`
- .release() `EXTRACTED`
- .count_news() `EXTRACTED`
- .__init__() `EXTRACTED`
- .initialize() `EXTRACTED`
- .add_ready_invalidator() `EXTRACTED`
- .close() `EXTRACTED`

### rationale_for
- Owns its engine; create one per application lifecycle and close at shutdown. `EXTRACTED`

### uses
- [CollectedArticle](CollectedArticle.md) `INFERRED`
- [SuccessContent](SuccessContent.md) `INFERRED`
- [_ManagedRuntime](_ManagedRuntime.md) `INFERRED`
- PipelineRecord `INFERRED`
- [ProcessingClaim](ProcessingClaim.md) `INFERRED`
- counts() `INFERRED`
- test_real_repository_news_service_fallback_without_redis() `INFERRED`
- test_worker_and_real_ai_processor_use_sqlite_repository() `INFERRED`
- save() `INFERRED`
- test_independent_workers_sqlite_claim_prevents_concurrent_llm() `INFERRED`
- ClaimDecision `INFERRED`
- test_boundary_rejects_corrupted_input_and_output() `INFERRED`
- test_foreign_key_and_delete_cascade() `INFERRED`
- test_db_one_to_one_constraint() `INFERRED`
- test_transaction_rolls_back_both_rows_and_completion() `INFERRED`
- test_db_rejects_incomplete_success() `INFERRED`
- test_db_unique_canonical_url() `INFERRED`
- test_expired_claim_is_replaced() `INFERRED`
- test_failed_notification_keeps_committed_rows() `INFERRED`
- test_parameterized_text_and_safe_logs() `INFERRED`
- *…and 14 more `uses` connection(s) not listed (lowest-degree first to go)*

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
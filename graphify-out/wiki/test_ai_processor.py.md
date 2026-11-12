# test_ai_processor.py

> 70 nodes

## Key Concepts

- **test_ai_processor.py** (70 connections) — `tests/backend/tests/unit/test_ai_processor.py`
- **worker()** (47 connections) — `tests/backend/tests/unit/test_ai_processor.py`
- **ProcessingError** (33 connections) — `src/backend/app/workers/ai_processor.py`
- **FakeLLM** (33 connections) — `tests/backend/tests/unit/test_ai_processor.py`
- **FakeCache** (32 connections) — `tests/backend/tests/unit/test_ai_processor.py`
- **article()** (32 connections) — `tests/backend/tests/unit/test_ai_processor.py`
- **GeneratedContent** (29 connections) — `src/backend/app/schemas/content.py`
- **LLMRequest** (18 connections) — `src/backend/app/schemas/content.py`
- **FakePrivacyGuard** (12 connections) — `tests/backend/tests/unit/test_ai_processor.py`
- **test_adapter_cannot_leak_processing_error_text()** (8 connections) — `tests/backend/tests/unit/test_ai_processor.py`
- **test_blank_translation_and_unsafe_protected_term()** (8 connections) — `tests/backend/tests/unit/test_ai_processor.py`
- **test_failed_output_is_retried_instead_of_cached()** (8 connections) — `tests/backend/tests/unit/test_ai_processor.py`
- **test_insufficient_does_not_call_llm_or_scanner()** (8 connections) — `tests/backend/tests/unit/test_ai_processor.py`
- **test_invalid_output_is_not_cached()** (8 connections) — `tests/backend/tests/unit/test_ai_processor.py`
- **test_cache_failure_fails_closed()** (7 connections) — `tests/backend/tests/unit/test_ai_processor.py`
- **test_injection_is_blocked()** (7 connections) — `tests/backend/tests/unit/test_ai_processor.py`
- **test_numeric_sign_changes_are_rejected()** (7 connections) — `tests/backend/tests/unit/test_ai_processor.py`
- **test_policy_approval_is_checked_even_when_cache_exists()** (7 connections) — `tests/backend/tests/unit/test_ai_processor.py`
- **test_policy_versions_invalidate_cache()** (7 connections) — `tests/backend/tests/unit/test_ai_processor.py`
- **test_post_redaction_insufficient()** (7 connections) — `tests/backend/tests/unit/test_ai_processor.py`
- **test_privacy_denial_prevents_llm()** (7 connections) — `tests/backend/tests/unit/test_ai_processor.py`
- **test_protected_name_must_survive_in_summary()** (7 connections) — `tests/backend/tests/unit/test_ai_processor.py`
- **test_provider_failure_is_sanitized_and_not_cached()** (7 connections) — `tests/backend/tests/unit/test_ai_processor.py`
- **test_timeout_and_lock_release()** (7 connections) — `tests/backend/tests/unit/test_ai_processor.py`
- **FakeLLM** (6 connections) — `tests/backend/tests/integration/test_pipeline_flow.py`
- *... and 45 more nodes in this community*

## Relationships

- [ai_processor.py](ai_processor.py.md) (36 shared connections)
- [test_pipeline_flow.py](test_pipeline_flow.py.md) (21 shared connections)
- [SummaryWorkerTests](SummaryWorkerTests.md) (6 shared connections)
- [test_queue.py](test_queue.py.md) (5 shared connections)
- [collections_abc](collections_abc.md) (5 shared connections)
- [NewsListItem](NewsListItem.md) (3 shared connections)
- [test_worker_and_real_ai_processor_use_sqlite_repository](test_worker_and_real_ai_processor_use_sqlite_repository.md) (3 shared connections)
- [GrokClient](GrokClient.md) (3 shared connections)
- [datetime](datetime.md) (3 shared connections)
- [test_translate_to_korean_logs_error_and_retries_on_translator_failure](test_translate_to_korean_logs_error_and_retries_on_translator_failure.md) (3 shared connections)
- [news_service.py](news_service.py.md) (2 shared connections)
- [test_news_repository.py](test_news_repository.py.md) (2 shared connections)

## Source Files

- `src/backend/app/schemas/content.py`
- `src/backend/app/workers/ai_processor.py`
- `tests/backend/tests/integration/test_news_repository.py`
- `tests/backend/tests/integration/test_pipeline_flow.py`
- `tests/backend/tests/unit/test_ai_processor.py`

## Audit Trail

- EXTRACTED: 278 (83%)
- INFERRED: 57 (17%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
# worker()

> God node · 47 connections · `tests/backend/tests/unit/test_ai_processor.py`

**Community:** [test_ai_processor.py](test_ai_processor.py.md)

## Connections by Relation

### calls
- AIProcessor `EXTRACTED`
- FakePrivacyGuard `EXTRACTED`
- test_adapter_cannot_leak_processing_error_text() `EXTRACTED`
- test_blank_translation_and_unsafe_protected_term() `EXTRACTED`
- test_failed_output_is_retried_instead_of_cached() `EXTRACTED`
- test_insufficient_does_not_call_llm_or_scanner() `EXTRACTED`
- test_invalid_output_is_not_cached() `EXTRACTED`
- test_cache_failure_fails_closed() `EXTRACTED`
- test_injection_is_blocked() `EXTRACTED`
- test_numeric_sign_changes_are_rejected() `EXTRACTED`
- test_policy_approval_is_checked_even_when_cache_exists() `EXTRACTED`
- test_post_redaction_insufficient() `EXTRACTED`
- test_privacy_denial_prevents_llm() `EXTRACTED`
- test_protected_name_must_survive_in_summary() `EXTRACTED`
- test_provider_failure_is_sanitized_and_not_cached() `EXTRACTED`
- test_timeout_and_lock_release() `EXTRACTED`
- test_cache_save_failure_is_reported() `EXTRACTED`
- test_forged_cache_hash_is_not_trusted() `EXTRACTED`
- test_lock_failure_prevents_llm() `EXTRACTED`
- test_oversized_input_does_not_call_llm() `EXTRACTED`
- *…and 11 more `calls` connection(s) not listed (lowest-degree first to go)*

### contains
- [test_ai_processor.py](test_ai_processor.py.md) `EXTRACTED`

### indirect_call
- .enqueue() `INFERRED`
- test_same_job_cannot_run_twice_concurrently() `INFERRED`
- test_blank_input_does_not_call_model() `INFERRED`
- test_failure_history_and_retry_budget() `INFERRED`
- test_storage_failure_never_marks_done() `INFERRED`
- test_valid_saved_summary_reused() `INFERRED`
- .test_failure_stops_after_three_attempts_and_preserves_history() `INFERRED`
- .test_reconcile_reuses_and_deduplicates() `INFERRED`
- .test_result_storage_failure_is_not_success() `INFERRED`
- .test_success_is_saved_and_not_generated_again() `INFERRED`
- .setUp() `INFERRED`

### references
- FakeLLM `EXTRACTED`
- FakeCache `EXTRACTED`
- 9-2. 의존 방향과 모듈화 규칙 `INFERRED`

### uses
- ContentPolicy `INFERRED`

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
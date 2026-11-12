# test_cloud_llm.py

> 38 nodes

## Key Concepts

- **test_cloud_llm.py** (59 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **FakeGrokClient** (21 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **CloudLLMContentProcessor** (18 connections) — `src/backend/app/workers/cloud_llm.py`
- **_processor()** (17 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **_settings()** (14 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **_completion_payload()** (13 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **_domestic_article()** (12 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **ContentStatus** (8 connections) — `src/backend/app/workers/cloud_llm.py`
- **test_content_processor_foreign_title_translation()** (8 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **test_content_processor_maps_insufficient()** (8 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **test_content_processor_maps_ready_result()** (8 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **test_batch_coalesces_calls_into_single_request()** (6 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **test_batch_result_count_mismatch_retries_individually()** (6 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **test_domestic_article_returns_three_summary_lines()** (6 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **test_foreign_article_translates_title_and_summarizes()** (6 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **test_insufficient_body_returns_insufficient_without_llm_call()** (6 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **_collected_article()** (5 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **test_cache_hit_makes_zero_api_calls()** (5 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **test_extra_field_in_completion_falls_back()** (5 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **test_missing_api_key_uses_regex_fallback()** (5 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **test_numeric_guard_rejects_invented_numbers()** (5 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **test_api_error_falls_back_to_regex_summary()** (4 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **test_batch_size_bounds_enforced()** (4 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **test_malformed_json_falls_back()** (4 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **test_regex_fallback_always_returns_three_lines()** (4 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- *... and 13 more nodes in this community*

## Relationships

- [ai_processor.py](ai_processor.py.md) (19 shared connections)
- [CloudSummaryProcessor](CloudSummaryProcessor.md) (17 shared connections)
- [GrokClient](GrokClient.md) (13 shared connections)
- [CloudLLMSettings](CloudLLMSettings.md) (8 shared connections)
- [test_ai_processor.py](test_ai_processor.py.md) (2 shared connections)
- [GrokSummaryCompletion](GrokSummaryCompletion.md) (2 shared connections)
- [datetime](datetime.md) (2 shared connections)
- [test_taxonomy_and_categories.py](test_taxonomy_and_categories.py.md) (1 shared connections)
- [_ManagedRuntime](_ManagedRuntime.md) (1 shared connections)
- [.__init__](__init__.md) (1 shared connections)
- [CollectionResult](CollectionResult.md) (1 shared connections)
- [pytest](pytest.md) (1 shared connections)

## Source Files

- `src/backend/app/workers/cloud_llm.py`
- `tests/backend/tests/unit/test_cloud_llm.py`

## Audit Trail

- EXTRACTED: 158 (90%)
- INFERRED: 17 (10%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
# CollectionResult

> 38 nodes

## Key Concepts

- **CollectionResult** (28 connections) — `src/backend/app/schemas/collector.py`
- **test_title_translation_context.py** (21 connections) — `tests/backend/tests/unit/test_title_translation_context.py`
- **translate_title_to_korean()** (18 connections) — `src/backend/app/workers/ai_processor.py`
- **TranslatingNewsCollector** (17 connections) — `src/backend/app/workers/ai_processor.py`
- **httpx** (15 connections)
- **test_offline_or_failed_translation_does_not_append_english_hint()** (11 connections) — `tests/backend/tests/unit/test_title_translation_context.py`
- **test_title_context_is_separated_from_translated_headline()** (11 connections) — `tests/backend/tests/unit/test_title_translation_context.py`
- **asyncio** (9 connections)
- **MonkeyPatch** (9 connections)
- **.collect()** (7 connections) — `src/backend/app/workers/ai_processor.py`
- **_SourceCollector** (6 connections) — `src/backend/app/workers/ai_processor.py`
- **test_flattened_whitespace_does_not_mix_context_into_title()** (6 connections) — `tests/backend/tests/unit/test_title_translation_context.py`
- **test_gtx_fallback_preserves_all_segments_and_extracts_title()** (6 connections) — `tests/backend/tests/unit/test_title_translation_context.py`
- **test_injection_context_is_not_sent()** (6 connections) — `tests/backend/tests/unit/test_title_translation_context.py`
- **test_invalid_markers_retry_title_only_without_body_leak()** (6 connections) — `tests/backend/tests/unit/test_title_translation_context.py`
- **test_long_title_skips_context_to_avoid_truncating_delimiters()** (6 connections) — `tests/backend/tests/unit/test_title_translation_context.py`
- **test_same_title_is_translated_using_different_body_context()** (6 connections) — `tests/backend/tests/unit/test_title_translation_context.py`
- **test_sent_context_is_cleaned_redacted_and_bounded()** (6 connections) — `tests/backend/tests/unit/test_title_translation_context.py`
- **_contains_hangul()** (5 connections) — `src/backend/app/workers/ai_processor.py`
- **fake()** (5 connections) — `tests/backend/tests/unit/test_title_translation_context.py`
- **parametrize** (4 connections)
- **.collect()** (3 connections) — `src/backend/app/workers/ai_processor.py`
- **collect()** (3 connections) — `tests/backend/tests/unit/test_title_translation_context.py`
- **collect()** (3 connections) — `tests/backend/tests/unit/test_title_translation_context.py`
- **.__init__()** (2 connections) — `src/backend/app/workers/ai_processor.py`
- *... and 13 more nodes in this community*

## Relationships

- [ai_processor.py](ai_processor.py.md) (26 shared connections)
- [CollectorSource](CollectorSource.md) (11 shared connections)
- [test_pipeline_flow.py](test_pipeline_flow.py.md) (7 shared connections)
- [test_taxonomy_and_categories.py](test_taxonomy_and_categories.py.md) (6 shared connections)
- [unit/test_collector.py](unit-test_collector.py.md) (4 shared connections)
- [test_worker_and_real_ai_processor_use_sqlite_repository](test_worker_and_real_ai_processor_use_sqlite_repository.md) (4 shared connections)
- [_ManagedRuntime](_ManagedRuntime.md) (3 shared connections)
- [test_ai_processor.py](test_ai_processor.py.md) (2 shared connections)
- [collections_abc](collections_abc.md) (2 shared connections)
- [test_news_repository.py](test_news_repository.py.md) (1 shared connections)
- [repair_contextual_title](repair_contextual_title.md) (1 shared connections)
- [pytest](pytest.md) (1 shared connections)

## Source Files

- `src/backend/app/schemas/collector.py`
- `src/backend/app/workers/ai_processor.py`
- `tests/backend/tests/integration/test_pipeline_flow.py`
- `tests/backend/tests/unit/test_title_translation_context.py`

## Audit Trail

- EXTRACTED: 116 (75%)
- INFERRED: 38 (25%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
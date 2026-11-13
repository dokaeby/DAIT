# CollectorSource

> God node · 43 connections · `src/backend/app/schemas/collector.py`

**Community:** [CollectorSource](CollectorSource.md)

## Connections by Relation

### calls
- source() `EXTRACTED`
- .__init__() `EXTRACTED`
- test_feed_query_token_is_not_logged() `EXTRACTED`
- test_rss_collector_extracts_item_guid_permalink_and_rejects_homepage_root() `EXTRACTED`

### contains
- collector.py `EXTRACTED`

### imports
- [test_news_repository.py](test_news_repository.py.md) `EXTRACTED`
- [ai_processor.py](ai_processor.py.md) `EXTRACTED`
- api/main.py `EXTRACTED`
- [test_pipeline_flow.py](test_pipeline_flow.py.md) `EXTRACTED`
- [unit/test_collector.py](unit-test_collector.py.md) `EXTRACTED`
- rss_collector.py `EXTRACTED`
- [test_taxonomy_and_categories.py](test_taxonomy_and_categories.py.md) `EXTRACTED`
- collector_worker.py `EXTRACTED`
- test_title_translation_context.py `EXTRACTED`

### inherits
- CollectorModel `EXTRACTED`

### method
- .normalize_hosts() `EXTRACTED`

### rationale_for
- Operator-approved source configuration, never supplied by an end user. `EXTRACTED`

### references
- .collect() `EXTRACTED`
- ._download() `EXTRACTED`
- ._robots() `EXTRACTED`
- .collect() `EXTRACTED`
- .run_once() `EXTRACTED`
- .__init__() `EXTRACTED`
- .collect() `EXTRACTED`
- .collect() `EXTRACTED`
- .collect() `EXTRACTED`

### uses
- RSSCollector `INFERRED`
- Pipeline `INFERRED`
- CollectorWorker `INFERRED`
- TranslatingNewsCollector `INFERRED`
- test_worker_and_real_ai_processor_use_sqlite_repository() `INFERRED`
- _parse() `INFERRED`
- test_independent_workers_sqlite_claim_prevents_concurrent_llm() `INFERRED`
- test_google_translate_processor_and_collector_monkeypatched() `INFERRED`
- test_offline_or_failed_translation_does_not_append_english_hint() `INFERRED`
- test_title_context_is_separated_from_translated_headline() `INFERRED`
- NewsCollector `INFERRED`
- _validate_url() `INFERRED`
- FakeCollector `INFERRED`
- _SourceCollector `INFERRED`
- test_worker_filters_duplicate_items_at_its_boundary() `INFERRED`
- _validated_collection() `INFERRED`
- test_models_are_frozen_and_reject_extra_fields() `INFERRED`

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
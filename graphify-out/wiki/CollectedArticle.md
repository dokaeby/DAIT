# CollectedArticle

> God node · 56 connections · `src/backend/app/schemas/collector.py`

**Community:** [ai_processor.py](ai_processor.py.md)

## Connections by Relation

### calls
- [news()](news.md) `EXTRACTED`
- article() `EXTRACTED`
- record() `EXTRACTED`
- _parse() `EXTRACTED`
- _stored_midterms_mistranslation() `EXTRACTED`
- .collect() `EXTRACTED`
- test_techcrunch_global_article_produces_pure_korean_three_line_summary() `EXTRACTED`
- test_domestic_korean_article_extracts_pure_factual_sentences_without_meta_text() `EXTRACTED`
- test_google_translate_processor_returns_insufficient_when_body_too_short() `EXTRACTED`

### contains
- collector.py `EXTRACTED`

### imports
- [test_news_repository.py](test_news_repository.py.md) `EXTRACTED`
- [test_news_service.py](test_news_service.py.md) `EXTRACTED`
- [test_ai_processor.py](test_ai_processor.py.md) `EXTRACTED`
- [news_service.py](news_service.py.md) `EXTRACTED`
- [ai_processor.py](ai_processor.py.md) `EXTRACTED`
- [test_cloud_llm.py](test_cloud_llm.py.md) `EXTRACTED`
- cloud_llm.py `EXTRACTED`
- [app/repositories/news_repository.py](app-repositories-news_repository.py.md) `EXTRACTED`
- [unit/test_collector.py](unit-test_collector.py.md) `EXTRACTED`
- rss_collector.py `EXTRACTED`
- collector_worker.py `EXTRACTED`
- app/schemas/news.py `EXTRACTED`
- test_title_translation_context.py `EXTRACTED`

### inherits
- CollectorModel `EXTRACTED`

### method
- .normalize_url() `EXTRACTED`
- .normalize_timestamp() `EXTRACTED`
- .nonblank() `EXTRACTED`

### references
- .process() `EXTRACTED`
- ._process() `EXTRACTED`
- .process() `EXTRACTED`
- .process() `EXTRACTED`
- ._process() `EXTRACTED`
- .process() `EXTRACTED`

### uses
- [NewsRepository](NewsRepository.md) `INFERRED`
- AIProcessor `INFERRED`
- PipelineRecord `INFERRED`
- [ProcessingClaim](ProcessingClaim.md) `INFERRED`
- GoogleTranslateContentProcessor `INFERRED`
- CloudLLMContentProcessor `INFERRED`
- CollectorWorker `INFERRED`
- TranslatingNewsCollector `INFERRED`
- [NewsListItem](NewsListItem.md) `INFERRED`
- [NewsDetailResponse](NewsDetailResponse.md) `INFERRED`
- NewsContent `INFERRED`
- test_offline_or_failed_translation_does_not_append_english_hint() `INFERRED`
- test_title_context_is_separated_from_translated_headline() `INFERRED`
- _stored_news() `INFERRED`
- NewsArticle `INFERRED`
- NewsSource `INFERRED`
- _NewsCursor `INFERRED`
- test_parameterized_text_and_safe_logs() `INFERRED`
- NewsKey `INFERRED`
- _collected_article() `INFERRED`
- *…and 3 more `uses` connection(s) not listed (lowest-degree first to go)*

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
# SuccessContent

> God node · 50 connections · `src/backend/app/schemas/content.py`

**Community:** [ai_processor.py](ai_processor.py.md)

## Connections by Relation

### calls
- [news()](news.md) `EXTRACTED`
- record() `EXTRACTED`
- candidate() `EXTRACTED`
- .process() `EXTRACTED`
- ._process() `EXTRACTED`
- .process() `EXTRACTED`
- _stored_midterms_mistranslation() `EXTRACTED`
- test_weighted_ranking_combines_recency_priority_keywords_and_popularity() `EXTRACTED`
- test_forged_cache_hash_is_not_trusted() `EXTRACTED`
- scenario() `EXTRACTED`

### contains
- content.py `EXTRACTED`

### imports
- [test_news_repository.py](test_news_repository.py.md) `EXTRACTED`
- [test_news_service.py](test_news_service.py.md) `EXTRACTED`
- [test_ai_processor.py](test_ai_processor.py.md) `EXTRACTED`
- [news_service.py](news_service.py.md) `EXTRACTED`
- [ai_processor.py](ai_processor.py.md) `EXTRACTED`
- api/main.py `EXTRACTED`
- [test_cloud_llm.py](test_cloud_llm.py.md) `EXTRACTED`
- cloud_llm.py `EXTRACTED`
- [app/repositories/news_repository.py](app-repositories-news_repository.py.md) `EXTRACTED`
- [test_pipeline_flow.py](test_pipeline_flow.py.md) `EXTRACTED`
- [test_ranking_service.py](test_ranking_service.py.md) `EXTRACTED`
- [test_taxonomy_and_categories.py](test_taxonomy_and_categories.py.md) `EXTRACTED`
- ranking_service.py `EXTRACTED`

### inherits
- GeneratedContent `EXTRACTED`

### references
- engine/model_id 영속화 + 폴백 재처리 + 검색 범위 + 본문 번역 (2026-11-12 추가) `INFERRED`
- ._cached() `EXTRACTED`
- prompt_version 추적 + 재처리 조건 개선 + 상세 본문 번역 표시 (2026-11-12 추가) `INFERRED`

### uses
- [NewsRepository](NewsRepository.md) `INFERRED`
- [NewsService](NewsService.md) `INFERRED`
- [_ManagedRuntime](_ManagedRuntime.md) `INFERRED`
- FakeRepository `INFERRED`
- AIProcessor `INFERRED`
- RankingCandidate `INFERRED`
- GoogleTranslateContentProcessor `INFERRED`
- CloudLLMContentProcessor `INFERRED`
- test_worker_and_real_ai_processor_use_sqlite_repository() `INFERRED`
- test_google_translate_processor_and_collector_monkeypatched() `INFERRED`
- [NewsDetailResponse](NewsDetailResponse.md) `INFERRED`
- test_boundary_rejects_corrupted_input_and_output() `INFERRED`
- _api_item() `INFERRED`
- test_failed_output_is_retried_instead_of_cached() `INFERRED`
- test_content_processor_foreign_title_translation() `INFERRED`
- test_content_processor_maps_ready_result() `INFERRED`
- _response() `INFERRED`
- test_success_and_cache_hit() `INFERRED`
- test_techcrunch_global_article_produces_pure_korean_three_line_summary() `INFERRED`
- test_domestic_korean_article_extracts_pure_factual_sentences_without_meta_text() `INFERRED`
- *…and 2 more `uses` connection(s) not listed (lowest-degree first to go)*

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
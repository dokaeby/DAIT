# ai_processor.py

> 84 nodes

## Key Concepts

- **ai_processor.py** (66 connections) — `src/backend/app/workers/ai_processor.py`
- **pydantic** (63 connections)
- **api/main.py** (60 connections) — `src/backend/app/api/main.py`
- **cloud_llm.py** (57 connections) — `src/backend/app/workers/cloud_llm.py`
- **CollectedArticle** (56 connections) — `src/backend/app/schemas/collector.py`
- **SuccessContent** (50 connections) — `src/backend/app/schemas/content.py`
- **collector_worker.py** (31 connections) — `src/backend/app/workers/collector_worker.py`
- **InsufficientContent** (29 connections) — `src/backend/app/schemas/content.py`
- **content.py** (27 connections) — `src/backend/app/schemas/content.py`
- **collector.py** (25 connections) — `src/backend/app/schemas/collector.py`
- **taxonomy.py** (21 connections) — `src/backend/app/core/taxonomy.py`
- **GoogleTranslateContentProcessor** (19 connections) — `src/backend/app/workers/ai_processor.py`
- **.process()** (16 connections) — `src/backend/app/workers/ai_processor.py`
- **translate_to_korean()** (16 connections) — `src/backend/app/workers/ai_processor.py`
- **._process()** (14 connections) — `src/backend/app/workers/ai_processor.py`
- **.process()** (13 connections) — `src/backend/app/workers/cloud_llm.py`
- **asyncio** (13 connections)
- **re** (13 connections)
- **extract_clean_body_with_trafilatura()** (11 connections) — `src/backend/app/collectors/content_extractor.py`
- **match_category()** (11 connections) — `src/backend/app/core/taxonomy.py`
- **8. 사용자 승인 후: Google 본문 문맥을 반영하는 제목 번역** (11 connections) — `HANDOVER.md`
- **ensure_terminal_punctuation()** (10 connections) — `src/backend/app/workers/ai_processor.py`
- **_build_three_factual_sentences()** (9 connections) — `src/backend/app/workers/ai_processor.py`
- **_validate_preservation()** (8 connections) — `src/backend/app/workers/ai_processor.py`
- **_safe_text()** (7 connections) — `src/backend/app/workers/ai_processor.py`
- *... and 59 more nodes in this community*

## Relationships

- [test_pipeline_flow.py](test_pipeline_flow.py.md) (42 shared connections)
- [test_ai_processor.py](test_ai_processor.py.md) (36 shared connections)
- [CollectionResult](CollectionResult.md) (26 shared connections)
- [news_service.py](news_service.py.md) (26 shared connections)
- [test_taxonomy_and_categories.py](test_taxonomy_and_categories.py.md) (23 shared connections)
- [test_cloud_llm.py](test_cloud_llm.py.md) (19 shared connections)
- [test_news_repository.py](test_news_repository.py.md) (17 shared connections)
- [test_news_service.py](test_news_service.py.md) (17 shared connections)
- [CollectorSource](CollectorSource.md) (16 shared connections)
- [collections_abc](collections_abc.md) (15 shared connections)
- [datetime](datetime.md) (15 shared connections)
- [test_ranking_service.py](test_ranking_service.py.md) (13 shared connections)

## Source Files

- `HANDOVER.md`
- `src/backend/app/api/main.py`
- `src/backend/app/collectors/content_extractor.py`
- `src/backend/app/core/taxonomy.py`
- `src/backend/app/schemas/collector.py`
- `src/backend/app/schemas/content.py`
- `src/backend/app/workers/ai_processor.py`
- `src/backend/app/workers/cloud_llm.py`
- `src/backend/app/workers/collector_worker.py`
- `tests/backend/tests/unit/test_ai_processor.py`

## Audit Trail

- EXTRACTED: 520 (85%)
- INFERRED: 89 (15%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
# CloudSummaryProcessor

> 38 nodes

## Key Concepts

- **CloudSummaryProcessor** (26 connections) — `src/backend/app/workers/cloud_llm.py`
- **ArticleContent** (16 connections) — `src/backend/app/workers/cloud_llm.py`
- **ProcessedContent** (13 connections) — `src/backend/app/workers/cloud_llm.py`
- **._generate()** (12 connections) — `src/backend/app/workers/cloud_llm.py`
- **._request_batch()** (12 connections) — `src/backend/app/workers/cloud_llm.py`
- **_PendingBatch** (7 connections) — `src/backend/app/workers/cloud_llm.py`
- **._fallback()** (7 connections) — `src/backend/app/workers/cloud_llm.py`
- **.process()** (7 connections) — `src/backend/app/workers/cloud_llm.py`
- **_guarded_completion()** (7 connections) — `src/backend/app/workers/cloud_llm.py`
- **._enqueue()** (6 connections) — `src/backend/app/workers/cloud_llm.py`
- **._is_daily_quota_error()** (6 connections) — `src/backend/app/workers/cloud_llm.py`
- **._flush_loop()** (5 connections) — `src/backend/app/workers/cloud_llm.py`
- **_build_user_prompt()** (4 connections) — `src/backend/app/workers/cloud_llm.py`
- **_clip_body()** (4 connections) — `src/backend/app/workers/cloud_llm.py`
- **._batch_prompt()** (4 connections) — `src/backend/app/workers/cloud_llm.py`
- **._flush_batch()** (4 connections) — `src/backend/app/workers/cloud_llm.py`
- **_content_hash()** (4 connections) — `src/backend/app/workers/cloud_llm.py`
- **_extract_json_object()** (4 connections) — `src/backend/app/workers/cloud_llm.py`
- **_normalize_text()** (4 connections) — `src/backend/app/workers/cloud_llm.py`
- **_regex_summary_lines()** (4 connections) — `src/backend/app/workers/cloud_llm.py`
- **clip_body_for_prompt()** (3 connections) — `src/backend/app/workers/cloud_llm.py`
- **.inner()** (3 connections) — `src/backend/app/workers/cloud_llm.py`
- **._collect_batch()** (3 connections) — `src/backend/app/workers/cloud_llm.py`
- **._ensure_flusher()** (3 connections) — `src/backend/app/workers/cloud_llm.py`
- **._quota_blocked()** (3 connections) — `src/backend/app/workers/cloud_llm.py`
- *... and 13 more nodes in this community*

## Relationships

- [test_cloud_llm.py](test_cloud_llm.py.md) (17 shared connections)
- [ai_processor.py](ai_processor.py.md) (13 shared connections)
- [GrokSummaryCompletion](GrokSummaryCompletion.md) (3 shared connections)
- [response](response.md) (3 shared connections)
- [CloudLLMSettings](CloudLLMSettings.md) (2 shared connections)
- [app/repositories/news_repository.py](app-repositories-news_repository.py.md) (1 shared connections)
- [test_ai_processor.py](test_ai_processor.py.md) (1 shared connections)
- [_allowed_source_numbers](_allowed_source_numbers.md) (1 shared connections)

## Source Files

- `src/backend/app/workers/cloud_llm.py`

## Audit Trail

- EXTRACTED: 107 (95%)
- INFERRED: 6 (5%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
# NewsListItem

> 26 nodes

## Key Concepts

- **NewsListItem** (14 connections) — `src/backend/app/schemas/news.py`
- **field_validator** (9 connections)
- **.normalize_timestamp()** (8 connections) — `src/backend/app/schemas/collector.py`
- **.normalize_url()** (8 connections) — `src/backend/app/schemas/collector.py`
- **item()** (5 connections) — `tests/backend/tests/unit/api/test_app_news_api.py`
- **test_models_forbid_extras_and_enforce_three_summary_sentences()** (5 connections) — `tests/backend/tests/unit/api/test_app_news_api.py`
- **.nonblank()** (4 connections) — `src/backend/app/schemas/collector.py`
- **.utc_time()** (4 connections) — `src/backend/app/schemas/news.py`
- **.utc_time()** (4 connections) — `src/backend/app/schemas/news.py`
- **.safe_url()** (4 connections) — `src/backend/app/schemas/news.py`
- **.utc_time()** (4 connections) — `src/backend/app/schemas/news.py`
- **.safe_url()** (4 connections) — `src/backend/app/schemas/news.py`
- **field_validator** (4 connections)
- **datetime** (4 connections)
- **.validate_sentences()** (3 connections) — `src/backend/app/schemas/content.py`
- **.nonblank()** (3 connections) — `src/backend/app/schemas/news.py`
- **.three_sentences()** (3 connections) — `src/backend/app/schemas/news.py`
- **.nonblank()** (3 connections) — `src/backend/app/services/news_service.py`
- **.normalize_hosts()** (2 connections) — `src/backend/app/schemas/collector.py`
- **.nonblank()** (2 connections) — `src/backend/app/schemas/content.py`
- **.integer_page_size()** (2 connections) — `src/backend/app/schemas/news.py`
- **.normalize_search()** (2 connections) — `src/backend/app/schemas/news.py`
- **datetime** (2 connections)
- **field_validator** (2 connections)
- **HttpUrl** (2 connections)
- *... and 1 more nodes in this community*

## Relationships

- [news_service.py](news_service.py.md) (12 shared connections)
- [test_app_news_api.py](test_app_news_api.py.md) (5 shared connections)
- [ai_processor.py](ai_processor.py.md) (5 shared connections)
- [NewsDetailResponse](NewsDetailResponse.md) (5 shared connections)
- [test_ai_processor.py](test_ai_processor.py.md) (3 shared connections)
- [repair_contextual_title](repair_contextual_title.md) (1 shared connections)
- [StoredNews](StoredNews.md) (1 shared connections)
- [ProcessingClaim](ProcessingClaim.md) (1 shared connections)
- [CollectorSource](CollectorSource.md) (1 shared connections)

## Source Files

- `src/backend/app/schemas/collector.py`
- `src/backend/app/schemas/content.py`
- `src/backend/app/schemas/news.py`
- `src/backend/app/services/news_service.py`
- `tests/backend/tests/unit/api/test_app_news_api.py`

## Audit Trail

- EXTRACTED: 66 (93%)
- INFERRED: 5 (7%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
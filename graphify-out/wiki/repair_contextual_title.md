# repair_contextual_title

> 12 nodes

## Key Concepts

- **repair_contextual_title()** (8 connections) — `src/backend/app/core/title_translation.py`
- **_api_item()** (8 connections) — `src/backend/app/services/news_service.py`
- **title_translation.py** (7 connections) — `src/backend/app/core/title_translation.py`
- **test_title_translation.py** (7 connections) — `tests/backend/tests/unit/test_title_translation.py`
- **contextualize_title()** (6 connections) — `src/backend/app/core/title_translation.py`
- **test_stored_title_repair()** (3 connections) — `tests/backend/tests/unit/test_title_translation.py`
- **test_context_after_first_thirty_five_words_is_used_locally()** (2 connections) — `tests/backend/tests/unit/test_title_translation.py`
- **parametrize** (1 connections)
- **Local, evidence-based disambiguation for bilingual news titles; no network I/O.** (1 connections) — `src/backend/app/core/title_translation.py`
- **Inspect complete supplied article evidence locally, not just the title/teaser.** (1 connections) — `src/backend/app/core/title_translation.py`
- **Repair a stored exam mistranslation only with explicit political evidence. No…** (1 connections) — `src/backend/app/core/title_translation.py`
- **Local title correction must use article evidence and preserve academic titles.** (1 connections) — `tests/backend/tests/unit/test_title_translation.py`

## Relationships

- [news_service.py](news_service.py.md) (5 shared connections)
- [ai_processor.py](ai_processor.py.md) (4 shared connections)
- [NewsDetailResponse](NewsDetailResponse.md) (2 shared connections)
- [CollectionResult](CollectionResult.md) (1 shared connections)
- [RedisNewsCache](RedisNewsCache.md) (1 shared connections)
- [NewsListItem](NewsListItem.md) (1 shared connections)
- [StoredNews](StoredNews.md) (1 shared connections)
- [pytest](pytest.md) (1 shared connections)

## Source Files

- `src/backend/app/core/title_translation.py`
- `src/backend/app/services/news_service.py`
- `tests/backend/tests/unit/test_title_translation.py`

## Audit Trail

- EXTRACTED: 29 (94%)
- INFERRED: 2 (6%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
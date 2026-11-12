# GrokSummaryCompletion

> 9 nodes

## Key Concepts

- **GrokSummaryCompletion** (9 connections) — `src/backend/app/workers/cloud_llm.py`
- **BaseModel** (6 connections)
- **_BatchItem** (3 connections) — `src/backend/app/workers/cloud_llm.py`
- **_BatchEnvelope** (2 connections) — `src/backend/app/workers/cloud_llm.py`
- **._lines_must_be_non_empty()** (2 connections) — `src/backend/app/workers/cloud_llm.py`
- **._title_must_be_non_empty()** (2 connections) — `src/backend/app/workers/cloud_llm.py`
- **test_completion_schema_rejects_empty_line()** (2 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **field_validator** (2 connections)
- **LLM이 반환해야 하는 JSON 출력 계약.** (1 connections) — `src/backend/app/workers/cloud_llm.py`

## Relationships

- [ai_processor.py](ai_processor.py.md) (3 shared connections)
- [CloudSummaryProcessor](CloudSummaryProcessor.md) (3 shared connections)
- [app/repositories/news_repository.py](app-repositories-news_repository.py.md) (2 shared connections)
- [test_cloud_llm.py](test_cloud_llm.py.md) (2 shared connections)
- [CloudLLMSettings](CloudLLMSettings.md) (1 shared connections)

## Source Files

- `src/backend/app/workers/cloud_llm.py`
- `tests/backend/tests/unit/test_cloud_llm.py`

## Audit Trail

- EXTRACTED: 17 (85%)
- INFERRED: 3 (15%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
# GrokClient

> 28 nodes

## Key Concepts

- **GrokClient** (19 connections) — `src/backend/app/workers/cloud_llm.py`
- **.from_settings()** (12 connections) — `src/backend/app/workers/cloud_llm.py`
- **.from_groq_settings()** (5 connections) — `src/backend/app/workers/cloud_llm.py`
- **test_grok_client_retries_on_429_then_succeeds()** (5 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **test_httpx_client_raises_processing_error_on_bad_payload()** (5 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **handler()** (5 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **.complete()** (4 connections) — `src/backend/app/workers/cloud_llm.py`
- **test_grok_client_from_settings_returns_none_without_api_key()** (4 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **test_groq_key_preferred_over_xai()** (4 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **run()** (4 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **test_httpx_client_sends_openai_compatible_request()** (4 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **run()** (4 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **._get_client()** (3 connections) — `src/backend/app/workers/cloud_llm.py`
- **._pace_request()** (3 connections) — `src/backend/app/workers/cloud_llm.py`
- **run()** (3 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **AsyncBaseTransport** (3 connections)
- **.aclose()** (2 connections) — `src/backend/app/workers/cloud_llm.py`
- **.__aexit__()** (2 connections) — `src/backend/app/workers/cloud_llm.py`
- **.__init__()** (2 connections) — `src/backend/app/workers/cloud_llm.py`
- **handler()** (2 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **.aclose()** (1 connections) — `src/backend/app/workers/cloud_llm.py`
- **.__aenter__()** (1 connections) — `src/backend/app/workers/cloud_llm.py`
- **.model()** (1 connections) — `src/backend/app/workers/cloud_llm.py`
- **handler()** (1 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **AsyncClient** (1 connections)
- *... and 3 more nodes in this community*

## Relationships

- [test_cloud_llm.py](test_cloud_llm.py.md) (13 shared connections)
- [CloudLLMSettings](CloudLLMSettings.md) (6 shared connections)
- [test_ai_processor.py](test_ai_processor.py.md) (3 shared connections)
- [ai_processor.py](ai_processor.py.md) (1 shared connections)

## Source Files

- `src/backend/app/workers/cloud_llm.py`
- `tests/backend/tests/unit/test_cloud_llm.py`

## Audit Trail

- EXTRACTED: 53 (84%)
- INFERRED: 10 (16%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
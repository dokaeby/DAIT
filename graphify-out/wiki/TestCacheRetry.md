# TestCacheRetry

> 8 nodes

## Key Concepts

- **TestCacheRetry** (5 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **.test_cache_roundtrip()** (3 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **.test_lock_excludes_concurrent()** (3 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **.test_list_cache_key_hides_query()** (2 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **cache_retry_service 메모리 fallback.** (1 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **Redis 없이도 set→get이 동작하고 TTL이 붙는다.** (1 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **같은 이름의 락은 한 번에 하나만 잡는다.** (1 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **캐시 키에 검색어 원문이 들어가지 않는다.** (1 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`

## Relationships

- [test_pipeline_safety.py](test_pipeline_safety.py.md) (3 shared connections)

## Source Files

- `tests/backend/tests/unit/test_pipeline_safety.py`

## Audit Trail

- EXTRACTED: 10 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
# FakeRedisWire

> 13 nodes

## Key Concepts

- **FakeRedisWire** (8 connections) — `tests/backend/tests/unit/test_news_service.py`
- **test_evicted_generation_is_not_reused_and_invalid_wire_reply_fails()** (6 connections) — `tests/backend/tests/unit/test_news_service.py`
- **no_external_connections()** (5 connections) — `tests/backend/tests/unit/test_news_service.py`
- **test_redis_adapter_wire_contract_ttls_generation_and_atomic_scripts()** (5 connections) — `tests/backend/tests/unit/test_news_service.py`
- **MonkeyPatch** (3 connections)
- **.eval()** (2 connections) — `tests/backend/tests/unit/test_news_service.py`
- **.get()** (2 connections) — `tests/backend/tests/unit/test_news_service.py`
- **deny()** (2 connections) — `tests/backend/tests/unit/test_news_service.py`
- **deny_async()** (2 connections) — `tests/backend/tests/unit/test_news_service.py`
- **.__init__()** (1 connections) — `tests/backend/tests/unit/test_news_service.py`
- **.set()** (1 connections) — `tests/backend/tests/unit/test_news_service.py`
- **fixture** (1 connections)
- **Mock the command boundary, not a real Redis interpreter or server.** (1 connections) — `tests/backend/tests/unit/test_news_service.py`

## Relationships

- [test_news_service.py](test_news_service.py.md) (6 shared connections)
- [RedisNewsCache](RedisNewsCache.md) (3 shared connections)

## Source Files

- `tests/backend/tests/unit/test_news_service.py`

## Audit Trail

- EXTRACTED: 19 (79%)
- INFERRED: 5 (21%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
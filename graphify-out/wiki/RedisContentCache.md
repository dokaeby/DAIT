# RedisContentCache

> 7 nodes

## Key Concepts

- **RedisContentCache** (8 connections) — `src/backend/app/workers/ai_processor.py`
- **.__init__()** (2 connections) — `src/backend/app/workers/ai_processor.py`
- **.get()** (1 connections) — `src/backend/app/workers/ai_processor.py`
- **.lock()** (1 connections) — `src/backend/app/workers/ai_processor.py`
- **.put()** (1 connections) — `src/backend/app/workers/ai_processor.py`
- **Redis** (1 connections)
- **Shared Redis cache with bounded, token-owned distributed locks. Caller owns the…** (1 connections) — `src/backend/app/workers/ai_processor.py`

## Relationships

- [ai_processor.py](ai_processor.py.md) (3 shared connections)

## Source Files

- `src/backend/app/workers/ai_processor.py`

## Audit Trail

- EXTRACTED: 7 (78%)
- INFERRED: 2 (22%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
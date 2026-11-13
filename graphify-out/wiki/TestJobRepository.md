# TestJobRepository

> 5 nodes

## Key Concepts

- **TestJobRepository** (4 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **.test_dedupe_key_conflict()** (2 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **.test_attempt_count_and_record()** (1 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **job_repository dedupe·attempt 기록.** (1 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`
- **같은 dedupe_key 두 번째 등록은 None을 돌려준다.** (1 connections) — `tests/backend/tests/unit/test_pipeline_safety.py`

## Relationships

- [test_pipeline_safety.py](test_pipeline_safety.py.md) (1 shared connections)

## Source Files

- `tests/backend/tests/unit/test_pipeline_safety.py`

## Audit Trail

- EXTRACTED: 5 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
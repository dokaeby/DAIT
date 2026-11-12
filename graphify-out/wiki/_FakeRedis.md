# _FakeRedis

> 7 nodes

## Key Concepts

- **_FakeRedis** (9 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **.delete()** (2 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **.eval()** (1 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **.get()** (1 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **.__init__()** (1 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **.set()** (1 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **RedisLike 프로토콜을 흉내 내는 인메모리 저장소.** (1 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`

## Relationships

- [RedisThrottle](RedisThrottle.md) (2 shared connections)
- [backend/tests/unit/test_password_policy_and_throttle.py](backend-tests-unit-test_password_policy_and_throttle.py.md) (1 shared connections)
- [test_news_repository.py](test_news_repository.py.md) (1 shared connections)

## Source Files

- `tests/backend/tests/unit/test_password_policy_and_throttle.py`

## Audit Trail

- EXTRACTED: 9 (90%)
- INFERRED: 1 (10%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
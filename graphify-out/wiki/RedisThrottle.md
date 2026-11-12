# RedisThrottle

> 16 nodes

## Key Concepts

- **RedisThrottle** (14 connections) — `src/backend/src/dait/services/login_throttle.py`
- **test_redis_throttle_survives_redis_error()** (8 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **test_redis_throttle_clear_and_isolation()** (7 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **test_redis_throttle_locks_at_threshold()** (7 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **_patch_client()** (6 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **_redis_settings()** (6 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **test_redis_throttle_falls_back_to_memory()** (6 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **MonkeyPatch** (5 connections)
- **get()** (1 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **set()** (1 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **Settings** (1 connections)
- **설계서 8절 `rate:{scope}:{identity}` 규격의 분산 잠금 구현. 입력: settings (REDIS_URL), scope…** (1 connections) — `src/backend/src/dait/services/login_throttle.py`
- **Redis 구현도 기준 횟수에 잠기고 시간이 지나면 풀린다.** (1 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **clear는 기록을 지우고, 키는 서로 독립이다.** (1 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **Redis가 없으면 메모리 구현과 같은 규칙으로 동작한다.** (1 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`
- **Redis 호출이 실패해도 예외 없이 fallback으로 동작한다.** (1 connections) — `tests/backend/tests/unit/test_password_policy_and_throttle.py`

## Relationships

- [.register_failure](register_failure.md) (6 shared connections)
- [backend/tests/unit/test_password_policy_and_throttle.py](backend-tests-unit-test_password_policy_and_throttle.py.md) (6 shared connections)
- [backend/src/dait/services/login_throttle.py](backend-src-dait-services-login_throttle.py.md) (3 shared connections)
- [_FakeRedis](_FakeRedis.md) (2 shared connections)

## Source Files

- `src/backend/src/dait/services/login_throttle.py`
- `tests/backend/tests/unit/test_password_policy_and_throttle.py`

## Audit Trail

- EXTRACTED: 38 (90%)
- INFERRED: 4 (10%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
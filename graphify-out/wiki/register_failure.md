# .register_failure

> 12 nodes

## Key Concepts

- **.register_failure()** (6 connections) — `src/backend/src/dait/services/login_throttle.py`
- **.is_locked()** (5 connections) — `src/backend/src/dait/services/login_throttle.py`
- **._key()** (5 connections) — `src/backend/src/dait/services/login_throttle.py`
- **._load()** (5 connections) — `src/backend/src/dait/services/login_throttle.py`
- **._store()** (4 connections) — `src/backend/src/dait/services/login_throttle.py`
- **.clear()** (3 connections) — `src/backend/src/dait/services/login_throttle.py`
- **개인정보를 남기지 않는 Redis 키를 만든다.** (1 connections) — `src/backend/src/dait/services/login_throttle.py`
- **저장된 상태 JSON을 읽는다. 없거나 깨졌으면 None.** (1 connections) — `src/backend/src/dait/services/login_throttle.py`
- **상태 JSON을 TTL과 함께 저장한다.** (1 connections) — `src/backend/src/dait/services/login_throttle.py`
- **해당 키가 지금 잠겨 있는지 알려 준다(Redis 우선, 실패 시 메모리).** (1 connections) — `src/backend/src/dait/services/login_throttle.py`
- **실패 한 번을 기록하고 기준을 넘으면 잠금 시각을 정한다.** (1 connections) — `src/backend/src/dait/services/login_throttle.py`
- **실패 기록을 지운다. 성공한 로그인에서 부른다.** (1 connections) — `src/backend/src/dait/services/login_throttle.py`

## Relationships

- [RedisThrottle](RedisThrottle.md) (6 shared connections)
- [backend/src/dait/services/login_throttle.py](backend-src-dait-services-login_throttle.py.md) (2 shared connections)
- [redis_repository.py](redis_repository.py.md) (2 shared connections)

## Source Files

- `src/backend/src/dait/services/login_throttle.py`

## Audit Trail

- EXTRACTED: 22 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
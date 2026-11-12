# redis_repository.py

> 43 nodes

## Key Concepts

- **redis_repository.py** (19 connections) — `src/backend/src/dait/repositories/redis_repository.py`
- **RedisLike** (16 connections) — `src/backend/src/dait/repositories/redis_repository.py`
- **backend/src/dait/services/health_service.py** (8 connections) — `src/backend/src/dait/services/health_service.py`
- **connect()** (5 connections) — `src/backend/src/dait/repositories/redis_repository.py`
- **shared_client()** (5 connections) — `src/backend/src/dait/repositories/redis_repository.py`
- **acquire_lock()** (4 connections) — `src/backend/src/dait/repositories/redis_repository.py`
- **cache_set()** (4 connections) — `src/backend/src/dait/repositories/redis_repository.py`
- **release_lock()** (4 connections) — `src/backend/src/dait/repositories/redis_repository.py`
- **ensure_redis_ready()** (4 connections) — `src/backend/src/dait/services/health_service.py`
- **cache_get()** (3 connections) — `src/backend/src/dait/repositories/redis_repository.py`
- **new_lock_token()** (3 connections) — `src/backend/src/dait/repositories/redis_repository.py`
- **reset_shared_client()** (3 connections) — `src/backend/src/dait/repositories/redis_repository.py`
- **clear_memory_state()** (3 connections) — `src/backend/src/dait/services/cache_retry_service.py`
- **_SharedState** (2 connections) — `src/backend/src/dait/repositories/redis_repository.py`
- **dumps_json()** (2 connections) — `src/backend/src/dait/repositories/redis_repository.py`
- **loads_json()** (2 connections) — `src/backend/src/dait/repositories/redis_repository.py`
- **.delete()** (2 connections) — `src/backend/src/dait/repositories/redis_repository.py`
- **ensure_database_ready()** (2 connections) — `src/backend/src/dait/services/health_service.py`
- **.eval()** (1 connections) — `src/backend/src/dait/repositories/redis_repository.py`
- **.get()** (1 connections) — `src/backend/src/dait/repositories/redis_repository.py`
- **.set()** (1 connections) — `src/backend/src/dait/repositories/redis_repository.py`
- **Protocol** (1 connections)
- **Settings** (1 connections)
- **Redis 접근 저장소: 분산 락(SET NX PX + 소유권 확인 해제)과 JSON 캐시.** (1 connections) — `src/backend/src/dait/repositories/redis_repository.py`
- **내 토큰일 때만 락을 해제한다. 입력: client, key, token 출력: bool (실제로 지웠으면 True) 기능: Lua…** (1 connections) — `src/backend/src/dait/repositories/redis_repository.py`
- *... and 18 more nodes in this community*

## Relationships

- [cache_retry_service.py](cache_retry_service.py.md) (9 shared connections)
- [.register_failure](register_failure.md) (2 shared connections)
- [datetime](datetime.md) (2 shared connections)
- [StoredNews](StoredNews.md) (1 shared connections)
- [typing](typing.md) (1 shared connections)
- [backend/src/dait/services/login_throttle.py](backend-src-dait-services-login_throttle.py.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/repositories/redis_repository.py`
- `src/backend/src/dait/services/cache_retry_service.py`
- `src/backend/src/dait/services/health_service.py`

## Audit Trail

- EXTRACTED: 65 (98%)
- INFERRED: 1 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
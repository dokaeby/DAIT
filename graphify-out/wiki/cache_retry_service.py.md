# cache_retry_service.py

> 30 nodes

## Key Concepts

- **cache_retry_service.py** (29 connections) — `src/backend/src/dait/services/cache_retry_service.py`
- **locked()** (13 connections) — `src/backend/src/dait/services/cache_retry_service.py`
- **cache_set()** (9 connections) — `src/backend/src/dait/services/cache_retry_service.py`
- **_get_redis()** (9 connections) — `src/backend/src/dait/services/cache_retry_service.py`
- **cache_get()** (8 connections) — `src/backend/src/dait/services/cache_retry_service.py`
- **load_cached()** (8 connections) — `src/backend/src/dait/services/cache_retry_service.py`
- **_redis_call()** (7 connections) — `src/backend/src/dait/services/cache_retry_service.py`
- **cache_delete()** (6 connections) — `src/backend/src/dait/services/cache_retry_service.py`
- **Settings** (6 connections)
- **_jittered_ttl()** (3 connections) — `src/backend/src/dait/services/cache_retry_service.py`
- **list_cache_key()** (3 connections) — `src/backend/src/dait/services/cache_retry_service.py`
- **_memory_try_lock()** (3 connections) — `src/backend/src/dait/services/cache_retry_service.py`
- **detail_cache_key()** (2 connections) — `src/backend/src/dait/services/cache_retry_service.py`
- **detail_ttl()** (2 connections) — `src/backend/src/dait/services/cache_retry_service.py`
- **list_ttl()** (2 connections) — `src/backend/src/dait/services/cache_retry_service.py`
- **_memory_release()** (2 connections) — `src/backend/src/dait/services/cache_retry_service.py`
- **T** (2 connections)
- **FR-PIPE-04 캐시·재시도 보조: TTL+jitter 캐시와 분산 락 stampede 방지. Redis가 설정돼 있으면 redis-py를…** (1 connections) — `src/backend/src/dait/services/cache_retry_service.py`
- **이름으로 분산 락을 잡는다. 못 잡으면 잠시 기다린 뒤 False로 진행한다. 입력: settings, lock_name (락 이름),…** (1 connections) — `src/backend/src/dait/services/cache_retry_service.py`
- **캐시 값을 지운다. 손상된 값을 제거할 때 쓴다. 실패해도 조용히 넘어간다.** (1 connections) — `src/backend/src/dait/services/cache_retry_service.py`
- **캐시 값을 모델로 복원한다. 없거나 손상됐으면 None(미스와 동일하게 처리). 입력: settings, key (캐시 키), model…** (1 connections) — `src/backend/src/dait/services/cache_retry_service.py`
- **목록 캐시 키를 만든다. 검색어 원문 대신 해시를 넣어 키에 개인정보를 남기지 않는다.** (1 connections) — `src/backend/src/dait/services/cache_retry_service.py`
- **TTL에 ±10% 지터를 더해 만료 시각을 분산한다.** (1 connections) — `src/backend/src/dait/services/cache_retry_service.py`
- **설정된 Redis 클라이언트를 지연 생성한다. 없거나 연결 실패면 None.** (1 connections) — `src/backend/src/dait/services/cache_retry_service.py`
- **Redis 호출 래퍼: 실패 시 None을 돌려 fallback으로 보낸다.** (1 connections) — `src/backend/src/dait/services/cache_retry_service.py`
- *... and 5 more nodes in this community*

## Relationships

- [redis_repository.py](redis_repository.py.md) (9 shared connections)
- [news_detail_service.py](news_detail_service.py.md) (6 shared connections)
- [dait/schemas/news.py](dait-schemas-news.py.md) (6 shared connections)
- [datetime](datetime.md) (4 shared connections)
- [collections_abc](collections_abc.md) (1 shared connections)
- [typing](typing.md) (1 shared connections)
- [ai_processor.py](ai_processor.py.md) (1 shared connections)
- [backend/src/dait/services/login_throttle.py](backend-src-dait-services-login_throttle.py.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/services/cache_retry_service.py`

## Audit Trail

- EXTRACTED: 78 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
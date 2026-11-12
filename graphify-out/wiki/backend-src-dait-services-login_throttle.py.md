# backend/src/dait/services/login_throttle.py

> 31 nodes

## Key Concepts

- **backend/src/dait/services/login_throttle.py** (16 connections) — `src/backend/src/dait/services/login_throttle.py`
- **AttemptThrottle** (9 connections) — `src/backend/src/dait/services/login_throttle.py`
- **datetime** (8 connections)
- **Throttle** (6 connections) — `src/backend/src/dait/services/login_throttle.py`
- **create_throttles()** (6 connections) — `src/backend/src/dait/services/login_throttle.py`
- **.register_failure()** (5 connections) — `src/backend/src/dait/services/login_throttle.py`
- **._drop_stale()** (4 connections) — `src/backend/src/dait/services/login_throttle.py`
- **LoginThrottles** (3 connections) — `src/backend/src/dait/services/login_throttle.py`
- **.is_locked()** (3 connections) — `src/backend/src/dait/services/login_throttle.py`
- **.__init__()** (3 connections) — `src/backend/src/dait/services/login_throttle.py`
- **.is_locked()** (3 connections) — `src/backend/src/dait/services/login_throttle.py`
- **_Entry** (2 connections) — `src/backend/src/dait/services/login_throttle.py`
- **.clear()** (2 connections) — `src/backend/src/dait/services/login_throttle.py`
- **.__init__()** (2 connections) — `src/backend/src/dait/services/login_throttle.py`
- **.register_failure()** (2 connections) — `src/backend/src/dait/services/login_throttle.py`
- **Settings** (2 connections)
- **redis_exceptions** (2 connections)
- **.clear()** (1 connections) — `src/backend/src/dait/services/login_throttle.py`
- **Protocol** (1 connections)
- **로그인 실패 누적 잠금. Redis가 있으면 분산 구현, 없거나 장애면 메모리 구현을 쓴다.** (1 connections) — `src/backend/src/dait/services/login_throttle.py`
- **오래된 기록을 버려 메모리를 줄인다(호출한 쪽이 락을 잡고 있어야 함). 입력: now (현재 UTC 시각) 출력: 없음 기능: 마지막…** (1 connections) — `src/backend/src/dait/services/login_throttle.py`
- **실패 횟수에 따라 잠그는 장치의 약속. Redis 구현이 같은 메서드를 가진다.** (1 connections) — `src/backend/src/dait/services/login_throttle.py`
- **로그인에 쓰는 두 잠금 장치: 계정 단위와 IP 단위.** (1 connections) — `src/backend/src/dait/services/login_throttle.py`
- **잠금 장치를 만든다. REDIS_URL이 있으면 분산 구현, 없으면 메모리 구현. 입력: settings (앱 설정, None이면 메모리…** (1 connections) — `src/backend/src/dait/services/login_throttle.py`
- **해당 키가 지금 잠겨 있는지 알려 준다.** (1 connections) — `src/backend/src/dait/services/login_throttle.py`
- *... and 6 more nodes in this community*

## Relationships

- [RedisThrottle](RedisThrottle.md) (3 shared connections)
- [datetime](datetime.md) (3 shared connections)
- [.register_failure](register_failure.md) (2 shared connections)
- [회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/login_throttle.py](회원가입_탈퇴_로그인_아웃_DB-main연결작업_담당자_홍록기-src-dait-services-login_throttle.py.md) (1 shared connections)
- [typing](typing.md) (1 shared connections)
- [redis_repository.py](redis_repository.py.md) (1 shared connections)
- [cache_retry_service.py](cache_retry_service.py.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/services/login_throttle.py`

## Audit Trail

- EXTRACTED: 52 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
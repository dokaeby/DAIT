# 회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/login_throttle.py

> 28 nodes

## Key Concepts

- **회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/login_throttle.py** (10 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/login_throttle.py`
- **AttemptThrottle** (8 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/login_throttle.py`
- **Throttle** (6 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/login_throttle.py`
- **datetime** (6 connections)
- **.register_failure()** (5 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/login_throttle.py`
- **._drop_stale()** (4 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/login_throttle.py`
- **create_throttles()** (4 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/login_throttle.py`
- **dataclasses** (4 connections)
- **LoginThrottles** (3 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/login_throttle.py`
- **.is_locked()** (3 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/login_throttle.py`
- **.is_locked()** (3 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/login_throttle.py`
- **_Entry** (2 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/login_throttle.py`
- **.clear()** (2 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/login_throttle.py`
- **.__init__()** (2 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/login_throttle.py`
- **.register_failure()** (2 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/login_throttle.py`
- **.clear()** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/login_throttle.py`
- **Protocol** (1 connections)
- **로그인 실패 누적 잠금. 지금은 메모리 구현이며 Redis 구현으로 같은 Protocol을 대체한다.** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/login_throttle.py`
- **로그인에 쓰는 두 잠금 장치: 계정 단위와 IP 단위.** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/login_throttle.py`
- **기본 잠금 장치(메모리)를 만든다. 입력: 없음 출력: LoginThrottles (계정 5회, IP 20회 실패부터 잠금) 기능: IP는…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/login_throttle.py`
- **실패 횟수에 따라 잠그는 장치의 약속. Redis 구현이 같은 메서드를 가진다.** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/login_throttle.py`
- **해당 키가 지금 잠겨 있는지 알려 준다.** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/login_throttle.py`
- **키(계정 또는 IP)별 실패를 세어 점진적으로 잠그는 메모리 구현.** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/login_throttle.py`
- **잠금 기준을 정해 만든다. 입력: threshold (이 횟수 이상 실패하면 잠금이 시작됨) 출력: 없음 기능: 잠금 시간은 60초에서 시작해…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/login_throttle.py`
- **해당 키가 지금 잠겨 있는지 알려 준다. 입력: key (계정 이메일 또는 IP), now (현재 UTC 시각) 출력: bool (잠겨 있으면…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/login_throttle.py`
- *... and 3 more nodes in this community*

## Relationships

- [datetime](datetime.md) (1 shared connections)
- [typing](typing.md) (1 shared connections)
- [collections_abc](collections_abc.md) (1 shared connections)
- [backend/src/dait/services/login_throttle.py](backend-src-dait-services-login_throttle.py.md) (1 shared connections)
- [schedule_run_service.py](schedule_run_service.py.md) (1 shared connections)

## Source Files

- `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/login_throttle.py`

## Audit Trail

- EXTRACTED: 41 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
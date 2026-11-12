# scheduler_routes.py

> 26 nodes

## Key Concepts

- **scheduler_routes.py** (27 connections) — `src/backend/src/dait/api/v1/scheduler_routes.py`
- **ScheduleSearcher** (9 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **SendOutcome** (9 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **KakaoMemoSender** (8 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **NotConfiguredSender** (5 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **get_searcher()** (4 connections) — `src/backend/src/dait/api/v1/scheduler_routes.py`
- **get_sender()** (4 connections) — `src/backend/src/dait/api/v1/scheduler_routes.py`
- **.send()** (3 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **.send()** (2 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **.__init__()** (2 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- **.send()** (2 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- **Protocol** (2 connections)
- **예약 검색 API. - POST /v1/internal/scheduler/tick : 외부 cron이 부르는 내부 트리거(Bearer…** (1 connections) — `src/backend/src/dait/api/v1/scheduler_routes.py`
- **예약 검색기. 지훈님 검색 워커가 준비되면 이 의존성만 바꿔 끼운다.** (1 connections) — `src/backend/src/dait/api/v1/scheduler_routes.py`
- **카카오 '나에게 보내기' 전송기. 카카오 앱 등록 전에는 '설정 전'으로 기록만 한다.** (1 connections) — `src/backend/src/dait/api/v1/scheduler_routes.py`
- **카카오 연동 전 기본값: 보내지 않고 '설정 전'으로 기록한다.** (1 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **예약 조건으로 기사를 찾는다. 지훈님 검색 워커가 이 형태로 연결된다.** (1 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **전송 결과와 실패 이유(로그·이력용, 비밀값 없음).** (1 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **카카오톡 '나에게 보내기'. 실제 구현은 카카오 앱 등록 후 연결한다.** (1 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **사용자 본인 카톡으로 text를 보낸다.** (1 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **ambiguous_python_import_1993c866cecc** (1 connections)
- **ambiguous_python_import_5e254edc953c** (1 connections)
- **ambiguous_python_import_753055f469bc** (1 connections)
- **ambiguous_python_import_969abe494f8a** (1 connections)
- **ambiguous_python_import_d32a311e8150** (1 connections)
- *... and 1 more nodes in this community*

## Relationships

- [schedule_run_repository.py](schedule_run_repository.py.md) (5 shared connections)
- [schedule_run_service.py](schedule_run_service.py.md) (5 shared connections)
- [test_schedule_runs.py](test_schedule_runs.py.md) (4 shared connections)
- [schedule_run.py](schedule_run.py.md) (4 shared connections)
- [DbNewsSearcher](DbNewsSearcher.md) (3 shared connections)
- [scheduler_tick](scheduler_tick.md) (3 shared connections)
- [schedule_service.py](schedule_service.py.md) (2 shared connections)
- [typing](typing.md) (2 shared connections)
- [NewsCategory](NewsCategory.md) (1 shared connections)
- [datetime](datetime.md) (1 shared connections)
- [src/backend/src/dait/main.py](src-backend-src-dait-main.py.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/api/v1/scheduler_routes.py`
- `src/backend/src/dait/services/schedule_run_service.py`
- `tests/backend/tests/unit/test_schedule_runs.py`

## Audit Trail

- EXTRACTED: 56 (92%)
- INFERRED: 5 (8%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
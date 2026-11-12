# scheduler_tick

> 14 nodes

## Key Concepts

- **scheduler_tick()** (13 connections) — `src/backend/src/dait/api/v1/scheduler_routes.py`
- **list_my_schedule_runs()** (7 connections) — `src/backend/src/dait/api/v1/scheduler_routes.py`
- **mark_my_schedule_runs_seen()** (6 connections) — `src/backend/src/dait/api/v1/scheduler_routes.py`
- **SettingsDep** (3 connections)
- **CurrentUser** (2 connections)
- **post** (2 connections)
- **BackgroundTasks** (1 connections)
- **Header** (1 connections)
- **SearcherDep** (1 connections)
- **SenderDep** (1 connections)
- **get** (1 connections)
- **Response** (1 connections)
- **실행할 예약 회차를 만들고, 검색·전송은 응답 뒤 백그라운드로 넘긴다. 입력: Authorization: Bearer…** (1 connections) — `src/backend/src/dait/api/v1/scheduler_routes.py`
- **로그인하면 보여줄 예약 검색 결과(검색·카카오 상태 포함)를 최신순으로 돌려준다.** (1 connections) — `src/backend/src/dait/api/v1/scheduler_routes.py`

## Relationships

- [schedule_run.py](schedule_run.py.md) (4 shared connections)
- [scheduler_routes.py](scheduler_routes.py.md) (3 shared connections)
- [schedule_run_service.py](schedule_run_service.py.md) (3 shared connections)
- [schedule_service.py](schedule_service.py.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/api/v1/scheduler_routes.py`

## Audit Trail

- EXTRACTED: 23 (88%)
- INFERRED: 3 (12%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
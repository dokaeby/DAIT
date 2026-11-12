# schedule_run.py

> 38 nodes

## Key Concepts

- **schedule_run.py** (13 connections) — `src/backend/src/dait/schemas/schedule_run.py`
- **list_runs()** (10 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **ScheduleRunListResponse** (9 connections) — `src/backend/src/dait/schemas/schedule_run.py`
- **TickResponse** (8 connections) — `src/backend/src/dait/schemas/schedule_run.py`
- **_to_response()** (8 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **7.5 POST `/v1/internal/scheduler/tick`** (8 connections) — `docs/DAIT_v1.0.3/06_API_설계서_v1.0.3.md`
- **NotifyStatus** (7 connections) — `src/backend/src/dait/schemas/schedule_run.py`
- **SearchStatus** (7 connections) — `src/backend/src/dait/schemas/schedule_run.py`
- **7. 운영/상태 API** (6 connections) — `docs/DAIT_v1.0.3/06_API_설계서_v1.0.3.md`
- **ScheduleRunResponse** (5 connections) — `src/backend/src/dait/schemas/schedule_run.py`
- **TickRequest** (5 connections) — `src/backend/src/dait/schemas/schedule_run.py`
- **BaseModel** (5 connections)
- **ScheduleRunItem** (4 connections) — `src/backend/src/dait/schemas/schedule_run.py`
- **Response 200 (`ScheduleRunListResponse`)** (4 connections) — `docs/DAIT_v1.0.3/06_API_설계서_v1.0.3.md`
- **7.3 GET `/v1/me/schedule-runs`** (3 connections) — `docs/DAIT_v1.0.3/06_API_설계서_v1.0.3.md`
- **7.4 POST `/v1/me/schedule-runs/seen`** (3 connections) — `docs/DAIT_v1.0.3/06_API_설계서_v1.0.3.md`
- **StrEnum** (2 connections)
- **UserRecord** (2 connections)
- **7.1 GET `/healthz`** (1 connections) — `docs/DAIT_v1.0.3/06_API_설계서_v1.0.3.md`
- **7.2 GET `/readyz`** (1 connections) — `docs/DAIT_v1.0.3/06_API_설계서_v1.0.3.md`
- **cron-job.org 등록 예시** (1 connections) — `docs/DAIT_v1.0.3/06_API_설계서_v1.0.3.md`
- **Request Body** (1 connections) — `docs/DAIT_v1.0.3/06_API_설계서_v1.0.3.md`
- **Response 200** (1 connections) — `docs/DAIT_v1.0.3/06_API_설계서_v1.0.3.md`
- **Response 204** (1 connections) — `docs/DAIT_v1.0.3/06_API_설계서_v1.0.3.md`
- **목적** (1 connections) — `docs/DAIT_v1.0.3/06_API_설계서_v1.0.3.md`
- *... and 13 more nodes in this community*

## Relationships

- [schedule_run_service.py](schedule_run_service.py.md) (12 shared connections)
- [schedule_run_repository.py](schedule_run_repository.py.md) (7 shared connections)
- [scheduler_routes.py](scheduler_routes.py.md) (4 shared connections)
- [scheduler_tick](scheduler_tick.md) (4 shared connections)
- [test_schedule_runs.py](test_schedule_runs.py.md) (2 shared connections)
- [datetime](datetime.md) (1 shared connections)
- [enum](enum.md) (1 shared connections)
- [ai_processor.py](ai_processor.py.md) (1 shared connections)
- [06_API_설계서_v1.0.3.md](06_API_설계서_v1.0.3.md.md) (1 shared connections)

## Source Files

- `docs/DAIT_v1.0.3/06_API_설계서_v1.0.3.md`
- `src/backend/src/dait/schemas/schedule_run.py`
- `src/backend/src/dait/services/schedule_run_service.py`

## Audit Trail

- EXTRACTED: 69 (85%)
- INFERRED: 12 (15%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
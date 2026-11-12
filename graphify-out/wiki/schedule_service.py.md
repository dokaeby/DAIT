# schedule_service.py

> 49 nodes

## Key Concepts

- **schedule_service.py** (33 connections) — `src/backend/src/dait/services/schedule_service.py`
- **update_schedule()** (19 connections) — `src/backend/src/dait/services/schedule_service.py`
- **create_schedule()** (18 connections) — `src/backend/src/dait/services/schedule_service.py`
- **insert_audit()** (12 connections) — `src/backend/src/dait/repositories/audit_repository.py`
- **ScheduleResponse** (9 connections) — `src/backend/src/dait/schemas/settings.py`
- **delete_schedule()** (9 connections) — `src/backend/src/dait/services/schedule_service.py`
- **ScheduleCreateRequest** (8 connections) — `src/backend/src/dait/schemas/settings.py`
- **create_my_schedule()** (8 connections) — `src/backend/src/dait/api/v1/settings_routes.py`
- **list_schedules()** (8 connections) — `src/backend/src/dait/services/schedule_service.py`
- **audit_repository.py** (8 connections) — `src/backend/src/dait/repositories/audit_repository.py`
- **_to_response()** (7 connections) — `src/backend/src/dait/services/schedule_service.py`
- **compute_next_run()** (6 connections) — `src/backend/src/dait/services/schedule_service.py`
- **_next_run_or_none()** (6 connections) — `src/backend/src/dait/services/schedule_service.py`
- **_normalized_criteria()** (6 connections) — `src/backend/src/dait/services/schedule_service.py`
- **_validate_criteria_sources()** (6 connections) — `src/backend/src/dait/services/schedule_service.py`
- **datetime** (6 connections)
- **_criteria_json()** (5 connections) — `src/backend/src/dait/services/schedule_service.py`
- **_parse_criteria()** (5 connections) — `src/backend/src/dait/services/schedule_service.py`
- **_validate_timezone()** (4 connections) — `src/backend/src/dait/services/schedule_service.py`
- **Settings** (4 connections)
- **UserRecord** (4 connections)
- **._check_time()** (3 connections) — `src/backend/src/dait/schemas/settings.py`
- **datetime** (2 connections)
- **zoneinfo** (2 connections)
- **post** (1 connections)
- *... and 24 more nodes in this community*

## Relationships

- [NewsCategory](NewsCategory.md) (20 shared connections)
- [src/backend/src/dait/api/v1/settings_routes.py](src-backend-src-dait-api-v1-settings_routes.py.md) (10 shared connections)
- [schedule_repository.py](schedule_repository.py.md) (8 shared connections)
- [schedule_run_service.py](schedule_run_service.py.md) (6 shared connections)
- [datetime](datetime.md) (3 shared connections)
- [scheduler_routes.py](scheduler_routes.py.md) (2 shared connections)
- [scheduler_tick](scheduler_tick.md) (1 shared connections)
- [create_app](create_app.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/api/v1/settings_routes.py`
- `src/backend/src/dait/repositories/audit_repository.py`
- `src/backend/src/dait/schemas/settings.py`
- `src/backend/src/dait/services/schedule_service.py`

## Audit Trail

- EXTRACTED: 127 (93%)
- INFERRED: 10 (7%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
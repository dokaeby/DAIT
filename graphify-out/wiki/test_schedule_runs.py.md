# test_schedule_runs.py

> 37 nodes

## Key Concepts

- **test_schedule_runs.py** (37 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- **FakeSender** (15 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- **_client()** (15 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- **test_kakao_failure_retries_only_send_and_unknown_is_not_resent()** (13 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- **Settings** (13 connections)
- **_tick()** (12 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- **_schedule()** (11 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- **test_search_failure_is_recorded_and_retried_without_blocking_others()** (11 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- **_signup()** (10 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- **_seed_news()** (9 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- **test_due_schedule_runs_once_and_result_is_stored()** (9 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- **test_no_results_skips_kakao()** (9 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- **test_runs_are_private_to_owner()** (9 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- **_runs()** (8 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- **test_concurrent_ticks_create_one_run()** (8 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- **test_disabled_and_not_yet_due_schedules_are_not_run()** (8 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- **test_missed_runs_are_executed_after_server_restart()** (8 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- **HttpClient** (5 connections)
- **test_tick_rejects_missing_or_wrong_secret()** (4 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- **test_tick_with_nothing_due_returns_ok()** (4 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- **tick_settings()** (4 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- **test_tick_is_disabled_when_secret_not_configured()** (3 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- **datetime** (3 connections)
- **tick()** (2 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- **test_message_fits_kakao_text_limit()** (2 connections) — `tests/backend/tests/unit/test_schedule_runs.py`
- *... and 12 more nodes in this community*

## Relationships

- [DbNewsSearcher](DbNewsSearcher.md) (5 shared connections)
- [scheduler_routes.py](scheduler_routes.py.md) (4 shared connections)
- [datetime](datetime.md) (3 shared connections)
- [schedule_run_service.py](schedule_run_service.py.md) (2 shared connections)
- [schedule_run.py](schedule_run.py.md) (2 shared connections)
- [schedule_run_repository.py](schedule_run_repository.py.md) (1 shared connections)
- [pytest](pytest.md) (1 shared connections)
- [collections_abc](collections_abc.md) (1 shared connections)
- [ai_processor.py](ai_processor.py.md) (1 shared connections)

## Source Files

- `tests/backend/tests/unit/test_schedule_runs.py`

## Audit Trail

- EXTRACTED: 121 (92%)
- INFERRED: 11 (8%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
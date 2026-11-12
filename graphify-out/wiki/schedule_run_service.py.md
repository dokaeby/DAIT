# schedule_run_service.py

> 28 nodes

## Key Concepts

- **schedule_run_service.py** (51 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **ScheduleRow** (16 connections) — `src/backend/src/dait/repositories/schedule_repository.py`
- **_plan_one()** (10 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **plan_due_runs()** (9 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **datetime** (9 connections)
- **Settings** (9 connections)
- **_insert_run_once()** (7 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **mark_runs_seen()** (7 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **_utc()** (7 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **SendResult** (5 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **notify_backoff()** (5 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **tick_secret_matches()** (4 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **NamedTuple** (1 connections)
- **StrEnum** (1 connections)
- **timedelta** (1 connections)
- **schedules 한 행. criteria_json은 TEXT 원문이다.** (1 connections) — `src/backend/src/dait/repositories/schedule_repository.py`
- **예약 검색 유스케이스. 흐름: tick 수신 → 실행할 회차 만들기 → 검색 → 결과 저장 → 카카오 전송 → 이력 기록. 외부 의존(검색…** (1 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **tick 요청의 Authorization: Bearer 값이 약속된 비밀값과 같은지 확인한다. 입력: settings…** (1 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **시간대가 없는 값은 UTC로 보고, 모든 비교를 UTC로 맞춘다.** (1 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **실행 시각이 된 예약마다 회차 기록을 만들고 다음 실행 시각을 옮긴다. 입력: settings, now (tick 기준 시각) 출력:…** (1 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **예약 하나의 놓친 회차들을 만들고 next_run_at을 미래로 옮긴다. 만든 회차 수를 돌려준다.** (1 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **회차를 넣되, 이미 있으면(같은 회차 중복) 조용히 건너뛴다.** (1 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **attempt번째 실패 뒤 다음 재시도까지 기다릴 시간(설정값, 기본 1분·5분·15분).** (1 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **카카오 전송 결과. UNKNOWN은 '갔는지 모름'이라 자동으로 다시 보내지 않는다.** (1 connections) — `src/backend/src/dait/services/schedule_run_service.py`
- **ambiguous_python_import_089f3e24d028** (1 connections)
- *... and 3 more nodes in this community*

## Relationships

- [schedule_run_repository.py](schedule_run_repository.py.md) (23 shared connections)
- [schedule_run.py](schedule_run.py.md) (12 shared connections)
- [schedule_repository.py](schedule_repository.py.md) (6 shared connections)
- [schedule_service.py](schedule_service.py.md) (6 shared connections)
- [scheduler_routes.py](scheduler_routes.py.md) (5 shared connections)
- [DbNewsSearcher](DbNewsSearcher.md) (3 shared connections)
- [scheduler_tick](scheduler_tick.md) (3 shared connections)
- [test_schedule_runs.py](test_schedule_runs.py.md) (2 shared connections)
- [datetime](datetime.md) (2 shared connections)
- [NewsCategory](NewsCategory.md) (2 shared connections)
- [src/backend/src/dait/api/v1/news_routes.py](src-backend-src-dait-api-v1-news_routes.py.md) (2 shared connections)
- [회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/schemas/auth.py](회원가입_탈퇴_로그인_아웃_DB-main연결작업_담당자_홍록기-src-dait-schemas-auth.py.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/repositories/schedule_repository.py`
- `src/backend/src/dait/services/schedule_run_service.py`

## Audit Trail

- EXTRACTED: 110 (97%)
- INFERRED: 3 (3%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
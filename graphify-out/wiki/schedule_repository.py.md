# schedule_repository.py

> 16 nodes

## Key Concepts

- **schedule_repository.py** (13 connections) — `src/backend/src/dait/repositories/schedule_repository.py`
- **get_by_id_and_user()** (7 connections) — `src/backend/src/dait/repositories/schedule_repository.py`
- **list_by_user()** (7 connections) — `src/backend/src/dait/repositories/schedule_repository.py`
- **insert_schedule()** (5 connections) — `src/backend/src/dait/repositories/schedule_repository.py`
- **_to_row()** (5 connections) — `src/backend/src/dait/repositories/schedule_repository.py`
- **update_schedule()** (5 connections) — `src/backend/src/dait/repositories/schedule_repository.py`
- **DbConnection** (5 connections)
- **delete_schedule()** (4 connections) — `src/backend/src/dait/repositories/schedule_repository.py`
- **schedules 테이블 접근. 예약은 항상 user_id와 함께 조회해 소유권을 지킨다.** (1 connections) — `src/backend/src/dait/repositories/schedule_repository.py`
- **본인의 예약을 새 값으로 갱신한다. 입력: conn (트랜잭션 연결), row (갱신할 전체 값) 출력: bool (갱신된 행이 있었으면…** (1 connections) — `src/backend/src/dait/repositories/schedule_repository.py`
- **본인의 예약을 삭제한다. 입력: conn (트랜잭션 연결), user_id (본인 id), schedule_id (예약 ID) 출력: bool…** (1 connections) — `src/backend/src/dait/repositories/schedule_repository.py`
- **DB 행을 ScheduleRow로 바꾼다. 입력: row (컬럼 순서대로 읽은 행) 출력: ScheduleRow 기능: next_run_at은…** (1 connections) — `src/backend/src/dait/repositories/schedule_repository.py`
- **사용자의 예약 목록을 읽는다. 입력: conn (연결), user_id (본인 id) 출력: ScheduleRow 목록 (생성 순) 기능:…** (1 connections) — `src/backend/src/dait/repositories/schedule_repository.py`
- **본인의 예약 한 건을 읽는다. 입력: conn (연결), user_id (본인 id), schedule_id (경로의 예약 ID) 출력:…** (1 connections) — `src/backend/src/dait/repositories/schedule_repository.py`
- **예약 한 건을 저장한다. 입력: conn (트랜잭션 연결), row (저장할 값) 출력: 없음 기능: enabled는 bool을 정수로 바꿔…** (1 connections) — `src/backend/src/dait/repositories/schedule_repository.py`
- **ambiguous_python_import_b5ed430401a1** (1 connections)

## Relationships

- [schedule_service.py](schedule_service.py.md) (8 shared connections)
- [schedule_run_service.py](schedule_run_service.py.md) (6 shared connections)
- [datetime](datetime.md) (1 shared connections)
- [typing](typing.md) (1 shared connections)
- [schedule_run_repository.py](schedule_run_repository.py.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/repositories/schedule_repository.py`

## Audit Trail

- EXTRACTED: 38 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
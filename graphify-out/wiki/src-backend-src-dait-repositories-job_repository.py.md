# src/backend/src/dait/repositories/job_repository.py

> 18 nodes

## Key Concepts

- **src/backend/src/dait/repositories/job_repository.py** (12 connections) — `src/backend/src/dait/repositories/job_repository.py`
- **JobRow** (5 connections) — `src/backend/src/dait/repositories/job_repository.py`
- **create_job()** (5 connections) — `src/backend/src/dait/repositories/job_repository.py`
- **get_by_dedupe_key()** (5 connections) — `src/backend/src/dait/repositories/job_repository.py`
- **DbConnection** (5 connections)
- **record_attempt()** (4 connections) — `src/backend/src/dait/repositories/job_repository.py`
- **update_status()** (4 connections) — `src/backend/src/dait/repositories/job_repository.py`
- **datetime** (4 connections)
- **count_attempts()** (3 connections) — `src/backend/src/dait/repositories/job_repository.py`
- **_to_row()** (3 connections) — `src/backend/src/dait/repositories/job_repository.py`
- **NamedTuple** (1 connections)
- **jobs·job_attempts 테이블 접근. dedupe_key unique와 단계별 시도 기록을 담당한다.** (1 connections) — `src/backend/src/dait/repositories/job_repository.py`
- **작업 상태를 갱신한다. 입력: conn, job_id, status (허용 Enum 문자열), started_at·finished_at 출력:…** (1 connections) — `src/backend/src/dait/repositories/job_repository.py`
- **특정 단계의 누적 시도 횟수를 센다. 입력: conn, job_id, step (예: COLLECT) 출력: int 기능: 최대 재시도 횟수…** (1 connections) — `src/backend/src/dait/repositories/job_repository.py`
- **단계별 시도 결과를 기록한다. 입력: conn, job_id, step, attempt_no, error_code (성공이면 None),…** (1 connections) — `src/backend/src/dait/repositories/job_repository.py`
- **dedupe_key로 기존 작업을 찾는다. 입력: conn (연결), dedupe_key (예: collect:src1:20261110)…** (1 connections) — `src/backend/src/dait/repositories/job_repository.py`
- **작업을 등록한다. dedupe_key 충돌이면 None을 돌려준다. 입력: conn (트랜잭션 연결), schedule_id (예약 발이면…** (1 connections) — `src/backend/src/dait/repositories/job_repository.py`
- **ambiguous_python_import_4d8e64de6058** (1 connections)

## Relationships

- [datetime](datetime.md) (1 shared connections)
- [typing](typing.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/repositories/job_repository.py`

## Audit Trail

- EXTRACTED: 30 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
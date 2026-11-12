# backend/tests/unit/test_db.py

> 23 nodes

## Key Concepts

- **backend/tests/unit/test_db.py** (17 connections) — `tests/backend/tests/unit/test_db.py`
- **url()** (4 connections) — `tests/backend/tests/unit/test_db.py`
- **_insert_orphan_child()** (3 connections) — `tests/backend/tests/unit/test_db.py`
- **_insert_then_fail()** (3 connections) — `tests/backend/tests/unit/test_db.py`
- **test_db_dialect_selects_backend()** (3 connections) — `tests/backend/tests/unit/test_db.py`
- **test_ping_fails_on_unopenable_path()** (3 connections) — `tests/backend/tests/unit/test_db.py`
- **scenario()** (2 connections) — `tests/backend/tests/integration/test_pipeline_flow.py`
- **test_foreign_key_violation_is_rejected()** (2 connections) — `tests/backend/tests/unit/test_db.py`
- **test_non_sqlite_url_raises_value_error()** (2 connections) — `tests/backend/tests/unit/test_db.py`
- **test_rollback_on_error()** (2 connections) — `tests/backend/tests/unit/test_db.py`
- **test_sqlite_path_is_extracted()** (2 connections) — `tests/backend/tests/unit/test_db.py`
- **Path** (2 connections)
- **test_commit_on_success()** (1 connections) — `tests/backend/tests/unit/test_db.py`
- **test_foreign_keys_on_for_each_connection()** (1 connections) — `tests/backend/tests/unit/test_db.py`
- **fixture** (1 connections)
- **repositories/db 연결·트랜잭션 테스트 (외래키, 롤백, 경로 파싱).** (1 connections) — `tests/backend/tests/unit/test_db.py`
- **DATABASE_URL에서 파일 경로를 꺼낸다.** (1 connections) — `tests/backend/tests/unit/test_db.py`
- **sqlite가 아니면 ValueError다.** (1 connections) — `tests/backend/tests/unit/test_db.py`
- **부모 없는 자식 행을 넣는다(외래키 위반).** (1 connections) — `tests/backend/tests/unit/test_db.py`
- **행을 넣은 직후 예외를 낸다(롤백 확인용).** (1 connections) — `tests/backend/tests/unit/test_db.py`
- **열 수 없는 경로는 ping에서 sqlite 오류가 난다.** (1 connections) — `tests/backend/tests/unit/test_db.py`
- **URL 스킴으로 sqlite/postgres 백엔드를 고른다.** (1 connections) — `tests/backend/tests/unit/test_db.py`
- **ambiguous_python_import_01a91f28737d** (1 connections)

## Relationships

- [datetime](datetime.md) (2 shared connections)
- [test_pipeline_flow.py](test_pipeline_flow.py.md) (1 shared connections)
- [.summary_lines](summary_lines.md) (1 shared connections)
- [pytest](pytest.md) (1 shared connections)
- [translate_sql](translate_sql.md) (1 shared connections)

## Source Files

- `tests/backend/tests/integration/test_pipeline_flow.py`
- `tests/backend/tests/unit/test_db.py`

## Audit Trail

- EXTRACTED: 29 (94%)
- INFERRED: 2 (6%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
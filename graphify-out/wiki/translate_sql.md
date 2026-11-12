# translate_sql

> 6 nodes

## Key Concepts

- **translate_sql()** (7 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **test_postgres_placeholder_translation()** (3 connections) — `tests/backend/tests/unit/test_db.py`
- **9. 참고: DB 이중 백엔드 구현 현황** (3 connections) — `docs/DAIT_v1.0.2/15_PostgreSQL_SQLite_전환_가이드.md`
- **9. 참고: DB 이중 백엔드 구현 현황** (3 connections) — `docs/DAIT_v1.0.3/15_PostgreSQL_SQLite_전환_가이드.md`
- **`?` 플레이스홀더를 `%s`로, 리터럴 `%`를 `%%`로 변환한다. 입력: sql (저장소가 작성한 ? 형식 SQL) 출력: str…** (1 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **postgres 백엔드는 ?를 %s로, 리터럴 %를 %%로 바꾸고 문자열 안은 보존한다.** (1 connections) — `tests/backend/tests/unit/test_db.py`

## Relationships

- [PgConnection](PgConnection.md) (2 shared connections)
- [DAIT SQLite → PostgreSQL 전환 가이드](DAIT_SQLite_→_PostgreSQL_전환_가이드.md) (2 shared connections)
- [.summary_lines](summary_lines.md) (2 shared connections)
- [db_postgres.py](db_postgres.py.md) (1 shared connections)
- [backend/tests/unit/test_db.py](backend-tests-unit-test_db.py.md) (1 shared connections)

## Source Files

- `docs/DAIT_v1.0.2/15_PostgreSQL_SQLite_전환_가이드.md`
- `docs/DAIT_v1.0.3/15_PostgreSQL_SQLite_전환_가이드.md`
- `src/backend/src/dait/repositories/db_postgres.py`
- `tests/backend/tests/unit/test_db.py`

## Audit Trail

- EXTRACTED: 8 (62%)
- INFERRED: 5 (38%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
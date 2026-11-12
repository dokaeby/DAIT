# PgConnection

> 19 nodes

## Key Concepts

- **PgConnection** (10 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **PgCursor** (9 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **Any** (7 connections)
- **_normalize()** (5 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **.execute()** (4 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **.executemany()** (4 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **.__init__()** (3 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **.fetchall()** (3 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **.fetchone()** (3 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **.__init__()** (3 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **.__iter__()** (3 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **.close()** (1 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **.commit()** (1 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **.rollback()** (1 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **Cursor** (1 connections)
- **Connection** (1 connections)
- **psycopg 연결을 감싼 DB-API 유사 연결. SQL 번역과 행 정규화를 담당한다.** (1 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **psycopg가 돌려주는 값을 sqlite 경로와 같은 모양으로 바꾼다. 입력: value (커서가 반환한 단일 컬럼 값) 출력: 변환된 값…** (1 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **psycopg 커서를 감싸 fetch 결과의 시각 값을 ISO 문자열로 정규화한다.** (1 connections) — `src/backend/src/dait/repositories/db_postgres.py`

## Relationships

- [db_postgres.py](db_postgres.py.md) (5 shared connections)
- [translate_sql](translate_sql.md) (2 shared connections)
- [.rowcount](rowcount.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/repositories/db_postgres.py`

## Audit Trail

- EXTRACTED: 35 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
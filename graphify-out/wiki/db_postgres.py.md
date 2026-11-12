# db_postgres.py

> 22 nodes

## Key Concepts

- **db_postgres.py** (17 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **backend/src/dait/repositories/db.py** (11 connections) — `src/backend/src/dait/repositories/db.py`
- **connect()** (7 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **connect()** (6 connections) — `src/backend/src/dait/repositories/db.py`
- **transaction()** (6 connections) — `src/backend/src/dait/repositories/db.py`
- **ping()** (5 connections) — `src/backend/src/dait/repositories/db.py`
- **transaction()** (5 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **ping()** (4 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **_to_psycopg_url()** (3 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **DbConnection** (2 connections)
- **psycopg** (2 connections)
- **PostgreSQL(psycopg3) 백엔드. sqlite 백엔드와 같은 connect/transaction/ping API를 제공한다.…** (1 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **PostgreSQL 연결을 만든다. 입력: database_url (postgresql:// 등 URI) 출력: PgConnection…** (1 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **한 의미 단위의 쓰기를 묶는 트랜잭션 컨텍스트(sqlite 백엔드와 같은 계약). 입력: database_url 출력:…** (1 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **DB가 열리고 질의가 되는지 확인한다(/readyz에서 사용). 입력: database_url 출력: 없음 기능: SELECT 1을 실행한다.…** (1 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **DATABASE_URL을 psycopg 접속 문자열로 정규화한다. 입력: database_url (postgresql://,…** (1 connections) — `src/backend/src/dait/repositories/db_postgres.py`
- **DATABASE_URL 스킴에 따라 sqlite(로컬)/postgres(서버) 백엔드를 고른다. 저장소·서비스는 이 모듈의…** (1 connections) — `src/backend/src/dait/repositories/db.py`
- **DATABASE_URL에 맞는 백엔드 연결을 만든다. 입력: database_url 출력: DbConnection (호출한 쪽이 닫아야 함)…** (1 connections) — `src/backend/src/dait/repositories/db.py`
- **백엔드에 맞는 트랜잭션 컨텍스트를 연다. 입력: database_url 출력: Generator[DbConnection] (with 블록…** (1 connections) — `src/backend/src/dait/repositories/db.py`
- **선택된 백엔드로 DB 연결을 확인한다. 입력: database_url 출력: 없음 기능: 실패하면 각 드라이버의 오류가…** (1 connections) — `src/backend/src/dait/repositories/db.py`
- **psycopg_abc** (1 connections)
- **psycopg_rows** (1 connections)

## Relationships

- [PgConnection](PgConnection.md) (5 shared connections)
- [.summary_lines](summary_lines.md) (4 shared connections)
- [db_sqlite.py](db_sqlite.py.md) (4 shared connections)
- [datetime](datetime.md) (4 shared connections)
- [collections_abc](collections_abc.md) (2 shared connections)
- [typing](typing.md) (1 shared connections)
- [translate_sql](translate_sql.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/repositories/db.py`
- `src/backend/src/dait/repositories/db_postgres.py`

## Audit Trail

- EXTRACTED: 50 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
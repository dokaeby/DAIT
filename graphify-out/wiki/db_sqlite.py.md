# db_sqlite.py

> 11 nodes

## Key Concepts

- **db_sqlite.py** (9 connections) — `src/backend/src/dait/repositories/db_sqlite.py`
- **connect()** (7 connections) — `src/backend/src/dait/repositories/db_sqlite.py`
- **transaction()** (5 connections) — `src/backend/src/dait/repositories/db_sqlite.py`
- **ping()** (4 connections) — `src/backend/src/dait/repositories/db_sqlite.py`
- **sqlite_path()** (3 connections) — `src/backend/src/dait/repositories/db_sqlite.py`
- **Connection** (2 connections)
- **sqlite 연결을 만들고 트랜잭션 경계를 제공한다. 테이블별 SQL은 각 repository가 맡는다.** (1 connections) — `src/backend/src/dait/repositories/db_sqlite.py`
- **DATABASE_URL에서 파일 경로를 꺼낸다. 입력: database_url (sqlite:///경로 형식 문자열) 출력: str…** (1 connections) — `src/backend/src/dait/repositories/db_sqlite.py`
- **외래키 검사를 켠 sqlite 연결을 만든다. 입력: database_url (sqlite:///경로 형식 문자열) 출력:…** (1 connections) — `src/backend/src/dait/repositories/db_sqlite.py`
- **한 의미 단위의 쓰기를 묶는 트랜잭션 컨텍스트. 입력: database_url (sqlite:///경로 형식 문자열) 출력:…** (1 connections) — `src/backend/src/dait/repositories/db_sqlite.py`
- **DB가 열리고 질의가 되는지 확인한다. 입력: database_url (sqlite:///경로 형식 문자열) 출력: 없음 기능: SELECT…** (1 connections) — `src/backend/src/dait/repositories/db_sqlite.py`

## Relationships

- [db_postgres.py](db_postgres.py.md) (4 shared connections)
- [datetime](datetime.md) (2 shared connections)
- [collections_abc](collections_abc.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/repositories/db_sqlite.py`

## Audit Trail

- EXTRACTED: 21 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
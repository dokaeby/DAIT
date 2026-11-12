# backend/migrations/env.py

> 13 nodes

## Key Concepts

- **backend/migrations/env.py** (9 connections) — `src/backend/migrations/env.py`
- **_is_sqlite()** (5 connections) — `src/backend/migrations/env.py`
- **_sqlalchemy_url()** (5 connections) — `src/backend/migrations/env.py`
- **_database_url()** (4 connections) — `src/backend/migrations/env.py`
- **run_migrations_offline()** (4 connections) — `src/backend/migrations/env.py`
- **run_migrations_online()** (4 connections) — `src/backend/migrations/env.py`
- **Alembic 실행 환경. DB 주소를 Settings에서 읽고 SQLite batch 모드를 켠다.** (1 connections) — `src/backend/migrations/env.py`
- **마이그레이션을 실행할 DB 주소를 정한다. 입력: 없음(alembic 옵션 sqlalchemy.url 또는 환경변수 DATABASE_URL)…** (1 connections) — `src/backend/migrations/env.py`
- **DB에 연결하지 않고 SQL 문만 출력하는 방식으로 마이그레이션을 실행한다. 입력: 없음(Settings의 DATABASE_URL) 출력:…** (1 connections) — `src/backend/migrations/env.py`
- **SQLAlchemy용 접속 주소를 만든다. 입력: 없음(Settings의 DATABASE_URL) 출력: str (create_engine이…** (1 connections) — `src/backend/migrations/env.py`
- **현재 DATABASE_URL이 sqlite인지 판별한다(render_as_batch 판단용).** (1 connections) — `src/backend/migrations/env.py`
- **DB에 연결해 마이그레이션을 실행한다. 입력: 없음(Settings의 DATABASE_URL) 출력: 없음(DB 스키마가 바뀜) 기능: 한…** (1 connections) — `src/backend/migrations/env.py`
- **ambiguous_python_import_84df32c846cb** (1 connections)

## Relationships

- [alembic](alembic.md) (1 shared connections)
- [app/repositories/news_repository.py](app-repositories-news_repository.py.md) (1 shared connections)

## Source Files

- `src/backend/migrations/env.py`

## Audit Trail

- EXTRACTED: 20 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
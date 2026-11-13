# alembic

> 25 nodes

## Key Concepts

- **alembic** (18 connections)
- **회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/migrations/versions/20261108_0002_user_interests.py** (4 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/migrations/versions/20261108_0002_user_interests.py`
- **20261110_0003_news_settings.py** (4 connections) — `src/backend/migrations/versions/20261110_0003_news_settings.py`
- **20261111_0004_schedule_runs.py** (4 connections) — `src/backend/migrations/versions/20261111_0004_schedule_runs.py`
- **20261111_0004_user_nickname.py** (4 connections) — `src/backend/migrations/versions/20261111_0004_user_nickname.py`
- **20261111_0005_news_reads.py** (4 connections) — `src/backend/migrations/versions/20261111_0005_news_reads.py`
- **downgrade()** (2 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/migrations/versions/20261108_0002_user_interests.py`
- **upgrade()** (2 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/migrations/versions/20261108_0002_user_interests.py`
- **downgrade()** (2 connections) — `src/backend/migrations/versions/20261110_0003_news_settings.py`
- **upgrade()** (2 connections) — `src/backend/migrations/versions/20261110_0003_news_settings.py`
- **downgrade()** (2 connections) — `src/backend/migrations/versions/20261111_0004_schedule_runs.py`
- **upgrade()** (2 connections) — `src/backend/migrations/versions/20261111_0004_schedule_runs.py`
- **downgrade()** (2 connections) — `src/backend/migrations/versions/20261111_0004_user_nickname.py`
- **upgrade()** (2 connections) — `src/backend/migrations/versions/20261111_0004_user_nickname.py`
- **upgrade()** (2 connections) — `src/backend/migrations/versions/20261111_0005_news_reads.py`
- **downgrade()** (1 connections) — `src/backend/migrations/versions/20261111_0005_news_reads.py`
- **user_interests를 만든다(SQLite·PostgreSQL 공통 문법만 사용). 입력: 없음 출력: 없음 기능: (user_id,…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/migrations/versions/20261108_0002_user_interests.py`
- **user_interests만 지운다. 입력: 없음 출력: 없음 기능: 가입·로그인에 쓰는 users, refresh_tokens는 건드리지…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/migrations/versions/20261108_0002_user_interests.py`
- **설계서의 테이블을 만든다(SQLite·PostgreSQL 공통 문법만 사용). 입력: 없음 출력: 없음 기능: JSON 계열은 TEXT로…** (1 connections) — `src/backend/migrations/versions/20261110_0003_news_settings.py`
- **만든 테이블을 외래키 역순으로 지운다. 입력: 없음 출력: 없음 기능: 자식 테이블부터 지워 참조 순서를 지킨다.** (1 connections) — `src/backend/migrations/versions/20261110_0003_news_settings.py`
- **schedule_runs(회차별 실행 이력)와 schedule_run_items(검색 결과)를 만든다. 입력: 없음 출력: 없음 기능: 한…** (1 connections) — `src/backend/migrations/versions/20261111_0004_schedule_runs.py`
- **만든 테이블을 자식부터 지운다. 입력: 없음 출력: 없음 기능: 외래키 순서를 지킨다.** (1 connections) — `src/backend/migrations/versions/20261111_0004_schedule_runs.py`
- **기존 사용자는 NULL을 유지하므로 이메일 표시가 보존된다.** (1 connections) — `src/backend/migrations/versions/20261111_0004_user_nickname.py`
- **닉네임만 제거하고 기존 계정은 유지한다.** (1 connections) — `src/backend/migrations/versions/20261111_0004_user_nickname.py`
- **Create account-owned, idempotent read records.** (1 connections) — `src/backend/migrations/versions/20261111_0005_news_reads.py`

## Relationships

- [app/repositories/news_repository.py](app-repositories-news_repository.py.md) (5 shared connections)
- [회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/migrations/env.py](회원가입_탈퇴_로그인_아웃_DB-main연결작업_담당자_홍록기-migrations-env.py.md) (1 shared connections)
- [회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/migrations/versions/20261108_0001_users_refresh_tokens.py](회원가입_탈퇴_로그인_아웃_DB-main연결작업_담당자_홍록기-migrations-versions-20261108_0001_users_refresh_tokens.py.md) (1 shared connections)
- [회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/conftest.py](회원가입_탈퇴_로그인_아웃_DB-main연결작업_담당자_홍록기-tests-conftest.py.md) (1 shared connections)
- [회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_interests.py](회원가입_탈퇴_로그인_아웃_DB-main연결작업_담당자_홍록기-tests-unit-test_interests.py.md) (1 shared connections)
- [회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_user_repository.py](회원가입_탈퇴_로그인_아웃_DB-main연결작업_담당자_홍록기-tests-unit-test_user_repository.py.md) (1 shared connections)
- [backend/migrations/env.py](backend-migrations-env.py.md) (1 shared connections)
- [backend/migrations/versions/20261108_0001_users_refresh_tokens.py](backend-migrations-versions-20261108_0001_users_refresh_tokens.py.md) (1 shared connections)
- [backend/migrations/versions/20261108_0002_user_interests.py](backend-migrations-versions-20261108_0002_user_interests.py.md) (1 shared connections)
- [20261112_0006_interest_onboarding.py](20261112_0006_interest_onboarding.py.md) (1 shared connections)
- [backend/tests/conftest.py](backend-tests-conftest.py.md) (1 shared connections)
- [backend/tests/unit/test_interests.py](backend-tests-unit-test_interests.py.md) (1 shared connections)

## Source Files

- `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/migrations/versions/20261108_0002_user_interests.py`
- `src/backend/migrations/versions/20261110_0003_news_settings.py`
- `src/backend/migrations/versions/20261111_0004_schedule_runs.py`
- `src/backend/migrations/versions/20261111_0004_user_nickname.py`
- `src/backend/migrations/versions/20261111_0005_news_reads.py`

## Audit Trail

- EXTRACTED: 42 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
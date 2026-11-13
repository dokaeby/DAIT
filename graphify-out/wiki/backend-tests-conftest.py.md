# backend/tests/conftest.py

> 13 nodes

## Key Concepts

- **backend/tests/conftest.py** (10 connections) — `tests/backend/tests/conftest.py`
- **_isolated_environment()** (5 connections) — `tests/backend/tests/conftest.py`
- **db_url()** (4 connections) — `tests/backend/tests/conftest.py`
- **settings()** (3 connections) — `tests/backend/tests/conftest.py`
- **fixture** (3 connections)
- **Path** (2 connections)
- **MonkeyPatch** (1 connections)
- **모든 테스트 공통 준비: 실제 .env와 셸 환경변수가 테스트에 섞이지 않게 한다.** (1 connections) — `tests/backend/tests/conftest.py`
- **빈 임시 폴더에서 실행하고 앱 환경변수를 테스트용으로 고정한다. pydantic-settings가 현재 폴더의 .env를 읽으므로, 폴더를…** (1 connections) — `tests/backend/tests/conftest.py`
- **마이그레이션을 끝까지 적용한 임시 sqlite DB 주소.** (1 connections) — `tests/backend/tests/conftest.py`
- **위 DB를 가리키는 테스트용 설정(서명 키는 환경변수에서 읽는다).** (1 connections) — `tests/backend/tests/conftest.py`
- **ambiguous_python_import_2a86b400a595** (1 connections)
- **ambiguous_python_import_45a45f659e38** (1 connections)

## Relationships

- [datetime](datetime.md) (2 shared connections)
- [pytest](pytest.md) (1 shared connections)
- [alembic](alembic.md) (1 shared connections)

## Source Files

- `tests/backend/tests/conftest.py`

## Audit Trail

- EXTRACTED: 19 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
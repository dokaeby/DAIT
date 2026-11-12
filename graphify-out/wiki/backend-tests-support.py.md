# backend/tests/support.py

> 19 nodes

## Key Concepts

- **backend/tests/support.py** (14 connections) — `tests/backend/tests/support.py`
- **HttpClient** (5 connections) — `tests/backend/tests/support.py`
- **as_client()** (4 connections) — `tests/backend/tests/support.py`
- **jwt** (4 connections)
- **alembic_config()** (3 connections) — `tests/backend/tests/support.py`
- **forge_token()** (2 connections) — `tests/backend/tests/support.py`
- **.request()** (2 connections) — `tests/backend/tests/support.py`
- **read_claim_names()** (2 connections) — `tests/backend/tests/support.py`
- **FastAPI** (2 connections)
- **Config** (1 connections)
- **Protocol** (1 connections)
- **Response** (1 connections)
- **테스트 공용 도구: 타입 고정된 HTTP 클라이언트와 Alembic 설정.** (1 connections) — `tests/backend/tests/support.py`
- **검증 우회 시도용 토큰을 원하는 알고리즘으로 만든다. 입력: payload (토큰에 넣을 값), key (서명 키), algorithm (예:…** (1 connections) — `tests/backend/tests/support.py`
- **토큰에 들어 있는 값의 이름 목록을 돌려준다. 입력: token (HS256 JWT), key (서명 키) 출력: set[str]…** (1 connections) — `tests/backend/tests/support.py`
- **TestClient 중 테스트에서 쓰는 부분만 타입으로 고정한다. starlette TestClient는 httpx 내부 타입을 참조해…** (1 connections) — `tests/backend/tests/support.py`
- **앱을 감싼 테스트 클라이언트를 HttpClient 타입으로 돌려준다(서버 오류도 응답으로 받는다).** (1 connections) — `tests/backend/tests/support.py`
- **프로젝트 Alembic 설정에 테스트용 DB 주소를 끼워 돌려준다. 입력: database_url (sqlite:///경로 형식) 출력:…** (1 connections) — `tests/backend/tests/support.py`
- **httpx2** (1 connections)

## Relationships

- [회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/support.py](회원가입_탈퇴_로그인_아웃_DB-main연결작업_담당자_홍록기-tests-support.py.md) (3 shared connections)
- [collections_abc](collections_abc.md) (1 shared connections)
- [datetime](datetime.md) (1 shared connections)
- [typing](typing.md) (1 shared connections)
- [회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/security.py](회원가입_탈퇴_로그인_아웃_DB-main연결작업_담당자_홍록기-src-dait-core-security.py.md) (1 shared connections)
- [backend/src/dait/core/security.py](backend-src-dait-core-security.py.md) (1 shared connections)

## Source Files

- `tests/backend/tests/support.py`

## Audit Trail

- EXTRACTED: 28 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
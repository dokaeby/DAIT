# Settings

> 14 nodes

## Key Concepts

- **Settings** (8 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/config.py`
- **get_settings()** (3 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/config.py`
- **._check_cors_origins()** (3 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/config.py`
- **._check_database_url()** (3 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/config.py`
- **.content_security_policy()** (2 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/config.py`
- **.docs_enabled()** (2 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/config.py`
- **field_validator** (2 connections)
- **BaseSettings** (1 connections)
- **환경변수에서 읽는 앱 설정. 잘못된 값이면 생성 시점에 예외가 나 서버가 시작되지 않는다.** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/config.py`
- **DATABASE_URL이 sqlite:/// 형식인지 확인한다. 입력: value (환경변수 DATABASE_URL 문자열) 출력: 검증을…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/config.py`
- **CORS 허용 출처에 와일드카드나 http(s) 아닌 값이 없는지 확인한다. 입력: value (환경변수 CORS_ORIGINS의 JSON…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/config.py`
- **API 문서(/docs, /redoc, /openapi.json)를 열지 여부. 입력: 없음(self.app_env) 출력: bool…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/config.py`
- **응답에 붙일 Content-Security-Policy 값. 입력: 없음(self.app_env) 출력: str (CSP 헤더 값) 기능:…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/config.py`
- **프로세스 전체에서 쓰는 설정 객체를 한 번만 만들어 돌려준다. 입력: 없음(환경변수와 .env 파일) 출력: Settings (불변 설정)…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/config.py`

## Relationships

- [src/backend/src/dait/core/config.py](src-backend-src-dait-core-config.py.md) (2 shared connections)

## Source Files

- `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/config.py`

## Audit Trail

- EXTRACTED: 16 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
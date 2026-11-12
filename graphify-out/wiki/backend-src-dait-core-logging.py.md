# backend/src/dait/core/logging.py

> 20 nodes

## Key Concepts

- **backend/src/dait/core/logging.py** (14 connections) — `src/backend/src/dait/core/logging.py`
- **configure_logging()** (5 connections) — `src/backend/src/dait/core/logging.py`
- **JsonFormatter** (4 connections) — `src/backend/src/dait/core/logging.py`
- **MaskingFilter** (4 connections) — `src/backend/src/dait/core/logging.py`
- **.filter()** (4 connections) — `src/backend/src/dait/core/logging.py`
- **.format()** (3 connections) — `src/backend/src/dait/core/logging.py`
- **mask_sensitive()** (3 connections) — `src/backend/src/dait/core/logging.py`
- **audit()** (2 connections) — `src/backend/src/dait/core/logging.py`
- **LogRecord** (2 connections)
- **Settings** (1 connections)
- **로깅 설정과 민감정보 마스킹을 담당한다. 로그 모드 분기는 여기서만 한다.** (1 connections) — `src/backend/src/dait/core/logging.py`
- **보안 이벤트를 감사 로그 한 줄로 남긴다. 입력: event (예: signup, login), outcome (success 또는…** (1 connections) — `src/backend/src/dait/core/logging.py`
- **로그 문자열에서 토큰, 비밀번호류 값, 이메일을 가린다. 입력: text (로그 메시지 문자열) 출력: str (민감정보가 *** 로 바뀐…** (1 connections) — `src/backend/src/dait/core/logging.py`
- **모든 로그 레코드에 마스킹을 적용하고 request_id를 붙이는 필터.** (1 connections) — `src/backend/src/dait/core/logging.py`
- **로그 레코드의 메시지를 마스킹하고 request_id를 달아 통과시킨다. 입력: record (logging이 만든 로그 레코드) 출력:…** (1 connections) — `src/backend/src/dait/core/logging.py`
- **한 줄 JSON으로 로그를 만드는 포매터. 예외는 종류 이름만 남긴다.** (1 connections) — `src/backend/src/dait/core/logging.py`
- **로그 레코드를 JSON 문자열 한 줄로 바꾼다. 입력: record (MaskingFilter를 통과한 로그 레코드) 출력: str…** (1 connections) — `src/backend/src/dait/core/logging.py`
- **실행 모드에 맞춰 루트 로거를 설정한다. 입력: settings (검증된 앱 설정) 출력: 없음(루트 로거와 uvicorn 로거 설정이 바뀜)…** (1 connections) — `src/backend/src/dait/core/logging.py`
- **ambiguous_python_import_0fc6bd9484e5** (1 connections)
- **ambiguous_python_import_d7379e33a3f3** (1 connections)

## Relationships

- [datetime](datetime.md) (2 shared connections)
- [ai_processor.py](ai_processor.py.md) (1 shared connections)
- [sys](sys.md) (1 shared connections)
- [회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/middleware.py](회원가입_탈퇴_로그인_아웃_DB-main연결작업_담당자_홍록기-src-dait-core-middleware.py.md) (1 shared connections)
- [회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/logging.py](회원가입_탈퇴_로그인_아웃_DB-main연결작업_담당자_홍록기-src-dait-core-logging.py.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/core/logging.py`

## Audit Trail

- EXTRACTED: 29 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
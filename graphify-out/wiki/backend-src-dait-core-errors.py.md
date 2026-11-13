# backend/src/dait/core/errors.py

> 34 nodes

## Key Concepts

- **backend/src/dait/core/errors.py** (24 connections) — `src/backend/src/dait/core/errors.py`
- **AppError** (16 connections) — `src/backend/src/dait/core/errors.py`
- **.__init__()** (4 connections) — `src/backend/src/dait/core/errors.py`
- **register_error_handlers()** (4 connections) — `src/backend/src/dait/core/errors.py`
- **AlreadyLoggedInError** (3 connections) — `src/backend/src/dait/core/errors.py`
- **InvalidCredentialsError** (3 connections) — `src/backend/src/dait/core/errors.py`
- **InvalidTokenError** (3 connections) — `src/backend/src/dait/core/errors.py`
- **NewsNotFoundError** (3 connections) — `src/backend/src/dait/core/errors.py`
- **NicknameTakenError** (3 connections) — `src/backend/src/dait/core/errors.py`
- **NotReadyError** (3 connections) — `src/backend/src/dait/core/errors.py`
- **ScheduleNotFoundError** (3 connections) — `src/backend/src/dait/core/errors.py`
- **SchedulerAuthError** (3 connections) — `src/backend/src/dait/core/errors.py`
- **SignupFailedError** (3 connections) — `src/backend/src/dait/core/errors.py`
- **TooManyAttemptsError** (3 connections) — `src/backend/src/dait/core/errors.py`
- **ValidationFailedError** (3 connections) — `src/backend/src/dait/core/errors.py`
- **WeakPasswordError** (3 connections) — `src/backend/src/dait/core/errors.py`
- **FastAPI** (2 connections)
- **도메인 예외와 통일된 오류 응답({code, message, request_id}) 형식을 정의한다.** (1 connections) — `src/backend/src/dait/core/errors.py`
- **뉴스가 없거나 공개할 수 없는 상태일 때. 내부 사유는 알려 주지 않는다.** (1 connections) — `src/backend/src/dait/core/errors.py`
- **예약이 없거나 다른 사용자의 예약일 때.** (1 connections) — `src/backend/src/dait/core/errors.py`
- **내부 스케줄러 tick 호출의 비밀값이 없거나 틀렸다.** (1 connections) — `src/backend/src/dait/core/errors.py`
- **토큰이 만료·변조됐거나 형식이 맞지 않을 때.** (1 connections) — `src/backend/src/dait/core/errors.py`
- **앱에 전역 예외 핸들러를 등록한다. 입력: app (FastAPI 앱) 출력: 없음 기능: 도메인 예외, 요청 검증 오류, HTTP 오류를…** (1 connections) — `src/backend/src/dait/core/errors.py`
- **도메인 예외의 부모. 하위 클래스가 상태 코드·코드·공개 메시지를 정한다.** (1 connections) — `src/backend/src/dait/core/errors.py`
- **공개 메시지를 예외 문자열로 쓴다. 입력: 없음 출력: 없음 기능: 내부 원인은 `raise ... from 원인`으로 잇고 메시지에는 담지…** (1 connections) — `src/backend/src/dait/core/errors.py`
- *... and 9 more nodes in this community*

## Relationships

- [handle_error](handle_error.md) (5 shared connections)
- [회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/errors.py](회원가입_탈퇴_로그인_아웃_DB-main연결작업_담당자_홍록기-src-dait-core-errors.py.md) (2 shared connections)
- [ai_processor.py](ai_processor.py.md) (1 shared connections)
- [회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/core/middleware.py](회원가입_탈퇴_로그인_아웃_DB-main연결작업_담당자_홍록기-src-dait-core-middleware.py.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/core/errors.py`

## Audit Trail

- EXTRACTED: 55 (98%)
- INFERRED: 1 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
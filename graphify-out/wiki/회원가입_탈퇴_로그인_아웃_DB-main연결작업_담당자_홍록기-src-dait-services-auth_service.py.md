# 회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/auth_service.py

> 41 nodes

## Key Concepts

- **회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/auth_service.py** (25 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/auth_service.py`
- **_issue_tokens()** (10 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/auth_service.py`
- **login()** (9 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/auth_service.py`
- **_rotate()** (9 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/auth_service.py`
- **signup()** (8 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/auth_service.py`
- **datetime** (8 connections)
- **refresh()** (7 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/auth_service.py`
- **_to_response()** (7 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/auth_service.py`
- **Settings** (6 connections)
- **logout()** (5 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/auth_service.py`
- **_revoke_family_for_reuse()** (5 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/auth_service.py`
- **TokenPair** (4 connections)
- **AuthResponse** (3 connections)
- **Connection** (3 connections)
- **UserRecord** (3 connections)
- **LoginRequest** (1 connections)
- **LoginThrottles** (1 connections)
- **RefreshRequest** (1 connections)
- **SignupRequest** (1 connections)
- **가입·로그인·토큰 갱신·로그아웃 규칙을 처리한다. HTTP 형식은 api, SQL은 repositories가 맡는다.** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/auth_service.py`
- **로그인을 처리하고 새 토큰을 발급한다. 입력: settings (앱 설정), request (검증된 로그인 요청), throttles (잠금…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/auth_service.py`
- **폐기된 토큰이 다시 쓰였을 때 그 계열 전체를 폐기한다. 입력: conn (열려 있는 트랜잭션 연결), user_id (소유자),…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/auth_service.py`
- **refresh 토큰 하나를 검사하고 정상이면 새 토큰으로 회전한다. 입력: conn (열려 있는 트랜잭션 연결), settings (앱…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/auth_service.py`
- **refresh 토큰을 새 토큰 한 쌍으로 회전한다. 입력: settings (앱 설정), request (refresh 토큰 원문),…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/auth_service.py`
- **한 사용자의 refresh 토큰을 모두 폐기한다. 입력: settings (앱 설정), user (인증된 본인), client_ip (감사…** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/auth_service.py`
- *... and 16 more nodes in this community*

## Relationships

- [datetime](datetime.md) (2 shared connections)

## Source Files

- `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/src/dait/services/auth_service.py`

## Audit Trail

- EXTRACTED: 70 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
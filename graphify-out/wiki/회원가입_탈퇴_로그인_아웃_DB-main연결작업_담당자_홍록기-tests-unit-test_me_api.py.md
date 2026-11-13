# 회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_me_api.py

> 33 nodes

## Key Concepts

- **회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_me_api.py** (19 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_me_api.py`
- **client_for()** (13 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_me_api.py`
- **sign_up()** (11 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_me_api.py`
- **Settings** (10 connections)
- **bearer()** (8 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_me_api.py`
- **test_logout_requires_login_and_blocks_refresh()** (6 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_me_api.py`
- **test_session_reports_login_state()** (6 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_me_api.py`
- **test_signup_and_login_are_rejected_while_logged_in()** (6 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_me_api.py`
- **test_withdraw_rejects_extra_field()** (6 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_me_api.py`
- **test_withdraw_removes_account_and_old_tokens_stop_working()** (6 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_me_api.py`
- **test_withdraw_requires_token_and_correct_password()** (6 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_me_api.py`
- **test_refresh_failures_look_identical()** (5 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_me_api.py`
- **test_refresh_rotates_and_old_token_stops_working()** (5 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_me_api.py`
- **test_refresh_rejects_short_token_and_extra_field()** (4 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_me_api.py`
- **HttpClient** (2 connections)
- **AuthResponse** (1 connections)
- **refresh·logout·/me/session·DELETE /v1/me HTTP 테스트.** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_me_api.py`
- **로그인된 상태에서 가입·로그인은 409이고, 잘못된 토큰이면 평소처럼 동작한다.** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_me_api.py`
- **토큰이 없으면 401, 비밀번호가 틀리면 401이며 계정은 그대로다.** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_me_api.py`
- **탈퇴 요청에 알 수 없는 필드가 있으면 422다.** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_me_api.py`
- **탈퇴 뒤에는 로그인·refresh·남은 access 토큰이 모두 거부된다.** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_me_api.py`
- **테스트 DB를 쓰는 앱의 클라이언트를 만든다.** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_me_api.py`
- **Authorization 헤더 값을 만든다.** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_me_api.py`
- **토큰이 없거나 틀리면 authenticated=false(200), 유효하면 true와 사용자 정보.** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_me_api.py`
- **refresh하면 새 토큰이 오고, 이전 refresh를 다시 쓰면 401이며 새 토큰도 막힌다.** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_me_api.py`
- *... and 8 more nodes in this community*

## Relationships

- [collections_abc](collections_abc.md) (1 shared connections)

## Source Files

- `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_me_api.py`

## Audit Trail

- EXTRACTED: 66 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
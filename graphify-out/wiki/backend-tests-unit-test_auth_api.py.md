# backend/tests/unit/test_auth_api.py

> 26 nodes

## Key Concepts

- **backend/tests/unit/test_auth_api.py** (15 connections) — `tests/backend/tests/unit/test_auth_api.py`
- **client_for()** (12 connections) — `tests/backend/tests/unit/test_auth_api.py`
- **Settings** (9 connections)
- **test_duplicate_signup_is_409_generic()** (4 connections) — `tests/backend/tests/unit/test_auth_api.py`
- **test_login_failures_return_same_401()** (4 connections) — `tests/backend/tests/unit/test_auth_api.py`
- **test_login_is_locked_after_repeated_failures()** (4 connections) — `tests/backend/tests/unit/test_auth_api.py`
- **test_login_success()** (4 connections) — `tests/backend/tests/unit/test_auth_api.py`
- **test_signup_rejects_unknown_field_and_mismatch()** (4 connections) — `tests/backend/tests/unit/test_auth_api.py`
- **test_signup_returns_201_with_tokens_and_no_secrets()** (4 connections) — `tests/backend/tests/unit/test_auth_api.py`
- **test_weak_password_signup_is_422()** (4 connections) — `tests/backend/tests/unit/test_auth_api.py`
- **test_signup_without_terms_field()** (3 connections) — `tests/backend/tests/unit/test_auth_api.py`
- **HttpClient** (1 connections)
- **POST /v1/auth/signup, /v1/auth/login HTTP 테스트.** (1 connections) — `tests/backend/tests/unit/test_auth_api.py`
- **5번 실패하면 맞는 비밀번호도 429로 막힌다.** (1 connections) — `tests/backend/tests/unit/test_auth_api.py`
- **테스트 DB를 쓰는 앱의 클라이언트를 만든다.** (1 connections) — `tests/backend/tests/unit/test_auth_api.py`
- **가입하면 201과 토큰을 받고 응답에 해시·비밀번호가 없다.** (1 connections) — `tests/backend/tests/unit/test_auth_api.py`
- **알 수 없는 필드와 확인 불일치는 422이고 입력한 비밀번호를 되돌려 주지 않는다.** (1 connections) — `tests/backend/tests/unit/test_auth_api.py`
- **같은 이메일로 다시 가입하면 409 SIGNUP_FAILED이고 이메일을 언급하지 않는다.** (1 connections) — `tests/backend/tests/unit/test_auth_api.py`
- **흔한 비밀번호는 422 WEAK_PASSWORD다.** (1 connections) — `tests/backend/tests/unit/test_auth_api.py`
- **가입한 계정으로 로그인하면 200과 토큰을 받는다.** (1 connections) — `tests/backend/tests/unit/test_auth_api.py`
- **없는 이메일과 틀린 비밀번호는 같은 401 코드·메시지다.** (1 connections) — `tests/backend/tests/unit/test_auth_api.py`
- **ambiguous_python_import_1ebc2ee093f7** (1 connections)
- **ambiguous_python_import_27c8cda86348** (1 connections)
- **ambiguous_python_import_36b08d242930** (1 connections)
- **ambiguous_python_import_4ea3905c655b** (1 connections)
- *... and 1 more nodes in this community*

## Relationships

- No strong cross-community connections detected

## Source Files

- `tests/backend/tests/unit/test_auth_api.py`

## Audit Trail

- EXTRACTED: 41 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
# backend/tests/unit/test_auth_service.py

> 45 nodes

## Key Concepts

- **backend/tests/unit/test_auth_service.py** (29 connections) — `tests/backend/tests/unit/test_auth_service.py`
- **Settings** (14 connections)
- **signup_request()** (13 connections) — `tests/backend/tests/unit/test_auth_service.py`
- **fail_login()** (11 connections) — `tests/backend/tests/unit/test_auth_service.py`
- **login_request()** (9 connections) — `tests/backend/tests/unit/test_auth_service.py`
- **rows()** (8 connections) — `tests/backend/tests/unit/test_auth_service.py`
- **test_account_is_locked_after_five_failures_even_with_right_password()** (6 connections) — `tests/backend/tests/unit/test_auth_service.py`
- **test_audit_log_has_event_but_no_secrets()** (6 connections) — `tests/backend/tests/unit/test_auth_service.py`
- **test_ip_lock_blocks_other_accounts()** (6 connections) — `tests/backend/tests/unit/test_auth_service.py`
- **test_login_success_issues_new_tokens()** (6 connections) — `tests/backend/tests/unit/test_auth_service.py`
- **test_success_clears_account_failures()** (6 connections) — `tests/backend/tests/unit/test_auth_service.py`
- **test_duplicate_email_is_rejected_without_new_rows()** (5 connections) — `tests/backend/tests/unit/test_auth_service.py`
- **test_lock_applies_to_unknown_email_too()** (5 connections) — `tests/backend/tests/unit/test_auth_service.py`
- **test_login_failures_look_identical()** (5 connections) — `tests/backend/tests/unit/test_auth_service.py`
- **test_signup_creates_active_user_with_hashed_password()** (5 connections) — `tests/backend/tests/unit/test_auth_service.py`
- **test_signup_stores_only_refresh_token_hash()** (5 connections) — `tests/backend/tests/unit/test_auth_service.py`
- **test_weak_password_is_rejected_without_user()** (5 connections) — `tests/backend/tests/unit/test_auth_service.py`
- **test_signup_email_is_stored_lowercase()** (3 connections) — `tests/backend/tests/unit/test_auth_service.py`
- **datetime** (2 connections)
- **LogCaptureFixture** (1 connections)
- **LoginRequest** (1 connections)
- **LoginThrottles** (1 connections)
- **SignupRequest** (1 connections)
- **services/auth_service 테스트 (UT-AUTH-001, 005, 006, 007 및 잠금·감사 로그).** (1 connections) — `tests/backend/tests/unit/test_auth_service.py`
- **흔한 비밀번호와 이메일 포함 비밀번호는 사용자를 만들지 않는다.** (1 connections) — `tests/backend/tests/unit/test_auth_service.py`
- *... and 20 more nodes in this community*

## Relationships

- [datetime](datetime.md) (2 shared connections)
- [pytest](pytest.md) (1 shared connections)

## Source Files

- `tests/backend/tests/unit/test_auth_service.py`

## Audit Trail

- EXTRACTED: 89 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
# backend/tests/unit/test_user_repository.py

> 30 nodes

## Key Concepts

- **backend/tests/unit/test_user_repository.py** (22 connections) — `tests/backend/tests/unit/test_user_repository.py`
- **make_user()** (7 connections) — `tests/backend/tests/unit/test_user_repository.py`
- **make_token()** (6 connections) — `tests/backend/tests/unit/test_user_repository.py`
- **test_deleting_user_removes_tokens()** (4 connections) — `tests/backend/tests/unit/test_user_repository.py`
- **test_refresh_token_hash_is_unique()** (4 connections) — `tests/backend/tests/unit/test_user_repository.py`
- **test_duplicate_email_is_rejected()** (3 connections) — `tests/backend/tests/unit/test_user_repository.py`
- **test_insert_and_find_user()** (3 connections) — `tests/backend/tests/unit/test_user_repository.py`
- **test_refresh_token_requires_existing_user()** (3 connections) — `tests/backend/tests/unit/test_user_repository.py`
- **test_sql_injection_text_is_just_a_value()** (3 connections) — `tests/backend/tests/unit/test_user_repository.py`
- **test_migration_downgrade_and_upgrade_again()** (2 connections) — `tests/backend/tests/unit/test_user_repository.py`
- **test_role_check_constraint_rejects_unknown_role()** (2 connections) — `tests/backend/tests/unit/test_user_repository.py`
- **test_find_unknown_email_returns_none()** (1 connections) — `tests/backend/tests/unit/test_user_repository.py`
- **RefreshTokenRecord** (1 connections)
- **UserRecord** (1 connections)
- **users·refresh_tokens 저장소와 마이그레이션 테스트 (UT-DB-001 포함).** (1 connections) — `tests/backend/tests/unit/test_user_repository.py`
- **허용되지 않은 역할은 DB가 거부한다.** (1 connections) — `tests/backend/tests/unit/test_user_repository.py`
- **마이그레이션은 되돌릴 수 있고 다시 적용할 수 있다.** (1 connections) — `tests/backend/tests/unit/test_user_repository.py`
- **테스트용 refresh 토큰 레코드를 만든다.** (1 connections) — `tests/backend/tests/unit/test_user_repository.py`
- **저장한 사용자를 이메일로 찾으면 같은 값이 나온다.** (1 connections) — `tests/backend/tests/unit/test_user_repository.py`
- **UT-DB-001: 같은 이메일을 두 번 저장하면 거부한다.** (1 connections) — `tests/backend/tests/unit/test_user_repository.py`
- **따옴표가 섞인 이메일도 값으로만 취급되어 다른 행을 건드리지 않는다.** (1 connections) — `tests/backend/tests/unit/test_user_repository.py`
- **없는 사용자의 토큰은 외래키 때문에 저장되지 않는다.** (1 connections) — `tests/backend/tests/unit/test_user_repository.py`
- **같은 토큰 해시는 두 번 저장되지 않는다.** (1 connections) — `tests/backend/tests/unit/test_user_repository.py`
- **사용자를 지우면 토큰도 함께 지워진다(탈퇴 때 쓸 ON DELETE CASCADE).** (1 connections) — `tests/backend/tests/unit/test_user_repository.py`
- **ambiguous_python_import_40bd8bdcfc7f** (1 connections)
- *... and 5 more nodes in this community*

## Relationships

- [datetime](datetime.md) (2 shared connections)
- [pytest](pytest.md) (1 shared connections)
- [alembic](alembic.md) (1 shared connections)

## Source Files

- `tests/backend/tests/unit/test_user_repository.py`

## Audit Trail

- EXTRACTED: 41 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
# 회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_token_repository.py

> 17 nodes

## Key Concepts

- **회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_token_repository.py** (13 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_token_repository.py`
- **add_token()** (5 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_token_repository.py`
- **add_user()** (5 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_token_repository.py`
- **test_find_by_hash()** (4 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_token_repository.py`
- **test_revoke_all_for_user_is_scoped_and_idempotent()** (4 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_token_repository.py`
- **test_revoke_family_is_limited_to_that_family()** (4 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_token_repository.py`
- **test_revoke_if_active_succeeds_only_once()** (4 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_token_repository.py`
- **refresh_tokens 폐기 쿼리 테스트 (조건부 UPDATE, family·사용자 범위).** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_token_repository.py`
- **해시로 찾으면 폐기 전에는 revoked_at이 None이고, 없는 해시는 None이다.** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_token_repository.py`
- **같은 토큰을 두 번 폐기하면 두 번째는 False다(동시 사용 방어의 기반).** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_token_repository.py`
- **family 폐기는 그 계열만 막고 같은 사용자의 다른 계열은 그대로 둔다.** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_token_repository.py`
- **사용자 전체 폐기는 그 사용자만 대상이고 두 번째 호출은 0건이다.** (1 connections) — `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_token_repository.py`
- **ambiguous_python_import_0482631645d5** (1 connections)
- **ambiguous_python_import_0f7b16928e89** (1 connections)
- **ambiguous_python_import_2047e658a202** (1 connections)
- **ambiguous_python_import_4fa3eebf6208** (1 connections)
- **ambiguous_python_import_7a8f1d487ec5** (1 connections)

## Relationships

- [datetime](datetime.md) (1 shared connections)

## Source Files

- `docs/회원가입_탈퇴 로그인_아웃 DB-main연결작업 담당자_홍록기/tests/unit/test_token_repository.py`

## Audit Trail

- EXTRACTED: 25 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
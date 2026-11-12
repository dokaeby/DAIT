# backend/tests/unit/test_security.py

> 24 nodes

## Key Concepts

- **backend/tests/unit/test_security.py** (19 connections) — `tests/backend/tests/unit/test_security.py`
- **test_access_token_roundtrip_has_only_minimal_claims()** (2 connections) — `tests/backend/tests/unit/test_security.py`
- **test_alg_none_token_is_rejected()** (2 connections) — `tests/backend/tests/unit/test_security.py`
- **test_hash_is_argon2id_and_salted()** (2 connections) — `tests/backend/tests/unit/test_security.py`
- **test_refresh_token_is_random_and_hash_is_stable()** (2 connections) — `tests/backend/tests/unit/test_security.py`
- **test_token_missing_required_claim_is_rejected()** (2 connections) — `tests/backend/tests/unit/test_security.py`
- **test_verify_password_with_broken_hash_is_false()** (2 connections) — `tests/backend/tests/unit/test_security.py`
- **test_verify_password_without_user_is_always_false()** (2 connections) — `tests/backend/tests/unit/test_security.py`
- **test_expired_token_is_rejected()** (1 connections) — `tests/backend/tests/unit/test_security.py`
- **test_garbage_token_is_rejected()** (1 connections) — `tests/backend/tests/unit/test_security.py`
- **test_tampered_token_is_rejected()** (1 connections) — `tests/backend/tests/unit/test_security.py`
- **test_token_signed_with_other_key_is_rejected()** (1 connections) — `tests/backend/tests/unit/test_security.py`
- **test_verify_password_accepts_only_the_right_one()** (1 connections) — `tests/backend/tests/unit/test_security.py`
- **core/security 해시·토큰 테스트 (만료, 변조, alg=none 차단 포함).** (1 connections) — `tests/backend/tests/unit/test_security.py`
- **refresh 토큰은 매번 다르고, 해시는 같은 입력에 같으며 원문과 다르다.** (1 connections) — `tests/backend/tests/unit/test_security.py`
- **해시는 argon2id이고 평문과 다르며 호출마다 다르다.** (1 connections) — `tests/backend/tests/unit/test_security.py`
- **사용자가 없을 때(None)는 어떤 비밀번호도 실패한다.** (1 connections) — `tests/backend/tests/unit/test_security.py`
- **깨진 해시는 예외 대신 실패로 처리한다.** (1 connections) — `tests/backend/tests/unit/test_security.py`
- **access 토큰은 sub, jti, iat, exp만 담고 만료는 지정한 분이다.** (1 connections) — `tests/backend/tests/unit/test_security.py`
- **서명 없는 토큰(alg=none)은 거부한다.** (1 connections) — `tests/backend/tests/unit/test_security.py`
- **필수 값(jti)이 없는 토큰은 거부한다.** (1 connections) — `tests/backend/tests/unit/test_security.py`
- **ambiguous_python_import_60ef2508c0b3** (1 connections)
- **ambiguous_python_import_a5d1932ea3a8** (1 connections)
- **ambiguous_python_import_d38d7889b8ec** (1 connections)

## Relationships

- [datetime](datetime.md) (2 shared connections)
- [pytest](pytest.md) (1 shared connections)

## Source Files

- `tests/backend/tests/unit/test_security.py`

## Audit Trail

- EXTRACTED: 26 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*
"""core/security 해시·토큰 테스트 (만료, 변조, alg=none 차단 포함)."""

import hashlib
from datetime import UTC, datetime

import pytest

from dait.core.errors import InvalidTokenError
from dait.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)
from support import forge_token, read_claim_names

SECRET = "unit-test-secret-0123456789-abcdefghijklmnop"  # noqa: S105 - 테스트 전용 가짜 키
PASSWORD = "Str0ng!Passw0rd-xyz"  # noqa: S105 - 테스트 전용 가짜 비밀번호


def test_hash_is_argon2id_and_salted() -> None:
    """해시는 argon2id이고 평문과 다르며 호출마다 다르다."""
    first, second = hash_password(PASSWORD), hash_password(PASSWORD)
    assert first.startswith("$argon2id$")
    assert PASSWORD not in first
    assert first != second


def test_verify_password_accepts_only_the_right_one() -> None:
    """맞는 비밀번호만 통과한다."""
    hashed = hash_password(PASSWORD)
    assert verify_password(PASSWORD, hashed) is True
    assert verify_password(PASSWORD + "x", hashed) is False


def test_verify_password_without_user_is_always_false() -> None:
    """사용자가 없을 때(None)는 어떤 비밀번호도 실패한다."""
    assert verify_password(PASSWORD, None) is False


def test_verify_password_with_broken_hash_is_false() -> None:
    """깨진 해시는 예외 대신 실패로 처리한다."""
    assert verify_password(PASSWORD, "not-a-hash") is False


def test_access_token_roundtrip_has_only_minimal_claims() -> None:
    """access 토큰은 sub, jti, iat, exp만 담고 만료는 지정한 분이다."""
    now = datetime.now(UTC)
    token = create_access_token("user-1", SECRET, 15, now)
    claims = decode_access_token(token, SECRET)
    assert claims.sub == "user-1"
    assert claims.exp - claims.iat == 15 * 60
    assert read_claim_names(token, SECRET) == {"sub", "jti", "iat", "exp"}


def test_expired_token_is_rejected() -> None:
    """만료된 토큰은 거부한다."""
    token = create_access_token("user-1", SECRET, 15, datetime(2020, 1, 1, tzinfo=UTC))
    with pytest.raises(InvalidTokenError):
        decode_access_token(token, SECRET)


def test_tampered_token_is_rejected() -> None:
    """서명이 바뀐 토큰은 거부한다."""
    token = create_access_token("user-1", SECRET, 15, datetime.now(UTC))
    tampered = token[:-2] + ("AA" if not token.endswith("AA") else "BB")
    with pytest.raises(InvalidTokenError):
        decode_access_token(tampered, SECRET)


def test_token_signed_with_other_key_is_rejected() -> None:
    """다른 키로 서명한 토큰은 거부한다."""
    token = create_access_token("user-1", SECRET + "x", 15, datetime.now(UTC))
    with pytest.raises(InvalidTokenError):
        decode_access_token(token, SECRET)


def test_alg_none_token_is_rejected() -> None:
    """서명 없는 토큰(alg=none)은 거부한다."""
    now = int(datetime.now(UTC).timestamp())
    payload = {"sub": "user-1", "jti": "j", "iat": now, "exp": now + 600}
    forged = forge_token(payload, "", "none")
    with pytest.raises(InvalidTokenError):
        decode_access_token(forged, SECRET)


def test_token_missing_required_claim_is_rejected() -> None:
    """필수 값(jti)이 없는 토큰은 거부한다."""
    now = int(datetime.now(UTC).timestamp())
    forged = forge_token({"sub": "u", "iat": now, "exp": now + 600}, SECRET, "HS256")
    with pytest.raises(InvalidTokenError):
        decode_access_token(forged, SECRET)


def test_garbage_token_is_rejected() -> None:
    """토큰 모양이 아닌 문자열은 거부한다."""
    with pytest.raises(InvalidTokenError):
        decode_access_token("not.a.token", SECRET)


def test_refresh_token_is_random_and_hash_is_stable() -> None:
    """refresh 토큰은 매번 다르고, 해시는 같은 입력에 같으며 원문과 다르다."""
    first, second = new_refresh_token(), new_refresh_token()
    assert first != second
    assert len(first) >= 43
    digest = hash_refresh_token(first)
    assert digest == hashlib.sha256(first.encode()).hexdigest()
    assert len(digest) == 64
    assert first not in digest

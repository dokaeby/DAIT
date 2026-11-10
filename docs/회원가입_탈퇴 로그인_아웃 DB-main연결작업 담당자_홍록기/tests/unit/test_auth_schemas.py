"""schemas/auth 입력 검증 테스트 (UT-AUTH-002, 003, 004 및 비밀번호 길이)."""

import pytest
from pydantic import ValidationError

from dait.schemas.auth import LoginRequest, SignupRequest

STRONG = "Str0ng!Passw0rd-xyz"
OTHER = "Other!Passw0rd-xyz"


def signup_data(**override: object) -> dict[str, object]:
    """유효한 가입 요청 값에 일부만 바꿔 돌려준다."""
    data: dict[str, object] = {
        "email": "usera@example.com",
        "password": STRONG,
        "password_confirm": STRONG,
        "terms_accepted": True,
    }
    return data | override


def test_valid_signup_request_passes() -> None:
    """올바른 가입 요청은 통과한다."""
    request = SignupRequest.model_validate(signup_data())
    assert str(request.email) == "usera@example.com"


@pytest.mark.parametrize("email", ["abc", "@example.com", "a" * 250 + "@example.com", ""])
def test_invalid_email_is_rejected(email: str) -> None:
    """UT-AUTH-002: 이메일 형식 오류와 254자 초과를 거부한다."""
    with pytest.raises(ValidationError):
        SignupRequest.model_validate(signup_data(email=email))


def test_password_confirm_mismatch_is_rejected() -> None:
    """UT-AUTH-003: 비밀번호 확인이 다르면 거부한다."""
    with pytest.raises(ValidationError):
        SignupRequest.model_validate(signup_data(password_confirm=OTHER))


def test_terms_not_accepted_is_rejected() -> None:
    """UT-AUTH-004: 약관에 동의하지 않으면 거부한다."""
    with pytest.raises(ValidationError):
        SignupRequest.model_validate(signup_data(terms_accepted=False))


@pytest.mark.parametrize("length", [7, 129])
def test_password_length_bounds_are_rejected(length: int) -> None:
    """비밀번호 7자 이하와 129자 이상을 거부한다."""
    value = "a1!" * 50
    value = value[:length]
    with pytest.raises(ValidationError):
        SignupRequest.model_validate(signup_data(password=value, password_confirm=value))


@pytest.mark.parametrize("length", [8, 128])
def test_password_length_bounds_are_accepted(length: int) -> None:
    """비밀번호 8자와 128자는 통과한다."""
    value = ("a1!" * 50)[:length]
    request = SignupRequest.model_validate(signup_data(password=value, password_confirm=value))
    assert len(request.password.get_secret_value()) == length


def test_unknown_field_is_rejected() -> None:
    """알 수 없는 필드는 거부한다(mass assignment 방지)."""
    with pytest.raises(ValidationError):
        SignupRequest.model_validate(signup_data(role="ADMIN"))


def test_password_is_hidden_in_repr() -> None:
    """요청 객체를 문자열로 찍어도 비밀번호가 보이지 않는다."""
    request = SignupRequest.model_validate(signup_data())
    assert STRONG not in repr(request)
    assert STRONG not in str(request)
    assert STRONG not in request.model_dump_json()


def test_login_request_rejects_empty_password() -> None:
    """로그인 비밀번호가 비어 있으면 거부한다."""
    with pytest.raises(ValidationError):
        LoginRequest.model_validate({"email": "usera@example.com", "password": ""})

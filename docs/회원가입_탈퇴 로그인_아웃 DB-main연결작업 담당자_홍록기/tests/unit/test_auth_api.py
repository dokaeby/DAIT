"""POST /v1/auth/signup, /v1/auth/login HTTP 테스트."""

import pytest

from dait.core.config import Settings
from dait.core.errors import ErrorResponse
from dait.main import create_app
from dait.schemas.auth import AuthResponse
from support import HttpClient, as_client

PASSWORD = "Str0ng!Passw0rd-xyz"  # noqa: S105 - 테스트 전용 가짜 비밀번호
SIGNUP = {
    "email": "UserA@example.com",
    "password": PASSWORD,
    "password_confirm": PASSWORD,
    "terms_accepted": True,
}


def client_for(settings: Settings) -> HttpClient:
    """테스트 DB를 쓰는 앱의 클라이언트를 만든다."""
    return as_client(create_app(settings))


def test_signup_returns_201_with_tokens_and_no_secrets(settings: Settings) -> None:
    """가입하면 201과 토큰을 받고 응답에 해시·비밀번호가 없다."""
    response = client_for(settings).request("POST", "/v1/auth/signup", json=SIGNUP)
    assert response.status_code == 201
    body = AuthResponse.model_validate_json(response.text)
    assert body.user.email == "usera@example.com"
    assert body.tokens.token_type == "bearer"  # noqa: S105 - 인증 방식 이름이지 비밀값이 아님
    assert "argon2" not in response.text
    assert "password" not in response.text


def test_signup_rejects_unknown_field_and_mismatch(settings: Settings) -> None:
    """알 수 없는 필드와 확인 불일치는 422이고 입력한 비밀번호를 되돌려 주지 않는다."""
    client = client_for(settings)
    extra = client.request("POST", "/v1/auth/signup", json=SIGNUP | {"role": "ADMIN"})
    mismatch = client.request(
        "POST", "/v1/auth/signup", json=SIGNUP | {"password_confirm": "Other!Passw0rd-123"}
    )
    for response in (extra, mismatch):
        assert response.status_code == 422
        assert ErrorResponse.model_validate_json(response.text).code == "VALIDATION_ERROR"
        assert PASSWORD not in response.text
        assert "Other!Passw0rd-123" not in response.text


def test_signup_without_terms_is_422(settings: Settings) -> None:
    """약관에 동의하지 않으면 422다."""
    response = client_for(settings).request(
        "POST", "/v1/auth/signup", json=SIGNUP | {"terms_accepted": False}
    )
    assert response.status_code == 422


def test_duplicate_signup_is_409_generic(settings: Settings) -> None:
    """같은 이메일로 다시 가입하면 409 SIGNUP_FAILED이고 이메일을 언급하지 않는다."""
    client = client_for(settings)
    client.request("POST", "/v1/auth/signup", json=SIGNUP)
    response = client.request("POST", "/v1/auth/signup", json=SIGNUP)
    assert response.status_code == 409
    assert ErrorResponse.model_validate_json(response.text).code == "SIGNUP_FAILED"
    body = ErrorResponse.model_validate_json(response.text)
    assert body.message == "이미 가입된 이메일입니다."
    assert "usera@example.com" not in response.text.lower()


def test_weak_password_signup_is_422(settings: Settings) -> None:
    """흔한 비밀번호는 422 WEAK_PASSWORD다."""
    weak = "password123"
    response = client_for(settings).request(
        "POST", "/v1/auth/signup", json=SIGNUP | {"password": weak, "password_confirm": weak}
    )
    assert response.status_code == 422
    body = ErrorResponse.model_validate_json(response.text)
    assert body.code == "WEAK_PASSWORD"
    assert body.message == "너무 흔한 비밀번호입니다."
    assert body.errors is not None
    assert (body.errors[0].field, body.errors[0].code) == ("password", "COMMON_PASSWORD")


def test_password_containing_email_is_422_with_reason(settings: Settings) -> None:
    """이메일 앞부분을 쓴 비밀번호는 전용 문구와 CONTAINS_EMAIL을 받는다."""
    weak = "Xusera-2026!ab"
    response = client_for(settings).request(
        "POST", "/v1/auth/signup", json=SIGNUP | {"password": weak, "password_confirm": weak}
    )
    body = ErrorResponse.model_validate_json(response.text)
    assert response.status_code == 422
    assert body.message == "비밀번호에 이메일 앞부분을 쓸 수 없습니다."
    assert body.errors is not None
    assert body.errors[0].code == "CONTAINS_EMAIL"
    assert weak not in response.text


def _first_error(settings: Settings, change: dict[str, object]) -> tuple[str, str, str, str]:
    """가입 요청을 바꿔 보내고 첫 칸별 오류와 최상위 문구를 돌려준다."""
    response = client_for(settings).request("POST", "/v1/auth/signup", json=SIGNUP | change)
    body = ErrorResponse.model_validate_json(response.text)
    assert response.status_code == 422
    assert body.code == "VALIDATION_ERROR"
    assert body.errors is not None
    first = body.errors[0]
    return first.field, first.code, first.message, body.message


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        (
            {"password": "Ab1!xyz", "password_confirm": "Ab1!xyz"},
            ("password", "TOO_SHORT", "비밀번호는 8자 이상이어야 합니다."),
        ),
        (
            {"password_confirm": "Other!Passw0rd-123"},
            ("password_confirm", "MISMATCH", "비밀번호가 서로 다릅니다."),
        ),
        (
            {"terms_accepted": False},
            ("terms_accepted", "TERMS_REQUIRED", "이용약관에 동의해 주세요."),
        ),
        (
            {"email": "not-an-email"},
            ("email", "INVALID_FORMAT", "올바른 이메일 형식이 아닙니다."),
        ),
    ],
)
def test_signup_validation_reasons(
    settings: Settings, change: dict[str, object], expected: tuple[str, str, str]
) -> None:
    """검증 실패는 칸·이유 코드·한국어 문구로 나오고 최상위 message는 첫 문구다."""
    field, code, message, top = _first_error(settings, change)
    assert (field, code, message) == expected
    assert top == expected[2]


def test_validation_error_never_echoes_input_value(settings: Settings) -> None:
    """알 수 없는 필드 이름과 틀린 값은 errors에 그대로 실리지 않는다."""
    response = client_for(settings).request(
        "POST",
        "/v1/auth/signup",
        json=SIGNUP | {"evil<script>": "SECRET-VALUE", "email": "bad-SECRET"},
    )
    assert response.status_code == 422
    assert "SECRET" not in response.text
    assert "evil" not in response.text


def test_login_success(settings: Settings) -> None:
    """가입한 계정으로 로그인하면 200과 토큰을 받는다."""
    client = client_for(settings)
    client.request("POST", "/v1/auth/signup", json=SIGNUP)
    response = client.request(
        "POST", "/v1/auth/login", json={"email": "usera@example.com", "password": PASSWORD}
    )
    assert response.status_code == 200
    assert AuthResponse.model_validate_json(response.text).tokens.access_token


def test_login_failures_return_same_401(settings: Settings) -> None:
    """없는 이메일과 틀린 비밀번호는 같은 401 코드·메시지다."""
    client = client_for(settings)
    client.request("POST", "/v1/auth/signup", json=SIGNUP)
    unknown = client.request(
        "POST", "/v1/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}
    )
    wrong = client.request(
        "POST",
        "/v1/auth/login",
        json={"email": "usera@example.com", "password": "Wr0ng!Passw0rd-xyz"},
    )
    assert unknown.status_code == wrong.status_code == 401
    first = ErrorResponse.model_validate_json(unknown.text)
    second = ErrorResponse.model_validate_json(wrong.text)
    assert (first.code, first.message) == (second.code, second.message)


def test_login_is_locked_after_repeated_failures(settings: Settings) -> None:
    """5번 실패하면 맞는 비밀번호도 429로 막힌다."""
    client = client_for(settings)
    client.request("POST", "/v1/auth/signup", json=SIGNUP)
    bad = {"email": "usera@example.com", "password": "Wr0ng!Passw0rd-xyz"}
    for _ in range(5):
        client.request("POST", "/v1/auth/login", json=bad)
    response = client.request(
        "POST", "/v1/auth/login", json={"email": "usera@example.com", "password": PASSWORD}
    )
    assert response.status_code == 429
    assert ErrorResponse.model_validate_json(response.text).code == "TOO_MANY_ATTEMPTS"

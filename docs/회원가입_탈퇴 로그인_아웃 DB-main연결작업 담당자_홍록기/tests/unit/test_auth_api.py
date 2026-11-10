"""POST /v1/auth/signup, /v1/auth/login HTTP 테스트."""

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
    assert "이메일" not in response.text


def test_weak_password_signup_is_422(settings: Settings) -> None:
    """흔한 비밀번호는 422 WEAK_PASSWORD다."""
    weak = "password123"
    response = client_for(settings).request(
        "POST", "/v1/auth/signup", json=SIGNUP | {"password": weak, "password_confirm": weak}
    )
    assert response.status_code == 422
    assert ErrorResponse.model_validate_json(response.text).code == "WEAK_PASSWORD"


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

"""refresh·logout·/me/session·DELETE /v1/me HTTP 테스트."""

from collections.abc import Mapping

from dait.core.config import Settings
from dait.core.errors import ErrorResponse
from dait.main import create_app
from dait.schemas.auth import AuthResponse, ResultResponse, SessionResponse, TokenPair
from support import HttpClient, as_client

PASSWORD = "Str0ng!Passw0rd-xyz"  # noqa: S105 - 테스트 전용 가짜 비밀번호
WRONG = "Wr0ng!Passw0rd-xyz"
SIGNUP = {
    "email": "usera@example.com",
    "password": PASSWORD,
    "password_confirm": PASSWORD,
    "terms_accepted": True,
}


def client_for(settings: Settings) -> HttpClient:
    """테스트 DB를 쓰는 앱의 클라이언트를 만든다."""
    return as_client(create_app(settings))


def bearer(token: str) -> Mapping[str, str]:
    """Authorization 헤더 값을 만든다."""
    return {"Authorization": f"Bearer {token}"}


def sign_up(client: HttpClient, body: Mapping[str, object] = SIGNUP) -> AuthResponse:
    """가입시키고 응답을 돌려준다."""
    response = client.request("POST", "/v1/auth/signup", json=body)
    assert response.status_code == 201
    return AuthResponse.model_validate_json(response.text)


def test_session_reports_login_state(settings: Settings) -> None:
    """토큰이 없거나 틀리면 authenticated=false(200), 유효하면 true와 사용자 정보."""
    client = client_for(settings)
    signed = sign_up(client)
    on = client.request("GET", "/v1/me/session", headers=bearer(signed.tokens.access_token))
    none = client.request("GET", "/v1/me/session")
    bad = client.request("GET", "/v1/me/session", headers=bearer("garbage"))
    assert SessionResponse.model_validate_json(on.text).authenticated is True
    assert SessionResponse.model_validate_json(on.text).user is not None
    assert SessionResponse.model_validate_json(none.text).authenticated is False
    assert (none.status_code, bad.status_code) == (200, 200)
    assert SessionResponse.model_validate_json(bad.text).authenticated is False


def test_refresh_rotates_and_old_token_stops_working(settings: Settings) -> None:
    """refresh하면 새 토큰이 오고, 이전 refresh를 다시 쓰면 401이며 새 토큰도 막힌다."""
    client = client_for(settings)
    old = sign_up(client).tokens.refresh_token
    first = client.request("POST", "/v1/auth/refresh", json={"refresh_token": old})
    assert first.status_code == 200
    new = TokenPair.model_validate_json(first.text).refresh_token
    assert new != old
    reuse = client.request("POST", "/v1/auth/refresh", json={"refresh_token": old})
    assert reuse.status_code == 401
    assert ErrorResponse.model_validate_json(reuse.text).code == "INVALID_TOKEN"
    after = client.request("POST", "/v1/auth/refresh", json={"refresh_token": new})
    assert after.status_code == 401


def test_refresh_failures_look_identical(settings: Settings) -> None:
    """모르는 토큰과 이미 쓴 토큰은 같은 401 코드·메시지다."""
    client = client_for(settings)
    old = sign_up(client).tokens.refresh_token
    client.request("POST", "/v1/auth/refresh", json={"refresh_token": old})
    reused = client.request("POST", "/v1/auth/refresh", json={"refresh_token": old})
    unknown = client.request("POST", "/v1/auth/refresh", json={"refresh_token": "z" * 43})
    first = ErrorResponse.model_validate_json(reused.text)
    second = ErrorResponse.model_validate_json(unknown.text)
    assert (first.code, first.message) == (second.code, second.message)
    assert reused.status_code == unknown.status_code == 401


def test_refresh_rejects_short_token_and_extra_field(settings: Settings) -> None:
    """형식이 맞지 않는 요청은 422이고 입력값을 되돌려 주지 않는다."""
    client = client_for(settings)
    short = client.request("POST", "/v1/auth/refresh", json={"refresh_token": "short-secret"})
    extra = client.request(
        "POST", "/v1/auth/refresh", json={"refresh_token": "x" * 43, "user_id": "someone"}
    )
    assert short.status_code == extra.status_code == 422
    assert "short-secret" not in short.text


def test_logout_requires_login_and_blocks_refresh(settings: Settings) -> None:
    """로그아웃은 토큰이 있어야 하고, 하고 나면 refresh가 막히며 두 번 불러도 같은 결과다."""
    client = client_for(settings)
    signed = sign_up(client)
    anonymous = client.request("POST", "/v1/auth/logout")
    assert anonymous.status_code == 401
    assert ErrorResponse.model_validate_json(anonymous.text).code == "INVALID_TOKEN"
    headers = bearer(signed.tokens.access_token)
    first = client.request("POST", "/v1/auth/logout", headers=headers)
    second = client.request("POST", "/v1/auth/logout", headers=headers)
    assert first.status_code == second.status_code == 200
    assert ResultResponse.model_validate_json(first.text).result == "done"
    after = client.request(
        "POST", "/v1/auth/refresh", json={"refresh_token": signed.tokens.refresh_token}
    )
    assert after.status_code == 401


def test_signup_and_login_are_rejected_while_logged_in(settings: Settings) -> None:
    """로그인된 상태에서 가입·로그인은 409이고, 잘못된 토큰이면 평소처럼 동작한다."""
    client = client_for(settings)
    signed = sign_up(client)
    headers = bearer(signed.tokens.access_token)
    login = {"email": "usera@example.com", "password": PASSWORD}
    other = SIGNUP | {"email": "userb@example.com"}
    for path, body in (("/v1/auth/login", login), ("/v1/auth/signup", other)):
        response = client.request("POST", path, json=body, headers=headers)
        assert response.status_code == 409
        assert ErrorResponse.model_validate_json(response.text).code == "ALREADY_LOGGED_IN"
    normal = client.request("POST", "/v1/auth/login", json=login, headers=bearer("garbage"))
    assert normal.status_code == 200


def test_withdraw_requires_token_and_correct_password(settings: Settings) -> None:
    """토큰이 없으면 401, 비밀번호가 틀리면 401이며 계정은 그대로다."""
    client = client_for(settings)
    signed = sign_up(client)
    headers = bearer(signed.tokens.access_token)
    anonymous = client.request("DELETE", "/v1/me", json={"password": PASSWORD})
    wrong = client.request("DELETE", "/v1/me", json={"password": WRONG}, headers=headers)
    assert anonymous.status_code == 401
    assert wrong.status_code == 401
    assert ErrorResponse.model_validate_json(wrong.text).code == "INVALID_CREDENTIALS"
    still = client.request("GET", "/v1/me/session", headers=headers)
    assert SessionResponse.model_validate_json(still.text).authenticated is True


def test_withdraw_rejects_extra_field(settings: Settings) -> None:
    """탈퇴 요청에 알 수 없는 필드가 있으면 422다."""
    client = client_for(settings)
    headers = bearer(sign_up(client).tokens.access_token)
    response = client.request(
        "DELETE", "/v1/me", json={"password": PASSWORD, "user_id": "someone"}, headers=headers
    )
    assert response.status_code == 422


def test_withdraw_removes_account_and_old_tokens_stop_working(settings: Settings) -> None:
    """탈퇴 뒤에는 로그인·refresh·남은 access 토큰이 모두 거부된다."""
    client = client_for(settings)
    signed = sign_up(client)
    headers = bearer(signed.tokens.access_token)
    done = client.request("DELETE", "/v1/me", json={"password": PASSWORD}, headers=headers)
    assert done.status_code == 200
    login = client.request(
        "POST", "/v1/auth/login", json={"email": "usera@example.com", "password": PASSWORD}
    )
    refresh = client.request(
        "POST", "/v1/auth/refresh", json={"refresh_token": signed.tokens.refresh_token}
    )
    session = client.request("GET", "/v1/me/session", headers=headers)
    logout = client.request("POST", "/v1/auth/logout", headers=headers)
    assert (login.status_code, refresh.status_code, logout.status_code) == (401, 401, 401)
    assert SessionResponse.model_validate_json(session.text).authenticated is False
    again = sign_up(client)  # 같은 이메일로 다시 가입할 수 있다(실제 삭제).
    assert again.user.email == "usera@example.com"

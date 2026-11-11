"""로그인·가입·세션 응답에 로컬 DB의 관심사가 실려 나가는지 시험한다 (자체 케이스)."""

from collections.abc import Mapping

from dait.core.config import Settings
from dait.main import create_app
from dait.schemas.auth import AuthResponse, SessionResponse
from support import HttpClient, as_client

PASSWORD = "Str0ng!Passw0rd-xyz"  # noqa: S105 - 테스트 전용 가짜 비밀번호


def new_client(settings: Settings) -> HttpClient:
    """같은 DB를 쓰는 새 앱(서버 재시작을 흉내 낸다)의 클라이언트를 만든다."""
    return as_client(create_app(settings))


def credentials(email: str = "usera@example.com") -> Mapping[str, str]:
    """로그인 요청 본문을 만든다."""
    return {"email": email, "password": PASSWORD}


def sign_up(client: HttpClient, email: str = "usera@example.com", **extra: object) -> AuthResponse:
    """가입시키고 응답을 돌려준다."""
    body = {**credentials(email), "password_confirm": PASSWORD, "terms_accepted": True, **extra}
    response = client.request("POST", "/v1/auth/signup", json=body)
    assert response.status_code == 201, response.text
    return AuthResponse.model_validate_json(response.text)


def log_in(client: HttpClient, email: str = "usera@example.com") -> AuthResponse:
    """로그인하고 응답을 돌려준다(토큰 없이 호출)."""
    response = client.request("POST", "/v1/auth/login", json=credentials(email))
    assert response.status_code == 200, response.text
    return AuthResponse.model_validate_json(response.text)


def codes(response: AuthResponse | SessionResponse) -> list[str]:
    """응답의 관심사 코드만 뽑는다."""
    return [item.code.value for item in response.interests]


def test_login_returns_saved_interests_in_catalog_order(settings: Settings) -> None:
    """로그인 응답에 DB에 저장된 관심사가 카탈로그 순서로, 한글 이름·대주제와 함께 들어 있다."""
    client = new_client(settings)
    sign_up(client, interests=["economy.jobs", "ai.models"])
    response = log_in(client)
    assert codes(response) == ["ai.models", "economy.jobs"]
    assert [(i.name, i.group) for i in response.interests] == [
        ("모델·연구", "ai"),
        ("일자리", "economy"),
    ]


def test_login_returns_empty_list_when_none_selected(settings: Settings) -> None:
    """고른 관심사가 없으면 빈 목록이다(건너뛰기 포함)."""
    client = new_client(settings)
    sign_up(client)
    assert log_in(client).interests == []


def test_signup_response_returns_just_saved_interests(settings: Settings) -> None:
    """가입 응답에도 방금 저장한 관심사가 돌아온다."""
    response = sign_up(new_client(settings), interests=["society.health"])
    assert codes(response) == ["society.health"]


def test_login_reflects_changes_made_after_signup(settings: Settings) -> None:
    """PUT으로 바꾼 관심사가 다음 로그인 응답에 반영된다."""
    client = new_client(settings)
    signed = sign_up(client, interests=["ai.models"])
    headers = {"Authorization": f"Bearer {signed.tokens.access_token}"}
    client.request("PUT", "/v1/me/interests", json={"interests": ["ai.infra"]}, headers=headers)
    client.request("POST", "/v1/auth/logout", headers=headers)
    assert codes(log_in(client)) == ["ai.infra"]


def test_interests_survive_server_restart(settings: Settings) -> None:
    """앱을 새로 만들어도(재시작) 같은 로컬 DB 파일에서 같은 관심사가 나온다."""
    first = new_client(settings)
    sign_up(first, interests=["ai.agents", "society.climate"])
    second = new_client(settings)
    assert codes(log_in(second)) == ["ai.agents", "society.climate"]


def test_each_user_gets_only_their_own_interests(settings: Settings) -> None:
    """두 사용자의 로그인 응답에 서로의 관심사가 섞이지 않는다."""
    client = new_client(settings)
    sign_up(client, "usera@example.com", interests=["ai.models"])
    sign_up(client, "userb@example.com", interests=["society.health"])
    assert codes(log_in(client, "usera@example.com")) == ["ai.models"]
    assert codes(log_in(client, "userb@example.com")) == ["society.health"]


def test_session_includes_interests_only_when_logged_in(settings: Settings) -> None:
    """세션 확인은 로그인 상태면 관심사를 함께 주고, 아니면 빈 목록이다."""
    client = new_client(settings)
    signed = sign_up(client, interests=["ai.models"])
    headers = {"Authorization": f"Bearer {signed.tokens.access_token}"}
    on = SessionResponse.model_validate_json(
        client.request("GET", "/v1/me/session", headers=headers).text
    )
    off = SessionResponse.model_validate_json(client.request("GET", "/v1/me/session").text)
    assert codes(on) == ["ai.models"]
    assert off.interests == []


def test_failed_login_does_not_reveal_interests(settings: Settings) -> None:
    """로그인에 실패하면 관심사가 응답에 없다."""
    client = new_client(settings)
    sign_up(client, interests=["ai.models"])
    wrong = {"email": "usera@example.com", "password": "Wr0ng!Passw0rd-xyz"}
    response = client.request("POST", "/v1/auth/login", json=wrong)
    assert response.status_code == 401
    assert "interests" not in response.text
    assert "ai.models" not in response.text


def test_re_signup_after_withdraw_starts_empty(settings: Settings) -> None:
    """탈퇴 뒤 같은 이메일로 다시 가입하면 이전 관심사가 남지 않는다."""
    client = new_client(settings)
    signed = sign_up(client, interests=["ai.models", "ai.infra"])
    headers = {"Authorization": f"Bearer {signed.tokens.access_token}"}
    done = client.request("DELETE", "/v1/me", json={"password": PASSWORD}, headers=headers)
    assert done.status_code == 200
    assert sign_up(client).interests == []

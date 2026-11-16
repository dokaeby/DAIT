"""닉네임 경계·중복·인증 응답·마이그레이션 회귀 검사."""

import sqlite3
from datetime import UTC, datetime

import pytest
from alembic import command
from pydantic import ValidationError

from dait.core.config import Settings
from dait.main import create_app
from dait.schemas.auth import SignupRequest
from support import alembic_config, as_client

PASSWORD = "Str0ng!Passw0rd-xyz"  # noqa: S105 - 테스트 전용 값


def signup_payload(email: str, nickname: object = None) -> dict[str, object]:
    """HTTP 경계 검증용 입력을 만든다."""
    return {
        "email": email,
        "nickname": nickname,
        "password": PASSWORD,
        "password_confirm": PASSWORD,
        "terms_accepted": True,
    }


@pytest.mark.parametrize("nickname", ["a", " ", None, "", "a" * 31, 123, "ab\x00"])
def test_nickname_input_bounds(nickname: object) -> None:
    """빈 입력만 선택 항목으로 허용하고 짧거나 잘못된 타입은 거부한다."""
    payload = signup_payload("test@example.com", nickname)
    if nickname is None or nickname in ("", " "):
        assert SignupRequest.model_validate(payload).nickname is None
    else:
        with pytest.raises(ValidationError):
            SignupRequest.model_validate(payload)


def test_nickname_duplicate_and_session(settings: Settings) -> None:
    """사전 확인 뒤 다른 사용자가 가입해도 DB 유니크 제약으로 중복을 막는다."""
    client = as_client(create_app(settings))
    check = "/v1/auth/nickname-availability"
    assert client.request("GET", check, params={"nickname": "Tester"}).json()["available"]
    response = client.request(
        "POST",
        "/v1/auth/signup",
        json=signup_payload("a@example.com", " \uff34\uff45\uff53\uff54\uff45\uff52 "),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["nickname"] == "Tester"
    assert not client.request("GET", check, params={"nickname": "tester"}).json()["available"]
    duplicate = client.request(
        "POST", "/v1/auth/signup", json=signup_payload("b@example.com", "tester")
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "NICKNAME_TAKEN"
    headers = {"Authorization": "Bearer " + body["tokens"]["access_token"]}
    session = client.request("GET", "/v1/me/session", headers=headers)
    assert session.json()["user"]["nickname"] == "Tester"
    assert client.request("GET", check, params={"nickname": "x"}).status_code == 422
    assert (
        client.request("POST", "/v1/auth/signup", json=signup_payload("c@example.com")).status_code
        == 201
    )
    assert (
        client.request("POST", "/v1/auth/signup", json=signup_payload("d@example.com")).status_code
        == 201
    )
    with sqlite3.connect(settings.database_url.removeprefix("sqlite:///")) as conn:
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 3


def test_authenticated_nickname_update(settings: Settings) -> None:
    """본인 변경·중복·초기화와 인증을 검증한다."""
    client = as_client(create_app(settings))
    first = client.request(
        "POST", "/v1/auth/signup", json=signup_payload("first@example.com", "첫번째")
    )
    second = client.request(
        "POST", "/v1/auth/signup", json=signup_payload("second@example.com", "두번째")
    )
    assert first.status_code == second.status_code == 201
    headers = {"Authorization": "Bearer " + first.json()["tokens"]["access_token"]}
    assert (
        client.request("PATCH", "/v1/me/nickname", json={"nickname": "새이름"}).status_code == 401
    )
    assert (
        client.request(
            "PATCH", "/v1/me/nickname", headers=headers, json={"nickname": "한"}
        ).status_code
        == 422
    )
    assert (
        client.request(
            "PATCH", "/v1/me/nickname", headers=headers, json={"nickname": "두번째"}
        ).status_code
        == 409
    )
    changed = client.request(
        "PATCH", "/v1/me/nickname", headers=headers, json={"nickname": " 새이름 "}
    )
    assert changed.status_code == 200
    assert changed.json()["nickname"] == "새이름"
    assert (
        client.request("GET", "/v1/me/session", headers=headers).json()["user"]["nickname"]
        == "새이름"
    )
    assert (
        client.request(
            "PATCH", "/v1/me/nickname", headers=headers, json={"nickname": "새이름"}
        ).status_code
        == 200
    )
    assert (
        client.request("PATCH", "/v1/me/nickname", headers=headers, json={"nickname": ""}).json()[
            "nickname"
        ]
        is None
    )


def test_nickname_upgrade_preserves_accounts_and_downgrade(db_url: str) -> None:
    """기존 계정·NULL 닉네임을 유지하고 롤백 후 재적용할 수 있다."""
    config = alembic_config(db_url)
    command.downgrade(config, "0003_news_settings")
    now = datetime.now(UTC).isoformat()
    with sqlite3.connect(db_url.removeprefix("sqlite:///")) as conn:
        conn.execute(
            "INSERT INTO users (id,email,password_hash,status,role,created_at) "
            "VALUES (?,?,?,'ACTIVE','USER',?)",
            ("existing", "old@example.com", "test-hash", now),
        )
    command.upgrade(config, "head")
    with sqlite3.connect(db_url.removeprefix("sqlite:///")) as conn:
        assert conn.execute("SELECT email,nickname FROM users").fetchone() == (
            "old@example.com",
            None,
        )
    command.downgrade(config, "0003_news_settings")
    command.upgrade(config, "head")

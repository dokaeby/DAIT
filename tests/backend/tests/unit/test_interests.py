"""관심사(FR-INTEREST-01) 테스트. 08 문서에 UT가 없어 같은 규칙으로 만든 자체 케이스다."""

import sqlite3
from collections.abc import Mapping

import pytest
from alembic import command
from pydantic import ValidationError

from dait.core.config import Settings
from dait.core.errors import ErrorResponse
from dait.main import create_app
from dait.repositories.db import connect
from dait.schemas.auth import AuthResponse, SignupRequest
from dait.schemas.interest import (
    INTEREST_NAMES,
    CatalogResponse,
    InterestCode,
    InterestsUpdateRequest,
    MyInterestsResponse,
)
from support import HttpClient, alembic_config, as_client

PASSWORD = "Str0ng!Passw0rd-xyz"  # noqa: S105 - 테스트 전용 가짜 비밀번호

# README 6.2절 표를 그대로 옮긴 기대값. 코드 철자가 바뀌면 이 테스트가 깨진다.
EXPECTED_CODES = [
    "ai.models",
    "ai.agents",
    "ai.devtools",
    "ai.opensource",
    "ai.infra",
    "economy.industry",
    "economy.business",
    "economy.startups",
    "economy.markets",
    "economy.jobs",
    "society.policy",
    "society.education",
    "society.health",
    "society.climate",
    "society.culture",
]


def client_for(settings: Settings) -> HttpClient:
    """테스트 DB를 쓰는 앱의 클라이언트를 만든다."""
    return as_client(create_app(settings))


def signup_body(email: str = "usera@example.com", **extra: object) -> Mapping[str, object]:
    """가입 요청 본문을 만든다."""
    return {
        "email": email,
        "password": PASSWORD,
        "password_confirm": PASSWORD,
        "terms_accepted": True,
    } | extra


def sign_up(
    client: HttpClient, email: str = "usera@example.com", **extra: object
) -> dict[str, str]:
    """가입시키고 Authorization 헤더를 돌려준다."""
    response = client.request("POST", "/v1/auth/signup", json=signup_body(email, **extra))
    assert response.status_code == 201, response.text
    token = AuthResponse.model_validate_json(response.text).tokens.access_token
    return {"Authorization": f"Bearer {token}"}


def codes_of(text: str) -> list[str]:
    """내 관심사 응답에서 코드만 뽑는다."""
    return [item.code.value for item in MyInterestsResponse.model_validate_json(text).interests]


def test_enum_matches_readme_table() -> None:
    """관심사 코드 15개가 README 6.2절 표와 철자·순서까지 같다."""
    assert [code.value for code in InterestCode] == EXPECTED_CODES
    assert set(INTEREST_NAMES) == set(InterestCode)


def test_catalog_is_public_and_grouped(settings: Settings) -> None:
    """카탈로그는 로그인 없이 대주제 3개·소주제 15개를 code·name·group과 함께 준다."""
    response = client_for(settings).request("GET", "/v1/interests/catalog")
    assert response.status_code == 200
    catalog = CatalogResponse.model_validate_json(response.text)
    assert [g.group for g in catalog.groups] == ["ai", "economy", "society"]
    assert [len(g.interests) for g in catalog.groups] == [5, 5, 5]
    first = catalog.groups[0].interests[1]
    assert (first.code.value, first.name, first.group) == ("ai.agents", "AI 에이전트", "ai")


def test_my_interests_requires_login(settings: Settings) -> None:
    """토큰 없이 조회·수정하면 401이다."""
    client = client_for(settings)
    assert client.request("GET", "/v1/me/interests").status_code == 401
    put = client.request("PUT", "/v1/me/interests", json={"interests": []})
    assert put.status_code == 401


def test_new_user_has_no_interests(settings: Settings) -> None:
    """관심사 없이 가입하면 내 관심사는 빈 목록이다(기존 가입 요청 호환)."""
    client = client_for(settings)
    headers = sign_up(client)
    response = client.request("GET", "/v1/me/interests", headers=headers)
    assert response.status_code == 200
    assert codes_of(response.text) == []


def test_signup_with_interests_saves_them(settings: Settings) -> None:
    """가입 때 보낸 관심사가 저장되고 카탈로그 순서로 조회된다."""
    client = client_for(settings)
    headers = sign_up(client, interests=["economy.jobs", "ai.models"])
    response = client.request("GET", "/v1/me/interests", headers=headers)
    assert codes_of(response.text) == ["ai.models", "economy.jobs"]


@pytest.mark.parametrize(
    "bad",
    [
        ["ai.unknown"],
        ["ai.models", "ai.models"],
        [*EXPECTED_CODES, "ai.models"],
        ["AI.MODELS"],
        [1],
    ],
)
def test_signup_rejects_bad_interests_without_creating_user(
    settings: Settings, bad: list[object]
) -> None:
    """가입 요청의 잘못된 관심사는 422이고 사용자가 만들어지지 않는다."""
    client = client_for(settings)
    response = client.request("POST", "/v1/auth/signup", json=signup_body(interests=bad))
    assert response.status_code == 422
    conn = connect(settings.database_url)
    try:
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone() == (0,)
    finally:
        conn.close()


def test_put_replaces_all_and_is_idempotent(settings: Settings) -> None:
    """PUT은 전체 교체이고 같은 요청을 반복해도 결과가 같다. 빈 목록은 선택 해제다."""
    client = client_for(settings)
    headers = sign_up(client, interests=["ai.models"])
    body = {"interests": ["society.health", "ai.agents"]}
    first = client.request("PUT", "/v1/me/interests", json=body, headers=headers)
    second = client.request("PUT", "/v1/me/interests", json=body, headers=headers)
    assert codes_of(first.text) == codes_of(second.text) == ["ai.agents", "society.health"]
    cleared = client.request("PUT", "/v1/me/interests", json={"interests": []}, headers=headers)
    assert codes_of(cleared.text) == []
    after = client.request("GET", "/v1/me/interests", headers=headers)
    assert codes_of(after.text) == []


def test_put_accepts_all_fifteen(settings: Settings) -> None:
    """15개 전체 선택은 허용한다(상한 경계)."""
    client = client_for(settings)
    headers = sign_up(client)
    response = client.request(
        "PUT", "/v1/me/interests", json={"interests": EXPECTED_CODES}, headers=headers
    )
    assert response.status_code == 200
    assert codes_of(response.text) == EXPECTED_CODES


@pytest.mark.parametrize(
    "bad",
    [["ai.unknown"], ["ai.models", "ai.models"], [*EXPECTED_CODES, "ai.models"], "ai.models", None],
)
def test_put_rejects_bad_values_and_keeps_previous(settings: Settings, bad: object) -> None:
    """잘못된 값은 422이고 이전에 저장한 관심사는 그대로다."""
    client = client_for(settings)
    headers = sign_up(client, interests=["ai.models"])
    response = client.request("PUT", "/v1/me/interests", json={"interests": bad}, headers=headers)
    assert response.status_code == 422
    assert ErrorResponse.model_validate_json(response.text).code == "VALIDATION_ERROR"
    kept = client.request("GET", "/v1/me/interests", headers=headers)
    assert codes_of(kept.text) == ["ai.models"]


def test_put_rejects_unknown_field(settings: Settings) -> None:
    """본문에 user_id 같은 다른 필드를 넣으면 422다(남의 관심사를 지정할 수 없다)."""
    client = client_for(settings)
    headers = sign_up(client)
    response = client.request(
        "PUT", "/v1/me/interests", json={"interests": [], "user_id": "other"}, headers=headers
    )
    assert response.status_code == 422


def test_users_are_isolated(settings: Settings) -> None:
    """한 사용자의 수정이 다른 사용자의 관심사에 영향을 주지 않는다."""
    client = client_for(settings)
    a = sign_up(client, "usera@example.com", interests=["ai.models"])
    b = sign_up(client, "userb@example.com", interests=["society.health"])
    client.request("PUT", "/v1/me/interests", json={"interests": ["ai.infra"]}, headers=a)
    other = client.request("GET", "/v1/me/interests", headers=b)
    assert codes_of(other.text) == ["society.health"]


def test_withdraw_deletes_interests(settings: Settings) -> None:
    """탈퇴하면 그 사용자의 관심사만 함께 삭제된다(UT-DB-009 확장)."""
    client = client_for(settings)
    a = sign_up(client, "usera@example.com", interests=["ai.models", "ai.infra"])
    sign_up(client, "userb@example.com", interests=["society.health"])
    done = client.request("DELETE", "/v1/me", json={"password": PASSWORD}, headers=a)
    assert done.status_code == 200
    conn = connect(settings.database_url)
    try:
        rows = conn.execute("SELECT interest_code FROM user_interests").fetchall()
    finally:
        conn.close()
    assert [tuple(r) for r in rows] == [("society.health",)]


def test_request_models_reject_bad_values() -> None:
    """요청 모델 자체가 중복·초과·모르는 코드를 거부한다."""
    with pytest.raises(ValidationError):
        InterestsUpdateRequest.model_validate({"interests": ["ai.models", "ai.models"]})
    with pytest.raises(ValidationError):
        InterestsUpdateRequest.model_validate({"interests": [*EXPECTED_CODES, "ai.models"]})
    with pytest.raises(ValidationError):
        SignupRequest.model_validate(signup_body(interests=["nope"]))
    assert InterestsUpdateRequest.model_validate({}).interests == []


def test_primary_key_blocks_duplicate_rows(settings: Settings) -> None:
    """DB 기본키가 같은 (사용자, 코드)의 중복 저장을 막는다."""
    client = client_for(settings)
    headers = sign_up(client, interests=["ai.models"])
    assert headers
    conn = connect(settings.database_url)
    try:
        row = conn.execute("SELECT id FROM users").fetchone()
        assert row is not None
        user_id = str(row[0])
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO user_interests (user_id, interest_code) VALUES (?, 'ai.models')",
                (user_id,),
            )
    finally:
        conn.close()


def test_interest_migration_downgrade_keeps_auth_working(db_url: str) -> None:
    """0002만 되돌려도 users·refresh_tokens는 남고 가입·로그인 테이블은 그대로다(독립 모듈)."""
    command.downgrade(alembic_config(db_url), "0001_users")
    conn = connect(db_url)
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()
    assert "user_interests" not in tables
    assert {"users", "refresh_tokens"} <= tables
    command.upgrade(alembic_config(db_url), "head")

"""src/dait 앱 종단간 흐름 통합 테스트 (IT-AUTH-HOME / IT-SET / IT-SCH 핵심 경로).

가입→로그인→뉴스 목록/상세→설정 저장→예약 CRUD→세션→로그아웃→탈퇴까지
실제 마이그레이션 DB와 HTTP 계약을 통과하는지 검증한다.
"""

import sqlite3
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import pytest

from dait.core.config import Settings
from dait.main import create_app
from src.server import create_app as create_unified_app
from support import HttpClient, as_client

PASSWORD = "It3gr@tion-Passw0rd!"  # noqa: S105 - 테스트 전용 가짜 비밀번호
EMAIL = "flow@example.com"
NOW = datetime(2026, 1, 1, tzinfo=UTC).isoformat()


def client_for(settings: Settings) -> HttpClient:
    return as_client(create_app(settings))


def _db_path(db_url: str) -> str:
    return db_url.removeprefix("sqlite:///")


def seed_minimum(db_url: str) -> None:
    """공개 가능한 기사 1건과 출처를 넣는다."""
    conn = sqlite3.connect(_db_path(db_url))
    try:
        conn.execute(
            "INSERT INTO sources (id, name, kind, base_url, priority, enabled, "
            "created_at, updated_at) VALUES ('src1', '통합통신', 'RSS', "
            "'https://example.com/feed', 10, 1, ?, ?)",
            (NOW, NOW),
        )
        conn.execute(
            "INSERT INTO news (id, source_id, title, canonical_url, published_at, "
            "collected_at, category, original_language, created_at) "
            "VALUES ('n1', 'src1', '통합 테스트 기사', 'https://example.com/a1', ?, ?, "
            "'AI', 'ko', ?)",
            (NOW, NOW, NOW),
        )
        conn.execute(
            "INSERT INTO content_results (news_id, extracted_text, translated_text, "
            "summary_lines, status, prompt_version, model_id, processed_at, updated_at) "
            "VALUES ('n1', '본문', '번역', '[\"요약1\",\"요약2\",\"요약3\"]', 'READY', "
            "'pv1', 'm1', ?, ?)",
            (NOW, NOW),
        )
        conn.commit()
    finally:
        conn.close()


def signup(client: HttpClient, email: str = EMAIL) -> dict[str, Any]:
    response = client.request(
        "POST",
        "/v1/auth/signup",
        json={
            "email": email,
            "password": PASSWORD,
            "password_confirm": PASSWORD,
            "terms_accepted": True,
        },
    )
    assert response.status_code == 201
    return response.json()


def auth(token: str) -> Mapping[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_unified_entrypoint(settings: Settings, db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """The root factory serves UI, auth, interests, settings and one shared news DB."""
    monkeypatch.setattr("dait.main.get_settings", lambda: settings)
    seed_minimum(db_url)
    app = create_unified_app()
    client = as_client(app)
    home = client.request("GET", "/")
    assert home.status_code == 200
    assert "script-src 'self'" in home.headers["content-security-policy"]
    assert client.request("GET", "/app.js").status_code == 200
    assert client.request("GET", "/mockup/mockup.css").status_code == 200
    assert client.request("GET", "/settings.html").status_code == 200
    assert client.request("GET", "/detail.html").status_code == 404
    assert client.request("GET", "/v1/news").json()["items"][0]["id"] == "n1"
    assert client.request("GET", "/v1/news/n1").status_code == 200
    assert client.request("GET", "/v1/interests/catalog").status_code == 200
    body = signup(client)
    headers = auth(body["tokens"]["access_token"])
    assert client.request("GET", "/v1/me/session", headers=headers).status_code == 200
    assert client.request("GET", "/v1/me/settings", headers=headers).status_code == 200
    assert client.request("GET", "/v1/me/interests", headers=headers).status_code == 200
    assert client.request("GET", "/v1/me/schedules", headers=headers).status_code == 200


def test_full_user_journey(settings: Settings, db_url: str) -> None:
    """가입→로그인→뉴스→설정→예약→로그아웃→탈퇴 전체 흐름."""
    seed_minimum(db_url)
    client = client_for(settings)

    # 1. 비인증 보호 API는 401
    assert client.request("GET", "/v1/me/settings").status_code == 401

    # 2. 가입 → 토큰 발급
    body = signup(client)
    access = body["tokens"]["access_token"]
    assert body["user"]["email"] == EMAIL

    # 3. 세션 확인
    me = client.request("GET", "/v1/me/session", headers=auth(access))
    assert me.status_code == 200
    assert me.json()["user"]["email"] == EMAIL

    # 4. 뉴스 목록·상세
    news = client.request("GET", "/v1/news", params={"category": "AI"})
    assert news.status_code == 200
    items = news.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "통합 테스트 기사"
    detail = client.request("GET", f"/v1/news/{items[0]['id']}")
    assert detail.status_code == 200
    assert len(detail.json()["content"]["summary_lines"]) == 3

    # 5. 설정 조회→수정→재조회
    got = client.request("GET", "/v1/me/settings", headers=auth(access))
    assert got.status_code == 200
    patched = client.request(
        "PATCH",
        "/v1/me/settings",
        headers=auth(access),
        json={"default_count": 5, "in_app_notice": False},
    )
    assert patched.status_code == 200
    assert patched.json()["default_count"] == 5
    again = client.request("GET", "/v1/me/settings", headers=auth(access))
    assert again.json()["default_count"] == 5

    # 6. 예약 생성→조회→삭제
    sch = client.request(
        "POST",
        "/v1/me/schedules",
        headers=auth(access),
        json={
            "local_time": "08:30",
            "timezone": "Asia/Seoul",
            "enabled": True,
            "criteria": {"keywords": ["AI"], "categories": ["AI"], "source_ids": []},
        },
    )
    assert sch.status_code == 201, sch.text
    schedule_id = sch.json()["id"]
    assert sch.json()["next_run_at"] is not None
    listing = client.request("GET", "/v1/me/schedules", headers=auth(access))
    assert len(listing.json()["items"]) == 1
    deleted = client.request("DELETE", f"/v1/me/schedules/{schedule_id}", headers=auth(access))
    assert deleted.status_code == 204

    # 7. 로그아웃 → refresh 세션 폐기(access 토큰은 단명 만료까지 유효)
    login2 = client.request("POST", "/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert login2.status_code == 200
    tokens2 = login2.json()["tokens"]
    rt = tokens2["refresh_token"]
    logout = client.request("POST", "/v1/auth/logout", headers=auth(tokens2["access_token"]))
    assert logout.status_code in (200, 204)
    assert client.request("POST", "/v1/auth/refresh", json={"refresh_token": rt}).status_code == 401


def test_login_refresh_logout_cycle(settings: Settings, db_url: str) -> None:
    """로그인→refresh 회전→재사용 탐지→로그아웃."""
    client = client_for(settings)
    signup(client)

    login = client.request("POST", "/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert login.status_code == 200
    tokens = login.json()["tokens"]

    refreshed = client.request(
        "POST", "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200
    new_tokens = refreshed.json()

    # 이전 refresh 재사용은 거부되어야 한다(재사용 탐지)
    reuse = client.request(
        "POST", "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert reuse.status_code == 401

    out = client.request("POST", "/v1/auth/logout", headers=auth(new_tokens["access_token"]))
    assert out.status_code in (200, 204)
    # 로그아웃은 refresh 세션을 폐기한다. access 토큰은 만료 전까지 유효하다(단명 설계).
    again = client.request(
        "POST", "/v1/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]}
    )
    assert again.status_code == 401


def test_account_deletion_removes_user(settings: Settings, db_url: str) -> None:
    """탈퇴는 비밀번호 재인증 후 계정과 세션을 지운다."""
    client = client_for(settings)
    signup(client, "bye@example.com")
    login = client.request(
        "POST", "/v1/auth/login", json={"email": "bye@example.com", "password": PASSWORD}
    )
    token = login.json()["tokens"]["access_token"]

    wrong = client.request(
        "DELETE",
        "/v1/me",
        headers=auth(token),
        json={"password": "wrong-password-1"},
    )
    assert wrong.status_code in (400, 401, 403, 422)

    deleted = client.request("DELETE", "/v1/me", headers=auth(token), json={"password": PASSWORD})
    assert deleted.status_code == 200
    session = client.request("GET", "/v1/me/session", headers=auth(token))
    assert session.status_code == 200
    assert session.json()["authenticated"] is False

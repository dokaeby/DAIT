"""First-login invitation is account-scoped and consumed only on successful login."""

import sqlite3

from dait.core.config import Settings
from dait.main import create_app
from dait.repositories.user_repository import delete_user
from support import as_client


def test_invitation_once_after_successful_login(settings: Settings) -> None:
    """Signup does not consume the invitation; a failed login does not consume it either."""
    client = as_client(create_app(settings))
    password = "Str0ng!Passw0rd-xyz"  # noqa: S105 - isolated fixture only
    signup = client.request(
        "POST",
        "/v1/auth/signup",
        json={
            "email": "onboarding@example.com",
            "password": password,
            "password_confirm": password,
            "terms_accepted": True,
        },
    )
    assert signup.status_code == 201
    assert signup.json()["onboarding_required"] is False
    failed = client.request(
        "POST", "/v1/auth/login", json={"email": "onboarding@example.com", "password": "wrong"}
    )
    assert failed.status_code == 401
    for expected in (True, False):
        login = client.request(
            "POST", "/v1/auth/login", json={"email": "onboarding@example.com", "password": password}
        )
        assert login.status_code == 200
        assert login.json()["onboarding_required"] is expected


def test_account_deletion_removes_only_owned_schedule_jobs() -> None:
    """RESTRICT 예약 작업이 있는 계정도 삭제하고 다른 사용자의 작업은 남긴다."""
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("CREATE TABLE users (id TEXT PRIMARY KEY)")
        conn.execute(
            "CREATE TABLE schedules (id TEXT PRIMARY KEY, "
            "user_id TEXT REFERENCES users(id) ON DELETE CASCADE)"
        )
        conn.execute(
            "CREATE TABLE jobs (id TEXT PRIMARY KEY, "
            "schedule_id TEXT REFERENCES schedules(id) ON DELETE RESTRICT)"
        )
        conn.executemany("INSERT INTO users VALUES (?)", [("u1",), ("u2",)])
        conn.executemany("INSERT INTO schedules VALUES (?, ?)", [("s1", "u1"), ("s2", "u2")])
        conn.executemany("INSERT INTO jobs VALUES (?, ?)", [("j1", "s1"), ("j2", "s2")])
        assert delete_user(conn, "u1") is True
        assert conn.execute("SELECT id FROM users").fetchall() == [("u2",)]
        assert conn.execute("SELECT id FROM jobs").fetchall() == [("j2",)]
    finally:
        conn.close()


def test_schedule_limit_five(settings: Settings) -> None:
    """여섯 번째 예약은 API에서도 거부한다."""
    client = as_client(create_app(settings))
    password = "Str0ng!Passw0rd-xyz"  # noqa: S105 - isolated fixture only
    signup = client.request(
        "POST",
        "/v1/auth/signup",
        json={
            "email": "schedule@example.com",
            "password": password,
            "password_confirm": password,
            "terms_accepted": True,
        },
    )
    assert signup.status_code == 201
    headers = {"Authorization": "Bearer " + signup.json()["tokens"]["access_token"]}
    for hour in range(6):
        response = client.request(
            "POST",
            "/v1/me/schedules",
            headers=headers,
            json={
                "local_time": f"{hour:02d}:00",
                "timezone": "Asia/Seoul",
                "enabled": True,
                "criteria": {"categories": ["AI"], "source_ids": [], "keywords": []},
            },
        )
        assert response.status_code == (201 if hour < 5 else 422)

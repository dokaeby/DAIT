import json

import pytest

from app.database import connect, initialize_database
from app.main import create_app
from tests.client import ASGIClient


def make_client(tmp_path):
    db_path = tmp_path / "dait.db"
    initialize_database(db_path)
    return db_path, ASGIClient(create_app(db_path=db_path))


def test_settings_get_patch_and_reload(tmp_path):
    db_path, client = make_client(tmp_path)

    initial = client.get("/v1/me/settings")
    updated = client.patch(
        "/v1/me/settings",
        json={"default_count": 5, "in_app_notice": False, "email_notice": True},
    )
    reloaded = ASGIClient(create_app(db_path=db_path)).get("/v1/me/settings")

    assert initial.status_code == 200
    assert initial.json()["default_count"] == 10
    assert updated.status_code == 200
    assert updated.json()["default_count"] == 5
    assert reloaded.json()["in_app_notice"] is False
    assert reloaded.json()["email_notice"] is True


def test_settings_normalizes_keywords_and_validates_sources(tmp_path):
    _, client = make_client(tmp_path)

    response = client.patch(
        "/v1/me/settings",
        json={
            "keywords": ["  멀티모달  ", "AI 에이전트", "멀티모달", ""],
            "source_ids": ["src_anthropic", "src_openai", "src_anthropic"],
            "categories": ["AI"],
        },
    )
    invalid = client.patch("/v1/me/settings", json={"source_ids": ["src_unknown"]})

    assert response.status_code == 200
    assert response.json()["keywords"] == ["멀티모달", "AI 에이전트"]
    assert response.json()["source_ids"] == ["src_anthropic", "src_openai"]
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "VALIDATION_ERROR"


def test_settings_empty_and_extra_patch_rejected(tmp_path):
    _, client = make_client(tmp_path)

    empty = client.patch("/v1/me/settings", json={})
    extra = client.patch("/v1/me/settings", json={"theme": "dark"})
    bad_count = client.patch("/v1/me/settings", json={"default_count": 7})

    assert empty.status_code == 422
    assert extra.status_code == 422
    assert bad_count.status_code == 422
    assert all(response.json()["code"] == "VALIDATION_ERROR" for response in (empty, extra, bad_count))


@pytest.mark.parametrize(
    "field",
    ["default_count", "keywords", "source_ids", "categories", "in_app_notice", "email_notice"],
)
def test_settings_patch_rejects_explicit_null_without_changing_storage(tmp_path, field):
    _, client = make_client(tmp_path)
    before = client.get("/v1/me/settings").json()

    response = client.patch("/v1/me/settings", json={field: None})

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert client.get("/v1/me/settings").json() == before


def test_schedule_create_update_list_delete(tmp_path):
    _, client = make_client(tmp_path)
    payload = {
        "local_time": "09:15",
        "timezone": "Asia/Seoul",
        "enabled": True,
        "criteria": {
            "keywords": ["멀티모달"],
            "source_ids": ["src_openai"],
            "categories": ["AI"],
        },
    }

    created = client.post("/v1/me/schedules", json=payload)
    schedule_id = created.json()["id"]
    updated = client.patch(
        f"/v1/me/schedules/{schedule_id}",
        json={"local_time": "10:00", "enabled": False},
    )
    listed = client.get("/v1/me/schedules")
    deleted = client.delete(f"/v1/me/schedules/{schedule_id}")
    missing = client.patch(f"/v1/me/schedules/{schedule_id}", json={"enabled": True})

    assert created.status_code == 201
    assert created.json()["timezone"] == "Asia/Seoul"
    assert updated.status_code == 200
    assert updated.json()["local_time"] == "10:00"
    assert updated.json()["enabled"] is False
    assert schedule_id in {item["id"] for item in listed.json()["items"]}
    assert deleted.status_code == 204
    assert missing.status_code == 404


def test_schedule_validation_and_extra_fields(tmp_path):
    _, client = make_client(tmp_path)
    base = {
        "local_time": "08:30",
        "timezone": "Asia/Seoul",
        "criteria": {"keywords": [], "source_ids": [], "categories": ["AI"]},
    }
    cases = [
        {**base, "local_time": "25:00"},
        {**base, "timezone": "UTC"},
        {**base, "criteria": {**base["criteria"], "categories": ["TECH"]}},
        {**base, "criteria": {**base["criteria"], "source_ids": ["src_unknown"]}},
        {**base, "unexpected": True},
    ]

    for payload in cases:
        response = client.post("/v1/me/schedules", json=payload)
        assert response.status_code == 422
        assert response.json()["code"] == "VALIDATION_ERROR"

    assert client.patch("/v1/me/schedules/sch_demo_0830", json={}).status_code == 422


@pytest.mark.parametrize("field", ["local_time", "timezone", "enabled", "criteria"])
def test_schedule_patch_rejects_explicit_null_without_changing_storage(tmp_path, field):
    _, client = make_client(tmp_path)
    before = client.get("/v1/me/schedules").json()

    response = client.patch("/v1/me/schedules/sch_demo_0830", json={field: None})

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert client.get("/v1/me/schedules").json() == before


def test_deleted_seed_schedule_stays_deleted_after_restart(tmp_path):
    db_path, client = make_client(tmp_path)
    assert client.delete("/v1/me/schedules/sch_demo_0830").status_code == 204

    restarted = ASGIClient(create_app(db_path=db_path))

    assert restarted.get("/v1/me/schedules").json() == {"items": []}


def test_schedule_is_scoped_to_demo_user(tmp_path):
    db_path, client = make_client(tmp_path)
    now = "2026-11-06T00:00:00Z"
    with connect(db_path) as connection:
        connection.execute(
            "INSERT INTO users VALUES (?, ?, NULL, 'ACTIVE', ?, ?, NULL)",
            ("usr_other", "other@dait.local", now, now),
        )
        connection.execute(
            "INSERT INTO schedules VALUES (?, ?, '11:00', 'Asia/Seoul', 1, ?, NULL, ?, ?)",
            (
                "sch_other_1100",
                "usr_other",
                json.dumps({"keywords": [], "source_ids": [], "categories": ["AI"]}),
                now,
                now,
            ),
        )

    update = client.patch("/v1/me/schedules/sch_other_1100", json={"enabled": False})
    delete = client.delete("/v1/me/schedules/sch_other_1100")
    with connect(db_path) as connection:
        enabled = connection.execute(
            "SELECT enabled FROM schedules WHERE id = ?", ("sch_other_1100",)
        ).fetchone()[0]

    assert update.status_code == 404
    assert delete.status_code == 404
    assert enabled == 1

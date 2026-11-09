import pytest
from fastapi.testclient import TestClient

from backend import users
from backend.main import app


@pytest.fixture
def client():
    with TestClient(app) as value:
        yield value


@pytest.mark.ut("UT-AUTH-003")
def test_invalid_signup_does_not_create_member(client):
    response = client.post(
        "/signup",
        data=dict(user="usr_test_a", password="abcde", password_confirm="other"),
    )
    assert response.status_code == 422
    assert users.authenticate_member("usr_test_a", "abcde") is None
    assert "abcde" not in response.text and "other" not in response.text


@pytest.mark.ut("UT-AUTH-007")
def test_login_errors_are_identical(client):
    users.create_user("usr_test_a", "abcde")
    first = client.post(
        "/login", data=dict(user="usr_test_a", password="wrong"), follow_redirects=False
    )
    second = client.post(
        "/login", data=dict(user="missing", password="wrong"), follow_redirects=False
    )
    assert first.status_code == second.status_code == 401
    assert first.json() == second.json()
    assert "wrong" not in first.text


@pytest.mark.ut("UT-AUTH-010")
def test_logout_revokes_session_and_is_idempotent(client):
    users.create_user("usr_test_a", "abcde")
    response = client.post(
        "/login", data=dict(user="usr_test_a", password="abcde"), follow_redirects=False
    )
    assert response.status_code == 303
    token = client.cookies.get("dait_session")
    assert users.session_identity(token) is not None
    assert client.post("/logout", follow_redirects=False).status_code == 303
    assert users.session_identity(token) is None
    assert client.post("/logout", follow_redirects=False).status_code == 303


@pytest.mark.extension
def test_same_account_login_keeps_existing_session(client):
    users.create_user("usr_test_a", "abcde")
    payload = dict(user="usr_test_a", password="abcde")
    client.post("/login", data=payload, follow_redirects=False)
    token = client.cookies.get("dait_session")
    response = client.post("/login", data=payload, follow_redirects=False)
    assert response.status_code == 409
    assert "이미 로그인" in response.json()["error"]
    assert client.cookies.get("dait_session") == token


@pytest.mark.ut("UT-AUTH-001")
@pytest.mark.spec_gap
def test_document_signup_creates_initial_session(client):
    response = client.post(
        "/signup",
        data=dict(user="usr_test_a", password="abcde", password_confirm="abcde"),
    )
    assert response.status_code == 201
    assert client.cookies.get("dait_session") is not None


@pytest.mark.ut("UT-DETAIL-008")
def test_missing_article_status(client):
    response = client.get("/article/news_missing_999?format=json")
    assert response.status_code == 404
    assert "error" in response.json()


@pytest.mark.ut("UT-DETAIL-008")
@pytest.mark.spec_gap
def test_document_missing_article_error_code(client):
    response = client.get("/article/news_missing_999?format=json")
    assert response.json().get("code") == "NEWS_NOT_FOUND"

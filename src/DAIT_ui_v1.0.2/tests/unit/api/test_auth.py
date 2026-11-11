import pytest
from fastapi.testclient import TestClient

from backend import users
from backend.main import app


# 기능: 네트워크 없이 요청할 FastAPI 테스트 클라이언트를 준비한다.
# 입력: 없음.
# 출력: TestClient를 yield하고 종료 시 자원을 정리한다.
@pytest.fixture
def client():
    with TestClient(app) as value:
        yield value


# 기능: 잘못된 가입 요청의 회원 생성 방지 동작을 검증한다.
# 입력:
#   client: 인메모리 FastAPI 테스트 클라이언트.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-AUTH-003")
def test_invalid_signup_does_not_create_member(client):
    response = client.post(
        "/signup",
        data=dict(nickname="Tester", user="usr_test_a", password="abcde", password_confirm="other"),
    )
    assert response.status_code == 422
    assert users.authenticate_member("usr_test_a", "abcde") is None
    assert "abcde" not in response.text and "other" not in response.text


# 기능: 인증 실패 응답의 일관성 동작을 검증한다.
# 입력:
#   client: 인메모리 FastAPI 테스트 클라이언트.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
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


# 기능: 세션 폐기와 반복 로그아웃 동작을 검증한다.
# 입력:
#   client: 인메모리 FastAPI 테스트 클라이언트.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
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


# 기능: 동일 계정 중복 로그인 시 기존 세션 유지 동작을 검증한다.
# 입력:
#   client: 인메모리 FastAPI 테스트 클라이언트.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
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


# 기능: 가입 직후 세션 생성 요구사항 동작을 검증한다.
# 입력:
#   client: 인메모리 FastAPI 테스트 클라이언트.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-AUTH-001")
@pytest.mark.spec_gap
def test_document_signup_creates_initial_session(client):
    response = client.post(
        "/signup",
        data=dict(nickname="Tester", user="usr_test_a", password="abcde", password_confirm="abcde"),
    )
    assert response.status_code == 201
    assert client.cookies.get("dait_session") is not None


# 기능: 없는 기사 상태 코드 동작을 검증한다.
# 입력:
#   client: 인메모리 FastAPI 테스트 클라이언트.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-DETAIL-008")
def test_missing_article_status(client):
    response = client.get("/article/news_missing_999?format=json")
    assert response.status_code == 404
    assert "error" in response.json()


# 기능: 없는 기사 오류 코드 요구사항 동작을 검증한다.
# 입력:
#   client: 인메모리 FastAPI 테스트 클라이언트.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-DETAIL-008")
@pytest.mark.spec_gap
def test_document_missing_article_error_code(client):
    response = client.get("/article/news_missing_999?format=json")
    assert response.json().get("code") == "NEWS_NOT_FOUND"


# 기능: 가입 닉네임의 로그인 후 화면 표시 동작을 검증한다.
# 입력:
#   client: 인메모리 FastAPI 테스트 클라이언트.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.extension
def test_signup_nickname_is_shown_after_login(client):
    response = client.post("/signup", data=dict(nickname="홍길동", user="member123", password="abcde", password_confirm="abcde"))
    assert response.status_code == 201
    client.post("/login", data=dict(user="member123", password="abcde"), follow_redirects=False)
    page = client.get("/")
    assert "홍길동님" in page.text
    assert 'id="login-open"' not in page.text


# 기능: 중복 닉네임 거부 동작을 검증한다.
# 입력:
#   client: 인메모리 FastAPI 테스트 클라이언트.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.extension
def test_duplicate_nickname_is_rejected(client):
    first = dict(nickname="홍길동", user="first", password="abcde", password_confirm="abcde")
    assert client.post("/signup", data=first).status_code == 201
    response = client.post("/signup", data={**first, "user": "second", "nickname": " 홍길동 "})
    assert response.status_code == 409
    assert "nickname" in response.json()["field_errors"]


# 기능: 닉네임 없는 기존 회원의 대체 표시 동작을 검증한다.
# 입력:
#   client: 인메모리 FastAPI 테스트 클라이언트.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.extension
def test_existing_member_without_nickname_has_fallback(client):
    users.create_user("old_member", "abcde")
    client.post("/login", data=dict(user="old_member", password="abcde"), follow_redirects=False)
    page = client.get("/")
    assert "회원님" in page.text
    assert "old_member 로그인 중" not in page.text

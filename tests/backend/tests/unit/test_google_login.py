"""구글 로그인: 가짜 구글로 네트워크 없이 흐름·보안 거부 경우를 검증한다."""

import base64
import hashlib
import sqlite3
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from pydantic import ValidationError

from conftest import TEST_JWT_SECRET
from dait.api.deps import get_google_client
from dait.core.config import AppEnv, Settings
from dait.core.errors import ErrorResponse
from dait.core.security import create_access_token
from dait.main import create_app
from dait.repositories.one_time_store import OneTimeStore
from dait.schemas.auth import AuthResponse
from dait.services.google_client import GoogleUnavailableError
from support import HttpClient, as_client

CLIENT_ID = "test-client-id.apps.googleusercontent.com"
REDIRECT = "http://localhost:8000/v1/auth/google/callback"
SUB = "google-sub-1"
EMAIL = "Person@Example.com"
PASSWORD = "Str0ng!Passw0rd-xyz"  # noqa: S105 - 테스트 전용 가짜 비밀번호
LONG_CODE = "x" * 43


class FakeGoogle:
    """구글 token 엔드포인트를 흉내 낸다. 받은 코드·verifier를 기록한다."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.fail = False
        self.nonce = ""
        self.overrides: dict[str, object] = {}

    def fetch_id_token(self, code: str, code_verifier: str) -> str:
        """설정에 따라 정상 id_token을 만들거나 장애를 낸다."""
        self.calls.append((code, code_verifier))
        if self.fail:
            raise GoogleUnavailableError
        claims: dict[str, object] = {
            "iss": "https://accounts.google.com",
            "aud": CLIENT_ID,
            "sub": SUB,
            "exp": int(time.time()) + 300,
            "nonce": self.nonce,
            "email": EMAIL,
            "email_verified": True,
        } | self.overrides
        return jwt.encode(claims, "fake-google-signing-key-0123456789-abcdef", algorithm="HS256")


def make_settings(db_url: str, **extra: object) -> Settings:
    """구글 설정이 켜진 debug 테스트 설정을 만든다(http://localhost 허용)."""
    values: dict[str, object] = {
        "database_url": db_url,
        "app_env": AppEnv.DEBUG,
        "google_client_id": CLIENT_ID,
        "google_client_secret": "test-client-secret",
        "google_redirect_uri": REDIRECT,
    } | extra
    return Settings.model_validate(values)


class Flow:
    """앱 한 개와 가짜 구글을 묶고 login → callback을 단계별로 돌린다."""

    def __init__(self, settings: Settings) -> None:
        self.google = FakeGoogle()
        app = create_app(settings)
        app.dependency_overrides[get_google_client] = lambda: self.google
        self.client: HttpClient = as_client(app)

    def login(self) -> tuple[str, dict[str, list[str]]]:
        """로그인을 시작하고 구글로 가는 주소와 그 쿼리를 돌려준다(nonce를 가짜 구글에 알림)."""
        response = self.client.request("GET", "/v1/auth/google/login", follow_redirects=False)
        assert response.status_code == 302
        location = response.headers["location"]
        query = parse_qs(urlparse(location).query)
        self.google.nonce = query["nonce"][0]
        return location, query

    def callback(self, state: str, code: str = "google-auth-code") -> str:
        """구글이 돌려보낸 것처럼 callback을 부르고 Location을 돌려준다."""
        response = self.client.request(
            "GET",
            "/v1/auth/google/callback",
            params={"state": state, "code": code},
            follow_redirects=False,
        )
        assert response.status_code == 302
        return response.headers["location"]

    def full(self) -> str:
        """정상 흐름을 끝까지 돌려 callback의 Location(# 뒤 포함)을 돌려준다."""
        _, query = self.login()
        return self.callback(query["state"][0])


def exchange_code(location: str) -> str:
    """callback Location에서 1회용 교환 코드를 꺼낸다."""
    assert location.startswith("/#google=")
    return location.removeprefix("/#google=")


def count(db: Path, sql: str) -> int:
    """SQL이 돌려주는 첫 숫자 하나를 읽는다."""
    with sqlite3.connect(db) as conn:
        return int(conn.execute(sql).fetchone()[0])


def post_exchange(flow: Flow, code: str) -> tuple[int, str]:
    """교환 코드로 토큰을 요청하고 상태 코드와 본문을 돌려준다."""
    response = flow.client.request("POST", "/v1/auth/google/exchange", json={"code": code})
    return response.status_code, response.text


@pytest.fixture
def flow(db_url: str) -> Flow:
    """구글 설정이 켜진 앱과 가짜 구글."""
    return Flow(make_settings(db_url))


def test_new_google_user_gets_passwordless_account_and_tokens(flow: Flow, tmp_path: Path) -> None:
    """처음 온 구글 사용자는 비밀번호 없는 계정·연결·토큰을 받는다."""
    status, text = post_exchange(flow, exchange_code(flow.full()))
    assert status == 200
    body = AuthResponse.model_validate_json(text)
    assert body.user.email == EMAIL.lower()
    assert body.onboarding_required is True
    assert "id_token" not in text
    db = tmp_path / "test.db"
    assert count(db, "SELECT COUNT(*) FROM users WHERE password_hash IS NULL") == 1
    assert count(db, "SELECT COUNT(*) FROM social_identities") == 1
    session = flow.client.request(
        "GET", "/v1/me/session", headers={"Authorization": f"Bearer {body.tokens.access_token}"}
    )
    assert '"authenticated":true' in session.text.replace(" ", "")


def test_second_google_login_reuses_same_account(flow: Flow, tmp_path: Path) -> None:
    """같은 구글 계정으로 다시 로그인해도 사용자는 한 명이다."""
    post_exchange(flow, exchange_code(flow.full()))
    status, _ = post_exchange(flow, exchange_code(flow.full()))
    assert status == 200
    assert count(tmp_path / "test.db", "SELECT COUNT(*) FROM users") == 1


def test_login_url_has_pkce_state_nonce_and_exact_redirect(flow: Flow) -> None:
    """구글로 가는 주소에 S256 PKCE·state·nonce가 있고 redirect_uri가 설정값 그대로다."""
    location, query = flow.login()
    assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert query["redirect_uri"] == [REDIRECT]
    assert query["client_id"] == [CLIENT_ID]
    assert query["code_challenge_method"] == ["S256"]
    assert query["scope"] == ["openid email"]
    flow.callback(query["state"][0])
    digest = hashlib.sha256(flow.google.calls[0][1].encode()).digest()
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    assert query["code_challenge"] == [expected]


def test_state_cookie_is_httponly_lax(flow: Flow) -> None:
    """state 쿠키는 HttpOnly이고 SameSite=Lax다."""
    response = flow.client.request("GET", "/v1/auth/google/login", follow_redirects=False)
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie


def signup_same_email(flow: Flow) -> None:
    """구글 이메일과 같은 주소로 이메일 가입을 해 둔다."""
    signup = {"email": EMAIL, "password": PASSWORD, "password_confirm": PASSWORD}
    assert flow.client.request("POST", "/v1/auth/signup", json=signup).status_code == 201


def link_ticket(flow: Flow) -> str:
    """같은 이메일 계정이 있을 때 callback이 주는 연결 표를 꺼낸다."""
    location = flow.full()
    assert location.startswith("/#google_link=")
    return location.removeprefix("/#google_link=")


def post_link(flow: Flow, ticket: str, password: str = PASSWORD) -> tuple[int, str]:
    """연결 표와 비밀번호로 연결을 요청한다."""
    response = flow.client.request(
        "POST", "/v1/auth/google/link", json={"ticket": ticket, "password": password}
    )
    return response.status_code, response.text


def test_same_email_account_is_not_merged_automatically(flow: Flow, tmp_path: Path) -> None:
    """같은 이메일 계정이 있어도 자동으로 합치지 않고, 선택용 연결 표만 준다."""
    signup_same_email(flow)
    link_ticket(flow)
    db = tmp_path / "test.db"
    assert count(db, "SELECT COUNT(*) FROM users") == 1
    assert count(db, "SELECT COUNT(*) FROM social_identities") == 0


def test_user_can_decline_link_and_keep_email_login(flow: Flow, tmp_path: Path) -> None:
    """연결하지 않으면 아무것도 바뀌지 않고 이메일 로그인이 그대로 된다."""
    signup_same_email(flow)
    link_ticket(flow)
    login = flow.client.request(
        "POST", "/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    assert login.status_code == 200
    assert count(tmp_path / "test.db", "SELECT COUNT(*) FROM social_identities") == 0


def test_link_with_correct_password_then_google_login_works(flow: Flow, tmp_path: Path) -> None:
    """비밀번호를 맞게 입력해 연결하면 로그인되고, 다음부터는 구글로 바로 로그인된다."""
    signup_same_email(flow)
    status, text = post_link(flow, link_ticket(flow))
    assert status == 200
    first = AuthResponse.model_validate_json(text)
    assert first.user.email == EMAIL.lower()
    db = tmp_path / "test.db"
    assert count(db, "SELECT COUNT(*) FROM social_identities") == 1
    status, text = post_exchange(flow, exchange_code(flow.full()))
    assert status == 200
    assert AuthResponse.model_validate_json(text).user.id == first.user.id
    assert count(db, "SELECT COUNT(*) FROM users") == 1
    again = flow.client.request(
        "POST", "/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    assert again.status_code == 200  # 기존 비밀번호도 계속 쓸 수 있다


def test_wrong_password_does_not_link_but_ticket_survives(flow: Flow, tmp_path: Path) -> None:
    """비밀번호가 틀리면 연결되지 않고 401이며, 같은 표로 다시 입력할 수 있다."""
    signup_same_email(flow)
    ticket = link_ticket(flow)
    status, text = post_link(flow, ticket, "Wrong!Passw0rd-123")
    assert status == 401
    assert ErrorResponse.model_validate_json(text).code == "INVALID_CREDENTIALS"
    assert count(tmp_path / "test.db", "SELECT COUNT(*) FROM social_identities") == 0
    assert post_link(flow, ticket)[0] == 200


def test_repeated_wrong_passwords_lock_the_link(flow: Flow, tmp_path: Path) -> None:
    """틀린 비밀번호가 쌓이면 맞는 비밀번호도 429로 막힌다(무차별 대입 방지)."""
    signup_same_email(flow)
    ticket = link_ticket(flow)
    for _ in range(5):
        assert post_link(flow, ticket, "Wrong!Passw0rd-123")[0] == 401
    status, text = post_link(flow, ticket)
    assert status == 429
    assert ErrorResponse.model_validate_json(text).code == "TOO_MANY_ATTEMPTS"
    assert count(tmp_path / "test.db", "SELECT COUNT(*) FROM social_identities") == 0


def test_link_ticket_is_single_use_and_unknown_is_401(flow: Flow) -> None:
    """연결에 성공한 표는 다시 쓸 수 없고, 모르는 표는 같은 401이다."""
    signup_same_email(flow)
    ticket = link_ticket(flow)
    assert post_link(flow, ticket)[0] == 200
    assert post_link(flow, ticket)[0] == 401
    assert post_link(flow, LONG_CODE)[0] == 401


def test_other_google_account_with_same_email_is_refused(flow: Flow) -> None:
    """이미 구글이 연결된 계정에 다른 구글 계정(sub)이 같은 이메일로 오면 연결을 제안하지 않는다."""
    signup_same_email(flow)
    assert post_link(flow, link_ticket(flow))[0] == 200
    flow.google.overrides = {"sub": "another-google-sub"}
    assert flow.full() == "/#google_error=google_account_mismatch"


def test_passwordless_account_with_same_email_is_refused(flow: Flow) -> None:
    """비밀번호 없는 구글 전용 계정과 이메일이 같은 다른 구글 계정은 연결 대상이 아니다."""
    post_exchange(flow, exchange_code(flow.full()))
    flow.google.overrides = {"sub": "another-google-sub"}
    assert flow.full() == "/#google_error=google_account_mismatch"


def test_one_time_store_peek_keeps_value() -> None:
    """peek은 값을 지우지 않고 TTL이 지나면 없어진다."""
    store = OneTimeStore(None)
    now = datetime.now(UTC)
    store.put("k", "raw", "value", 60, now)
    assert store.peek("k", "raw", now) == "value"
    assert store.peek("k", "raw", now) == "value"
    assert store.peek("k", "raw", now + timedelta(seconds=61)) is None
    assert store.pop("k", "raw", now) == "value"


def test_unverified_google_email_is_rejected(flow: Flow, tmp_path: Path) -> None:
    """구글이 이메일 미인증이라고 하면 가입시키지 않는다."""
    flow.google.overrides = {"email_verified": False}
    assert flow.full() == "/#google_error=email_unverified"
    assert count(tmp_path / "test.db", "SELECT COUNT(*) FROM users") == 0


@pytest.mark.parametrize(
    "overrides",
    [
        {"nonce": "another-nonce-value-1234567890"},
        {"aud": "someone-elses-client-id"},
        {"exp": 1},
        {"iss": "https://evil.example.com"},
    ],
)
def test_bad_id_token_is_rejected(flow: Flow, overrides: dict[str, object], tmp_path: Path) -> None:
    """nonce·aud·exp·iss가 어긋난 id_token은 거부하고 계정을 만들지 않는다."""
    flow.google.overrides = overrides
    assert flow.full() == "/#google_error=invalid_id_token"
    assert count(tmp_path / "test.db", "SELECT COUNT(*) FROM users") == 0


def test_unknown_or_reused_state_is_rejected(flow: Flow) -> None:
    """모르는 state와 이미 쓴 state는 거부한다."""
    flow.login()
    assert flow.callback("unknown-state-value") == "/#google_error=state_invalid"
    _, query = flow.login()  # callback은 쿠키를 지우므로 다시 시작한다
    state = query["state"][0]
    assert flow.callback(state).startswith("/#google=")  # 처음 한 번은 성공
    assert flow.callback(state) == "/#google_error=state_invalid"  # 재사용 거부


def test_cookie_state_mismatch_is_rejected(flow: Flow, db_url: str) -> None:
    """다른 브라우저(쿠키 없음)에서 남의 state를 끼워 넣어도 거부한다(로그인 CSRF)."""
    _, query = flow.login()
    attacker = Flow(make_settings(db_url))  # 쿠키가 비어 있는 다른 클라이언트
    attacker.google.nonce = query["nonce"][0]
    response = attacker.client.request(
        "GET",
        "/v1/auth/google/callback",
        params={"state": query["state"][0], "code": "c"},
        follow_redirects=False,
    )
    assert response.headers["location"] == "/#google_error=state_invalid"


def test_google_outage_creates_nothing(flow: Flow, tmp_path: Path) -> None:
    """구글 장애면 provider_unavailable이고 계정이 생기지 않는다."""
    flow.google.fail = True
    assert flow.full() == "/#google_error=provider_unavailable"
    assert count(tmp_path / "test.db", "SELECT COUNT(*) FROM users") == 0


def test_user_cancel_at_google_returns_access_denied(flow: Flow) -> None:
    """사용자가 구글 화면에서 취소하면 access_denied로 돌아온다."""
    flow.login()
    response = flow.client.request(
        "GET", "/v1/auth/google/callback", params={"error": "access_denied"}, follow_redirects=False
    )
    assert response.headers["location"] == "/#google_error=access_denied"


def test_exchange_code_is_single_use_and_unknown_is_401(flow: Flow) -> None:
    """교환 코드는 한 번만 쓸 수 있고, 모르는 코드는 같은 401이다."""
    code = exchange_code(flow.full())
    assert post_exchange(flow, code)[0] == 200
    again, text = post_exchange(flow, code)
    assert again == 401
    assert ErrorResponse.model_validate_json(text).code == "INVALID_TOKEN"
    assert post_exchange(flow, LONG_CODE)[0] == 401


def test_google_only_account_cannot_password_login(flow: Flow) -> None:
    """비밀번호 없는 계정에 이메일 로그인을 시도하면 일반 401이다."""
    post_exchange(flow, exchange_code(flow.full()))
    response = flow.client.request(
        "POST", "/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    assert response.status_code == 401


def test_logged_in_user_cannot_start_google_login(flow: Flow) -> None:
    """이미 로그인한 요청이 구글 로그인을 시작하면 409다."""
    _, text = post_exchange(flow, exchange_code(flow.full()))
    token = AuthResponse.model_validate_json(text).tokens.access_token
    response = flow.client.request(
        "GET",
        "/v1/auth/google/login",
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=False,
    )
    assert response.status_code == 409


def test_google_only_withdraw_needs_recent_login_and_phrase(flow: Flow, tmp_path: Path) -> None:
    """구글 전용 계정은 로그인 5분 이내 + '탈퇴' 문구일 때만 삭제된다."""
    _, text = post_exchange(flow, exchange_code(flow.full()))
    body = AuthResponse.model_validate_json(text)
    auth = {"Authorization": f"Bearer {body.tokens.access_token}"}
    wrong = flow.client.request("DELETE", "/v1/me", headers=auth, json={"confirm_text": "삭제"})
    assert wrong.status_code == 422  # 허용된 문구가 아니면 형식 단계에서 거부
    nothing = flow.client.request("DELETE", "/v1/me", headers=auth, json={})
    assert nothing.status_code == 403
    stale = create_access_token(
        body.user.id, TEST_JWT_SECRET, 60, datetime.now(UTC) - timedelta(minutes=10)
    )
    old = flow.client.request(
        "DELETE",
        "/v1/me",
        headers={"Authorization": f"Bearer {stale}"},
        json={"confirm_text": "탈퇴"},
    )
    assert old.status_code == 403
    db = tmp_path / "test.db"
    assert count(db, "SELECT COUNT(*) FROM users") == 1
    done = flow.client.request("DELETE", "/v1/me", headers=auth, json={"confirm_text": "탈퇴"})
    assert done.status_code == 200
    assert count(db, "SELECT COUNT(*) FROM users") == 0
    assert count(db, "SELECT COUNT(*) FROM social_identities") == 0


def test_password_account_cannot_withdraw_with_phrase_only(flow: Flow) -> None:
    """비밀번호 계정은 확인 문구만으로 탈퇴할 수 없다."""
    signup = {"email": "p@example.com", "password": PASSWORD, "password_confirm": PASSWORD}
    body = AuthResponse.model_validate_json(
        flow.client.request("POST", "/v1/auth/signup", json=signup).text
    )
    auth = {"Authorization": f"Bearer {body.tokens.access_token}"}
    skipped = flow.client.request("DELETE", "/v1/me", headers=auth, json={"confirm_text": "탈퇴"})
    assert skipped.status_code == 401


def test_disabled_when_unconfigured(db_url: str) -> None:
    """구글 설정이 없으면 세 엔드포인트 모두 404다."""
    client = as_client(create_app(Settings(database_url=db_url)))
    assert client.request("GET", "/v1/auth/google/login", follow_redirects=False).status_code == 404
    callback = client.request("GET", "/v1/auth/google/callback", follow_redirects=False)
    assert callback.status_code == 404
    exchange = client.request("POST", "/v1/auth/google/exchange", json={"code": LONG_CODE})
    assert exchange.status_code == 404


def test_partial_or_insecure_config_refuses_start(db_url: str) -> None:
    """일부만 설정했거나 release에서 http 주소면 시작을 거부한다."""
    with pytest.raises(ValidationError):
        Settings(database_url=db_url, google_client_id=CLIENT_ID)
    with pytest.raises(ValidationError):
        make_settings(db_url, app_env=AppEnv.RELEASE)  # release에서는 https만 허용


def test_one_time_store_pops_once_and_expires() -> None:
    """저장소는 값을 한 번만 돌려주고 TTL이 지나면 없어진다."""
    store = OneTimeStore(None)
    now = datetime.now(UTC)
    store.put("k", "raw", "value", 60, now)
    assert store.pop("k", "raw", now) == "value"
    assert store.pop("k", "raw", now) is None
    store.put("k", "raw", "value", 60, now)
    assert store.pop("k", "raw", now + timedelta(seconds=61)) is None

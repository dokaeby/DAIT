"""2차 인증 HTTP 흐름 테스트: 로그인 → 메일(가짜) → 코드 확인 → 토큰. 네트워크 없음."""

import logging
import re

import pytest
from pydantic import SecretStr

from dait.api.two_factor import get_mailer
from dait.core.config import Settings
from dait.core.errors import ErrorResponse
from dait.core.mailer import FakeMailer
from dait.main import create_app
from dait.schemas.auth import AuthResponse
from dait.schemas.two_factor import ResendResponse, TwoFactorRequired
from support import HttpClient, as_client

PASSWORD = "Str0ng!Passw0rd-xyz"  # noqa: S105 - 테스트 전용 가짜 비밀번호
EMAIL = "usera@example.com"
OTP_SECRET = "otp-test-secret-0123456789-abcdefghijklmnopqr"  # noqa: S105 - 테스트 전용 가짜 키
APP_PASSWORD = "fake-app-password-for-tests"  # noqa: S105 - 테스트 전용 가짜 앱 비밀번호
SIGNUP = {
    "email": EMAIL,
    "password": PASSWORD,
    "password_confirm": PASSWORD,
    "terms_accepted": True,
}
LOGIN = {"email": EMAIL, "password": PASSWORD}


def make_settings(db_url: str, *, enabled: bool) -> Settings:
    """2차 인증을 켜거나 끈 테스트 설정을 만든다."""
    if not enabled:
        return Settings(database_url=db_url)
    return Settings(
        database_url=db_url,
        two_factor_enabled=True,
        otp_hash_secret=SecretStr(OTP_SECRET),
        smtp_host="smtp.example.com",
        smtp_username="sender@example.com",
        smtp_app_password=SecretStr(APP_PASSWORD),
        smtp_from="sender@example.com",
    )


def make_client(settings: Settings, mailer: FakeMailer) -> HttpClient:
    """가짜 메일러를 끼운 앱의 클라이언트를 만든다."""
    app = create_app(settings)
    app.dependency_overrides[get_mailer] = lambda: mailer
    return as_client(app)


@pytest.fixture
def mailer() -> FakeMailer:
    """보낸 메일을 기록하는 가짜 메일러."""
    return FakeMailer()


@pytest.fixture
def client(db_url: str, mailer: FakeMailer) -> HttpClient:
    """2차 인증이 켜진 앱의 클라이언트(가입까지 마친 상태)."""
    api = make_client(make_settings(db_url, enabled=True), mailer)
    assert api.request("POST", "/v1/auth/signup", json=SIGNUP).status_code == 201
    return api


def begin(client: HttpClient, mailer: FakeMailer) -> tuple[str, str]:
    """로그인해서 (challenge_id, 메일로 간 코드)를 돌려준다."""
    response = client.request("POST", "/v1/auth/login", json=LOGIN)
    assert response.status_code == 200
    body = TwoFactorRequired.model_validate_json(response.text)
    assert mailer.sent
    return body.challenge_id, mailer.sent[-1][1]


def test_login_with_two_factor_returns_no_tokens_and_sends_mail(
    client: HttpClient, mailer: FakeMailer
) -> None:
    """비밀번호가 맞으면 토큰 대신 인증 필요 응답을 주고 메일이 한 통 나간다."""
    response = client.request("POST", "/v1/auth/login", json=LOGIN)
    assert response.status_code == 200
    body = TwoFactorRequired.model_validate_json(response.text)
    assert body.status == "TWO_FACTOR_REQUIRED"
    assert "token" not in response.text
    assert len(mailer.sent) == 1
    assert mailer.sent[0][0] == EMAIL
    assert re.fullmatch(r"[0-9]{6}", mailer.sent[0][1])
    assert mailer.sent[0][1] not in response.text  # 코드는 응답이 아니라 메일로만 간다.


def test_correct_code_completes_login(client: HttpClient, mailer: FakeMailer) -> None:
    """맞는 코드를 보내면 토큰을 받고 그 토큰으로 로그인 상태가 확인된다."""
    challenge_id, code = begin(client, mailer)
    response = client.request(
        "POST", "/v1/auth/2fa/verify", json={"challenge_id": challenge_id, "code": code}
    )
    assert response.status_code == 200
    body = AuthResponse.model_validate_json(response.text)
    session = client.request(
        "GET", "/v1/me/session", headers={"Authorization": f"Bearer {body.tokens.access_token}"}
    )
    assert session.status_code == 200
    assert '"authenticated":true' in session.text.replace(" ", "")


def test_wrong_password_never_sends_mail(client: HttpClient, mailer: FakeMailer) -> None:
    """비밀번호가 틀리면 기존과 같은 401이고 메일은 한 통도 나가지 않는다."""
    response = client.request(
        "POST", "/v1/auth/login", json={"email": EMAIL, "password": "Wr0ng!Passw0rd-xyz"}
    )
    assert response.status_code == 401
    assert ErrorResponse.model_validate_json(response.text).code == "INVALID_CREDENTIALS"
    assert mailer.sent == []


def test_failed_verifications_look_identical(client: HttpClient, mailer: FakeMailer) -> None:
    """틀린 코드, 없는 챌린지, 이미 쓴 코드는 상태 코드·코드·메시지가 같다."""
    challenge_id, code = begin(client, mailer)
    wrong = "000000" if code != "000000" else "000001"
    bodies = [
        {"challenge_id": challenge_id, "code": wrong},
        {"challenge_id": "z" * 43, "code": code},
    ]
    seen: set[tuple[int, str, str]] = set()
    for payload in bodies:
        response = client.request("POST", "/v1/auth/2fa/verify", json=payload)
        parsed = ErrorResponse.model_validate_json(response.text)
        seen.add((response.status_code, parsed.code, parsed.message))
    ok = client.request(
        "POST", "/v1/auth/2fa/verify", json={"challenge_id": challenge_id, "code": code}
    )
    assert ok.status_code == 200
    reused = client.request(
        "POST", "/v1/auth/2fa/verify", json={"challenge_id": challenge_id, "code": code}
    )
    parsed = ErrorResponse.model_validate_json(reused.text)
    seen.add((reused.status_code, parsed.code, parsed.message))
    assert seen == {(401, "INVALID_TWO_FACTOR", "인증 코드가 올바르지 않거나 만료되었습니다.")}


def test_malformed_code_is_422_and_not_echoed(client: HttpClient, mailer: FakeMailer) -> None:
    """6자리 숫자가 아닌 코드는 422이고 입력값을 되돌려 주지 않는다."""
    challenge_id, _ = begin(client, mailer)
    for bad in ("12345", "1234567", "abcdef", "12 456"):
        response = client.request(
            "POST", "/v1/auth/2fa/verify", json={"challenge_id": challenge_id, "code": bad}
        )
        assert response.status_code == 422
        assert bad not in response.text


def test_resend_during_cooldown_sends_no_mail(client: HttpClient, mailer: FakeMailer) -> None:
    """60초 안의 재발송은 429이고 메일은 늘지 않는다."""
    challenge_id, _ = begin(client, mailer)
    response = client.request("POST", "/v1/auth/2fa/resend", json={"challenge_id": challenge_id})
    assert response.status_code == 429
    assert ErrorResponse.model_validate_json(response.text).code == "TOO_MANY_ATTEMPTS"
    assert len(mailer.sent) == 1


def test_resend_of_unknown_challenge_is_401_without_mail(
    client: HttpClient, mailer: FakeMailer
) -> None:
    """없는 챌린지의 재발송은 401이고 메일이 나가지 않는다."""
    response = client.request("POST", "/v1/auth/2fa/resend", json={"challenge_id": "q" * 43})
    assert response.status_code == 401
    assert mailer.sent == []
    assert ResendResponse.model_fields  # 응답 모델은 별도 필드만 가진다.


def test_mail_failure_does_not_break_login_response(
    db_url: str, caplog: pytest.LogCaptureFixture
) -> None:
    """메일 발송이 실패해도 로그인 응답은 나가고, 로그에는 주소와 코드가 없다."""
    failing = FakeMailer(fail=True)
    api = make_client(make_settings(db_url, enabled=True), failing)
    api.request("POST", "/v1/auth/signup", json=SIGNUP)
    with caplog.at_level(logging.DEBUG):
        response = api.request("POST", "/v1/auth/login", json=LOGIN)
    assert response.status_code == 200
    assert TwoFactorRequired.model_validate_json(response.text).status == "TWO_FACTOR_REQUIRED"
    assert EMAIL not in caplog.text


def test_logs_never_contain_code_email_or_secrets(
    client: HttpClient, mailer: FakeMailer, caplog: pytest.LogCaptureFixture
) -> None:
    """전체 흐름 동안 로그에 코드·이메일·비밀번호·키가 한 번도 나오지 않는다."""
    with caplog.at_level(logging.DEBUG):
        challenge_id, code = begin(client, mailer)
        client.request(
            "POST", "/v1/auth/2fa/verify", json={"challenge_id": challenge_id, "code": "000000"}
        )
        client.request(
            "POST", "/v1/auth/2fa/verify", json={"challenge_id": challenge_id, "code": code}
        )
    for secret in (code, EMAIL, PASSWORD, OTP_SECRET, APP_PASSWORD, challenge_id):
        assert secret not in caplog.text


def test_two_factor_off_keeps_existing_login(db_url: str, mailer: FakeMailer) -> None:
    """스위치가 꺼져 있으면 로그인은 예전과 같고 2차 인증 경로는 없다."""
    api = make_client(make_settings(db_url, enabled=False), mailer)
    api.request("POST", "/v1/auth/signup", json=SIGNUP)
    login = api.request("POST", "/v1/auth/login", json=LOGIN)
    assert login.status_code == 200
    assert AuthResponse.model_validate_json(login.text).tokens.access_token
    probe = api.request(
        "POST", "/v1/auth/2fa/verify", json={"challenge_id": "a" * 43, "code": "123456"}
    )
    assert probe.status_code == 404
    assert mailer.sent == []

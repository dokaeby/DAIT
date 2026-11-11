"""메일 발송기(SMTP는 가짜로 대체)와 2차 인증 설정 검증 테스트. 네트워크 없음."""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from typing import Self

import pytest
from pydantic import SecretStr, ValidationError

from dait.core.config import Settings
from dait.core.mailer import SMTP_TIMEOUT_SECONDS, MailSendError, SmtpMailer

APP_PASSWORD = "fake-app-password-for-tests"  # noqa: S105 - 테스트 전용 가짜 앱 비밀번호
CALLS: list[str] = []
SENT: list[EmailMessage] = []


class FakeSmtp:
    """smtplib.SMTP 대역: 어떤 순서로 불렸는지만 기록한다."""

    def __init__(self, host: str, port: int, timeout: float) -> None:
        """접속 시도를 기록한다."""
        CALLS.append(f"connect:{host}:{port}:{timeout}")

    def __enter__(self) -> Self:
        """with 블록을 연다."""
        return self

    def __exit__(self, *_args: object) -> None:
        """with 블록을 닫는다."""

    def starttls(self, context: ssl.SSLContext) -> None:
        """TLS 전환을 기록하고 인증서 검증이 켜져 있는지 확인한다."""
        assert context.verify_mode == ssl.CERT_REQUIRED
        CALLS.append("starttls")

    def login(self, user: str, password: str) -> None:
        """로그인을 기록한다(비밀번호 값은 기록하지 않는다)."""
        CALLS.append(f"login:{user}:{'ok' if password else 'empty'}")

    def send_message(self, message: EmailMessage) -> None:
        """보낸 메시지를 보관한다."""
        SENT.append(message)


class RefusingSmtp(FakeSmtp):
    """로그인을 거부하는 SMTP 대역."""

    def login(self, user: str, password: str) -> None:
        """항상 인증 실패를 낸다."""
        raise smtplib.SMTPAuthenticationError(535, b"bad credentials")


@pytest.fixture(autouse=True)
def _reset_records() -> None:
    """시험 사이에 기록을 비운다."""
    CALLS.clear()
    SENT.clear()


def mailer() -> SmtpMailer:
    """가짜 접속 정보의 SmtpMailer."""
    return SmtpMailer(
        "smtp.example.com", 587, "sender@example.com", SecretStr(APP_PASSWORD), "sender@example.com"
    )


def test_smtp_flow_is_tls_then_login_then_send_with_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """STARTTLS 후에 로그인하고 보내며, 접속에는 10초 타임아웃이 걸린다."""
    monkeypatch.setattr(smtplib, "SMTP", FakeSmtp)
    mailer().send_code("usera@example.com", "123456")
    assert CALLS[0] == f"connect:smtp.example.com:587:{SMTP_TIMEOUT_SECONDS}"
    assert CALLS[1:] == ["starttls", "login:sender@example.com:ok"]
    assert SMTP_TIMEOUT_SECONDS == 10.0
    message = SENT[0]
    assert message["To"] == "usera@example.com"
    assert message["Subject"] == "[DAIT] 로그인 인증 코드"
    assert "123456" in message.get_content()


@pytest.mark.parametrize(
    "address",
    [
        "usera@example.com\nBcc: evil@example.com",
        "usera@example.com\r\nSubject: hacked",
        "usera@example.com\rX",
    ],
)
def test_newline_in_address_is_refused_before_any_connection(
    monkeypatch: pytest.MonkeyPatch, address: str
) -> None:
    """받는 주소에 줄바꿈이 있으면 연결도 하지 않고 거부한다(헤더 인젝션 방지)."""
    monkeypatch.setattr(smtplib, "SMTP", FakeSmtp)
    with pytest.raises(MailSendError):
        mailer().send_code(address, "123456")
    assert CALLS == []
    assert SENT == []


def test_smtp_failure_becomes_mail_send_error_without_leaking_secrets(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """SMTP가 로그인을 거부하면 MailSendError이고 로그에 주소·코드·비밀번호가 없다."""
    monkeypatch.setattr(smtplib, "SMTP", RefusingSmtp)
    with caplog.at_level(logging.DEBUG), pytest.raises(MailSendError):
        mailer().send_code("usera@example.com", "123456")
    for leaked in ("usera@example.com", "123456", APP_PASSWORD, "bad credentials"):
        assert leaked not in caplog.text


def test_network_error_becomes_mail_send_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """연결 자체가 안 돼도(OSError) MailSendError로 바뀐다."""

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise OSError

    monkeypatch.setattr(smtplib, "SMTP", refuse)
    with pytest.raises(MailSendError):
        mailer().send_code("usera@example.com", "123456")


def test_default_settings_have_two_factor_off() -> None:
    """기본값은 꺼짐이고 꺼져 있으면 SMTP 값이 없어도 시작된다."""
    settings = Settings()
    assert settings.two_factor_enabled is False


def test_enabling_without_required_values_is_refused() -> None:
    """켰는데 필요한 값이 없으면 시작을 거부하고, 오류 메시지에는 항목 이름만 나온다."""
    with pytest.raises(ValidationError) as caught:
        Settings(two_factor_enabled=True)
    text = str(caught.value)
    assert "OTP_HASH_SECRET" in text
    assert "SMTP_HOST" in text


def test_enabling_with_short_hash_secret_is_refused() -> None:
    """해시 키가 32자 미만이면 거부한다."""
    with pytest.raises(ValidationError):
        Settings(
            two_factor_enabled=True,
            otp_hash_secret=SecretStr("short"),
            smtp_host="smtp.example.com",
            smtp_username="sender@example.com",
            smtp_app_password=SecretStr(APP_PASSWORD),
            smtp_from="sender@example.com",
        )


def test_enabling_with_bad_sender_address_is_refused() -> None:
    """보내는 주소가 이메일 형식이 아니거나 줄바꿈을 품으면 거부한다."""
    for sender in ("not-an-email", "a@example.com\nBcc: x@example.com"):
        with pytest.raises(ValidationError):
            Settings(
                two_factor_enabled=True,
                otp_hash_secret=SecretStr("o" * 40),
                smtp_host="smtp.example.com",
                smtp_username="sender@example.com",
                smtp_app_password=SecretStr(APP_PASSWORD),
                smtp_from=sender,
            )


def test_valid_two_factor_settings_are_accepted() -> None:
    """모든 값이 있으면 켜진 채로 만들어진다."""
    settings = Settings(
        two_factor_enabled=True,
        otp_hash_secret=SecretStr("o" * 40),
        smtp_host="smtp.example.com",
        smtp_username="sender@example.com",
        smtp_app_password=SecretStr(APP_PASSWORD),
        smtp_from="sender@example.com",
    )
    assert settings.two_factor_enabled is True
    assert APP_PASSWORD not in repr(settings)

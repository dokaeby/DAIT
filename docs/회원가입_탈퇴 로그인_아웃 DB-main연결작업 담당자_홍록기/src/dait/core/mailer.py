"""메일 발송 인터페이스와 구현(Google SMTP, 시험용 가짜). 서비스는 Mailer 모양만 안다."""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from typing import Protocol

from pydantic import SecretStr

logger = logging.getLogger(__name__)

SMTP_TIMEOUT_SECONDS = 10.0  # 메일 서버가 멈춰도 작업이 무한정 붙잡히지 않게 한다.
# 제목·발신 표시는 고정 문자열만 쓴다. 사용자 입력이 헤더에 들어갈 길이 없어 헤더 인젝션이 막힌다.
_SUBJECT = "[DAIT] 로그인 인증 코드"
_BODY = (
    "인증 코드: {code}\n이 코드는 5분 동안만 유효합니다. 본인이 요청하지 않았다면 무시해 주세요.\n"
)


class MailSendError(Exception):
    """메일을 보내지 못했을 때. 원인(서버 응답, 주소)은 메시지에 담지 않는다."""


class Mailer(Protocol):
    """코드를 메일로 보내는 동작."""

    def send_code(self, to: str, code: str) -> None:
        """to 주소로 인증 코드를 보낸다. 실패하면 MailSendError."""
        ...


class SmtpMailer:
    """Google SMTP(STARTTLS, 앱 비밀번호)로 보내는 Mailer."""

    def __init__(
        self, host: str, port: int, username: str, password: SecretStr, sender: str
    ) -> None:
        """접속 정보를 보관한다. 이 시점에는 네트워크에 연결하지 않는다.

        입력: host, port, username, password (앱 비밀번호, SecretStr), sender (보내는 주소)
        출력: 없음
        기능: 연결은 send_code를 부를 때만 맺는다.
        """
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._sender = sender

    def send_code(self, to: str, code: str) -> None:
        """인증 코드 메일을 보낸다.

        입력: to (받는 사람 주소), code (6자리 코드)
        출력: 없음
        기능: 주소에 줄바꿈이 있으면 연결도 하지 않고 거부한다. STARTTLS로 암호화하고
              인증서를 검증하며, 10초 안에 응답이 없으면 포기한다.
        """
        if "\r" in to or "\n" in to or "\r" in self._sender or "\n" in self._sender:
            raise MailSendError
        message = EmailMessage()
        message["Subject"] = _SUBJECT
        message["From"] = self._sender
        message["To"] = to
        message.set_content(_BODY.format(code=code))
        try:
            with smtplib.SMTP(self._host, self._port, timeout=SMTP_TIMEOUT_SECONDS) as smtp:
                smtp.starttls(context=ssl.create_default_context())
                smtp.login(self._username, self._password.get_secret_value())
                smtp.send_message(message)
        except (smtplib.SMTPException, OSError) as exc:
            # 원인 클래스 이름만 남긴다: 서버 응답에 주소나 계정 정보가 섞일 수 있다.
            logger.warning("2차 인증 메일 발송 실패: %s", type(exc).__name__)
            raise MailSendError from exc


class FakeMailer:
    """시험용: 실제로 보내지 않고 보낸 내용을 기록한다. 설정으로 고를 수 없다."""

    def __init__(self, *, fail: bool = False) -> None:
        """기록 목록을 비워 만든다.

        입력: fail (True면 send_code가 항상 MailSendError)
        출력: 없음
        기능: 시험이 보낸 횟수와 마지막 코드를 확인하는 데 쓴다.
        """
        self.sent: list[tuple[str, str]] = []
        self._fail = fail

    def send_code(self, to: str, code: str) -> None:
        """보낸 척하고 (받는 주소, 코드)를 기록한다.

        입력: to (받는 사람), code (코드)
        출력: 없음
        기능: fail이면 기록 없이 MailSendError.
        """
        if self._fail:
            raise MailSendError
        self.sent.append((to, code))

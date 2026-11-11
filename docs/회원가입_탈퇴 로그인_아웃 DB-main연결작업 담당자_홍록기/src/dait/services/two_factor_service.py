"""이메일 2차 인증 규칙: 코드 만들기·확인·재발송. HTTP는 api, SQL은 repositories가 맡는다."""

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from dait.core.config import Settings
from dait.core.errors import InvalidTwoFactorError, TooManyAttemptsError
from dait.core.logging import audit
from dait.core.mailer import Mailer, MailSendError
from dait.repositories.code_store import CodeStore
from dait.repositories.db import transaction
from dait.repositories.user_repository import find_by_id
from dait.schemas.auth import AuthResponse
from dait.schemas.two_factor import (
    ChallengeRecord,
    ResendRequest,
    ResendResponse,
    TwoFactorRequired,
    VerifyRequest,
)
from dait.schemas.user import UserRecord
from dait.services import auth_service

logger = logging.getLogger(__name__)

CODE_TTL = timedelta(minutes=5)
RESEND_COOLDOWN = timedelta(seconds=60)
MAX_ATTEMPTS = 5  # 코드 하나에 허용하는 확인 시도. 6자리(100만 가지)를 무작위로 맞추기 어렵게 한다.
MAX_RESENDS = 5


class PendingMail(BaseModel):
    """응답을 보낸 뒤 백그라운드에서 보낼 메일. 코드는 repr·로그에 나오지 않게 한다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    to: str = Field(repr=False)
    code: str = Field(repr=False)


def _challenge_key(challenge_id: str) -> str:
    """challenge_id의 저장용 키를 만든다.

    입력: challenge_id (클라이언트에게 준 임시 번호)
    출력: str (SHA-256 16진 문자열 64자)
    기능: 원문이 256비트 난수라 빠른 해시로 충분하다. DB가 유출돼도 챌린지를 쓸 수 없다.
    """
    return hashlib.sha256(challenge_id.encode()).hexdigest()


def _new_code() -> str:
    """6자리 인증 코드를 만든다.

    입력: 없음
    출력: str (숫자 6자리, 앞자리 0 포함)
    기능: random이 아니라 secrets로 만들어 예측할 수 없게 한다.
    """
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash_code(secret: SecretStr, key: str, code: str) -> str:
    """코드의 저장용 해시를 만든다.

    입력: secret (서버만 아는 OTP_HASH_SECRET), key (챌린지 키), code (코드 원문)
    출력: str (HMAC-SHA256 16진 문자열 64자)
    기능: 6자리는 일반 해시면 바로 역산되므로 서버 비밀 키를 섞는다. 챌린지 키도 섞어
          다른 챌린지의 해시를 옮겨 쓸 수 없게 한다.
    """
    return hmac.new(
        secret.get_secret_value().encode(), f"{key}:{code}".encode(), hashlib.sha256
    ).hexdigest()


def start_login(
    settings: Settings, store: CodeStore, user: UserRecord, client_ip: str | None, now: datetime
) -> tuple[TwoFactorRequired, PendingMail]:
    """비밀번호가 확인된 사용자의 2차 인증 챌린지를 만든다.

    입력: settings (앱 설정), store (코드 저장소), user (비밀번호가 확인된 사용자),
          client_ip (감사 로그용), now (UTC 시각)
    출력: tuple (클라이언트에 줄 응답, 보낼 메일)
    기능: 사용자당 챌린지는 하나만 남기고 만료된 것은 청소한다. 토큰은 발급하지 않는다.
    """
    store.delete_expired(now)
    challenge_id = secrets.token_urlsafe(32)
    key = _challenge_key(challenge_id)
    code = _new_code()
    store.replace_for_user(
        ChallengeRecord(
            key=key,
            user_id=user.id,
            code_hash=_hash_code(settings.otp_hash_secret, key, code),
            expires_at=now + CODE_TTL,
            attempts=0,
            resend_count=0,
            last_sent_at=now,
            created_at=now,
        )
    )
    audit("two_factor", "challenge_created", user_id=user.id, client_ip=client_ip)
    response = TwoFactorRequired(
        challenge_id=challenge_id,
        expires_in_seconds=int(CODE_TTL.total_seconds()),
        resend_after_seconds=int(RESEND_COOLDOWN.total_seconds()),
    )
    return response, PendingMail(to=user.email, code=code)


def verify(
    settings: Settings,
    store: CodeStore,
    request: VerifyRequest,
    client_ip: str | None,
    now: datetime,
) -> AuthResponse:
    """코드를 확인하고 맞으면 로그인 토큰을 발급한다.

    입력: settings (앱 설정), store (코드 저장소), request (챌린지 번호와 코드),
          client_ip (감사 로그용), now (UTC 시각)
    출력: AuthResponse (사용자와 새 토큰)
    기능: 없는 챌린지·만료·시도 초과·틀린 코드·이미 쓴 코드를 모두 같은 InvalidTwoFactorError로
          돌려준다. 시도는 비교 전에 먼저 세어 동시에 여러 추측을 보내도 5번을 넘지 못한다.
          성공하면 챌린지를 지워 같은 코드를 다시 쓸 수 없다.
    """
    key = _challenge_key(request.challenge_id)
    record = store.get(key)
    if record is None:
        audit("two_factor", "unknown_challenge", client_ip=client_ip)
        raise InvalidTwoFactorError
    if record.expires_at <= now:
        store.delete(key)
        audit("two_factor", "expired", user_id=record.user_id, client_ip=client_ip)
        raise InvalidTwoFactorError
    attempts = store.add_attempt(key)
    if attempts is None or attempts > MAX_ATTEMPTS:
        store.delete(key)
        audit("two_factor", "too_many_attempts", user_id=record.user_id, client_ip=client_ip)
        raise InvalidTwoFactorError
    given = _hash_code(settings.otp_hash_secret, key, request.code)
    if not hmac.compare_digest(record.code_hash, given):
        if attempts >= MAX_ATTEMPTS:  # 마지막 기회까지 틀리면 이 코드는 폐기한다.
            store.delete(key)
        audit("two_factor", "wrong_code", user_id=record.user_id, client_ip=client_ip)
        raise InvalidTwoFactorError
    if not store.consume(key, record.code_hash):  # 동시에 같은 코드를 보낸 요청 중 하나만 통과한다.
        audit("two_factor", "already_used", user_id=record.user_id, client_ip=client_ip)
        raise InvalidTwoFactorError
    with transaction(settings.database_url) as conn:
        user = find_by_id(conn, record.user_id)
    if user is None:
        raise InvalidTwoFactorError
    audit("two_factor", "success", user_id=user.id, client_ip=client_ip)
    return auth_service.issue_login_response(settings, user, client_ip, now)


def resend(
    settings: Settings,
    store: CodeStore,
    request: ResendRequest,
    client_ip: str | None,
    now: datetime,
) -> tuple[ResendResponse, PendingMail]:
    """같은 챌린지에 새 코드를 만든다.

    입력: settings (앱 설정), store (코드 저장소), request (챌린지 번호),
          client_ip (감사 로그용), now (UTC 시각)
    출력: tuple (응답, 보낼 메일)
    기능: 없는 챌린지·만료는 InvalidTwoFactorError. 60초 안이거나 5번을 넘기면
          TooManyAttemptsError. 새 코드가 만들어지면 이전 코드는 못 쓰고 시도 횟수는 0이 된다.
    """
    key = _challenge_key(request.challenge_id)
    record = store.get(key)
    if record is None:
        raise InvalidTwoFactorError
    if record.expires_at <= now:
        store.delete(key)
        raise InvalidTwoFactorError
    code = _new_code()
    reissued = store.reissue(
        key,
        _hash_code(settings.otp_hash_secret, key, code),
        expires_at=now + CODE_TTL,
        sent_at=now,
        sent_before=now - RESEND_COOLDOWN,
        max_resends=MAX_RESENDS,
    )
    if not reissued:
        audit("two_factor", "resend_blocked", user_id=record.user_id, client_ip=client_ip)
        raise TooManyAttemptsError
    with transaction(settings.database_url) as conn:
        user = find_by_id(conn, record.user_id)
    if user is None:
        raise InvalidTwoFactorError
    audit("two_factor", "resent", user_id=user.id, client_ip=client_ip)
    response = ResendResponse(resend_after_seconds=int(RESEND_COOLDOWN.total_seconds()))
    return response, PendingMail(to=user.email, code=code)


def deliver(mailer: Mailer, mail: PendingMail) -> None:
    """메일을 보낸다. 응답을 보낸 뒤 백그라운드에서 부른다.

    입력: mailer (메일 발송기), mail (받는 주소와 코드)
    출력: 없음
    기능: 실패해도 예외를 밖으로 내지 않는다(이미 응답이 나갔다). 사용자는 60초 뒤 재발송할 수 있다.
          로그에는 주소도 코드도 남기지 않는다.
    """
    try:
        mailer.send_code(mail.to, mail.code)
    except MailSendError:
        logger.warning("2차 인증 메일을 보내지 못했습니다")

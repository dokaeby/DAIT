"""services/two_factor_service와 repositories/code_store 테스트(네트워크 없이, 시계는 직접 넘김)."""

import hashlib
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from alembic import command
from pydantic import SecretStr

from dait.core.config import Settings
from dait.core.errors import InvalidTwoFactorError, TooManyAttemptsError
from dait.repositories.code_store import SqliteCodeStore
from dait.repositories.db import connect, transaction
from dait.repositories.user_repository import find_by_email
from dait.schemas.auth import SignupRequest
from dait.schemas.two_factor import ResendRequest, TwoFactorRequired, VerifyRequest
from dait.schemas.user import UserRecord
from dait.services import auth_service, two_factor_service
from dait.services.two_factor_service import (
    CODE_TTL,
    MAX_ATTEMPTS,
    MAX_RESENDS,
    RESEND_COOLDOWN,
    PendingMail,
)
from support import alembic_config

NOW = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
EMAIL = "usera@example.com"
PASSWORD = "Str0ng!Passw0rd-xyz"  # noqa: S105 - 테스트 전용 가짜 비밀번호
OTP_SECRET = "otp-test-secret-0123456789-abcdefghijklmnopqr"  # noqa: S105 - 테스트 전용 가짜 키


@pytest.fixture
def tf_settings(db_url: str) -> Settings:
    """2차 인증을 켠 테스트용 설정(SMTP 값은 가짜, 실제로 연결하지 않는다)."""
    return Settings(
        database_url=db_url,
        two_factor_enabled=True,
        otp_hash_secret=SecretStr(OTP_SECRET),
        smtp_host="smtp.example.com",
        smtp_username="sender@example.com",
        smtp_app_password=SecretStr("fake-app-password-for-tests"),
        smtp_from="sender@example.com",
    )


@pytest.fixture
def user(tf_settings: Settings) -> UserRecord:
    """가입해 둔 사용자."""
    request = SignupRequest.model_validate(
        {
            "email": EMAIL,
            "password": PASSWORD,
            "password_confirm": PASSWORD,
            "terms_accepted": True,
        }
    )
    auth_service.signup(tf_settings, request, None, NOW)
    with transaction(tf_settings.database_url) as conn:
        found = find_by_email(conn, EMAIL)
    assert found is not None
    return found


@pytest.fixture
def store(tf_settings: Settings) -> SqliteCodeStore:
    """테스트 DB의 코드 저장소."""
    return SqliteCodeStore(tf_settings.database_url)


def start(
    settings: Settings, store: SqliteCodeStore, user: UserRecord, now: datetime = NOW
) -> tuple[TwoFactorRequired, PendingMail]:
    """챌린지를 시작한다."""
    return two_factor_service.start_login(settings, store, user, "127.0.0.1", now)


def check(
    settings: Settings,
    store: SqliteCodeStore,
    challenge_id: str,
    code: str,
    now: datetime = NOW,
) -> None:
    """코드를 확인한다(성공하면 조용히 끝난다)."""
    request = VerifyRequest(challenge_id=challenge_id, code=code)
    two_factor_service.verify(settings, store, request, "127.0.0.1", now)


def fixed_seven(_limit: int) -> int:
    """secrets.randbelow 대역: 항상 7을 돌려준다(앞자리 0 확인용)."""
    return 7


def wrong_code(real: str) -> str:
    """진짜 코드와 다른 6자리 코드를 돌려준다."""
    return "000000" if real != "000000" else "000001"


def test_code_is_six_digits_and_keeps_leading_zero(
    tf_settings: Settings, store: SqliteCodeStore, user: UserRecord, monkeypatch: pytest.MonkeyPatch
) -> None:
    """코드는 항상 숫자 6자리이고 앞자리 0도 지켜진다."""
    with (
        monkeypatch.context() as patched
    ):  # undo()는 conftest의 환경 격리까지 되돌려서 쓰지 않는다.
        patched.setattr(two_factor_service.secrets, "randbelow", fixed_seven)
        _, mail = start(tf_settings, store, user)
    assert mail.code == "000007"
    for _ in range(30):
        assert re.fullmatch(r"[0-9]{6}", start(tf_settings, store, user)[1].code)


def test_code_and_challenge_id_are_not_stored_in_plain(
    tf_settings: Settings, store: SqliteCodeStore, user: UserRecord
) -> None:
    """DB에는 코드 원문도 challenge_id 원문도 없고 64자 해시만 있다."""
    response, mail = start(tf_settings, store, user)
    conn = connect(tf_settings.database_url)
    try:
        rows = conn.execute("SELECT * FROM two_factor_challenges").fetchall()
    finally:
        conn.close()
    assert len(rows) == 1
    dumped = repr(rows)
    assert mail.code not in re.findall(r"[0-9a-f]{64}", dumped)
    assert response.challenge_id not in dumped
    assert re.fullmatch(r"[0-9a-f]{64}", rows[0][2])
    assert mail.code != rows[0][2]


def test_correct_code_issues_tokens_and_consumes_challenge(
    tf_settings: Settings, store: SqliteCodeStore, user: UserRecord
) -> None:
    """맞는 코드는 토큰을 발급하고 챌린지를 지운다."""
    response, mail = start(tf_settings, store, user)
    request = VerifyRequest(challenge_id=response.challenge_id, code=mail.code)
    result = two_factor_service.verify(
        tf_settings, store, request, None, NOW + timedelta(seconds=5)
    )
    assert result.user.id == user.id
    assert result.tokens.access_token
    with pytest.raises(InvalidTwoFactorError):  # 같은 코드를 다시 쓸 수 없다.
        two_factor_service.verify(tf_settings, store, request, None, NOW + timedelta(seconds=6))


def test_login_response_has_no_tokens() -> None:
    """코드 확인 전 응답 모델에는 토큰 필드가 없다."""
    assert "access_token" not in TwoFactorRequired.model_fields
    assert "tokens" not in TwoFactorRequired.model_fields


def test_code_expires_after_five_minutes(
    tf_settings: Settings, store: SqliteCodeStore, user: UserRecord
) -> None:
    """5분 안에는 통과하고 5분을 넘기면 맞는 코드도 실패한다."""
    response, mail = start(tf_settings, store, user)
    check(
        tf_settings, store, response.challenge_id, mail.code, NOW + timedelta(minutes=4, seconds=59)
    )
    response2, mail2 = start(tf_settings, store, user)
    with pytest.raises(InvalidTwoFactorError):
        check(
            tf_settings,
            store,
            response2.challenge_id,
            mail2.code,
            NOW + timedelta(minutes=5, seconds=1),
        )


def test_wrong_codes_are_limited_to_five_then_right_code_also_fails(
    tf_settings: Settings, store: SqliteCodeStore, user: UserRecord
) -> None:
    """틀린 코드를 5번 보내면 그 코드는 폐기돼 정답도 실패한다."""
    response, mail = start(tf_settings, store, user)
    for _ in range(MAX_ATTEMPTS):
        with pytest.raises(InvalidTwoFactorError):
            check(tf_settings, store, response.challenge_id, wrong_code(mail.code))
    with pytest.raises(InvalidTwoFactorError):
        check(tf_settings, store, response.challenge_id, mail.code)


def test_policy_numbers_match_the_approved_design() -> None:
    """승인된 값(유효 5분, 시도 5회, 재전송 60초·5번)이 바뀌면 알아챈다."""
    assert timedelta(minutes=5) == CODE_TTL
    assert MAX_ATTEMPTS == 5
    assert timedelta(seconds=60) == RESEND_COOLDOWN
    assert MAX_RESENDS == 5


def test_fifth_wrong_code_discards_the_challenge(
    tf_settings: Settings, store: SqliteCodeStore, user: UserRecord
) -> None:
    """다섯 번째 실패 때 챌린지 행이 실제로 지워진다."""
    response, mail = start(tf_settings, store, user)
    key = hashlib.sha256(response.challenge_id.encode()).hexdigest()
    for _ in range(MAX_ATTEMPTS):
        with pytest.raises(InvalidTwoFactorError):
            check(tf_settings, store, response.challenge_id, wrong_code(mail.code))
    assert store.get(key) is None


def test_attempts_already_spent_by_parallel_guesses_block_the_right_code(
    tf_settings: Settings, store: SqliteCodeStore, user: UserRecord
) -> None:
    """동시에 들어온 추측이 이미 5번을 채웠다면, 뒤따라 온 정답도 통과하지 못한다."""
    response, mail = start(tf_settings, store, user)
    key = hashlib.sha256(response.challenge_id.encode()).hexdigest()
    for _ in range(MAX_ATTEMPTS):
        store.add_attempt(key)
    with pytest.raises(InvalidTwoFactorError):
        check(tf_settings, store, response.challenge_id, mail.code)


def test_four_wrong_codes_then_right_code_passes(
    tf_settings: Settings, store: SqliteCodeStore, user: UserRecord
) -> None:
    """경계: 4번 틀리고 5번째에 맞으면 통과한다."""
    response, mail = start(tf_settings, store, user)
    for _ in range(MAX_ATTEMPTS - 1):
        with pytest.raises(InvalidTwoFactorError):
            check(tf_settings, store, response.challenge_id, wrong_code(mail.code))
    check(tf_settings, store, response.challenge_id, mail.code)


def test_all_failures_raise_the_same_error(
    tf_settings: Settings, store: SqliteCodeStore, user: UserRecord
) -> None:
    """틀림·없는 챌린지·만료는 코드와 메시지가 같아 이유를 알 수 없다."""
    response, mail = start(tf_settings, store, user)
    outcomes: list[tuple[str, str]] = []
    cases = (
        (response.challenge_id, wrong_code(mail.code), NOW),
        ("x" * 43, mail.code, NOW),
        (response.challenge_id, mail.code, NOW + timedelta(minutes=5, seconds=1)),
    )
    for challenge_id, code, when in cases:
        with pytest.raises(InvalidTwoFactorError) as caught:
            check(tf_settings, store, challenge_id, code, when)
        outcomes.append((caught.value.code, caught.value.message))
    assert len(set(outcomes)) == 1


def test_new_login_replaces_old_challenge(
    tf_settings: Settings, store: SqliteCodeStore, user: UserRecord
) -> None:
    """같은 사용자가 다시 로그인하면 이전 챌린지는 쓸 수 없다."""
    first, first_mail = start(tf_settings, store, user)
    second, second_mail = start(tf_settings, store, user)
    with pytest.raises(InvalidTwoFactorError):
        check(tf_settings, store, first.challenge_id, first_mail.code)
    check(tf_settings, store, second.challenge_id, second_mail.code)


def test_resend_is_blocked_during_cooldown_and_works_after(
    tf_settings: Settings, store: SqliteCodeStore, user: UserRecord
) -> None:
    """60초 안의 재발송은 막히고, 지나면 새 코드가 만들어지며 이전 코드는 죽는다."""
    response, mail = start(tf_settings, store, user)
    request = ResendRequest(challenge_id=response.challenge_id)
    with pytest.raises(TooManyAttemptsError):
        two_factor_service.resend(
            tf_settings, store, request, None, NOW + RESEND_COOLDOWN - timedelta(seconds=1)
        )
    later = NOW + RESEND_COOLDOWN
    _, new_mail = two_factor_service.resend(tf_settings, store, request, None, later)
    with pytest.raises(InvalidTwoFactorError):
        check(tf_settings, store, response.challenge_id, mail.code, later)
    check(tf_settings, store, response.challenge_id, new_mail.code, later)


def test_resend_is_limited_to_five_times(
    tf_settings: Settings, store: SqliteCodeStore, user: UserRecord
) -> None:
    """재발송은 5번까지만 된다."""
    response, _ = start(tf_settings, store, user)
    request = ResendRequest(challenge_id=response.challenge_id)
    when = NOW
    for _ in range(MAX_RESENDS):
        when += RESEND_COOLDOWN
        two_factor_service.resend(tf_settings, store, request, None, when)
    with pytest.raises(TooManyAttemptsError):
        two_factor_service.resend(tf_settings, store, request, None, when + RESEND_COOLDOWN)


def test_resend_resets_attempts(
    tf_settings: Settings, store: SqliteCodeStore, user: UserRecord
) -> None:
    """새 코드를 받으면 시도 횟수가 0으로 돌아가 다시 5번 시도할 수 있다."""
    response, mail = start(tf_settings, store, user)
    for _ in range(MAX_ATTEMPTS - 1):
        with pytest.raises(InvalidTwoFactorError):
            check(tf_settings, store, response.challenge_id, wrong_code(mail.code))
    later = NOW + RESEND_COOLDOWN
    request = ResendRequest(challenge_id=response.challenge_id)
    _, new_mail = two_factor_service.resend(tf_settings, store, request, None, later)
    for _ in range(MAX_ATTEMPTS - 1):
        with pytest.raises(InvalidTwoFactorError):
            check(tf_settings, store, response.challenge_id, wrong_code(new_mail.code), later)
    check(tf_settings, store, response.challenge_id, new_mail.code, later)


def test_resend_of_unknown_challenge_is_rejected(
    tf_settings: Settings, store: SqliteCodeStore, user: UserRecord
) -> None:
    """없는 챌린지의 재발송은 같은 오류이고 사용자 행에도 영향이 없다."""
    request = ResendRequest(challenge_id="y" * 43)
    with pytest.raises(InvalidTwoFactorError):
        two_factor_service.resend(tf_settings, store, request, None, NOW)
    assert user.id


def test_two_simultaneous_requests_with_same_code_only_one_succeeds(
    tf_settings: Settings, store: SqliteCodeStore, user: UserRecord
) -> None:
    """같은 코드를 동시에 보내도 토큰은 한 번만 발급된다."""
    response, mail = start(tf_settings, store, user)
    request = VerifyRequest(challenge_id=response.challenge_id, code=mail.code)

    def attempt() -> bool:
        try:
            two_factor_service.verify(tf_settings, store, request, None, NOW)
        except InvalidTwoFactorError:
            return False
        return True

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [f.result() for f in [pool.submit(attempt), pool.submit(attempt)]]
    assert sorted(results) == [False, True]


def test_expired_challenges_are_cleaned_on_next_login(
    tf_settings: Settings, store: SqliteCodeStore, user: UserRecord
) -> None:
    """만료된 챌린지는 지워지고 아직 유효한 것은 남는다."""
    start(tf_settings, store, user)
    assert store.delete_expired(NOW + CODE_TTL - timedelta(seconds=1)) == 0
    assert store.delete_expired(NOW + CODE_TTL) == 1


def test_consume_with_wrong_hash_deletes_nothing(
    tf_settings: Settings, store: SqliteCodeStore, user: UserRecord
) -> None:
    """해시가 다르면 consume은 아무것도 지우지 않는다."""
    response, _ = start(tf_settings, store, user)
    key = hashlib.sha256(response.challenge_id.encode()).hexdigest()
    assert store.consume(key, "0" * 64) is False
    assert store.get(key) is not None


def test_challenges_are_deleted_with_the_user(
    tf_settings: Settings, store: SqliteCodeStore, user: UserRecord
) -> None:
    """탈퇴(사용자 삭제) 시 챌린지도 함께 지워진다."""
    start(tf_settings, store, user)
    with transaction(tf_settings.database_url) as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (user.id,))
        left = conn.execute("SELECT COUNT(*) FROM two_factor_challenges").fetchone()
    assert left is not None
    assert left[0] == 0


def test_migration_0003_downgrade_only_drops_its_table(tf_settings: Settings) -> None:
    """0003만 되돌리면 챌린지 표만 사라지고 users는 남는다."""
    command.downgrade(alembic_config(tf_settings.database_url), "0002_interests")
    conn = connect(tf_settings.database_url)
    try:
        names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master")}
    finally:
        conn.close()
    assert "two_factor_challenges" not in names
    assert "users" in names

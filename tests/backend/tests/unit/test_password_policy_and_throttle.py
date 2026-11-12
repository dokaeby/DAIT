"""비밀번호 정책(흔한 값, 이메일 포함)과 로그인 잠금 테스트."""

from datetime import UTC, datetime, timedelta

import pytest

from dait.core.config import Settings
from dait.core.password_policy import is_weak_password
from dait.services.login_throttle import AttemptThrottle, create_throttles

NOW = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize("password", ["password123", "PASSWORD123", "12345678", "qwerty123"])
def test_common_passwords_are_weak(password: str) -> None:
    """흔한 비밀번호는 대소문자와 관계없이 막는다."""
    assert is_weak_password(password, "someone@example.com") is True


def test_password_containing_email_local_part_is_weak() -> None:
    """이메일 앞부분을 포함한 비밀번호는 막는다."""
    assert is_weak_password("Xjohnsmith-2026!", "JohnSmith@example.com") is True


def test_short_local_part_is_not_compared() -> None:
    """앞부분이 3자 미만이면 우연히 겹치기 쉬워 비교하지 않는다."""
    assert is_weak_password("Zab!Xk39-pqr", "ab@example.com") is False


def test_strong_password_is_allowed() -> None:
    """흔하지 않고 이메일과 무관한 비밀번호는 통과한다."""
    assert is_weak_password("Str0ng!Passw0rd-xyz", "usera@example.com") is False


def test_not_locked_before_threshold() -> None:
    """기준 횟수 전에는 잠기지 않는다."""
    throttle = AttemptThrottle(threshold=5)
    for _ in range(4):
        throttle.register_failure("a", NOW)
    assert throttle.is_locked("a", NOW) is False


def test_locked_at_threshold_for_60_seconds() -> None:
    """기준 횟수에 닿으면 60초 잠기고 그 뒤에 풀린다."""
    throttle = AttemptThrottle(threshold=5)
    for _ in range(5):
        throttle.register_failure("a", NOW)
    assert throttle.is_locked("a", NOW + timedelta(seconds=59)) is True
    assert throttle.is_locked("a", NOW + timedelta(seconds=60)) is False


def test_lock_doubles_and_is_capped_at_15_minutes() -> None:
    """실패가 늘수록 잠금이 두 배로 길어지고 15분을 넘지 않는다."""
    throttle = AttemptThrottle(threshold=5)
    for _ in range(6):
        throttle.register_failure("a", NOW)
    assert throttle.is_locked("a", NOW + timedelta(seconds=119)) is True
    assert throttle.is_locked("a", NOW + timedelta(seconds=120)) is False
    for _ in range(10):
        throttle.register_failure("a", NOW)
    assert throttle.is_locked("a", NOW + timedelta(seconds=899)) is True
    assert throttle.is_locked("a", NOW + timedelta(seconds=900)) is False


def test_clear_resets_failures() -> None:
    """성공해서 지우면 처음부터 다시 센다."""
    throttle = AttemptThrottle(threshold=5)
    for _ in range(4):
        throttle.register_failure("a", NOW)
    throttle.clear("a")
    throttle.register_failure("a", NOW)
    assert throttle.is_locked("a", NOW) is False


def test_old_failures_are_forgotten() -> None:
    """마지막 실패가 15분보다 오래됐으면 횟수를 새로 센다."""
    throttle = AttemptThrottle(threshold=2)
    throttle.register_failure("a", NOW)
    throttle.register_failure("a", NOW + timedelta(minutes=16))
    assert throttle.is_locked("a", NOW + timedelta(minutes=16)) is False


def test_keys_are_independent() -> None:
    """다른 키는 서로 영향을 주지 않는다."""
    throttle = AttemptThrottle(threshold=2)
    throttle.register_failure("a", NOW)
    throttle.register_failure("a", NOW)
    assert throttle.is_locked("a", NOW) is True
    assert throttle.is_locked("b", NOW) is False


def test_default_thresholds_are_account_5_and_ip_20() -> None:
    """기본 잠금은 계정 5회, IP 20회부터다."""
    throttles = create_throttles()
    for _ in range(5):
        throttles.account.register_failure("a", NOW)
        throttles.ip.register_failure("ip", NOW)
    assert throttles.account.is_locked("a", NOW) is True
    assert throttles.ip.is_locked("ip", NOW) is False


class _FakeRedis:
    """RedisLike 프로토콜을 흉내 내는 인메모리 저장소."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def set(self, name: str, value: str, *, nx: bool = False, px: int | None = None) -> bool:
        if nx and name in self.store:
            return False
        self.store[name] = value
        return True

    def get(self, name: str) -> str | None:
        return self.store.get(name)

    def delete(self, *names: str) -> int:
        return sum(1 for n in names if self.store.pop(n, None) is not None)

    def eval(self, script: str, numkeys: int, *keys_and_args: object) -> object:
        raise NotImplementedError


def _redis_settings() -> Settings:
    return Settings(database_url="sqlite:///:memory:", redis_url="redis://fake:6379")


def _patch_client(monkeypatch: pytest.MonkeyPatch, client: object | None) -> None:
    monkeypatch.setattr(
        "dait.repositories.redis_repository.shared_client", lambda _url, timeout=2.0: client
    )


def test_redis_throttle_locks_at_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    """Redis 구현도 기준 횟수에 잠기고 시간이 지나면 풀린다."""
    from dait.services.login_throttle import RedisThrottle

    _patch_client(monkeypatch, _FakeRedis())
    throttle = RedisThrottle(_redis_settings(), "account", 5)
    for _ in range(4):
        throttle.register_failure("user@example.com", NOW)
    assert throttle.is_locked("user@example.com", NOW) is False
    throttle.register_failure("user@example.com", NOW)
    assert throttle.is_locked("user@example.com", NOW) is True
    assert throttle.is_locked("user@example.com", NOW + timedelta(seconds=61)) is False


def test_redis_throttle_clear_and_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    """clear는 기록을 지우고, 키는 서로 독립이다."""
    from dait.services.login_throttle import RedisThrottle

    fake = _FakeRedis()
    _patch_client(monkeypatch, fake)
    throttle = RedisThrottle(_redis_settings(), "ip", 2)
    throttle.register_failure("ip1", NOW)
    throttle.register_failure("ip1", NOW)
    assert throttle.is_locked("ip1", NOW) is True
    assert throttle.is_locked("ip2", NOW) is False
    throttle.clear("ip1")
    assert throttle.is_locked("ip1", NOW) is False
    # 이메일·IP 원문이 키에 남지 않는다.
    assert all("ip1" not in key and "@" not in key for key in fake.store)


def test_redis_throttle_falls_back_to_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    """Redis가 없으면 메모리 구현과 같은 규칙으로 동작한다."""
    from dait.services.login_throttle import RedisThrottle

    _patch_client(monkeypatch, None)
    throttle = RedisThrottle(_redis_settings(), "account", 2)
    throttle.register_failure("a", NOW)
    throttle.register_failure("a", NOW)
    assert throttle.is_locked("a", NOW) is True
    throttle.clear("a")
    assert throttle.is_locked("a", NOW) is False


def test_redis_throttle_survives_redis_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Redis 호출이 실패해도 예외 없이 fallback으로 동작한다."""
    from dait.services.login_throttle import RedisThrottle

    class _BrokenRedis(_FakeRedis):
        def get(self, name: str) -> str | None:
            raise ConnectionError("down")

        def set(self, name: str, value: str, *, nx: bool = False, px: int | None = None) -> bool:
            raise ConnectionError("down")

    _patch_client(monkeypatch, _BrokenRedis())
    throttle = RedisThrottle(_redis_settings(), "account", 2)
    throttle.register_failure("a", NOW)  # 예외 없이 fallback 기록
    throttle.register_failure("a", NOW)
    assert throttle.is_locked("a", NOW) is True

"""비밀번호 정책(흔한 값, 이메일 포함)과 로그인 잠금 테스트."""

import json
from datetime import UTC, datetime, timedelta

import pytest

from dait.core.config import Settings
from dait.core.password_policy import is_weak_password
from dait.repositories.redis_repository import RedisLike
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


# 입력: Redis 연결 대역을 바꾸는 pytest 도구.
# 출력: 반환값 없음.
# 동작: Redis 쓰기만 실패해도 메모리 잠금이 유지되고 성공 후 지워지는지 검증한다.
def test_atomic_write_failure_keeps_fallback_lock_until_clear(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """읽기가 정상이어도 쓰기 장애로 기록한 메모리 잠금을 유지한다.

    입력: Lua 응답만 잘못된 Redis 대역이다.
    출력: 없다.
    기능: Redis 조회 성공으로 대체 잠금이 무시되거나 성공 후 남는 것을 막는다.
    """
    from dait.services.login_throttle import RedisThrottle

    fake = _FakeRedis()
    fake.eval_result = None
    _patch_client(monkeypatch, fake)
    throttle = RedisThrottle(_redis_settings(), "account", 2)
    throttle.register_failure("a", NOW)
    throttle.register_failure("a", NOW)
    assert throttle.is_locked("a", NOW)
    throttle.clear("a")
    assert not throttle.is_locked("a", NOW)


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

    # 입력: 없음.
    # 출력: 반환값 없음.
    # 동작: Redis 값과 Lua 호출 정보를 보관할 빈 테스트 대역을 만든다.
    def __init__(self) -> None:
        """Redis 연결 테스트 대역을 초기화한다.

        입력: 없음.
        출력: 없음.
        기능: 키·값 저장소와 Lua 호출 기록, 기본 응답 JSON을 준비한다.
        """
        self.store: dict[str, str] = {}
        self.evaluations: list[tuple[int, tuple[object, ...]]] = []
        self.eval_result: object = json.dumps({"f": 1, "lf": NOW.timestamp(), "lu": None})

    def set(self, name: str, value: str, *, nx: bool = False, px: int | None = None) -> bool:
        if nx and name in self.store:
            return False
        self.store[name] = value
        return True

    def get(self, name: str) -> str | None:
        return self.store.get(name)

    def delete(self, *names: str) -> int:
        return sum(1 for n in names if self.store.pop(n, None) is not None)

    # 입력: Lua 스크립트, 키 개수, 키와 인자.
    # 출력: 테스트에서 지정한 Redis EVAL 응답.
    # 동작: 호출 정보를 기록하고 실제 Redis 대신 준비된 상태 JSON을 반환한다.
    def eval(self, script: str, numkeys: int, *keys_and_args: object) -> object:
        """Redis Lua 호출을 테스트 대역으로 처리한다.

        입력: script는 실행할 Lua이고 numkeys와 keys_and_args는 키·인자 정보다.
        출력: eval_result에 준비한 테스트 응답이다.
        기능: 서비스 계층이 원자 갱신을 한 번 호출했는지 검증할 정보를 남긴다.
        """
        self.evaluations.append((numkeys, keys_and_args))
        return self.eval_result


def _redis_settings() -> Settings:
    return Settings(database_url="sqlite:///:memory:", redis_url="redis://fake:6379")


# 입력: pytest 환경 격리 도구와 주입할 Redis 연결 대역.
# 출력: 반환값 없음.
# 동작: 공용 Redis 연결 함수를 타입이 유지되는 테스트 함수로 교체한다.
def _patch_client(monkeypatch: pytest.MonkeyPatch, client: RedisLike | None) -> None:
    """타입을 명시한 Redis 연결 대역을 주입한다.

    입력: monkeypatch와 테스트 클라이언트다.
    출력: 없다.
    기능: 실제 Redis를 연결하지 않고 공통 연결 계약을 유지한다.
    """

    # 입력: 무시할 Redis 주소와 연결 제한 시간.
    # 출력: 외부에서 주입한 Redis 연결 또는 None.
    # 동작: 네트워크 연결 없이 같은 테스트 대역을 반환한다.
    def shared_client(_url: str | None, timeout: float = 2.0) -> RedisLike | None:
        """지정한 테스트 연결만 반환한다.

        입력: 연결 주소와 제한 시간이다.
        출력: 주입한 Redis 대역 또는 None이다.
        기능: 타입 없는 람다로 검사 오류를 숨기지 않는다.
        """
        return client

    monkeypatch.setattr("dait.repositories.redis_repository.shared_client", shared_client)


# 입력: Redis 연결 함수를 바꾸는 pytest 도구.
# 출력: 반환값 없음.
# 동작: 로그인 실패 한 건이 Lua 원자 갱신 한 번으로 전달되는지 검증한다.
def test_redis_throttle_delegates_one_atomic_update(monkeypatch: pytest.MonkeyPatch) -> None:
    """실패 기록을 하나의 Lua 호출로 전달하고 기존 잠금 상태를 읽는다.

    입력: 호출 기록을 보관하는 Redis 대역이다.
    출력: 없다.
    기능: Lua 동작은 실제 Redis 시험에서 확인하고 이 시험은 계층 연결을 확인한다.
    """
    from dait.services.login_throttle import RedisThrottle

    fake = _FakeRedis()
    _patch_client(monkeypatch, fake)
    throttle = RedisThrottle(_redis_settings(), "account", 5)
    assert throttle.is_locked("user@example.com", NOW) is False
    throttle.register_failure("user@example.com", NOW)
    assert len(fake.evaluations) == 1
    numkeys, args = fake.evaluations[0]
    assert numkeys == 1
    assert args[1:] == (NOW.timestamp(), 5, 60, 900, 960_000)
    key = args[0]
    assert isinstance(key, str)
    assert "user@example.com" not in key
    fake.store[key] = json.dumps({"f": 5, "lf": NOW.timestamp(), "lu": NOW.timestamp() + 60})
    assert throttle.is_locked("user@example.com", NOW) is True
    assert throttle.is_locked("user@example.com", NOW + timedelta(seconds=61)) is False


# 입력: Redis 연결 함수를 바꾸는 pytest 도구.
# 출력: 반환값 없음.
# 동작: 로그인 성공 시 해당 키만 지우고 다른 식별자의 기록은 분리하는지 검증한다.
def test_redis_throttle_clear_and_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Redis 로그인 제한 키의 삭제와 분리를 검증한다.

    입력: monkeypatch는 실제 Redis 연결을 대역으로 교체한다.
    출력: 없음.
    기능: clear가 지정한 실패 기록만 지우고 식별자 원문을 키에 남기지 않는지 확인한다.
    """
    from dait.services.login_throttle import RedisThrottle

    fake = _FakeRedis()
    _patch_client(monkeypatch, fake)
    throttle = RedisThrottle(_redis_settings(), "ip", 2)
    throttle.register_failure("ip1", NOW)
    key = fake.evaluations[0][1][0]
    assert isinstance(key, str)
    fake.store[key] = json.dumps({"f": 2, "lf": NOW.timestamp(), "lu": NOW.timestamp() + 60})
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


# 입력: Redis 연결 함수를 바꾸는 pytest 도구.
# 출력: 반환값 없음.
# 동작: Redis 조회·저장·Lua 실행 장애에서 메모리 제한으로 전환하는지 검증한다.
def test_redis_throttle_survives_redis_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Redis 호출 장애의 메모리 대체 동작을 검증한다.

    입력: monkeypatch는 모든 Redis 호출이 실패하는 대역을 주입한다.
    출력: 없음.
    기능: Redis 예외를 외부로 내보내지 않고 동일한 잠금 기준을 유지하는지 확인한다.
    """
    from dait.services.login_throttle import RedisThrottle

    class _BrokenRedis(_FakeRedis):
        def get(self, name: str) -> str | None:
            raise ConnectionError("down")

        def set(self, name: str, value: str, *, nx: bool = False, px: int | None = None) -> bool:
            raise ConnectionError("down")

        # 입력: Lua 스크립트, 키 개수, 키와 인자.
        # 출력: 정상 반환 없이 연결 오류 발생.
        # 동작: 실제 Redis Lua 호출 장애를 재현한다.
        def eval(self, script: str, numkeys: int, *keys_and_args: object) -> object:
            """Redis Lua 실행 장애를 발생시킨다.

            입력: 호출 계약을 맞추기 위한 Lua와 키·인자 정보다.
            출력: 없음(ConnectionError 발생).
            기능: 서비스가 Redis 장애를 메모리 제한으로 대체하는지 검증하게 한다.
            """
            raise ConnectionError("down")

    _patch_client(monkeypatch, _BrokenRedis())
    throttle = RedisThrottle(_redis_settings(), "account", 2)
    throttle.register_failure("a", NOW)  # 예외 없이 fallback 기록
    throttle.register_failure("a", NOW)
    assert throttle.is_locked("a", NOW) is True

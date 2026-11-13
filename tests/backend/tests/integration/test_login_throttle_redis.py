"""실제 Redis에서 로그인 실패 기록의 동시성·잠금 정책·기존 형식 호환성을 검증한다."""

import json
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from dait.core.config import Settings
from dait.repositories import login_throttle_repository, redis_repository
from dait.repositories.redis_repository import RedisLike
from dait.services.login_throttle import AttemptThrottle, RedisThrottle

_INVALID_KEY_TYPE = "테스트 Redis 키가 문자열이 아닙니다."


# 입력: 실제 localhost Redis 연결.
# 출력: 생성한 키만 추적하는 RedisLike 테스트 대역.
# 동작: 운영 키를 조회하거나 전체 삭제하지 않고 시험 데이터만 정리하게 한다.
class TrackedRedis:
    """테스트가 사용하는 키만 기록하며 기존 키는 조회하거나 정리하지 않는다."""

    # 입력: 실제 로컬 Redis 연결.
    # 출력: 반환값 없음.
    # 동작: 연결을 감싸고 이 테스트가 만든 키만 추적할 준비를 한다.
    def __init__(self, client: RedisLike) -> None:
        """테스트 연결을 감싼다.

        입력: client는 localhost Redis 연결이다.
        출력: 없다.
        기능: 테스트가 만든 키만 정리할 수 있게 한다.
        """
        self.client = client
        self.keys: set[str] = set()

    # 입력: Redis 키, 값, 덮어쓰기 제한, 만료 시간.
    # 출력: 실제 Redis SET 응답.
    # 동작: 저장할 키를 기록하고 SET 요청을 그대로 전달한다.
    def set(self, name: str, value: str, *, nx: bool = False, px: int | None = None) -> object:
        """테스트 키의 저장을 전달한다.

        입력: 이름·값·덮어쓰기 제한·만료 시간이다.
        출력: 실제 Redis 응답이다.
        기능: 정리할 키의 이름만 기록한다.
        """
        self.keys.add(name)
        return self.client.set(name, value, nx=nx, px=px)

    # 입력: 조회할 Redis 키.
    # 출력: 실제 Redis GET 응답.
    # 동작: 지정한 키의 값을 전체 키 탐색 없이 조회한다.
    def get(self, name: str) -> object:
        """지정한 테스트 키를 읽는다.

        입력: name은 테스트가 만든 키다.
        출력: 실제 Redis 응답이다.
        기능: 전체 키 목록을 조회하지 않는다.
        """
        return self.client.get(name)

    # 입력: 삭제할 Redis 키 목록.
    # 출력: 실제로 삭제된 키 개수.
    # 동작: 이 테스트가 지정한 키만 삭제한다.
    def delete(self, *names: str) -> object:
        """지정한 테스트 키만 삭제한다.

        입력: names는 삭제할 키다.
        출력: 실제 삭제 개수다.
        기능: 전체 DB 초기화 명령을 사용하지 않는다.
        """
        return self.client.delete(*names)

    # 입력: Lua 스크립트, 키 개수, 키와 인자.
    # 출력: 실제 Redis EVAL 응답.
    # 동작: 사용한 키를 추적하고 스크립트를 수정 없이 실행한다.
    def eval(self, script: str, numkeys: int, *keys_and_args: object) -> object:
        """테스트 Lua를 실행하고 해당 키를 기록한다.

        입력: script와 키·인자다.
        출력: 실제 Lua 응답이다.
        기능: 소스에 작성된 Lua를 수정 없이 서버에서 검증한다.
        """
        for key in keys_and_args[:numkeys]:
            if not isinstance(key, str):
                raise TypeError(_INVALID_KEY_TYPE)
            self.keys.add(key)
        return self.client.eval(script, numkeys, *keys_and_args)


# 입력: pytest 환경 격리 도구.
# 출력: localhost DB 15를 감싼 추적 Redis 연결.
# 동작: 테스트별 고유 키만 사용하고 종료 시 해당 키만 정리한다.
@pytest.fixture
def login_redis(monkeypatch: pytest.MonkeyPatch) -> Generator[TrackedRedis]:
    """고유한 시험 키만 생성·정리하는 실제 Redis 연결을 주입한다.

    입력: monkeypatch는 공용 연결 함수를 시험 동안 대체한다.
    출력: localhost DB 15의 추적 연결이다.
    기능: 운영 환경설정이나 기존 Redis 키를 읽거나 초기화하지 않는다.
    """
    client = redis_repository.connect("redis://127.0.0.1:6379/15", timeout=0.2)
    if client is None:
        pytest.skip("로컬 테스트 Redis가 실행되지 않습니다.")
    tracked = TrackedRedis(client)

    # 입력: 무시할 설정 주소와 연결 제한 시간.
    # 출력: 현재 테스트의 추적 Redis 연결.
    # 동작: 코드가 실제 운영 Redis 대신 격리된 테스트 연결을 재사용하게 한다.
    def shared(_url: str | None, timeout: float = 2.0) -> RedisLike:
        """시험용 연결만 반환한다.

        입력: 주소와 연결 제한 시간이다.
        출력: 현재 시험의 Redis 연결이다.
        기능: 설정에 포함된 다른 Redis 주소로 접속하지 않는다.
        """
        return tracked

    monkeypatch.setattr(redis_repository, "shared_client", shared)
    try:
        yield tracked
    finally:
        if tracked.keys:
            client.delete(*tracked.keys)


# 입력: 실제 Redis 연결, 앱 설정, 제한 범위·기준·동시 요청 수.
# 출력: 반환값 없음.
# 동작: 여러 서비스 인스턴스의 동시 실패가 하나도 유실되지 않는지 검증한다.
@pytest.mark.parametrize(
    ("scope", "threshold", "count"), [("account", 5, 5), ("ip", 20, 20), ("account", 5, 100)]
)
def test_concurrent_failures_are_all_counted_across_instances(
    login_redis: TrackedRedis, settings: Settings, scope: str, threshold: int, count: int
) -> None:
    """여러 서비스 인스턴스의 동시 실패를 하나도 잃지 않는다.

    입력: 같은 Redis를 사용하는 두 로그인 제한 인스턴스다.
    출력: 없다.
    기능: 프로세스 내부 락 대신 Redis 원자성이 횟수와 잠금을 보장하는지 확인한다.
    """
    identity = uuid4().hex + "@example.com"
    now = datetime.now(UTC)
    throttles = [RedisThrottle(settings, scope, threshold) for _ in range(2)]

    # 입력: 동시 실행할 요청 순번.
    # 출력: 반환값 없음.
    # 동작: 두 서비스 인스턴스에 실패 기록을 번갈아 전달한다.
    def fail(index: int) -> None:
        """번갈아 다른 인스턴스로 실패를 기록한다.

        입력: 요청 순번이다.
        출력: 없다.
        기능: 같은 키의 읽기·쓰기 경합을 실제 서버에서 재현한다.
        """
        throttles[index % 2].register_failure(identity, now)

    with ThreadPoolExecutor(max_workers=16) as executor:
        list(executor.map(fail, range(count)))
    key = next(iter(login_redis.keys))
    state = login_throttle_repository.read_state(login_redis, key)
    assert state is not None
    assert state.failures == count
    assert all(throttle.is_locked(identity, now) for throttle in throttles)
    assert identity not in key
    ttl = login_redis.eval("return redis.call('PTTL', KEYS[1])", 1, key)
    assert isinstance(ttl, int)
    assert 0 < ttl <= 960_000


# 입력: 실제 Redis 연결과 앱 설정.
# 출력: 반환값 없음.
# 동작: Redis 잠금 증가 정책이 기존 메모리 정책과 모든 경계에서 같은지 검증한다.
def test_redis_backoff_matches_existing_memory_policy(
    login_redis: TrackedRedis, settings: Settings
) -> None:
    """60초·두 배 증가·최대 15분 정책을 그대로 유지한다.

    입력: 실제 Redis와 기존 메모리 구현이다.
    출력: 없다.
    기능: 실패 횟수와 잠금 만료 경계별 결과를 두 구현에서 비교한다.
    """
    identity = uuid4().hex
    now = datetime.now(UTC)
    memory, remote = AttemptThrottle(5), RedisThrottle(settings, "account", 5)
    for _ in range(15):
        memory.register_failure(identity, now)
        remote.register_failure(identity, now)
        for seconds in (0, 59, 60, 119, 120, 899, 900):
            at = now + timedelta(seconds=seconds)
            assert remote.is_locked(identity, at) == memory.is_locked(identity, at)
    key = next(iter(login_redis.keys))
    before = login_redis.eval("return redis.call('PTTL', KEYS[1])", 1, key)
    assert remote.is_locked(identity, now)
    after = login_redis.eval("return redis.call('PTTL', KEYS[1])", 1, key)
    assert isinstance(before, int)
    assert isinstance(after, int)
    assert 0 < after <= before <= 960_000


# 입력: 실제 Redis 연결.
# 출력: 반환값 없음.
# 동작: 이전 JSON 형식의 연속 계산과 15분 경과 후 초기화를 검증한다.
def test_old_format_continues_counting_and_stale_failures_reset(login_redis: TrackedRedis) -> None:
    """이전 배포의 JSON을 이어 읽고 오래된 실패는 초기화한다.

    입력: 고유 키에 저장한 기존 f·lf·lu 형식이다.
    출력: 없다.
    기능: 배포 때 별도 Redis 마이그레이션이나 전체 키 삭제가 필요 없음을 검증한다.
    """
    key = "rate:login:account:" + uuid4().hex
    now = datetime.now(UTC)
    login_redis.set(key, json.dumps({"f": 4, "lf": now.timestamp(), "lu": None}), px=960_000)
    state = login_throttle_repository.register_failure(login_redis, key, 5, now)
    assert state.failures == 5
    assert state.locked_until == now.timestamp() + 60
    reset = login_throttle_repository.register_failure(
        login_redis, key, 5, now + timedelta(seconds=901)
    )
    assert reset.failures == 1
    assert reset.locked_until is None


# 입력: 실제 Redis 연결과 앱 설정.
# 출력: 반환값 없음.
# 동작: 성공한 계정 기록만 지우고 다른 계정 잠금을 보존하는지 검증한다.
def test_success_clear_preserves_other_accounts(
    login_redis: TrackedRedis, settings: Settings
) -> None:
    """성공 시 본인 실패 기록만 지우고 다른 계정 잠금을 보존한다.

    입력: 서로 다른 고유 계정 키다.
    출력: 없다.
    기능: 성공 이후 첫 실패는 다시 1회부터 기록한다.
    """
    first, second = uuid4().hex, uuid4().hex
    now = datetime.now(UTC)
    throttle = RedisThrottle(settings, "account", 2)
    for identity in (first, second):
        throttle.register_failure(identity, now)
        throttle.register_failure(identity, now)
    throttle.clear(first)
    assert not throttle.is_locked(first, now)
    assert throttle.is_locked(second, now)
    throttle.register_failure(first, now)
    assert not throttle.is_locked(first, now)


# 입력: 실제 Redis 연결과 손상된 기존 JSON 값.
# 출력: 반환값 없음.
# 동작: 손상 상태를 정상 실패 한 건과 유효한 TTL로 교체하는지 검증한다.
@pytest.mark.parametrize("raw", ["broken-json", "[]", '{"f":false,"lf":0}', '{"f":-1,"lf":0}'])
def test_corrupt_history_is_replaced_with_valid_expiring_state(
    login_redis: TrackedRedis, raw: str
) -> None:
    """기존 손상 데이터는 정상 실패 한 건으로 재시작한다.

    입력: 손상된 값이 있는 고유 시험 키다.
    출력: 없다.
    기능: Lua 예외로 실패 횟수 기록이 중단되거나 TTL 없는 상태가 남지 않게 한다.
    """
    key = "rate:login:account:" + uuid4().hex
    login_redis.set(key, raw)
    state = login_throttle_repository.register_failure(login_redis, key, 5, datetime.now(UTC))
    assert state.failures == 1
    assert state.locked_until is None
    ttl = login_redis.eval("return redis.call('PTTL', KEYS[1])", 1, key)
    assert isinstance(ttl, int)
    assert 0 < ttl <= 960_000

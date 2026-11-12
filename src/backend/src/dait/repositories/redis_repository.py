"""Redis 접근 저장소: 분산 락(SET NX PX + 소유권 확인 해제)과 JSON 캐시."""

import json
import uuid
from typing import Protocol, cast


class RedisLike(Protocol):
    """redis-py 클라이언트 중 이 모듈이 쓰는 부분만 타입으로 고정한다."""

    def set(self, name: str, value: str, *, nx: bool = False, px: int | None = None) -> object: ...

    def get(self, name: str) -> object: ...

    def delete(self, *names: str) -> object: ...

    def eval(self, script: str, numkeys: int, *keys_and_args: object) -> object: ...


_LOCK_RELEASE_LUA = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
else
    return 0
end
"""


def connect(redis_url: str, timeout: float = 2.0) -> RedisLike | None:
    """Redis 클라이언트를 만들고 ping으로 연결을 확인한다.

    입력: redis_url (redis://...), timeout (초)
    출력: RedisLike 또는 None (미설정·연결 실패 시)
    기능: 스텁이 불완전한 redis-py 경계라 이 함수 안에서만 캐스팅한다.
    """
    try:
        import redis
    except ImportError:
        return None
    try:
        client = redis.Redis.from_url(  # pyright: ignore[reportUnknownMemberType] - redis-py 스텁 불완전
            redis_url, socket_timeout=timeout, socket_connect_timeout=timeout
        )
        client.ping()  # pyright: ignore[reportUnknownMemberType] - redis-py 스텁 불완전
        return cast(RedisLike, client)
    except (redis.RedisError, OSError):
        return None


class _SharedState:
    """공유 클라이언트와 장애 플래그를 한 곳에 묶는다(global 문 회피)."""

    client: RedisLike | None = None
    failed: bool = False


_shared = _SharedState()


def shared_client(redis_url: str | None, timeout: float = 2.0) -> RedisLike | None:
    """프로セ스에서 공유하는 Redis 클라이언트를 지연 생성한다.

    입력: redis_url (None이면 미설정), timeout (초)
    출력: RedisLike 또는 None (미설정·연결 실패·redis-py 없음)
    기능: 한 번 연결에 실패하면 프로세스가 끝날 때까지 fallback으로 둔다.
          cache·throttle 등 여러 서비스가 같은 연결을 나눠 쓴다.
    """
    if _shared.failed or not redis_url:
        return None
    if _shared.client is None:
        client = connect(redis_url, timeout)
        if client is None:
            _shared.failed = True
            return None
        _shared.client = client
    return _shared.client


def reset_shared_client() -> None:
    """테스트용: 공유 클라이언트와 장애 플래그를 초기화한다."""
    _shared.client = None
    _shared.failed = False


def new_lock_token() -> str:
    """락 소유권 토큰을 만든다. 값이 내 것일 때만 해제하기 위한 비교값이다."""
    return uuid.uuid4().hex


def acquire_lock(client: RedisLike, key: str, token: str, ttl_ms: int) -> bool:
    """분산 락을 원자적으로 획득한다.

    입력: client, key (namespaced), token (소유권 값), ttl_ms (자동 만료)
    출력: bool (획득 성공 여부)
    기능: SET NX PX라 TTL 없는 락은 생기지 않고, 만료 전 해제는 소유자만 한다.
    """
    result = client.set(key, token, nx=True, px=ttl_ms)
    return bool(result)


def release_lock(client: RedisLike, key: str, token: str) -> bool:
    """내 토큰일 때만 락을 해제한다.

    입력: client, key, token
    출력: bool (실제로 지웠으면 True)
    기능: Lua compare-and-delete로 TTL 만료 후 다른 주체의 락을 지우는 사고를 막는다.
    """
    result = client.eval(_LOCK_RELEASE_LUA, 1, key, token)
    return bool(result)


def cache_get(client: RedisLike, key: str) -> str | None:
    """캐시 값을 문자열로 읽는다."""
    value = client.get(key)
    if isinstance(value, bytes):
        return value.decode()
    return str(value) if value is not None else None


def cache_set(client: RedisLike, key: str, payload: str, ttl_seconds: int) -> None:
    """TTL을 붙여 캐시 값을 쓴다. TTL 없는 쓰기는 이 모듈에서 허용하지 않는다."""
    client.set(key, payload, px=max(1, ttl_seconds) * 1000)


def dumps_json(value: object) -> str:
    """캐시 payload를 JSON 문자열로 직렬화한다."""
    return json.dumps(value, ensure_ascii=False)


def loads_json(raw: str) -> object:
    """캐시 JSON 문자열을 객체로 되돌린다."""
    return json.loads(raw)

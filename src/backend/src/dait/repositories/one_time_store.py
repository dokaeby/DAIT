"""한 번만 꺼낼 수 있는 짧은 수명 저장소(OAuth state, 교환 코드). Redis, 장애·미설정 시 메모리."""

import hashlib
import threading
from datetime import datetime

from redis.exceptions import RedisError

from dait.repositories import redis_repository

# 읽으면서 지우는 동작이 원자적이어야 같은 값을 두 요청이 동시에 꺼내지 못한다(GETDEL은 Redis 6.2+).
_POP_LUA = """
local v = redis.call('get', KEYS[1])
if v then redis.call('del', KEYS[1]) end
return v
"""


class OneTimeStore:
    """put으로 넣은 값을 pop으로 딱 한 번만 돌려준다. 키 원문은 저장하지 않고 해시만 쓴다."""

    # 입력: 선택적 Redis URL.
    # 출력: 초기화된 저장소.
    # 동작: 메모리 대체 저장소와 잠금을 준비한다(다중 서버 운영에서는 Redis가 필요하다).
    def __init__(self, redis_url: str | None) -> None:
        """저장소를 만든다.

        입력: redis_url (None이면 메모리만 사용)
        출력: 없음
        기능: Redis 연결은 최초 사용 때 지연 생성하고, 장애 시 메모리로 내려간다.
        """
        self._redis_url = redis_url
        self._memory: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _key(kind: str, raw: str) -> str:
        """원문(state·코드)을 해시한 저장 키를 만든다. Redis가 유출돼도 원문은 알 수 없다."""
        return f"oauth:{kind}:{hashlib.sha256(raw.encode()).hexdigest()}"

    # 입력: 값 종류, 원문 키, 저장할 값, 수명(초), 현재 시각.
    # 출력: 반환값 없음.
    # 동작: TTL을 붙여 저장한다. Redis 장애면 메모리에 저장한다.
    def put(self, kind: str, raw: str, value: str, ttl_seconds: int, now: datetime) -> None:
        """값을 TTL과 함께 저장한다.

        입력: kind (state 또는 xcode), raw (원문 키), value (저장 값), ttl_seconds, now
        출력: 없음
        기능: TTL 없는 저장은 허용하지 않는다.
        """
        key = self._key(kind, raw)
        client = redis_repository.shared_client(self._redis_url)
        if client is not None:
            try:
                redis_repository.cache_set(client, key, value, ttl_seconds)
            except (RedisError, OSError):
                pass  # 아래 메모리 저장으로 대체한다.
            else:
                return
        with self._lock:
            self._memory[key] = (value, now.timestamp() + ttl_seconds)

    # 입력: 값 종류, 원문 키, 현재 시각.
    # 출력: 저장된 값 또는 없음.
    # 동작: 값을 읽는 동시에 지워 두 번째 호출은 항상 없음을 돌려준다.
    def pop(self, kind: str, raw: str, now: datetime) -> str | None:
        """값을 한 번만 꺼낸다.

        입력: kind, raw (원문 키), now (만료 판단용 UTC 시각)
        출력: str 또는 None (없음·이미 사용·만료)
        기능: Redis는 Lua로 원자적으로 꺼내고, 메모리는 잠금 안에서 꺼낸다.
        """
        key = self._key(kind, raw)
        client = redis_repository.shared_client(self._redis_url)
        if client is not None:
            try:
                found = client.eval(_POP_LUA, 1, key)
            except (RedisError, OSError):
                found = None
            if found is not None:
                return found.decode() if isinstance(found, bytes) else str(found)
        with self._lock:
            entry = self._memory.pop(key, None)
        if entry is None or entry[1] <= now.timestamp():
            return None
        return entry[0]

    # 입력: 값 종류, 원문 키, 현재 시각.
    # 출력: 저장된 값 또는 없음.
    # 동작: 값을 지우지 않고 읽는다(비밀번호를 틀려도 표를 다시 쓰게 하려는 용도).
    def peek(self, kind: str, raw: str, now: datetime) -> str | None:
        """값을 지우지 않고 읽는다.

        입력: kind, raw (원문 키), now (만료 판단용 UTC 시각)
        출력: str 또는 None (없음·만료)
        기능: 지우는 것은 pop만 한다. 호출하는 쪽이 시도 횟수를 따로 제한해야 한다.
        """
        key = self._key(kind, raw)
        client = redis_repository.shared_client(self._redis_url)
        if client is not None:
            try:
                found = redis_repository.cache_get(client, key)
            except (RedisError, OSError):
                found = None
            if found is not None:
                return found
        with self._lock:
            entry = self._memory.get(key)
        if entry is None or entry[1] <= now.timestamp():
            return None
        return entry[0]

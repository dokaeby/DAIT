"""FR-PIPE-04 캐시·재시도 보조: TTL+jitter 캐시와 분산 락 stampede 방지.

Redis가 설정돼 있으면 redis-py를 쓰고, 없거나 장애면 프로세스 내
메모리 fallback을 쓴다(단일 워커 기준). 캐시 미스·락 실패가 본 기능을 막지 않는다.
"""

import hashlib
import random
import threading
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import TypeVar

from redis.exceptions import RedisError

from dait.core.config import Settings
from dait.repositories import redis_repository

_LIST_TTL_SECONDS = 300  # 목록 캐시 5분
_DETAIL_TTL_SECONDS = 1800  # 상세 캐시 30분
_JITTER_RATIO = 0.1  # TTL의 ±10% 지터로 만료 시각을 분산한다
_LOCK_WAIT_SECONDS = 2.0
_LOCK_TTL_MS = 10_000
_POLL_SECONDS = 0.05

_T = TypeVar("_T")


class _RedisState:
    """Redis 클라이언트와 장애 플래그를 한 곳에 묶는다(global 문 회피)."""

    client: redis_repository.RedisLike | None = None
    failed: bool = False


_lock = threading.Lock()
_memory_cache: dict[str, tuple[float, str]] = {}
_memory_locks: dict[str, tuple[str, float]] = {}
_redis_state = _RedisState()


def _jittered_ttl(base_seconds: int) -> int:
    """TTL에 ±10% 지터를 더해 만료 시각을 분산한다."""
    delta = int(base_seconds * _JITTER_RATIO)
    return max(1, base_seconds + random.randint(-delta, delta))  # noqa: S311 - 지터용 난수, 보안 용도 아님


def _get_redis(settings: Settings) -> redis_repository.RedisLike | None:
    """설정된 Redis 클라이언트를 지연 생성한다. 없거나 연결 실패면 None."""
    if _redis_state.failed or not settings.redis_url:
        return None
    if _redis_state.client is None:
        client = redis_repository.connect(settings.redis_url)
        if client is None:
            _redis_state.failed = True
            return None
        _redis_state.client = client
    return _redis_state.client


def _redis_call[T](fn: Callable[[], T]) -> T | None:
    """Redis 호출 래퍼: 실패 시 None을 돌려 fallback으로 보낸다."""
    try:
        return fn()
    except (RedisError, OSError):
        return None


def cache_get(settings: Settings, key: str) -> str | None:
    """캐시 값을 읽는다. Redis 우선, 실패·미스면 메모리 fallback."""
    client = _get_redis(settings)
    if client is not None:
        value = _redis_call(lambda: redis_repository.cache_get(client, key))
        if value is not None:
            return value
    with _lock:
        entry = _memory_cache.get(key)
        if entry is None:
            return None
        expires_at, payload = entry
        if expires_at <= time.monotonic():
            del _memory_cache[key]
            return None
        return payload


def cache_set(settings: Settings, key: str, payload: str, ttl_seconds: int) -> None:
    """TTL+jitter로 캐시 값을 쓴다. 실패해도 조용히 넘어간다(캐시는 최적화다)."""
    ttl = _jittered_ttl(ttl_seconds)
    client = _get_redis(settings)
    if client is not None:
        _redis_call(lambda: redis_repository.cache_set(client, key, payload, ttl))
        return
    with _lock:
        _memory_cache[key] = (time.monotonic() + ttl, payload)


def _memory_try_lock(key: str, token: str, ttl_ms: int) -> bool:
    """메모리 락 획득. 만료된 락은 회수한다."""
    now = time.monotonic()
    with _lock:
        current = _memory_locks.get(key)
        if current is not None and current[1] > now:
            return False
        _memory_locks[key] = (token, now + ttl_ms / 1000)
        return True


def _memory_release(key: str, token: str) -> bool:
    """내 토큰의 메모리 락만 해제한다."""
    with _lock:
        current = _memory_locks.get(key)
        if current is None or current[0] != token:
            return False
        del _memory_locks[key]
        return True


@contextmanager
def locked(
    settings: Settings, lock_name: str, cache_key: str | None = None
) -> Generator[bool, None, None]:
    """이름으로 분산 락을 잡는다. 못 잡으면 잠시 기다린 뒤 False로 진행한다.

    입력: settings, lock_name (락 이름), cache_key (대기 중 다시 확인할 캐시 키)
    출력: Generator[bool] (락을 잡았으면 True, 대기 후 포기하면 False)
    기능: 캐시 stampede 방지용이다. 락 실패가 본 조회를 막지는 않는다.
          cache_key가 있으면 대기 중 그 키를 다시 확인해 선점자가 채운 값을 재사용하게 한다.
    """
    key = f"dait:lock:{lock_name}"
    token = redis_repository.new_lock_token()
    client = _get_redis(settings)
    if client is not None:
        acquired = bool(
            _redis_call(lambda: redis_repository.acquire_lock(client, key, token, _LOCK_TTL_MS))
        )
    else:
        acquired = _memory_try_lock(key, token, _LOCK_TTL_MS)

    if not acquired:
        deadline = time.monotonic() + _LOCK_WAIT_SECONDS
        while time.monotonic() < deadline:
            time.sleep(_POLL_SECONDS)
            if cache_key is not None and cache_get(settings, cache_key) is not None:
                break
        yield False
        return

    try:
        yield True
    finally:
        if client is not None:
            _redis_call(lambda: redis_repository.release_lock(client, key, token))
        else:
            _memory_release(key, token)


def clear_memory_state() -> None:
    """테스트용: 메모리 캐시·락·Redis 상태를 초기화한다."""
    with _lock:
        _memory_cache.clear()
        _memory_locks.clear()
    _redis_state.client = None
    _redis_state.failed = False


def list_cache_key(category: str, query: str, sort: str, page_size: int, cursor: str | None) -> str:
    """목록 캐시 키를 만든다. 검색어 원문 대신 해시를 넣어 키에 개인정보를 남기지 않는다."""
    digest = hashlib.sha256(
        f"{category}|{query}|{sort}|{page_size}|{cursor or ''}".encode()
    ).hexdigest()[:24]
    return f"news:list:{digest}"


def detail_cache_key(news_id: str) -> str:
    """상세 캐시 키."""
    return f"news:detail:{news_id}"


def list_ttl() -> int:
    """목록 캐시 TTL(초)."""
    return _LIST_TTL_SECONDS


def detail_ttl() -> int:
    """상세 캐시 TTL(초)."""
    return _DETAIL_TTL_SECONDS

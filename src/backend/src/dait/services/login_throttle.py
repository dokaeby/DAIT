"""로그인 실패 누적 잠금. Redis가 있으면 분산 구현, 없거나 장애면 메모리 구현을 쓴다."""

import hashlib
import json
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol, cast

from redis.exceptions import RedisError

from dait.core.config import Settings
from dait.repositories import redis_repository

_BASE_LOCK_SECONDS = 60
_MAX_LOCK_SECONDS = 900
_MAX_ENTRIES = 10_000  # 공격자가 이메일을 무한히 바꿔도 메모리가 무한정 늘지 않게 하는 상한


class Throttle(Protocol):
    """실패 횟수에 따라 잠그는 장치의 약속. Redis 구현이 같은 메서드를 가진다."""

    def is_locked(self, key: str, now: datetime) -> bool:
        """해당 키가 지금 잠겨 있는지 알려 준다."""
        ...

    def register_failure(self, key: str, now: datetime) -> None:
        """실패 한 번을 기록한다."""
        ...

    def clear(self, key: str) -> None:
        """성공했을 때 실패 기록을 지운다."""
        ...


@dataclass
class _Entry:
    failures: int
    last_failure: datetime
    locked_until: datetime | None


class AttemptThrottle:
    """키(계정 또는 IP)별 실패를 세어 점진적으로 잠그는 메모리 구현."""

    def __init__(self, threshold: int) -> None:
        """잠금 기준을 정해 만든다.

        입력: threshold (이 횟수 이상 실패하면 잠금이 시작됨)
        출력: 없음
        기능: 잠금 시간은 60초에서 시작해 실패가 늘 때마다 두 배, 최대 15분이다.
              서버를 다시 시작하면 초기화된다.
        """
        self._threshold = threshold
        self._entries: dict[str, _Entry] = {}
        self._lock = threading.Lock()  # 요청이 스레드풀에서 동시에 들어오므로 보호한다.

    def is_locked(self, key: str, now: datetime) -> bool:
        """해당 키가 지금 잠겨 있는지 알려 준다.

        입력: key (계정 이메일 또는 IP), now (현재 UTC 시각)
        출력: bool (잠겨 있으면 True)
        기능: 잠금 시간이 지났으면 False. 기록은 다음 실패 때 정리된다.
        """
        with self._lock:
            entry = self._entries.get(key)
            return entry is not None and entry.locked_until is not None and now < entry.locked_until

    def register_failure(self, key: str, now: datetime) -> None:
        """실패 한 번을 기록하고 기준을 넘으면 잠금 시각을 정한다.

        입력: key (계정 이메일 또는 IP), now (현재 UTC 시각)
        출력: 없음
        기능: 마지막 실패로부터 최대 잠금 시간이 지났으면 횟수를 처음부터 센다.
        """
        with self._lock:
            if len(self._entries) >= _MAX_ENTRIES:
                self._drop_stale(now)
            entry = self._entries.get(key)
            if entry is None or now - entry.last_failure > timedelta(seconds=_MAX_LOCK_SECONDS):
                entry = _Entry(failures=0, last_failure=now, locked_until=None)
            entry.failures += 1
            entry.last_failure = now
            if entry.failures >= self._threshold:
                seconds = min(
                    _BASE_LOCK_SECONDS * 2 ** (entry.failures - self._threshold), _MAX_LOCK_SECONDS
                )
                entry.locked_until = now + timedelta(seconds=seconds)
            self._entries[key] = entry

    def clear(self, key: str) -> None:
        """실패 기록을 지운다.

        입력: key (계정 이메일 또는 IP)
        출력: 없음
        기능: 로그인에 성공했을 때 부른다. 기록이 없어도 오류 없이 지나간다.
        """
        with self._lock:
            self._entries.pop(key, None)

    def _drop_stale(self, now: datetime) -> None:
        """오래된 기록을 버려 메모리를 줄인다(호출한 쪽이 락을 잡고 있어야 함).

        입력: now (현재 UTC 시각)
        출력: 없음
        기능: 마지막 실패로부터 최대 잠금 시간이 지난 항목을 지운다.
        """
        limit = timedelta(seconds=_MAX_LOCK_SECONDS)
        stale = [k for k, e in self._entries.items() if now - e.last_failure > limit]
        for key in stale:
            del self._entries[key]


_STATE_TTL_MS = (_MAX_LOCK_SECONDS + 60) * 1000  # 상태가 잠금 시간보다 오래 살 이유가 없다.


class RedisThrottle:
    """설계서 8절 `rate:{scope}:{identity}` 규격의 분산 잠금 구현.

    입력: settings (REDIS_URL), scope ("account"|"ip"), threshold (잠금 시작 실패 횟수)
    출력: Throttle과 같은 메서드
    기능: 이메일·IP 원문을 키에 넣지 않고 SHA-256 해시를 쓴다.
          Redis가 없거나 호출이 실패하면 프로세스 내 AttemptThrottle로 fallback한다.
          상태는 JSON 하나에 failures·last_failure·locked_until을 담고 TTL을 붙인다.
    """

    def __init__(self, settings: Settings, scope: str, threshold: int) -> None:
        self._settings = settings
        self._scope = scope
        self._threshold = threshold
        self._fallback = AttemptThrottle(threshold)

    def _key(self, identity: str) -> str:
        """개인정보를 남기지 않는 Redis 키를 만든다."""
        digest = hashlib.sha256(identity.encode()).hexdigest()[:24]
        return f"rate:login:{self._scope}:{digest}"

    def _load(self, client: redis_repository.RedisLike, key: str) -> dict[str, object] | None:
        """저장된 상태 JSON을 읽는다. 없거나 깨졌으면 None."""
        raw = client.get(key)
        text = raw.decode() if isinstance(raw, bytes) else raw
        if not isinstance(text, str):
            return None
        try:
            state: object = json.loads(text)
        except ValueError:
            return None
        if not isinstance(state, dict):
            return None
        return cast("dict[str, object]", state)

    def _store(
        self, client: redis_repository.RedisLike, key: str, state: dict[str, object]
    ) -> None:
        """상태 JSON을 TTL과 함께 저장한다."""
        client.set(key, json.dumps(state), px=_STATE_TTL_MS)

    def is_locked(self, key: str, now: datetime) -> bool:
        """해당 키가 지금 잠겨 있는지 알려 준다(Redis 우선, 실패 시 메모리)."""
        client = redis_repository.shared_client(self._settings.redis_url)
        if client is None:
            return self._fallback.is_locked(key, now)
        try:
            state = self._load(client, self._key(key))
        except (RedisError, OSError):
            return self._fallback.is_locked(key, now)
        if state is None:
            return False
        locked_until = state.get("lu")
        return isinstance(locked_until, (int, float)) and now.timestamp() < locked_until

    def register_failure(self, key: str, now: datetime) -> None:
        """실패 한 번을 기록하고 기준을 넘으면 잠금 시각을 정한다."""
        client = redis_repository.shared_client(self._settings.redis_url)
        if client is None:
            self._fallback.register_failure(key, now)
            return
        rkey = self._key(key)
        try:
            state = self._load(client, rkey) or {}
            failures = state.get("f")
            last = state.get("lf")
            count = failures + 1 if isinstance(failures, int) else 1
            # 마지막 실패로부터 최대 잠금 시간이 지났으면 처음부터 센다(메모리 구현과 동일 규칙).
            if not isinstance(last, (int, float)) or now.timestamp() - last > _MAX_LOCK_SECONDS:
                count = 1
            locked_until: float | None = None
            if count >= self._threshold:
                seconds = min(
                    _BASE_LOCK_SECONDS * 2 ** (count - self._threshold), _MAX_LOCK_SECONDS
                )
                locked_until = now.timestamp() + seconds
            self._store(
                client,
                rkey,
                {"f": count, "lf": now.timestamp(), "lu": locked_until},
            )
        except (RedisError, OSError):
            self._fallback.register_failure(key, now)

    def clear(self, key: str) -> None:
        """실패 기록을 지운다. 성공한 로그인에서 부른다."""
        client = redis_repository.shared_client(self._settings.redis_url)
        if client is None:
            self._fallback.clear(key)
            return
        try:
            client.delete(self._key(key))
        except (RedisError, OSError):
            self._fallback.clear(key)


_ACCOUNT_CLIENT_THRESHOLD = 5
_ACCOUNT_GLOBAL_THRESHOLD = 50  # 남이 IP를 바꿔 가며 실패를 쌓아도 쉽게 잠기지 않게 높게 둔다.
_IP_THRESHOLD = 20
_UNKNOWN_IP = "unknown"


@dataclass(frozen=True)
class LoginThrottles:
    """로그인에 쓰는 세 잠금 장치.

    account: 계정+접속 IP 단위. 한 곳에서 같은 계정을 계속 틀리면 빨리 잠근다.
    account_global: 계정 단위. 여러 IP에 나눠 대입하는 공격을 느슨한 기준으로 막는다.
    ip: IP 단위. 한 곳에서 여러 계정을 대입하는 공격을 막는다.
    """

    account: Throttle
    account_global: Throttle
    ip: Throttle

    def is_locked(self, email: str, client_ip: str | None, now: datetime) -> bool:
        """이 이메일·IP 조합으로 지금 시도할 수 없는지 알려 준다.

        입력: email (소문자 이메일), client_ip (접속 IP, 모르면 None), now (UTC 시각)
        출력: bool (셋 중 하나라도 잠겨 있으면 True)
        기능: 다른 IP에서 쌓인 실패만으로는 계정+IP 잠금이 걸리지 않는다.
        """
        ip_key = client_ip or _UNKNOWN_IP
        return (
            self.account.is_locked(_account_client_key(email, ip_key), now)
            or self.account_global.is_locked(email, now)
            or self.ip.is_locked(ip_key, now)
        )

    def register_failure(self, email: str, client_ip: str | None, now: datetime) -> None:
        """실패 한 번을 세 장치에 모두 기록한다."""
        ip_key = client_ip or _UNKNOWN_IP
        self.account.register_failure(_account_client_key(email, ip_key), now)
        self.account_global.register_failure(email, now)
        self.ip.register_failure(ip_key, now)

    def clear(self, email: str, client_ip: str | None) -> None:
        """성공했을 때 이 계정의 실패 기록을 지운다(IP 기록은 남긴다)."""
        ip_key = client_ip or _UNKNOWN_IP
        self.account.clear(_account_client_key(email, ip_key))
        self.account_global.clear(email)


def _account_client_key(email: str, ip_key: str) -> str:
    """계정+IP 잠금 키. 이메일에는 개행이 들어갈 수 없어 구분자로 쓴다."""
    return f"{email}\n{ip_key}"


def create_throttles(settings: Settings | None = None) -> LoginThrottles:
    """잠금 장치를 만든다. REDIS_URL이 있으면 분산 구현, 없으면 메모리 구현.

    입력: settings (앱 설정, None이면 메모리 구현)
    출력: LoginThrottles (계정+IP 5회, 계정 전체 50회, IP 20회 실패부터 잠금)
    기능: 계정 잠금을 IP와 묶어, 이메일만 아는 남이 본인을 쉽게 잠그지 못하게 한다.
          IP는 같은 공유기를 쓰는 여러 사용자가 있을 수 있어 기준을 더 느슨하게 둔다.
          Redis 연결이 안 되면 각 호출 시점에 메모리 fallback으로 자동 전환된다.
    """
    if settings is not None and settings.redis_url:
        return LoginThrottles(
            account=RedisThrottle(settings, "account_ip", _ACCOUNT_CLIENT_THRESHOLD),
            account_global=RedisThrottle(settings, "account", _ACCOUNT_GLOBAL_THRESHOLD),
            ip=RedisThrottle(settings, "ip", _IP_THRESHOLD),
        )
    return LoginThrottles(
        account=AttemptThrottle(_ACCOUNT_CLIENT_THRESHOLD),
        account_global=AttemptThrottle(_ACCOUNT_GLOBAL_THRESHOLD),
        ip=AttemptThrottle(_IP_THRESHOLD),
    )

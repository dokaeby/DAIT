"""로그인 실패 누적 잠금. Redis가 있으면 분산 구현, 없거나 장애면 메모리 구현을 쓴다."""

import hashlib
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from redis.exceptions import RedisError

from dait.core.config import Settings
from dait.repositories import login_throttle_repository, redis_repository

_BASE_LOCK_SECONDS = login_throttle_repository.BASE_LOCK_SECONDS
_MAX_LOCK_SECONDS = login_throttle_repository.MAX_LOCK_SECONDS
_MAX_ENTRIES = 10_000  # 공격자가 이메일을 무한히 바꿔도 메모리가 무한정 늘지 않게 하는 상한


class Throttle(Protocol):
    """실패 횟수에 따라 잠그는 장치의 약속. Redis 구현이 같은 메서드를 가진다."""

    # 입력: 계정 또는 IP 키와 현재 UTC 시각.
    # 출력: 현재 잠금 여부.
    # 동작: 구현체의 실패 기록을 기준으로 로그인 허용 여부를 확인한다.
    def is_locked(self, key: str, now: datetime) -> bool:
        """해당 키가 지금 잠겨 있는지 알려 준다.

        입력: key (계정 또는 IP 키), now (현재 UTC 시각)
        출력: bool (잠겨 있으면 True)
        기능: 구현체가 관리하는 실패 기록으로 현재 잠금 여부를 계산한다.
        """
        ...

    # 입력: 계정 또는 IP 키와 현재 UTC 시각.
    # 출력: 반환값 없음.
    # 동작: 로그인 실패 한 번을 구현체의 저장소에 누적한다.
    def register_failure(self, key: str, now: datetime) -> None:
        """로그인 실패 한 번을 기록한다.

        입력: key (계정 또는 IP 키), now (현재 UTC 시각)
        출력: 없음
        기능: 구현체의 저장소에 실패 횟수와 시각을 갱신한다.
        """
        ...

    # 입력: 로그인에 성공한 계정 또는 IP 키.
    # 출력: 반환값 없음.
    # 동작: 성공한 키의 누적 실패 기록을 지운다.
    def clear(self, key: str) -> None:
        """성공한 키의 실패 기록을 지운다.

        입력: key (계정 또는 IP 키)
        출력: 없음
        기능: 이후 로그인이 이전 실패 횟수의 영향을 받지 않게 한다.
        """
        ...


@dataclass
class _Entry:
    failures: int
    last_failure: datetime
    locked_until: datetime | None


class AttemptThrottle:
    """키(계정 또는 IP)별 실패를 세어 점진적으로 잠그는 메모리 구현."""

    # 입력: 잠금이 시작되는 실패 횟수.
    # 출력: 메모리 기반 실패 제한 객체.
    # 동작: 동시 요청을 보호할 빈 실패 기록과 잠금 장치를 초기화한다.
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

    # 입력: 계정 또는 IP 키와 현재 UTC 시각.
    # 출력: 현재 잠금 여부.
    # 동작: 메모리 기록의 잠금 종료 시각과 현재 시각을 비교한다.
    def is_locked(self, key: str, now: datetime) -> bool:
        """해당 키가 지금 잠겨 있는지 알려 준다.

        입력: key (계정 이메일 또는 IP), now (현재 UTC 시각)
        출력: bool (잠겨 있으면 True)
        기능: 잠금 시간이 지났으면 False. 기록은 다음 실패 때 정리된다.
        """
        with self._lock:
            entry = self._entries.get(key)
            return entry is not None and entry.locked_until is not None and now < entry.locked_until

    # 입력: 계정 또는 IP 키와 현재 UTC 시각.
    # 출력: 반환값 없음.
    # 동작: 실패 횟수를 누적하고 기준 이후 잠금 시간을 점진적으로 늘린다.
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

    # 입력: 로그인에 성공한 계정 또는 IP 키.
    # 출력: 반환값 없음.
    # 동작: 메모리에 남은 해당 키의 실패 기록을 제거한다.
    def clear(self, key: str) -> None:
        """실패 기록을 지운다.

        입력: key (계정 이메일 또는 IP)
        출력: 없음
        기능: 로그인에 성공했을 때 부른다. 기록이 없어도 오류 없이 지나간다.
        """
        with self._lock:
            self._entries.pop(key, None)

    # 입력: 현재 UTC 시각.
    # 출력: 반환값 없음.
    # 동작: 최대 잠금 시간보다 오래된 메모리 기록을 제거한다.
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


class RedisThrottle:
    """설계서 8절 `rate:{scope}:{identity}` 규격의 분산 잠금 구현.

    입력: settings (REDIS_URL), scope ("account"|"ip"), threshold (잠금 시작 실패 횟수)
    출력: Throttle과 같은 메서드
    기능: 이메일·IP 원문을 키에 넣지 않고 SHA-256 해시를 쓴다.
          Redis가 없거나 호출이 실패하면 프로세스 내 AttemptThrottle로 fallback한다.
          상태는 JSON 하나에 failures·last_failure·locked_until을 담고 TTL을 붙인다.
    """

    # 입력: 앱 설정, 제한 범위, 잠금 시작 실패 횟수.
    # 출력: Redis 기반 실패 제한 객체.
    # 동작: Redis 장애에 대비한 같은 정책의 메모리 구현을 함께 초기화한다.
    def __init__(self, settings: Settings, scope: str, threshold: int) -> None:
        """Redis 기반 실패 제한 객체를 만든다.

        입력: settings (앱 설정), scope (account 또는 ip), threshold (잠금 시작 횟수)
        출력: 없음
        기능: Redis 장애 때 사용할 같은 정책의 메모리 구현을 함께 준비한다.
        """
        self._settings = settings
        self._scope = scope
        self._threshold = threshold
        self._fallback = AttemptThrottle(threshold)

    # 입력: 계정 이메일 또는 클라이언트 IP 원문.
    # 출력: 원문이 포함되지 않은 Redis 키.
    # 동작: 식별자를 SHA-256으로 줄여 실패 제한 범위 키를 만든다.
    def _key(self, identity: str) -> str:
        """개인정보를 남기지 않는 Redis 키를 만든다.

        입력: identity (계정 이메일 또는 클라이언트 IP 원문)
        출력: str (범위와 해시가 포함된 Redis 키)
        기능: 원문 대신 SHA-256 앞 24자를 사용해 개인정보 노출을 줄인다.
        """
        digest = hashlib.sha256(identity.encode()).hexdigest()[:24]
        return f"rate:login:{self._scope}:{digest}"

    # 입력: 계정 또는 IP 식별 키와 현재 UTC 시각.
    # 출력: 현재 로그인 시도가 잠겼는지 여부.
    # 동작: 메모리 장애 대체 기록을 먼저 확인하고 Redis 상태를 검증한다.
    def is_locked(self, key: str, now: datetime) -> bool:
        """해당 키가 지금 잠겨 있는지 알려 준다.

        입력: key는 계정 또는 IP 식별자이고 now는 현재 UTC 시각이다.
        출력: Redis 또는 메모리 상태에 따른 잠금 여부다.
        기능: Redis 쓰기 장애 때 남긴 메모리 잠금을 조회 성공으로 잃지 않는다.
        """
        # 쓰기만 실패한 경우에도 메모리에 기록한 잠금이 다음 조회에서 사라지지 않게 한다.
        if self._fallback.is_locked(key, now):
            return True
        client = redis_repository.shared_client(self._settings.redis_url)
        if client is None:
            return self._fallback.is_locked(key, now)
        try:
            state = login_throttle_repository.read_state(client, self._key(key))
        except (RedisError, OSError):
            return self._fallback.is_locked(key, now)
        if state is None:
            return False
        return state.locked_until is not None and now.timestamp() < state.locked_until

    # 입력: 계정 또는 IP 식별 키와 현재 UTC 시각.
    # 출력: 반환값 없음.
    # 동작: Redis에서 실패 횟수를 원자적으로 늘리고 장애면 메모리에 기록한다.
    def register_failure(self, key: str, now: datetime) -> None:
        """로그인 실패 한 번을 기록한다.

        입력: key는 계정 또는 IP 식별자이고 now는 현재 UTC 시각이다.
        출력: 없음.
        기능: Redis 원자 갱신이 실패하면 같은 잠금 정책의 메모리 구현을 사용한다.
        """
        client = redis_repository.shared_client(self._settings.redis_url)
        if client is None:
            self._fallback.register_failure(key, now)
            return
        try:
            login_throttle_repository.register_failure(client, self._key(key), self._threshold, now)
        except (RedisError, OSError, ValueError, TypeError):
            self._fallback.register_failure(key, now)

    # 입력: 성공한 로그인의 계정 또는 IP 식별 키.
    # 출력: 반환값 없음.
    # 동작: 메모리와 Redis의 실패 기록을 모두 지운다.
    def clear(self, key: str) -> None:
        """성공한 로그인의 실패 기록을 지운다.

        입력: key는 계정 또는 IP 식별자다.
        출력: 없음.
        기능: 장애 대체 기록이 남지 않도록 메모리를 먼저 지우고 Redis도 정리한다.
        """
        self._fallback.clear(key)
        client = redis_repository.shared_client(self._settings.redis_url)
        if client is None:
            return
        try:
            client.delete(self._key(key))
        except (RedisError, OSError):
            return


@dataclass(frozen=True)
class LoginThrottles:
    """로그인에 쓰는 두 잠금 장치: 계정 단위와 IP 단위."""

    account: Throttle
    ip: Throttle


# 입력: 선택적 앱 설정.
# 출력: 계정·IP 단위 로그인 실패 제한 장치 묶음.
# 동작: Redis URL이 있으면 분산 구현, 없으면 메모리 구현을 만든다.
def create_throttles(settings: Settings | None = None) -> LoginThrottles:
    """잠금 장치를 만든다. REDIS_URL이 있으면 분산 구현, 없으면 메모리 구현.

    입력: settings (앱 설정, None이면 메모리 구현)
    출력: LoginThrottles (계정 5회, IP 20회 실패부터 잠금)
    기능: IP는 같은 공유기를 쓰는 여러 사용자가 있을 수 있어 기준을 더 느슨하게 둔다.
          Redis 연결이 안 되면 각 호출 시점에 메모리 fallback으로 자동 전환된다.
    """
    if settings is not None and settings.redis_url:
        return LoginThrottles(
            account=RedisThrottle(settings, "account", 5),
            ip=RedisThrottle(settings, "ip", 20),
        )
    return LoginThrottles(account=AttemptThrottle(5), ip=AttemptThrottle(20))

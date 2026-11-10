"""로그인 실패 누적 잠금. 지금은 메모리 구현이며 Redis 구현으로 같은 Protocol을 대체한다."""

import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

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


@dataclass(frozen=True)
class LoginThrottles:
    """로그인에 쓰는 두 잠금 장치: 계정 단위와 IP 단위."""

    account: Throttle
    ip: Throttle


def create_throttles() -> LoginThrottles:
    """기본 잠금 장치(메모리)를 만든다.

    입력: 없음
    출력: LoginThrottles (계정 5회, IP 20회 실패부터 잠금)
    기능: IP는 같은 공유기를 쓰는 여러 사용자가 있을 수 있어 기준을 더 느슨하게 둔다.
    """
    return LoginThrottles(account=AttemptThrottle(5), ip=AttemptThrottle(20))

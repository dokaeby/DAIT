"""robots.txt 확인: 수집 전 대상 사이트의 크롤 허용 규칙을 읽는다 (FR-PIPE-01)."""

import time
import urllib.robotparser
from collections.abc import Callable
from urllib.parse import urlsplit, urlunsplit

from dait.core.url_safety import (
    FetchedBody,
    FetchFailedError,
    Resolver,
    UnsafeUrlError,
    fetch_public_bytes,
    validate_public_https_url,
)

USER_AGENT_NAME = "DAITBot"
_CACHE_TTL_SECONDS = 3600

FetchFn = Callable[[str], FetchedBody | None]

# 캐시 값: RobotFileParser(규칙 있음), _ALLOW_ALL(404=제한 없음), None(가져오기 실패=보수적 거부)
_ALLOW_ALL = "ALLOW_ALL"
_UNAVAILABLE = "UNAVAILABLE"

_robots_cache: dict[str, tuple[float, object]] = {}


def robots_url(base_url: str) -> str:
    """출처 base_url에서 robots.txt URL을 만든다.

    입력: base_url (예: https://example.com/feed)
    출력: str (예: https://example.com/robots.txt)
    기능: origin + /robots.txt만 사용한다.
    """
    parts = urlsplit(base_url)
    return urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))


def _parse(body: bytes) -> urllib.robotparser.RobotFileParser:
    """robots.txt 본문을 RobotFileParser로 파싱한다."""
    parser = urllib.robotparser.RobotFileParser()
    parser.parse(body.decode("utf-8", errors="replace").splitlines())
    return parser


def _default_fetch(url: str) -> FetchedBody | None:
    """실제 안전 fetch로 robots.txt를 가져온다. 404는 None이 아니라 표시용 예외 없이 구분한다."""
    import httpx

    return fetch_public_bytes(httpx.Client(timeout=10.0), url)


def _load_rules(
    base_url: str, fetch: FetchFn | None, now: float, resolver: Resolver | None
) -> object:
    """robots 규칙을 캐시와 함께 불러온다.

    출력: RobotFileParser | _ALLOW_ALL | _UNAVAILABLE
    """
    key = robots_url(base_url)
    cached = _robots_cache.get(key)
    if cached is not None and cached[0] > now:
        return cached[1]

    rules: object
    fetcher = fetch if fetch is not None else _default_fetch
    try:
        validate_public_https_url(key, resolver)
        body = fetcher(key)
    except FetchFailedError as exc:
        rules = _ALLOW_ALL if exc.status_code == 404 else _UNAVAILABLE
    except (UnsafeUrlError, OSError, ValueError):
        rules = _UNAVAILABLE
    else:
        rules = _ALLOW_ALL if body is None else _parse(body.body)
    _robots_cache[key] = (now + _CACHE_TTL_SECONDS, rules)
    return rules


def check_robots(
    base_url: str,
    target_url: str,
    *,
    fetch: FetchFn | None = None,
    resolver: Resolver | None = None,
    now: float | None = None,
) -> bool:
    """대상 URL을 현재 User-Agent로 가져와도 되는지 robots.txt로 판정한다.

    입력: base_url (출처 기준 URL), target_url (가져올 피드 URL),
          fetch (테스트용 fetch 함수, None이면 실제 안전 fetch), now (캐시용 시각)
    출력: bool (허용 여부)
    기능: 404면 허용, 명시적 Disallow면 거부, robots를 가져오지 못하면
          보수적으로 거부한다. 규칙은 1시간 메모리 캐시한다.
    """
    current = now if now is not None else time.monotonic()
    rules = _load_rules(base_url, fetch, current, resolver)
    if rules is _UNAVAILABLE:
        return False
    if rules is _ALLOW_ALL:
        return True
    if not isinstance(rules, urllib.robotparser.RobotFileParser):
        return False
    return rules.can_fetch(USER_AGENT_NAME, target_url)


def clear_cache() -> None:
    """메모리 캐시를 비운다. 테스트와 설정 변경 시 호출한다."""
    _robots_cache.clear()

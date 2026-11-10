"""SSRF 방어: 외부 URL이 공인 HTTPS 주소인지 확인하고 안전하게 가져온다 (FR-PIPE-01).

모든 외부 요청 전에 이 모듈의 검증을 거친다. 사설·루프백·링크로컬·예약 대역과
리다이렉트 홉마다 목적지를 다시 검증한다.
"""

import ipaddress
import socket
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

USER_AGENT = "DAITBot/0.1 (+https://dait.local/bot)"
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_BYTES = 2_000_000
DEFAULT_MAX_REDIRECTS = 3
_ALLOWED_CONTENT_PREFIXES = (
    "application/rss",
    "application/atom",
    "application/xml",
    "text/xml",
    "text/html",
)

Resolver = Callable[[str], Sequence[str]]


class UnsafeUrlError(Exception):
    """허용되지 않은 URL·사설 주소 등 안전하지 않은 대상."""


class FetchFailedError(Exception):
    """네트워크 오류·시간 초과·크기 초과·허용되지 않는 형식."""

    def __init__(self, status_code: int | None = None) -> None:
        """HTTP 상태 코드가 있으면 함께 보관한다(robots 404 판별용)."""
        super().__init__()
        self.status_code = status_code


def _default_resolver(hostname: str) -> Sequence[str]:
    """호스트명에 연결되는 IP 문자열 목록을 돌려준다(socket.getaddrinfo 래퍼)."""
    infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    return [str(info[4][0]) for info in infos]


def _is_blocked_ip(raw: str) -> bool:
    """IP 문자열이 차단 대상인지 확인한다.

    입력: raw (IPv4/IPv6 주소 문자열)
    출력: bool
    기능: 사설·루프백·링크로컬·멀티캐스트·예약·미지정 대역을 모두 차단한다.
          IPv4-mapped IPv6(::ffff:10.0.0.1)도 IPv6 객체로 판정된다.
    """
    try:
        ip = ipaddress.ip_address(raw)
    except ValueError:
        return True  # 해석 불가 주소는 안전하지 않다고 본다.
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_public_https_url(url: str, resolver: Resolver | None = None) -> str:
    """URL이 공인 HTTPS 주소인지 검증하고 DNS 결과까지 확인한다.

    입력: url (검사할 절대 URL), resolver (테스트용 IP 해석기, None이면 DNS)
    출력: str (검증을 통과한 원래 URL)
    기능: http·자격증명 포함·IP 리터럴 차단 대역·사설로 해석되는 호스트를 거부한다.
          DNS 해석 자체가 실패하면 FetchFailedError가 아닌 UnsafeUrlError로 거부한다.
    """
    try:
        parts = urlsplit(url)
    except ValueError as exc:
        raise UnsafeUrlError from exc
    if parts.scheme.lower() != "https" or not parts.hostname:
        raise UnsafeUrlError
    if parts.username is not None or parts.password is not None:
        raise UnsafeUrlError
    host = parts.hostname
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        if _is_blocked_ip(str(literal)):
            raise UnsafeUrlError
        return url
    resolve = resolver if resolver is not None else _default_resolver
    try:
        addresses = resolve(host)
    except (OSError, socket.gaierror) as exc:
        raise UnsafeUrlError from exc
    if not addresses or any(_is_blocked_ip(str(addr)) for addr in addresses):
        raise UnsafeUrlError
    return url


def canonicalize_url(url: str) -> str:
    """dedupe 비교용으로 URL을 정규화한다.

    입력: url (검증을 통과한 절대 URL)
    출력: str (스킴·호스트 소문자, 기본 포트 제거, fragment 제거)
    기능: 같은 기사로 이어지는 표현 차이(http/https 외)를 하나로 모은다.
          https 검증은 validate_public_https_url이 먼저 수행한다고 가정한다.
    """
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    port = parts.port
    if (scheme == "https" and port == 443) or (scheme == "http" and port == 80):
        port = None
    netloc = host if port is None else f"{host}:{port}"
    return urlunsplit((scheme, netloc, parts.path or "/", parts.query, ""))


@dataclass(frozen=True)
class FetchedBody:
    """안전하게 가져온 응답 본문."""

    body: bytes
    content_type: str
    final_url: str


def fetch_public_bytes(
    client: httpx.Client,
    url: str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
    resolver: Resolver | None = None,
) -> FetchedBody:
    """공인 HTTPS URL의 본문을 크기 제한과 함께 가져온다.

    입력: client (httpx.Client), url (시작 URL), max_bytes·max_redirects (상한),
          resolver (테스트용 DNS)
    출력: FetchedBody (본문·Content-Type·최종 URL)
    기능: 매 홉마다 스킴·호스트·DNS를 다시 검증하고, 리다이렉트는 수동으로 따라간다.
          본문은 스트리밍으로 읽어 max_bytes를 넘으면 중단한다.
    """
    current = validate_public_https_url(url, resolver)
    for _ in range(max_redirects + 1):
        try:
            with client.stream(
                "GET", current, headers={"User-Agent": USER_AGENT}, follow_redirects=False
            ) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise FetchFailedError
                    current = validate_public_https_url(urljoin(current, location), resolver)
                    continue
                if response.status_code != 200:
                    raise FetchFailedError(response.status_code)
                content_type = response.headers.get("content-type", "")
                if not content_type.lower().startswith(_ALLOWED_CONTENT_PREFIXES):
                    raise FetchFailedError
                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        raise FetchFailedError
                    chunks.append(chunk)
                return FetchedBody(
                    body=b"".join(chunks),
                    content_type=content_type.split(";")[0].strip().lower(),
                    final_url=current,
                )
        except httpx.HTTPError as exc:
            raise FetchFailedError from exc
    raise FetchFailedError

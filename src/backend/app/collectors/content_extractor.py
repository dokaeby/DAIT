"""SSRF-safe article HTML fetcher and Trafilatura pure-body text extractor."""

import asyncio
import ipaddress
import logging
import socket
from collections.abc import Awaitable, Callable
from urllib.parse import urljoin

import httpx
import trafilatura
from pydantic import HttpUrl

logger = logging.getLogger(__name__)
USER_AGENT = "Mozilla/5.0 (compatible; DAITCollector/1.0)"
type Resolver = Callable[[str, int], Awaitable[tuple[str, ...]]]


async def resolve_public_host(host: str, port: int) -> tuple[str, ...]:
    """Resolve hostname via OS DNS and return all socket addresses."""
    records = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return tuple(str(record[4][0]) for record in records)


def is_public_ip(address: str) -> bool:
    """Reject loopback, private, link-local, multicast, and cloud metadata IPs (SSRF defense)."""
    ip = ipaddress.ip_address(address)
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            return is_public_ip(str(ip.ipv4_mapped))
        if (
            ip.sixtofour is not None
            or ip.teredo is not None
            or ip in ipaddress.IPv6Network("64:ff9b::/96")
        ):
            return False
    return (
        ip.is_global
        and not ip.is_multicast
        and not ip.is_unspecified
        and str(ip) != "168.63.129.16"
    )


def _validate_public_url(url: HttpUrl) -> str:
    host = (url.host or "").strip("[]").lower()
    expected_port = 443 if url.scheme == "https" else 80
    if (
        not host
        or url.scheme not in {"http", "https"}
        or url.username is not None
        or url.password is not None
        or (url.port is not None and url.port != expected_port)
    ):
        msg = "Unsafe article URL"
        raise ValueError(msg)
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return host
    if not is_public_ip(host):
        msg = "Nonpublic destination IP"
        raise ValueError(msg)
    return host


def extract_clean_body_with_trafilatura(html_content: str) -> str:
    """Extract pure article paragraphs via Trafilatura (excluding ads, headers, footers, tables)."""
    if not html_content or not html_content.strip():
        return ""
    extracted = trafilatura.extract(
        html_content,
        include_comments=False,
        include_tables=False,
    )
    if not extracted:
        return ""
    paragraphs = [" ".join(line.split()).strip() for line in extracted.splitlines() if line.strip()]
    return " ".join(paragraphs).strip()


async def _fetch_public_html(
    url: HttpUrl,
    *,
    resolver: Resolver,
    transport: httpx.AsyncBaseTransport | None,
    timeout_seconds: float,
    max_bytes: int,
    max_redirects: int,
) -> str:
    """Fetch article HTML via pinned public IPs, validating every redirect hop (SSRF defense)."""
    current_url = url
    for _ in range(max_redirects + 1):
        host = _validate_public_url(current_url)
        port = current_url.port or (443 if current_url.scheme == "https" else 80)
        addresses = await resolver(host, port)
        if not addresses or not all(is_public_ip(addr) for addr in addresses):
            return ""

        target = httpx.URL(str(current_url)).copy_with(host=addresses[0])
        active_transport = transport or httpx.AsyncHTTPTransport(
            limits=httpx.Limits(max_keepalive_connections=0)
        )
        async with active_transport:
            request = httpx.Request(
                "GET",
                target,
                headers=[
                    ("Host", host),
                    ("User-Agent", USER_AGENT),
                    ("Accept", "text/html,application/xhtml+xml"),
                ],
            )
            request.extensions["sni_hostname"] = host
            request.extensions["timeout"] = httpx.Timeout(timeout_seconds).as_dict()
            response = await active_transport.handle_async_request(request)
            try:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location", "").strip()
                    if not location:
                        return ""
                    current_url = HttpUrl(urljoin(str(current_url), location))
                    continue
                if response.status_code != 200:
                    return ""
                raw_bytes = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(raw_bytes) + len(chunk) > max_bytes:
                        break
                    raw_bytes.extend(chunk)
                html_text = bytes(raw_bytes).decode("utf-8", errors="ignore")
            finally:
                await response.aclose()

        return html_text
    return ""


async def fetch_article_html_and_body(
    url: HttpUrl,
    *,
    resolver: Resolver = resolve_public_host,
    transport: httpx.AsyncBaseTransport | None = None,
    timeout_seconds: float = 6.0,
    max_bytes: int = 2_000_000,
    max_redirects: int = 3,
) -> tuple[str, str]:
    """Return (html, Trafilatura body) for an article page fetched with strict SSRF protection.

    Returns empty strings on any network error, safety rejection, or extraction failure.
    """
    try:
        async with asyncio.timeout(timeout_seconds):
            html_text = await _fetch_public_html(
                url,
                resolver=resolver,
                transport=transport,
                timeout_seconds=timeout_seconds,
                max_bytes=max_bytes,
                max_redirects=max_redirects,
            )
            if not html_text:
                return "", ""
            body = await asyncio.to_thread(extract_clean_body_with_trafilatura, html_text)
            return html_text, body
    except Exception:  # noqa: BLE001 -- return empty strings safely on network/SSRF error
        logger.debug("Remote article fetch skipped for article URL")
        return "", ""


async def fetch_article_body_with_trafilatura(
    url: HttpUrl,
    *,
    resolver: Resolver = resolve_public_host,
    transport: httpx.AsyncBaseTransport | None = None,
    timeout_seconds: float = 6.0,
    max_bytes: int = 2_000_000,
    max_redirects: int = 3,
) -> str:
    """Fetch an article detail page with strict SSRF protection and extract body via Trafilatura."""
    _, body = await fetch_article_html_and_body(
        url,
        resolver=resolver,
        transport=transport,
        timeout_seconds=timeout_seconds,
        max_bytes=max_bytes,
        max_redirects=max_redirects,
    )
    return body

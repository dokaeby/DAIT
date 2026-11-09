"""Bounded asynchronous RSS/Atom collection from operator-approved sources.

Feed text remains untrusted data: downstream AI must treat it as content, never
as instructions. No article page or LLM is requested by this collector.
"""

import asyncio
import ipaddress
import logging
import socket
from collections.abc import Awaitable, Callable
from datetime import datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree

import httpx
from pydantic import HttpUrl, ValidationError
from src.backend.app.collectors.content_extractor import extract_clean_body_with_trafilatura
from src.backend.app.core.taxonomy import OFFICIAL_SOURCE_NAMES, match_category
from src.backend.app.schemas.collector import CollectedArticle, CollectionResult, CollectorSource

logger = logging.getLogger(__name__)
USER_AGENT = "DAITCollector/1.0"
type Resolver = Callable[[str, int], Awaitable[tuple[str, ...]]]


class _Messages:
    UNSAFE_XML: str = "Unsafe XML"
    INVALID_UTF_8_XML: str = "Invalid UTF-8 XML"
    UNSUPPORTED_FEED: str = "Unsupported feed"
    MISSING_ARTICLE_URL: str = "Missing article URL"
    UNAPPROVED_URL: str = "Unapproved URL"
    NONPUBLIC_DESTINATION: str = "Nonpublic destination"
    INVALID_COLLECTION_LIMITS: str = "Invalid collection limits"
    NONPUBLIC_DNS_DESTINATION: str = "Nonpublic DNS destination"
    ENCODED_RESPONSES_ARE_UNSUPPORTED: str = "Encoded responses are unsupported"
    RESPONSE_SIZE_LIMIT_EXCEEDED: str = "Response size limit exceeded"
    ROBOTS_POLICY_UNAVAILABLE: str = "Robots policy unavailable"
    ROBOTS_POLICY_DISALLOWS_COLLECTION: str = "Robots policy disallows collection"
    UNAPPROVED_SOURCE: str = "Unapproved source"
    MISSING_REDIRECT_LOCATION: str = "Missing redirect location"
    FEED_REQUEST_FAILED: str = "Feed request failed"
    REDIRECT_LIMIT_EXCEEDED: str = "Redirect limit exceeded"
    COLLECTION_FAILED: str = "Collection failed"


class CollectionError(ValueError):
    """Safe, fixed diagnostic without URLs, response bodies or credentials."""


async def resolve_host(host: str, port: int) -> tuple[str, ...]:
    records = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return tuple(str(record[4][0]) for record in records)


def _public_ip(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            return _public_ip(str(ip.ipv4_mapped))
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


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.hidden += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def _text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value)
    return " ".join(" ".join(parser.parts).split())


def _child_text(element: ElementTree.Element, names: tuple[str, ...]) -> str:
    for child in element:
        if child.tag.rsplit("}", 1)[-1] in names:
            return "".join(child.itertext()).strip()
    return ""


def _extract_body_text(element: ElementTree.Element) -> str:
    """Extract the richest non-empty body from <encoded>, <content>, <description>, or <summary>."""
    candidates: list[str] = []
    for child in element:
        tag_name = child.tag.rsplit("}", 1)[-1]
        if tag_name in {"encoded", "content", "description", "summary"}:
            raw_val = "".join(child.itertext()).strip()
            if raw_val:
                trafilatura_text = (
                    extract_clean_body_with_trafilatura(raw_val)
                    if "<" in raw_val and len(raw_val) >= 200
                    else ""
                )
                extracted = trafilatura_text if len(trafilatura_text) >= 80 else _text(raw_val)
                if extracted:
                    candidates.append(extracted)
    if not candidates:
        return ""
    return max(candidates, key=len)


def _is_article_detail_url(url: HttpUrl) -> bool:
    """Ensure the URL points to a specific article path or query, not a bare domain root."""
    has_path = url.path not in (None, "", "/")
    has_query = bool(url.query)
    return has_path or has_query


def _extract_article_url(item: ElementTree.Element, base_url: str) -> HttpUrl:
    """Extract the individual article permalink from <item>/<entry> (<link> or <guid>)."""
    candidates: list[str] = []
    direct_link = _child_text(item, ("link",))
    if direct_link:
        candidates.append(direct_link)
    for child in item:
        tag_name = child.tag.rsplit("}", 1)[-1]
        if tag_name == "link" and child.get("rel", "alternate") == "alternate":
            href = (child.get("href") or "").strip()
            if href:
                candidates.insert(0, href)
        elif tag_name == "guid" and child.get("isPermaLink", "true").lower() == "true":
            guid_text = "".join(child.itertext()).strip()
            if guid_text:
                candidates.append(guid_text)

    for raw_link in candidates:
        try:
            resolved = HttpUrl(urljoin(base_url, raw_link))
        except ValueError:
            continue
        if _is_article_detail_url(resolved):
            return resolved
    raise CollectionError(_Messages.MISSING_ARTICLE_URL)


def _parse_pub_date(raw_date: str) -> datetime:
    """Parse RSS/Atom publication dates, including Korean space-separated KST and colon offsets."""
    cleaned = raw_date.strip()
    if len(cleaned) == 19 and cleaned[10] == " ":
        cleaned = f"{cleaned}+09:00"
    try:
        return datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    except ValueError:
        if len(cleaned) > 6 and cleaned[-6] in {"+", "-"} and cleaned[-3] == ":":
            cleaned = cleaned[:-3] + cleaned[-2:]
        return parsedate_to_datetime(cleaned)


def _parse(
    source: CollectorSource,
    data: bytes,
    base_url: str,
    max_items: int | None = None,
) -> CollectionResult:
    # UTF-8 only: reject declarations before parsing, including entity expansion.
    try:
        xml = data.decode("utf-8-sig")
        if "<!DOCTYPE" in xml.upper() or "<!ENTITY" in xml.upper() or "\x00" in xml:
            raise CollectionError(_Messages.UNSAFE_XML)
        root = ElementTree.fromstring(xml)  # noqa: S314 -- DTD/entities rejected above
    except (UnicodeError, ElementTree.ParseError) as exc:
        raise CollectionError(_Messages.INVALID_UTF_8_XML) from exc
    if root.tag.rsplit("}", 1)[-1] not in {"rss", "feed", "RDF"}:
        raise CollectionError(_Messages.UNSUPPORTED_FEED)
    articles: list[CollectedArticle] = []
    seen: set[str] = set()
    rejected = 0
    for item in root.iter():
        if item.tag.rsplit("}", 1)[-1] not in {"item", "entry"}:
            continue
        if max_items is not None and len(articles) >= max_items:
            break
        try:
            url = _extract_article_url(item, base_url)
            _validate_url(url, source)
            date = _child_text(item, ("pubDate", "published", "date", "updated"))
            published = _parse_pub_date(date)
            title_text = _text(_child_text(item, ("title",)))
            if source.source_name in OFFICIAL_SOURCE_NAMES and title_text.startswith(
                ("[인사]", "[부고]", "[동정]", "[포토]", "[알림]")
            ):
                continue
            body = _extract_body_text(item)
            category = (
                match_category(title_text, body or None, default=source.category)
                if source.source_name in OFFICIAL_SOURCE_NAMES
                else source.category
            )
            article = CollectedArticle(
                source_name=source.source_name,
                title=title_text,
                canonical_url=url,
                category=category,
                published_at=published,
                raw_text=body or None,
            )
        except ValueError, TypeError, OverflowError:
            rejected += 1
            continue
        key = str(article.canonical_url)
        if key not in seen:
            seen.add(key)
            articles.append(article)
    return CollectionResult(
        source_name=source.source_name,
        category=source.category,
        articles=tuple(articles),
        rejected_count=rejected,
    )


def _validate_url(url: HttpUrl, source: CollectorSource) -> None:
    host = (url.host or "").strip("[]").lower()
    if (
        host not in source.allowed_hosts
        or url.username is not None
        or url.password is not None
        or url.port != (443 if url.scheme == "https" else 80)
    ):
        raise CollectionError(_Messages.UNAPPROVED_URL)
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return
    if not _public_ip(host):
        raise CollectionError(_Messages.NONPUBLIC_DESTINATION)


def _robots_allowed(body: bytes, url: str) -> bool:
    parser = RobotFileParser()
    parser.parse(body.decode("utf-8").splitlines())
    return parser.can_fetch(USER_AGENT, url)


class RSSCollector:
    """Collect only configured sources; injected transport/resolver enable offline tests."""

    def __init__(
        self,
        approved_sources: tuple[CollectorSource, ...],
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        resolver: Resolver = resolve_host,
        timeout_seconds: float = 15.0,
        max_bytes: int = 2_000_000,
        max_redirects: int = 3,
        max_items_per_feed: int | None = None,
    ) -> None:
        if timeout_seconds <= 0 or max_bytes <= 0 or max_redirects < 0:
            raise CollectionError(_Messages.INVALID_COLLECTION_LIMITS)
        self.sources = approved_sources
        self.transport = transport
        self.resolver = resolver
        self.timeout = timeout_seconds
        self.max_bytes = max_bytes
        self.max_redirects = max_redirects
        self.max_items_per_feed = max_items_per_feed

    async def _download(self, url: HttpUrl, source: CollectorSource) -> tuple[int, str, bytes]:
        _validate_url(url, source)
        host = (url.host or "").strip("[]")
        addresses = await self.resolver(host, url.port or 443)
        if not addresses or not all(_public_ip(address) for address in addresses):
            raise CollectionError(_Messages.NONPUBLIC_DNS_DESTINATION)
        # Pin the socket to the validated IP; preserve HTTP Host and TLS identity.
        target = httpx.URL(str(url)).copy_with(host=addresses[0])
        transport = self.transport or httpx.AsyncHTTPTransport(
            limits=httpx.Limits(max_keepalive_connections=0)
        )
        # The low-level transport avoids client URL logging (queries may contain tokens).
        # No cookies, environment proxies or automatic redirects are used.
        async with transport:
            request = httpx.Request(
                "GET",
                target,
                headers=[
                    ("Host", host),
                    ("User-Agent", USER_AGENT),
                    ("Accept-Encoding", "identity"),
                ],
            )
            request.extensions["sni_hostname"] = host
            request.extensions["timeout"] = httpx.Timeout(self.timeout).as_dict()
            response = await transport.handle_async_request(request)
            try:
                if response.headers.get("content-encoding", "identity").lower() != "identity":
                    raise CollectionError(_Messages.ENCODED_RESPONSES_ARE_UNSUPPORTED)
                body = bytearray()
                async for chunk in response.aiter_raw():
                    if len(body) + len(chunk) > self.max_bytes:
                        raise CollectionError(_Messages.RESPONSE_SIZE_LIMIT_EXCEEDED)
                    body.extend(chunk)
                return response.status_code, response.headers.get("location", ""), bytes(body)
            finally:
                await response.aclose()

    async def _robots(self, url: HttpUrl, source: CollectorSource) -> None:
        robots_url = HttpUrl(urljoin(str(url), "/robots.txt"))
        status, _, body = await self._download(robots_url, source)
        if status in {404, 410}:
            return
        if status != 200:
            raise CollectionError(_Messages.ROBOTS_POLICY_UNAVAILABLE)
        if not await asyncio.to_thread(_robots_allowed, body, str(url)):
            raise CollectionError(_Messages.ROBOTS_POLICY_DISALLOWS_COLLECTION)

    async def collect(self, source: CollectorSource) -> CollectionResult:
        if source not in self.sources:
            raise CollectionError(_Messages.UNAPPROVED_SOURCE)
        try:
            async with asyncio.timeout(self.timeout):
                url = source.feed_url
                for _ in range(self.max_redirects + 1):
                    _validate_url(url, source)
                    await self._robots(url, source)
                    status, location, body = await self._download(url, source)
                    if status in {301, 302, 303, 307, 308}:
                        if not location:
                            raise CollectionError(_Messages.MISSING_REDIRECT_LOCATION)
                        url = HttpUrl(urljoin(str(url), location))
                        continue
                    if status != 200:
                        raise CollectionError(_Messages.FEED_REQUEST_FAILED)
                    result = await asyncio.to_thread(
                        _parse, source, body, str(url), self.max_items_per_feed
                    )
                    logger.info(
                        "RSS collection completed; accepted=%d rejected=%d",
                        len(result.articles),
                        result.rejected_count,
                    )
                    return result
                raise CollectionError(_Messages.REDIRECT_LIMIT_EXCEEDED)
        except (httpx.HTTPError, OSError, TimeoutError, ValidationError, UnicodeError) as exc:
            logger.warning("RSS collection failed")
            raise CollectionError(_Messages.COLLECTION_FAILED) from exc

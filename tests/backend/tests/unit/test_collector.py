"""Offline contract and adversarial tests for the approved-source collector."""

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from pydantic import HttpUrl, ValidationError
from src.backend.app.collectors.rss_collector import CollectionError, RSSCollector
from src.backend.app.schemas.collector import CollectedArticle, CollectionResult, CollectorSource


class Body(httpx.AsyncByteStream):
    def __init__(self, data: bytes) -> None:
        self.data = data

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield self.data


def response(status: int = 200, body: bytes = b"", location: str = "") -> httpx.Response:
    return httpx.Response(status, stream=Body(body), headers=[("location", location)])


def source() -> CollectorSource:
    return CollectorSource(
        source_name="Approved AI News",
        feed_url=HttpUrl("https://news.example/feed"),
        allowed_hosts=("news.example",),
    )


async def public_dns(host: str, port: int) -> tuple[str, ...]:
    return ("8.8.8.8",)


def item(
    link: str = "https://news.example/article#fragment",
    date: str = "Sun, 08 Nov 2026 12:00:00 +0900",
) -> bytes:
    return (
        f"<item><title>AI News</title><link>{link}</link><pubDate>{date}</pubDate>"
        "<description><![CDATA[<p>Hello</p><script>secret()</script>]]></description></item>"
    ).encode()


def feed(items: bytes | None = None) -> bytes:
    return b"<rss><channel>" + (item() if items is None else items) + b"</channel></rss>"


def collect(
    payload: bytes,
    *,
    robots: bytes = b"User-agent: *\nAllow: /",
    max_bytes: int = 10000,
) -> CollectionResult:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "8.8.8.8"
        assert request.headers["host"] == "news.example"
        assert request.extensions["sni_hostname"] == "news.example"
        if request.url.path == "/robots.txt":
            return response(body=robots)
        return response(body=payload)

    config = source()
    collector = RSSCollector(
        (config,), transport=httpx.MockTransport(handler), resolver=public_dns, max_bytes=max_bytes
    )
    return asyncio.run(collector.collect(config))


def test_contract_normalization_and_deduplication() -> None:
    result = collect(feed(item() + item("https://NEWS.example:443/article#second")))
    assert len(result.articles) == 1
    article = result.articles[0]
    assert str(article.canonical_url) == "https://news.example/article"
    assert article.published_at == datetime(2026, 11, 8, 3, tzinfo=UTC)
    assert article.raw_text == "Hello"
    assert article.category == "AI"
    assert result.rejected_count == 0


def test_models_are_frozen_and_reject_extra_fields() -> None:
    article = collect(feed()).articles[0]
    with pytest.raises(ValidationError):
        article.title = "changed"
    with pytest.raises(ValidationError):
        CollectedArticle.model_validate_json(article.model_dump_json()[:-1] + ',"extra":1}')
    with pytest.raises(ValidationError):
        CollectorSource.model_validate_json(
            '{"source_name":"x","feed_url":"https://news.example/feed",'
            '"allowed_hosts":["news.example"],"category":"OTHER"}'
        )


def test_naive_date_is_rejected_and_optional_body_is_required() -> None:
    assert collect(feed(item(date="2026-11-08T12:00:00"))).rejected_count == 1
    article = collect(feed()).articles[0]
    with pytest.raises(ValidationError):
        CollectedArticle.model_validate_json(article.model_dump_json(exclude={"raw_text"}))
    converted = article.model_copy()
    assert converted.published_at.utcoffset() == timedelta(0)


def test_atom_and_missing_body() -> None:
    result = collect(
        b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>AI</title>'
        b'<link href="/atom"/><published>2026-11-08T12:00:00Z</published>'
        b"</entry></feed>"
    )
    assert str(result.articles[0].canonical_url) == "https://news.example/atom"
    assert result.articles[0].raw_text is None


@pytest.mark.parametrize(
    "payload",
    [
        b"broken",
        b"<html/>",
        b"\xff",
        b"<rss>\x00</rss>",
        b'<!DOCTYPE rss [<!ENTITY x "bad">]><rss>&x;</rss>',
    ],
)
def test_unsafe_or_invalid_xml(payload: bytes) -> None:
    with pytest.raises(CollectionError):
        collect(payload)


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example/a",
        "http://127.0.0.1/a",
        "https://user:password@news.example/a",
        "https://news.example:8080/a",
    ],
)
def test_invalid_article_urls_are_rejected(url: str) -> None:
    result = collect(feed(item(url)))
    assert not result.articles
    assert result.rejected_count == 1


@pytest.mark.parametrize(
    "addresses",
    [
        ("127.0.0.1",),
        ("169.254.169.254",),
        ("168.63.129.16",),
        ("64:ff9b::7f00:1",),
        ("10.0.0.1",),
        ("::1",),
        ("::ffff:127.0.0.1",),
        ("8.8.8.8", "192.168.1.1"),
        (),
    ],
)
def test_dns_ssrf_is_rejected_before_connection(addresses: tuple[str, ...]) -> None:
    async def dns(host: str, port: int) -> tuple[str, ...]:
        return addresses

    def forbidden(request: httpx.Request) -> httpx.Response:
        pytest.fail("Network transport must not be called")

    config = source()
    collector = RSSCollector((config,), resolver=dns, transport=httpx.MockTransport(forbidden))
    with pytest.raises(CollectionError, match="DNS"):
        asyncio.run(collector.collect(config))


def test_unapproved_source_is_rejected() -> None:
    with pytest.raises(CollectionError, match="source"):
        asyncio.run(RSSCollector(()).collect(source()))


def test_robots_disallow_and_size_limit() -> None:
    with pytest.raises(CollectionError, match="Robots"):
        collect(feed(), robots=b"User-agent: *\nDisallow: /feed")
    with pytest.raises(CollectionError, match="size"):
        collect(feed(), max_bytes=50)


@pytest.mark.parametrize("location", ["https://evil.example/feed", "http://127.0.0.1/feed"])
def test_redirect_destination_is_checked(location: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return response(404)
        return response(302, location=location)

    config = source()
    collector = RSSCollector((config,), resolver=public_dns, transport=httpx.MockTransport(handler))
    with pytest.raises(CollectionError, match="Unapproved"):
        asyncio.run(collector.collect(config))


def test_timeout_is_bounded() -> None:
    async def slow_dns(host: str, port: int) -> tuple[str, ...]:
        await asyncio.sleep(1)
        return ("8.8.8.8",)

    config = source()
    with pytest.raises(CollectionError, match="Collection failed"):
        asyncio.run(
            RSSCollector((config,), resolver=slow_dns, timeout_seconds=0.01).collect(config)
        )


@pytest.mark.parametrize("robots_status", [403, 500, 302])
def test_robots_errors_fail_closed(robots_status: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return response(robots_status)

    config = source()
    with pytest.raises(CollectionError, match="Robots"):
        asyncio.run(
            RSSCollector(
                (config,), resolver=public_dns, transport=httpx.MockTransport(handler)
            ).collect(config)
        )


def test_redirect_limit_and_http_failure() -> None:
    for status, message in ((302, "Redirect limit"), (500, "Feed request failed")):

        def handler(request: httpx.Request, status: int = status) -> httpx.Response:
            if request.url.path == "/robots.txt":
                return response(404)
            return response(status, location="/feed")

        config = source()
        with pytest.raises(CollectionError, match=message):
            asyncio.run(
                RSSCollector(
                    (config,),
                    resolver=public_dns,
                    max_redirects=1,
                    transport=httpx.MockTransport(handler),
                ).collect(config)
            )


def test_sensitive_values_are_not_logged(caplog: pytest.LogCaptureFixture) -> None:
    result = collect(feed(item("https://user:secret-token@news.example/a")))
    assert result.rejected_count == 1
    assert "secret-token" not in caplog.text
    assert "Traceback" not in caplog.text


def test_dns_rebinding_is_checked_for_every_request() -> None:
    calls = 0
    connections = 0

    async def changing_dns(host: str, port: int) -> tuple[str, ...]:
        nonlocal calls
        calls += 1
        return ("8.8.8.8",) if calls == 1 else ("127.0.0.1",)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal connections
        connections += 1
        return response(404)

    config = source()
    with pytest.raises(CollectionError, match="DNS"):
        asyncio.run(
            RSSCollector(
                (config,), resolver=changing_dns, transport=httpx.MockTransport(handler)
            ).collect(config)
        )
    assert connections == 1


def test_successful_relative_redirect() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path == "/robots.txt":
            return response(404)
        if request.url.path == "/feed":
            return response(302, location="/moved")
        return response(body=feed())

    config = source()
    result = asyncio.run(
        RSSCollector(
            (config,), resolver=public_dns, transport=httpx.MockTransport(handler)
        ).collect(config)
    )
    assert len(result.articles) == 1
    assert paths == ["/robots.txt", "/feed", "/robots.txt", "/moved"]


def test_feed_query_token_is_not_logged(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("DEBUG")
    config = CollectorSource(
        source_name="AI",
        allowed_hosts=("news.example",),
        feed_url=HttpUrl("https://news.example/feed?token=secret-token"),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return response(404)
        return response(body=feed())

    asyncio.run(
        RSSCollector(
            (config,), resolver=public_dns, transport=httpx.MockTransport(handler)
        ).collect(config)
    )
    assert "secret-token" not in caplog.text
    assert "Traceback" not in caplog.text


def test_compressed_response_is_rejected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers=[("content-encoding", "gzip")], stream=Body(b"bad"))

    config = source()
    with pytest.raises(CollectionError, match="Encoded"):
        asyncio.run(
            RSSCollector(
                (config,), resolver=public_dns, transport=httpx.MockTransport(handler)
            ).collect(config)
        )


def test_transport_error_is_sanitized(caplog: pytest.LogCaptureFixture) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("secret-token", request=request)

    config = source()
    with pytest.raises(CollectionError, match="Collection failed"):
        asyncio.run(
            RSSCollector(
                (config,), resolver=public_dns, transport=httpx.MockTransport(handler)
            ).collect(config)
        )
    assert "secret-token" not in caplog.text


def test_missing_article_fields_are_rejected() -> None:
    result = collect(feed(b"<item><title>AI</title></item>" + item(date="invalid")))
    assert result.rejected_count == 2
    assert not result.articles


def test_url_identity_preserves_query() -> None:
    result = collect(
        feed(item("https://news.example/a?id=1") + item("https://news.example/a?id=2"))
    )
    assert len(result.articles) == 2

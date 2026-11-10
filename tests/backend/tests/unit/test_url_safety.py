"""SSRF·안전 fetch 테스트. 모든 네트워크는 httpx.MockTransport로 대체한다."""

from collections.abc import Callable

import httpx
import pytest

from dait.core.url_safety import (
    FetchFailedError,
    UnsafeUrlError,
    canonicalize_url,
    fetch_public_bytes,
    validate_public_https_url,
)

PUBLIC_IP = "93.184.216.34"


def public_resolver(host: str) -> list[str]:
    """테스트용 DNS: 어떤 호스트든 공인 IP로 해석한다."""
    return [PUBLIC_IP]


def private_resolver(host: str) -> list[str]:
    """테스트용 DNS: 사설 IP로 해석한다(rebinding·내부 호스트 흉내)."""
    return ["10.0.0.8"]


class TestValidateUrl:
    """validate_public_https_url 규칙."""

    @pytest.mark.parametrize(
        "url",
        [
            "http://example.com/feed",  # http 금지
            "ftp://example.com/x",
            "https://user:pw@example.com/x",  # 자격증명 금지
            "https://127.0.0.1/x",
            "https://10.1.2.3/x",
            "https://169.254.169.254/latest/meta-data",  # 클라우드 메타데이터
            "https://[::1]/x",
            "https://[fd00::1]/x",
            "notaurl",
            "",
        ],
    )
    def test_rejects_unsafe(self, url: str) -> None:
        """http·자격증명·사설 IP 리터럴·IPv6 사설 주소는 거부된다."""
        with pytest.raises(UnsafeUrlError):
            validate_public_https_url(url, public_resolver)

    def test_rejects_private_dns_result(self) -> None:
        """호스트명이 사설 IP로 해석되면 거부한다(DNS 기반 SSRF)."""
        with pytest.raises(UnsafeUrlError):
            validate_public_https_url("https://internal.example.com/x", private_resolver)

    def test_rejects_unresolvable(self) -> None:
        """DNS 해석 실패는 안전하지 않다고 거부한다."""

        def failing(host: str) -> list[str]:
            raise OSError("nx")

        with pytest.raises(UnsafeUrlError):
            validate_public_https_url("https://gone.example.com/x", failing)

    def test_accepts_public_https(self) -> None:
        """공인 IP로 해석되는 https는 통과한다."""
        url = "https://news.example.com/feed.xml"
        assert validate_public_https_url(url, public_resolver) == url


class TestCanonicalize:
    """canonicalize_url 정규화."""

    def test_normalizes(self) -> None:
        """스킴·호스트 소문자, 기본 포트·fragment 제거."""
        assert (
            canonicalize_url("HTTPS://Example.COM:443/a/b?x=1#frag")
            == "https://example.com/a/b?x=1"
        )


class TestFetch:
    """fetch_public_bytes: 리다이렉트·형식·크기 제한."""

    def _client(self, handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(handler))

    def test_fetch_ok(self) -> None:
        """200 + 허용 Content-Type이면 본문을 돌려준다."""
        seen: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(str(request.url))
            return httpx.Response(
                200, content=b"<rss/>", headers={"content-type": "application/rss+xml"}
            )

        result = fetch_public_bytes(
            self._client(handler), "https://news.example.com/feed", resolver=public_resolver
        )
        assert result.body == b"<rss/>"
        assert result.content_type == "application/rss+xml"

    def test_redirect_to_private_is_blocked(self) -> None:
        """공인 URL이 사설 주소로 리다이렉트하면 두 번째 홉에서 거부된다."""

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/feed":
                return httpx.Response(302, headers={"location": "https://internal.example.com/x"})
            return httpx.Response(200, content=b"x")

        def resolver(host: str) -> list[str]:
            return ["10.0.0.5"] if host == "internal.example.com" else [PUBLIC_IP]

        with pytest.raises(UnsafeUrlError):
            fetch_public_bytes(
                self._client(handler), "https://news.example.com/feed", resolver=resolver
            )

    def test_disallowed_content_type(self) -> None:
        """html·json 등 허용 목록 밖 형식은 거부한다."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"{}", headers={"content-type": "application/json"})

        with pytest.raises(FetchFailedError):
            fetch_public_bytes(
                self._client(handler), "https://news.example.com/feed", resolver=public_resolver
            )

    def test_oversize_body(self) -> None:
        """max_bytes를 넘는 본문은 거부한다."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"x" * 100, headers={"content-type": "text/xml"})

        with pytest.raises(FetchFailedError):
            fetch_public_bytes(
                self._client(handler),
                "https://news.example.com/feed",
                max_bytes=10,
                resolver=public_resolver,
            )

    def test_http_error_status(self) -> None:
        """200이 아닌 응답은 실패다."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, content=b"", headers={"content-type": "text/xml"})

        with pytest.raises(FetchFailedError):
            fetch_public_bytes(
                self._client(handler), "https://news.example.com/feed", resolver=public_resolver
            )

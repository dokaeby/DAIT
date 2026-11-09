import asyncio

import httpx


class ASGIClient:
    """Small synchronous facade over HTTPX's in-process ASGI transport."""

    # 입력: `app`.
    # 출력: 반환값 없음.
    # 동작: `__init__` 기능을 수행한다.
    def __init__(self, app):
        self.app = app

    # 입력: `method`, `url`, `**kwargs`.
    # 출력: `httpx.Response` 값.
    # 동작: `request` 기능을 수행한다.
    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        # 입력: 없음.
        # 출력: `httpx.Response` 값.
        # 동작: `send` 기능을 수행한다.
        async def send() -> httpx.Response:
            transport = httpx.ASGITransport(app=self.app, raise_app_exceptions=False)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.request(method, url, **kwargs)

        return asyncio.run(send())

    # 입력: `url`, `**kwargs`.
    # 출력: `httpx.Response` 값.
    # 동작: ASGI 애플리케이션에 GET 요청을 전달한다.
    def get(self, url: str, **kwargs) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    # 입력: `url`, `**kwargs`.
    # 출력: `httpx.Response` 값.
    # 동작: ASGI 애플리케이션에 POST 요청을 전달한다.
    def post(self, url: str, **kwargs) -> httpx.Response:
        return self.request("POST", url, **kwargs)

    # 입력: `url`, `**kwargs`.
    # 출력: `httpx.Response` 값.
    # 동작: ASGI 애플리케이션에 PATCH 요청을 전달한다.
    def patch(self, url: str, **kwargs) -> httpx.Response:
        return self.request("PATCH", url, **kwargs)

    # 입력: `url`, `**kwargs`.
    # 출력: `httpx.Response` 값.
    # 동작: ASGI 애플리케이션에 DELETE 요청을 전달한다.
    def delete(self, url: str, **kwargs) -> httpx.Response:
        return self.request("DELETE", url, **kwargs)

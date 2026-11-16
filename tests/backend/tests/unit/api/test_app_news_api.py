"""In-process FastAPI contracts with FakeNewsService: no real network/Redis/LLM."""

import asyncio
import socket
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest
import pytest_asyncio
from fastapi import routing
from fastapi.routing import APIRoute
from pydantic import HttpUrl, ValidationError
from src.backend.app.api.v1.news import create_app
from src.backend.app.schemas.news import (
    LATEST_BASIS,
    RANK_BASIS,
    ApiErrorResponse,
    NewsArticle,
    NewsContent,
    NewsDetailResponse,
    NewsListItem,
    NewsListResponse,
    NewsMeta,
    NewsPage,
    NewsProcessing,
    NewsQuery,
    NewsSource,
)
from src.backend.app.services.news_service import InvalidNewsCursorError

TIME = datetime(2026, 11, 8, tzinfo=UTC)
LINES = ("AI 뉴스가 발표됐다.", "새 모델을 소개했다.", "연구 결과를 공개했다.")
PRIVATE_ERROR = "secret-token internal SQL and private-body"
INVALID_CURSOR = "Invalid cursor"


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def deny(*args: object, **kwargs: object) -> None:
        pytest.fail("API contract tests must not open real network connections")

    async def deny_async(*args: object, **kwargs: object) -> None:
        deny()

    monkeypatch.setattr(socket, "getaddrinfo", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(asyncio.BaseEventLoop, "create_connection", deny_async)


def item(identifier: str = "news_fake_01", rank: int = 1) -> NewsListItem:
    return NewsListItem(
        id=identifier,
        rank=rank,
        title="AI news",
        source_name="Fake Source",
        published_at=TIME,
        summary_lines=LINES,
        original_url=HttpUrl("https://news.example/a"),
    )


def listing(sort: str = "rank") -> NewsListResponse:
    return NewsListResponse(
        items=[item()],
        page=NewsPage(next_cursor=None, has_more=False),
        meta=NewsMeta(
            total_visible=1,
            partial=False,
            message=None,
            rank_basis=RANK_BASIS if sort == "rank" else LATEST_BASIS,
        ),
    )


def detail() -> NewsDetailResponse:
    return NewsDetailResponse(
        article=NewsArticle(
            id="news_fake_01",
            title="AI news",
            source_name="Fake Source",
            published_at=TIME,
            original_language=None,
            estimated_read_minutes=None,
        ),
        content=NewsContent(
            summary_lines=LINES,
            translated_text="AI 뉴스의 모델 연구 결과다.",
            processed_at=None,
            content_status="READY",
            summary_model_version=None,
        ),
        source=NewsSource(
            original_url=HttpUrl("https://news.example/a"),
            url_verified=False,
            source_type="UNKNOWN",
        ),
        related_news=[item("news_related_02", 2)],
        processing=NewsProcessing(
            collection_status="COLLECTED", translation_status="SUCCESS", summary_status="SUCCESS"
        ),
    )


class FakeNewsService:
    def __init__(self) -> None:
        self.queries: list[NewsQuery] = []
        self.ids: list[str] = []
        self.fail = False
        self.invalid_output = False

    async def query_news(self, query: NewsQuery) -> NewsListResponse:
        self.queries.append(query)
        if self.fail:
            raise RuntimeError(PRIVATE_ERROR)
        if query.cursor == "bad":
            raise InvalidNewsCursorError(INVALID_CURSOR)
        if self.invalid_output:
            broken = NewsListItem.model_construct(
                id="fake",
                rank=1,
                title="private-body",
                source_name="Fake Source",
                published_at=TIME,
                summary_lines=(),
                original_url=HttpUrl("https://news.example/a"),
            )
            return NewsListResponse.model_construct(
                items=[broken], page=NewsPage(next_cursor=None, has_more=False), meta=listing().meta
            )
        return listing(query.sort)

    async def get_api_detail(self, news_id: str) -> NewsDetailResponse | None:
        self.ids.append(news_id)
        if self.fail:
            raise RuntimeError(PRIVATE_ERROR)
        return detail() if news_id == "news_fake_01" else None


@pytest.fixture
def fake_service() -> FakeNewsService:
    return FakeNewsService()


@pytest_asyncio.fixture
async def client(fake_service: FakeNewsService) -> AsyncGenerator[httpx.AsyncClient]:
    app = create_app(fake_service)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as session:
        yield session


@pytest.mark.asyncio
async def test_list_defaults_and_exact_response_contract(
    client: httpx.AsyncClient, fake_service: FakeNewsService
) -> None:
    response = await client.get("/v1/news")
    assert response.status_code == 200
    parsed = NewsListResponse.model_validate_json(response.text)
    assert parsed.model_fields_set == {"items", "page", "meta"}
    assert parsed.items[0].model_fields_set == {
        "id",
        "rank",
        "title",
        "source_name",
        "published_at",
        "category",
        "summary_lines",
        "processing_status",
        "original_url",
        "is_partial",
    }
    assert len(parsed.items[0].summary_lines) == 3
    assert len(fake_service.queries) == 1
    assert fake_service.queries[0] == NewsQuery()
    assert UUID(response.headers["X-Request-ID"])


@pytest.mark.asyncio
async def test_parameters_are_validated_and_forwarded(
    client: httpx.AsyncClient, fake_service: FakeNewsService
) -> None:
    response = await client.get(
        "/v1/news?category=AI&q=AI%20Model&sort=latest&page_size=50&cursor=opaque-next"
    )
    assert response.status_code == 200
    query = fake_service.queries[0]
    assert query.category == "AI"
    assert query.q == "ai model"
    assert query.sort == "latest"
    assert query.page_size == 50
    assert query.cursor == "opaque-next"
    assert NewsListResponse.model_validate_json(response.text).meta.rank_basis == LATEST_BASIS


@pytest.mark.asyncio
@pytest.mark.parametrize("page_size", [1, 10, 50])
async def test_valid_page_sizes(client: httpx.AsyncClient, page_size: int) -> None:
    assert (await client.get(f"/v1/news?page_size={page_size}")).status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query",
    [
        "category=OTHER",
        "sort=views",
        "page_size=0",
        "page_size=51",
        "page_size=-1",
        "page_size=1.5",
        "page_size=10.0",
        "page_size=true",
        "page_size=abc",
        "cursor=",
        "unknown=1",
        "category=AI&category=AI",
        "q=" + "x" * 201,
        "cursor=" + "a" * 2049,
    ],
)
async def test_invalid_query_returns_generalized_422_without_service_call(
    client: httpx.AsyncClient,
    fake_service: FakeNewsService,
    query: str,
) -> None:
    response = await client.get("/v1/news?" + query)
    assert response.status_code == 422
    error = ApiErrorResponse.model_validate_json(response.text)
    assert error.error.code == "INVALID_REQUEST"
    assert response.headers["X-Request-ID"] == error.request_id
    assert UUID(error.request_id)
    assert not fake_service.queries
    assert "traceback" not in response.text.lower()


@pytest.mark.asyncio
async def test_opaque_detail_id_contract_and_nested_fields(
    client: httpx.AsyncClient, fake_service: FakeNewsService
) -> None:
    response = await client.get("/v1/news/news_fake_01")
    assert response.status_code == 200
    parsed = NewsDetailResponse.model_validate_json(response.text)
    assert parsed.article.id == "news_fake_01"
    assert parsed.model_fields_set == {"article", "content", "source", "related_news", "processing"}
    assert parsed.article.model_fields_set == {
        "id",
        "title",
        "source_name",
        "published_at",
        "original_language",
        "category",
        "estimated_read_minutes",
    }
    assert parsed.content.model_fields_set == {
        "summary_lines",
        "translated_text",
        "processed_at",
        "content_status",
        "summary_model_version",
    }
    assert parsed.source.model_fields_set == {"original_url", "url_verified", "source_type"}
    assert parsed.processing.model_fields_set == {
        "collection_status",
        "translation_status",
        "summary_status",
    }
    assert len(parsed.content.summary_lines) == 3
    assert parsed.related_news[0].id == "news_related_02"
    assert fake_service.ids == ["news_fake_01"]


@pytest.mark.asyncio
@pytest.mark.parametrize("identifier", ["unknown", "not-a-uuid", "news_missing_opaque_02"])
async def test_missing_opaque_id_returns_404_with_request_id(
    client: httpx.AsyncClient, identifier: str
) -> None:
    response = await client.get(
        "/v1/news/" + identifier, headers=[("X-Request-ID", "untrusted-input")]
    )
    assert response.status_code == 404
    error = ApiErrorResponse.model_validate_json(response.text)
    assert error.error.code == "NEWS_NOT_FOUND"
    assert error.request_id != "untrusted-input"
    assert response.headers["X-Request-ID"] == error.request_id
    assert UUID(error.request_id)


@pytest.mark.asyncio
async def test_invalid_cursor_is_sanitized_422(client: httpx.AsyncClient) -> None:
    response = await client.get("/v1/news?cursor=bad")
    assert response.status_code == 422
    assert ApiErrorResponse.model_validate_json(response.text).error.code == "INVALID_CURSOR"


@pytest.mark.asyncio
@pytest.mark.parametrize("url", ["/v1/news", "/v1/news/news_fake_01"])
async def test_service_failure_does_not_leak_details(
    client: httpx.AsyncClient,
    fake_service: FakeNewsService,
    url: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake_service.fail = True
    response = await client.get(url)
    assert response.status_code == 500
    error = ApiErrorResponse.model_validate_json(response.text)
    assert error.error.code == "INTERNAL_ERROR"
    assert error.request_id == response.headers["X-Request-ID"]
    assert "secret-token" not in response.text + caplog.text
    assert "private-body" not in response.text + caplog.text
    assert "Traceback" not in response.text + caplog.text


@pytest.mark.asyncio
async def test_response_model_rejects_bypassed_invalid_output(
    client: httpx.AsyncClient, fake_service: FakeNewsService, caplog: pytest.LogCaptureFixture
) -> None:
    fake_service.invalid_output = True
    response = await client.get("/v1/news")
    assert response.status_code == 500
    assert ApiErrorResponse.model_validate_json(response.text).error.code == "INTERNAL_ERROR"
    assert "private-body" not in response.text + caplog.text


@pytest.mark.asyncio
async def test_request_ids_are_unique_per_request(client: httpx.AsyncClient) -> None:
    responses = await asyncio.gather(client.get("/v1/news/missing"), client.get("/v1/news/missing"))
    ids = tuple(
        ApiErrorResponse.model_validate_json(response.text).request_id for response in responses
    )
    assert ids[0] != ids[1]


@pytest.mark.asyncio
async def test_openapi_uses_contract_response_models(
    client: httpx.AsyncClient, fake_service: FakeNewsService
) -> None:
    app = create_app(fake_service)
    operations = tuple(
        api_route
        # FastAPI 최신 버전의 _IncludedRouter 구조를 순회하여
        # 등록된 엔드포인트 컨텍스트를 수집합니다.
        for route in routing.iter_route_contexts(app.routes)
        if (
            isinstance(api_route := route.original_route, APIRoute)
            and route.path is not None
            and route.path.startswith("/v1/news")
        )
    )
    assert len(operations) == 2
    assert operations[0].response_model is NewsListResponse
    assert operations[1].response_model is NewsDetailResponse
    assert all(
        route.response_fields[404].field_info.annotation is ApiErrorResponse for route in operations
    )
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    assert '"ApiErrorResponse"' in response.text
    assert '"additionalProperties":false' in response.text


def test_models_forbid_extras_and_enforce_three_summary_sentences() -> None:
    valid = listing().model_dump_json()
    with pytest.raises(ValidationError):
        NewsListResponse.model_validate_json(valid[:-1] + ',"extra":true}')
    with pytest.raises(ValidationError):
        NewsListItem.model_validate_json(
            item().model_dump_json().replace(LINES[0], "No sentence ending")
        )
    frozen = item()
    with pytest.raises(ValidationError):
        frozen.rank = 20

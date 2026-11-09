"""v1.0.1 news router, dependency injection, and sanitized request-scoped errors."""

import logging
from collections.abc import Callable
from types import CoroutineType
from typing import Annotated, Protocol
from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, Path, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from fastapi.utils import create_model_field
from src.backend.app.schemas.news import (
    ApiError,
    ApiErrorCode,
    ApiErrorResponse,
    ApiModel,
    NewsDetailResponse,
    NewsListResponse,
    NewsQuery,
)
from src.backend.app.services.news_service import InvalidNewsCursorError

logger = logging.getLogger(__name__)
SERVICE_UNAVAILABLE = "News service dependency is not configured"


class NewsApiService(Protocol):
    async def query_news(self, query: NewsQuery) -> NewsListResponse: ...
    async def get_api_detail(self, news_id: str) -> NewsDetailResponse | None: ...


class NewsNotFoundError(Exception):
    pass


class InvalidQueryError(Exception):
    pass


class _ErrorDocumentation(ApiModel):
    model: type[ApiErrorResponse] = ApiErrorResponse


def _failure(code: ApiErrorCode, message: str, request_id: str, status: int) -> Response:
    error = ApiErrorResponse(error=ApiError(code=code, message=message), request_id=request_id)
    return Response(
        content=error.model_dump_json(), status_code=status, media_type="application/json"
    )


def _unique_query_parameters(request: Request) -> None:
    for name in request.query_params:
        if len(request.query_params.getlist(name)) > 1:
            raise InvalidQueryError


class NewsApiRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], CoroutineType[object, object, Response]]:
        original = super().get_route_handler()

        async def handle(request: Request) -> Response:
            request_id = str(uuid4())  # Caller-supplied request IDs are never trusted or reflected.
            try:
                _unique_query_parameters(request)
                response = await original(request)
            except NewsNotFoundError:
                response = _failure("NEWS_NOT_FOUND", "뉴스를 찾을 수 없습니다.", request_id, 404)
            except InvalidNewsCursorError:
                response = _failure("INVALID_CURSOR", "커서를 확인해 주세요.", request_id, 422)
            except RequestValidationError, InvalidQueryError:
                response = _failure("INVALID_REQUEST", "요청을 확인해 주세요.", request_id, 422)
            except Exception:  # noqa: BLE001 -- validation/adapter details may contain private data
                logger.warning("News API request failed")
                response = _failure("INTERNAL_ERROR", "요청을 처리할 수 없습니다.", request_id, 500)
            response.headers["X-Request-ID"] = request_id
            return response

        return handle


async def get_news_service() -> NewsApiService:
    raise RuntimeError(SERVICE_UNAVAILABLE)


# 뉴스 관련 엔드포인트를 담당하는 APIRouter를 정의합니다.
# 하위 경로 접두어로 "/news"를 사용하며,
# 앱 등록 시 prefix="/v1"과 조합되어 최종적으로 "/v1/news"가 됩니다.
router = APIRouter(prefix="/news", tags=["news"], route_class=NewsApiRoute)


@router.get("", response_model=NewsListResponse)
async def list_news(
    query: Annotated[NewsQuery, Query()],
    service: Annotated[NewsApiService, Depends(get_news_service)],
) -> NewsListResponse:
    return await service.query_news(query)


@router.get(
    "/{news_id}",
    response_model=NewsDetailResponse,
)
async def get_news_detail(
    news_id: Annotated[str, Path(min_length=1, max_length=200)],
    service: Annotated[NewsApiService, Depends(get_news_service)],
) -> NewsDetailResponse:
    detail = await service.get_api_detail(news_id)
    if detail is None:
        raise NewsNotFoundError
    return detail


# FastAPI owns these mappings; typed Pydantic metadata avoids handwritten untyped maps.
for api_route in router.routes:
    if isinstance(api_route, APIRoute):
        for status_code in (404, 422, 500):
            api_route.responses[status_code] = _ErrorDocumentation().model_dump()
            api_route.response_fields[status_code] = create_model_field(
                name=f"NewsError{status_code}", type_=ApiErrorResponse, mode="serialization"
            )


def create_app(service: NewsApiService) -> FastAPI:
    """App factory for embedding or tests; owns no DB/Redis/LLM connections.

    Production composition creates NewsService with its dependencies and a stable
    cursor key, then passes it here. It also owns their startup/shutdown lifecycle.
    """
    app = FastAPI(title="DAIT News API", version="1.0.1")

    async def provide_service() -> NewsApiService:
        return service

    app.dependency_overrides[get_news_service] = provide_service
    # 라우터를 등록할 때 prefix="/v1"을 지정하여
    # 최종 경로가 /v1/news 및 /v1/news/{news_id}가 되도록 조합합니다.
    app.include_router(router, prefix="/v1")
    return app

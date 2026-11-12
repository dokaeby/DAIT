"""FastAPI 앱을 조립한다. 라우터는 한 줄씩 등록하며 업무 로직은 두지 않는다."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from dait.api.deps import get_throttles
from dait.api.v1 import (
    auth_routes,
    health_routes,
    interest_routes,
    me_routes,
    news_routes,
    scheduler_routes,
    settings_routes,
)
from dait.core.config import Settings, get_settings
from dait.core.errors import register_error_handlers
from dait.core.logging import configure_logging
from dait.core.middleware import RequestContextMiddleware
from dait.services.legacy_news_service import import_saved_news
from dait.services.login_throttle import create_throttles


def create_app(settings: Settings | None = None) -> FastAPI:
    """설정에 맞는 FastAPI 앱을 만든다.

    입력: settings (None이면 환경변수에서 읽은 설정, 테스트는 직접 넘김)
    출력: FastAPI (미들웨어·오류 핸들러·라우터가 연결된 앱)
    기능: release에서는 docs/redoc/openapi 경로를 만들지 않는다.
          설정이 잘못되면 여기서 예외가 나 시작이 막힌다.
    """
    config = settings if settings is not None else get_settings()
    configure_logging(config)
    docs = config.docs_enabled

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
        await run_in_threadpool(import_saved_news, config)
        yield

    app = FastAPI(
        lifespan=lifespan,
        title="DAIT 회원 API",
        docs_url="/docs" if docs else None,
        redoc_url="/redoc" if docs else None,
        openapi_url="/openapi.json" if docs else None,
    )
    app.dependency_overrides[get_settings] = lambda: config  # 라우트가 같은 설정을 보게 한다.
    register_error_handlers(app)
    if config.cors_origins:  # 허용 출처가 없으면 CORS 자체를 켜지 않는다(와일드카드 금지).
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        )
    # 마지막에 추가한 미들웨어가 가장 바깥이라, CORS 사전 요청 응답에도 보안 헤더가 붙는다.
    app.add_middleware(
        RequestContextMiddleware,
        csp=config.content_security_policy,
        html_csp=(
            "default-src 'self'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
            "connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
        ),
    )
    # 앱마다 하나: REDIS_URL이 있으면 실패 기록을 Redis에 공유하고, 없으면 메모리에 둔다.
    throttles = create_throttles(config)
    app.dependency_overrides[get_throttles] = lambda: throttles
    app.include_router(health_routes.router)
    app.include_router(auth_routes.router)
    app.include_router(me_routes.router)
    app.include_router(interest_routes.router)
    app.include_router(news_routes.router)
    app.include_router(settings_routes.router)
    app.include_router(scheduler_routes.router)
    frontend_dir = Path(__file__).resolve().parents[3] / "frontend" / "public"
    if frontend_dir.is_dir():
        app.mount("/mockup", StaticFiles(directory=str(frontend_dir)), name="mockup-static")

        for route_path, filename in (
            ("/", "index.html"),
            ("/settings.html", "settings.html"),
            ("/app.js", "app.js"),
        ):

            def _serve(f: Path = frontend_dir / filename) -> FileResponse:
                return FileResponse(
                    path=str(f), media_type=_media_type(f), headers={"Cache-Control": "no-cache"}
                )

            app.add_api_route(
                route_path,
                _serve,
                include_in_schema=False,
                methods=["GET"],
            )
    return app


def _media_type(path: Path) -> str:
    """정적 파일 경로의 Content-Type을 정한다."""
    return {
        ".html": "text/html",
        ".js": "text/javascript",
        ".css": "text/css",
    }.get(path.suffix.lower(), "application/octet-stream")

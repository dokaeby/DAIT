"""FastAPI 앱을 조립한다. 라우터는 한 줄씩 등록하며 업무 로직은 두지 않는다."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dait.api.auth import router as auth_router
from dait.api.deps import get_throttles
from dait.api.health import router as health_router
from dait.api.interests import router as interests_router
from dait.api.me import router as me_router
from dait.api.two_factor import router as two_factor_router
from dait.core.config import Settings, get_settings
from dait.core.errors import register_error_handlers
from dait.core.logging import configure_logging
from dait.core.middleware import RequestContextMiddleware
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
    app = FastAPI(
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
    app.add_middleware(RequestContextMiddleware, csp=config.content_security_policy)
    throttles = create_throttles()  # 앱마다 하나: 실패 기록은 프로세스 메모리에만 있다.
    app.dependency_overrides[get_throttles] = lambda: throttles
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(me_router)
    app.include_router(interests_router)
    if config.two_factor_enabled:  # 꺼져 있으면 2차 인증 경로 자체가 없다.
        app.include_router(two_factor_router)
    return app

"""실행: python -m uvicorn dait.main:app --host 127.0.0.1 --port 8000"""
import logging
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .auth import router as auth_router
from .compatibility import router as compatibility_router
from .settings import router as settings_router
from dait.repositories.user_repository import initialize_auth_db
from .interests import router as interests_router
from . import news

@asynccontextmanager
async def lifespan(app: FastAPI):
    from dait.core.config import ensure_runtime_dirs
    ensure_runtime_dirs()
    initialize_auth_db()
    news.summary_service.worker.start()
    try:
        yield
    finally:
        news.summary_service.worker.stop()


app = FastAPI(title="DAIT API", version="0.2.0", description="DB 회원 로그인·세션 및 기존 화면 연결", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(compatibility_router)
app.include_router(settings_router)
app.include_router(interests_router)
logger = logging.getLogger(__name__)


@app.middleware("http")
async def disable_response_cache(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    # 기본 검증 응답의 input 필드로 비밀번호를 다시 전달하지 않습니다.
    if request.url.path == "/api/interests":
        return JSONResponse({"error": "관심 카테고리를 한 개 이상 선택하고 선택 항목을 확인해주세요."}, status_code=422)
    if request.url.path == "/signup":
        errors = {}
        for error in exc.errors():
            field = error["loc"][-1] if error["loc"] else ""
            if field == "nickname":
                errors[field] = "닉네임을 1~30자로 입력해주세요."
            elif field == "user":
                errors[field] = "아이디는 공백 없이 1~30자로 입력해주세요."
            elif field in ("password", "password_confirm"):
                if error["type"] == "value_error" and field == "password_confirm":
                    errors[field] = "비밀번호가 일치 하지 않습니다. 다시 입력해주세요"
                elif error.get("ctx", {}).get("max_length"):
                    errors[field] = "비밀번호는 최대 128자까지 입력해주세요."
                else:
                    errors[field] = "비밀번호는 최소 5자 이상 입력해주세요"
        return JSONResponse({"error": next(iter(errors.values()), "입력값을 확인해주세요."), "field_errors": errors}, status_code=422)
    message = ("아이디와 비밀번호를 입력하고 입력 길이를 확인해 주세요." if request.url.path == "/login"
               else "요청 형식과 입력값의 길이·범위를 확인해 주세요.")
    return JSONResponse({"error": message}, status_code=422)


@app.exception_handler(sqlite3.Error)
async def database_error(request: Request, exc: sqlite3.Error):
    logger.error("DB 처리 실패: %s", exc)
    return JSONResponse({"error": "데이터베이스를 조회할 수 없습니다."}, status_code=500)


@app.exception_handler(OSError)
async def file_error(request: Request, exc: OSError):
    logger.error("파일 처리 실패: %s", exc)
    return JSONResponse({"error": "필요한 파일을 읽을 수 없습니다."}, status_code=500)

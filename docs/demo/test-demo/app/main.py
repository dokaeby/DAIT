"""FastAPI entrypoint for the standalone DAIT local demo."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Literal, cast

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response

from .common import Criteria, ScheduleCreate, SchedulePatch, SettingsPatch, error_body
from .database import (
    DEMO_USER_ID,
    connect,
    create_schedule,
    delete_schedule,
    enabled_source_ids,
    get_news_detail,
    get_settings,
    initialize_database,
    list_news,
    list_schedules,
    update_schedule,
    update_settings,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "data" / "dait.db"


def create_app(db_path: Path | None = None, static_dir: Path | None = None) -> FastAPI:
    database_path = Path(db_path or os.getenv("DAIT_DB_PATH", DEFAULT_DB_PATH))
    public_path = Path(static_dir or ROOT / "public")
    initialize_database(database_path)
    application = FastAPI(title="DAIT Local Demo", version="1.0.1")
    application.state.db_path = database_path
    application.state.static_dir = static_dir

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        fields = {
            ".".join(str(part) for part in error["loc"] if part not in {"body", "query"}): error["msg"]
            for error in exc.errors()
        }
        return JSONResponse(
            status_code=422,
            content=error_body(request, "VALIDATION_ERROR", "입력값을 확인해 주세요.", fields),
        )

    @application.get("/healthz")
    async def health():
        return {"status": "ok"}

    @application.get("/readyz")
    async def ready(request: Request):
        try:
            with connect(database_path) as connection:
                connection.execute("SELECT 1").fetchone()
        except sqlite3.Error:
            return JSONResponse(
                status_code=503,
                content=error_body(request, "DEPENDENCY_UNAVAILABLE", "데이터베이스를 사용할 수 없습니다."),
            )
        return {
            "status": "ready",
            "dependencies": {"database": "ok", "redis": "not_used"},
        }

    @application.get("/v1/news")
    async def news_list(
        request: Request,
        category: Literal["AI"] = "AI",
        q: str | None = Query(default=None, max_length=100),
        sort: Literal["rank", "latest"] = "rank",
        page_size: int = Query(default=10, ge=1, le=50),
        cursor: str | None = None,
    ):
        if cursor is not None:
            return JSONResponse(
                status_code=422,
                content=error_body(
                    request,
                    "VALIDATION_ERROR",
                    "cursor는 이 로컬 데모에서 지원하지 않습니다.",
                ),
            )
        query = q.strip() if q and q.strip() else None
        try:
            rows = list_news(database_path, query=query, sort=sort, page_size=page_size)
        except (sqlite3.Error, ValueError, TypeError):
            return JSONResponse(
                status_code=500,
                content=error_body(request, "INTERNAL_ERROR", "요청을 처리하지 못했습니다."),
            )
        items = [
            {
                "id": row["id"],
                "rank": index,
                "title": row["title"],
                "source_name": row["source_name"],
                "published_at": row["published_at"],
                "category": row["category"],
                "summary_lines": row["summary_lines"],
                "processing_status": row["processing_status"],
                "original_url": row["canonical_url"],
                "is_partial": row["processing_status"] != "READY",
            }
            for index, row in enumerate(rows, 1)
        ]
        partial = any(item["is_partial"] for item in items)
        return {
            "items": items,
            "page": {"next_cursor": None, "has_more": False},
            "meta": {
                "total_visible": len(items),
                "partial": partial,
                "message": "일부 기사의 원문 정보가 부족합니다." if partial else None,
                "rank_basis": ["processing_status", "source_priority", "published_at"],
            },
        }

    @application.get("/v1/news/{news_id}")
    async def news_detail(news_id: str, request: Request):
        try:
            row = get_news_detail(database_path, news_id)
        except (sqlite3.Error, ValueError, TypeError):
            return JSONResponse(
                status_code=500,
                content=error_body(request, "INTERNAL_ERROR", "요청을 처리하지 못했습니다."),
            )
        if row is None:
            return JSONResponse(
                status_code=404,
                content=error_body(request, "NEWS_NOT_FOUND", "요청한 뉴스를 찾을 수 없습니다."),
            )
        translated = cast(str, row["translated_text"] or "")
        canonical_url = cast(str, row["canonical_url"])
        return {
            "article": {
                "id": row["id"],
                "title": row["title"],
                "source_name": row["source_name"],
                "published_at": row["published_at"],
                "original_language": row["original_language"],
                "category": row["category"],
                "estimated_read_minutes": max(1, len(translated.split()) // 200) if translated else None,
            },
            "content": {
                "summary_lines": row["summary_lines"],
                "translated_text": row["translated_text"],
                "processed_at": row["processed_at"],
                "content_status": row["content_status"],
                "summary_model_version": row["prompt_version"],
            },
            "source": {
                "original_url": canonical_url,
                "url_verified": canonical_url.startswith("https://"),
                "source_type": row["source_type"],
            },
            "related_news": row["related_news"],
            "processing": {
                "collection_status": "SUCCEEDED",
                "translation_status": "SUCCEEDED" if row["translated_text"] else "INSUFFICIENT",
                "summary_status": row["content_status"],
            },
        }

    def invalid_sources(request: Request, source_ids: list[str]) -> JSONResponse | None:
        if set(source_ids) != enabled_source_ids(database_path, source_ids):
            return JSONResponse(
                status_code=422,
                content=error_body(
                    request,
                    "VALIDATION_ERROR",
                    "활성화된 승인 출처만 선택할 수 있습니다.",
                    {"source_ids": "unknown or disabled source"},
                ),
            )
        return None

    @application.get("/v1/me/settings")
    async def settings_get():
        return get_settings(database_path, DEMO_USER_ID)

    @application.patch("/v1/me/settings")
    async def settings_patch(payload: SettingsPatch, request: Request):
        values = payload.model_dump(exclude_unset=True)
        if "source_ids" in values:
            error = invalid_sources(request, values["source_ids"])
            if error:
                return error
        return update_settings(database_path, DEMO_USER_ID, values)

    @application.get("/v1/me/schedules")
    async def schedules_get():
        return {"items": list_schedules(database_path, DEMO_USER_ID)}

    @application.post("/v1/me/schedules", status_code=201)
    async def schedules_post(payload: ScheduleCreate, request: Request):
        values = payload.model_dump()
        error = invalid_sources(request, values["criteria"]["source_ids"])
        if error:
            return error
        return create_schedule(database_path, DEMO_USER_ID, values)

    @application.patch("/v1/me/schedules/{schedule_id}")
    async def schedules_patch(schedule_id: str, payload: SchedulePatch, request: Request):
        values = payload.model_dump(exclude_unset=True)
        if "criteria" in values:
            error = invalid_sources(request, values["criteria"]["source_ids"])
            if error:
                return error
        schedule = update_schedule(database_path, DEMO_USER_ID, schedule_id, values)
        if schedule is None:
            return JSONResponse(
                status_code=404,
                content=error_body(request, "SCHEDULE_NOT_FOUND", "예약을 찾을 수 없습니다."),
            )
        return schedule

    @application.delete("/v1/me/schedules/{schedule_id}", status_code=204)
    async def schedules_delete(schedule_id: str, request: Request):
        if not delete_schedule(database_path, DEMO_USER_ID, schedule_id):
            return JSONResponse(
                status_code=404,
                content=error_body(request, "SCHEDULE_NOT_FOUND", "예약을 찾을 수 없습니다."),
            )
        return None

    @application.get("/", include_in_schema=False)
    async def main_page():
        return HTMLResponse((public_path / "index.html").read_text(encoding="utf-8"))

    @application.get("/detail.html", include_in_schema=False)
    async def detail_page():
        return HTMLResponse((public_path / "detail.html").read_text(encoding="utf-8"))

    @application.get("/settings.html", include_in_schema=False)
    async def settings_page():
        return HTMLResponse((public_path / "settings.html").read_text(encoding="utf-8"))

    @application.get("/styles.css", include_in_schema=False)
    async def styles():
        return Response((public_path / "styles.css").read_text(encoding="utf-8"), media_type="text/css")

    @application.get("/app.js", include_in_schema=False)
    async def script():
        return Response(
            (public_path / "app.js").read_text(encoding="utf-8"),
            media_type="application/javascript",
        )

    @application.get("/schedule-actions.js", include_in_schema=False)
    async def schedule_actions_script():
        return Response(
            (public_path / "schedule-actions.js").read_text(encoding="utf-8"),
            media_type="application/javascript",
        )

    return application


app = create_app()

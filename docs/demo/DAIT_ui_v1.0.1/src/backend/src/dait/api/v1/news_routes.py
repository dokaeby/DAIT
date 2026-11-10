"""로그인 전환을 기존 화면에서 확인하기 위한 HTTP 연결부.

기사 조회·추천·검색·요약 처리는 기존 함수를 그대로 호출합니다.
"""
import sqlite3
from typing import Annotated, Literal
from urllib.parse import unquote, urlsplit

from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response

from dait.auth import current_user
from dait.repositories.user_repository import display_nickname
from dait import news
from dait.core.config import ASSETS_DIR
from dait.schemas import SearchJobRequest, SummaryJobRequest
from dait.preferences import user_interests

router = APIRouter(tags=["기존 화면 연결"])
CurrentUser = Annotated[str | None, Depends(current_user)]


@router.get("/assets/{filename}", include_in_schema=False)
def asset(filename: str) -> Response:
    if filename not in {"design.css", "app.css", "app.js", "detail.js", "settings.js", "interests.js"}:
        return JSONResponse({"error": "파일을 찾을 수 없습니다."}, status_code=404)
    media_type = "text/css" if filename.endswith(".css") else "text/javascript"
    return FileResponse(ASSETS_DIR / filename, media_type=media_type)


@router.get("/", response_class=HTMLResponse, summary="비로그인·맞춤 메인")
def homepage(user: CurrentUser,
             q: Annotated[str, Query(max_length=200)] = "",
             category: Annotated[str, Query(max_length=40)] = "",
             sort: Literal["rank", "latest"] = "rank",
             search_job: Annotated[str, Query(max_length=128)] = "") -> Response:
    query = news.normalize_query(q)
    selected = user_interests(user)
    scores = None
    fallback = False
    if search_job:
        job = news.search_lab_service.get(search_job, user)
        data = job.get("result") if job and job["status"] == "completed" else None
        if (not data or data.get("query") != query or data.get("user") != (user or "비로그인")
                or data.get("category", "") != category
                or sorted(data.get("interests", [])) != sorted(selected)):
            return JSONResponse({"error": "현재 계정의 검색 결과를 찾을 수 없습니다."}, status_code=404)
        rows, scores = [], {}
        for item in data["hybrid"]:
            article = news.get_article(item["id"])
            if article is not None:
                rows.append((item["id"], article[0], article[1], article[2], article[7], article[6], article[3]))
                scores[item["id"]] = item["cosine"]
        if sort == "latest":
            rows.sort(key=lambda row: row[3], reverse=True)
    else:
        rows = news.recommended_articles(user, query, category, interests=selected) if user else news.latest_articles(query, category)
    if user and selected and not query and not category and not search_job and not rows:
        rows = news.latest_articles()
        fallback = True
    return HTMLResponse(news.page(rows, user, query, scores, category, sort, interests=selected, nickname=display_nickname(user), fallback=fallback))


@router.get("/article/{article_id}", response_class=HTMLResponse, summary="기사 상세·팝업 데이터")
def article_detail(article_id: str, user: CurrentUser, format: Literal["html", "json"] = "html") -> Response:
    article = news.get_article(article_id)
    if article is None:
        return JSONResponse({"error": "해당 기사를 찾을 수 없습니다."}, status_code=404)
    summary = news.get_saved_summary(article_id, article[0], article[3], article[6])
    translation = summary if article[6] else None
    if format == "json":
        title, source, published, description, content, original_url, foreign, categories = article
        url = urlsplit(original_url or "")
        safe_url = original_url if url.scheme in ("http", "https") and url.netloc else None
        display_title = translation["title_ko"] if translation and translation["title_ko"] else title
        notice = ("해외 기사 · AI 번역 제목과 원문 RSS 설명을 함께 제공합니다." if translation and translation["title_ko"]
                  else "해외 기사 · 한국어 결과가 준비되지 않아 원문 제목과 설명을 표시합니다." if foreign else "")
        return JSONResponse({"title": display_title, "original_title": title, "foreign_notice": notice,
                             "source": source, "published_at": news.display_date(published),
                             "description": description or content or "", "original_url": safe_url,
                             "is_foreign": bool(foreign), "categories": categories, "ai_summary": summary})
    return HTMLResponse(news.detail_page(article, user, summary, translation))


@router.get("/api/search-lab/info")
def search_info(user: CurrentUser):
    return {"user": user, "interests": user_interests(user), "model": news.search_lab_service.MODEL,
            "index_exists": news.search_lab_service.INDEX_DB.is_file()}


@router.get("/api/search-lab/jobs/{job_id}")
def search_job_status(job_id: str, user: CurrentUser) -> Response:
    job = news.search_lab_service.get(job_id, user)
    return JSONResponse(job or {"error": "작업을 찾을 수 없습니다. 현재 계정을 확인해 주세요."}, status_code=200 if job else 404)


def start_job(action) -> Response:
    try:
        return JSONResponse({"job_id": action()}, status_code=202)
    except RuntimeError as exc:
        return JSONResponse({"error": str(exc)}, status_code=409)
    except (ValueError, TypeError, sqlite3.Error, OSError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@router.post("/api/search-lab/jobs", status_code=202)
def start_search(data: SearchJobRequest, user: CurrentUser) -> Response:
    selected = user_interests(user)
    return start_job(lambda: news.search_lab_service.start(data.action, data.query, data.min_score, user, data.category, interests=selected))


@router.get("/api/summary/batch-status")
def summary_batch_status():
    return news.summary_service.batch_status()


@router.get("/api/summary/jobs/{job_id}")
def summary_job_status(job_id: str) -> Response:
    job = news.summary_service.get(job_id)
    return JSONResponse(job or {"error": "작업을 찾을 수 없습니다."}, status_code=200 if job else 404)


@router.post("/api/summary/batch", status_code=202)
def start_summary_batch(data: Annotated[dict, Body()]) -> Response:
    return start_job(news.summary_service.start_batch)


@router.post("/api/summary/jobs", status_code=202)
def start_summary(data: SummaryJobRequest) -> Response:
    article_id = unquote(data.article_path[len("/article/"):])
    article = news.get_article(article_id)
    if article is None:
        return JSONResponse({"error": "기사를 찾을 수 없습니다."}, status_code=400)
    return start_job(lambda: news.summary_service.start(article_id, article))

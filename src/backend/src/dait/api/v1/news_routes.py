"""뉴스 목록·갱신 API — 저장소의 처리 완료 기사를 제공하고 수집을 트리거한다."""

from __future__ import annotations

from typing import Annotated

from dait.collectors.rss import FEED_SOURCES
from dait.repositories.news_repository import NewsRepository
from dait.services.collection_service import CollectionService
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict

router = APIRouter(prefix="/v1/news", tags=["news"])

_VALID_CATEGORIES = {s.category for s in FEED_SOURCES}


class NewsItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    title: str
    body_text: str
    category: str
    is_foreign: bool
    published_at: str
    status: str
    summary_lines: list[str]
    translated_title: str | None
    engine: str
    model_id: str


class NewsListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[NewsItem]
    counts: dict[str, int]


class RefreshResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collected: int
    processed: int
    counts: dict[str, int]


def get_repository(request: Request) -> NewsRepository:
    repo: NewsRepository | None = request.app.state.news_repository
    if repo is None:
        raise HTTPException(status_code=503, detail="news repository not initialized")
    return repo


def get_collection_service(request: Request) -> CollectionService:
    service: CollectionService | None = request.app.state.collection_service
    if service is None:
        raise HTTPException(status_code=503, detail="collection service not initialized")
    return service


RepoDep = Annotated[NewsRepository, Depends(get_repository)]
ServiceDep = Annotated[CollectionService, Depends(get_collection_service)]


@router.get("", response_model=NewsListResponse)
async def list_news(
    repo: RepoDep,
    category: Annotated[str | None, Query(max_length=50)] = None,
) -> NewsListResponse:
    if category is not None and category not in _VALID_CATEGORIES:
        raise HTTPException(status_code=422, detail="unknown category")
    items = [NewsItem.model_validate(a) for a in repo.list_articles(category)]
    return NewsListResponse(items=items, counts=repo.category_counts())


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_news(
    service: ServiceDep,
    repo: RepoDep,
    category: Annotated[str | None, Query(max_length=50)] = None,
) -> RefreshResponse:
    if category is not None and category not in _VALID_CATEGORIES:
        raise HTTPException(status_code=422, detail="unknown category")
    stats = (
        await service.collect_category(category)
        if category
        else await service.collect_all()
    )
    return RefreshResponse(**stats, counts=repo.category_counts())

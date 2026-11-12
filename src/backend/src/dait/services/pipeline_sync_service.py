"""pipeline 스키마의 수집·AI 처리 결과를 공개 스키마로 동기화한다.

배경: 뉴스 수집·요약·번역은 pipeline 서비스(src/backend/app)가 담당하고
pipeline 스키마에 저장한다. 공개 API는 public 스키마의 news/content_results만
읽으므로, 처리 완료(SUCCESS)된 기사만 주기적으로 복사해 온다.

동작: sync_if_needed가 일정 간격마다 sync_pipeline_news를 호출한다.
PostgreSQL 전용 — SQLite(로컬/테스트)에서는 pipeline 스키마가 없으므로 건너뛴다.
"""

import json
import logging
import threading
import time
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any
from uuid import uuid4

from dait.core.config import Settings
from dait.repositories import db as db_module
from dait.repositories.db import DbConnection, transaction
from dait.schemas.news import ACTIVE_CATEGORIES, NewsCategory

logger = logging.getLogger(__name__)

_SYNC_INTERVAL_SECONDS = 300.0
_EN_SOURCE_NAMES = frozenset({"MIT Tech Review", "TechCrunch", "The Verge"})
_CATEGORY_MAP = {"SOCIETY": NewsCategory.POLITICS.value}
_lock = threading.Lock()
_state = {"last_sync_monotonic": 0.0}


def sync_if_needed(settings: Settings) -> None:
    """간격이 지났으면 pipeline → public 동기화를 1회 실행한다.

    입력: settings (데이터베이스 URL·Redis 설정)
    출력: 없음
    기능: postgres가 아니거나 간격 미만이면 즉시 반환한다. 동기화 실패는
          로그만 남기고 API 응답에는 영향을 주지 않는다.
    """
    if db_module.db_dialect(settings.database_url) != "postgres":
        return
    now = time.monotonic()
    if now - _state["last_sync_monotonic"] < _SYNC_INTERVAL_SECONDS:
        return
    with _lock:
        now = time.monotonic()
        if now - _state["last_sync_monotonic"] < _SYNC_INTERVAL_SECONDS:
            return
        _state["last_sync_monotonic"] = now
        try:
            with transaction(settings.database_url) as conn:
                inserted = sync_pipeline_news(conn)
            if inserted:
                logger.info("pipeline 뉴스 동기화 완료: %d건", inserted)
        except Exception:
            logger.warning("pipeline 뉴스 동기화 실패", exc_info=True)


def _source_language(source_name: str) -> str:
    """출처 이름으로 원문 언어를 추정한다."""
    return "en" if source_name in _EN_SOURCE_NAMES else "ko"


def _category_for(raw: str) -> str | None:
    """pipeline 카테고리를 공개 카테고리로 변환한다. 변환 불가면 None."""
    mapped = _CATEGORY_MAP.get(raw, raw)
    try:
        category = NewsCategory(mapped)
    except ValueError:
        return None
    return category.value if category in ACTIVE_CATEGORIES else None


def _lines(row: tuple[Any, ...]) -> list[str]:
    """content_results의 line_1~3을 비어 있지 않은 문자열 목록으로 만든다."""
    return [line for line in row[5:8] if isinstance(line, str) and line.strip()]


def sync_pipeline_news(conn: DbConnection) -> int:
    """처리 완료된 pipeline 기사를 public news/content_results에 복사한다.

    입력: conn (호출자가 연 트랜잭션 연결)
    출력: 새로 삽입한 기사 수
    기능: canonical_url 중복은 삽입하지 않는다. SUCCESS가 아닌 기사는
          다음 동기화에서 다시 시도한다. 요약 3줄이 모두 있으면 READY,
          부족하면 INSUFFICIENT로 기록한다.
    """
    source_rows = conn.execute("SELECT id, name FROM sources").fetchall()
    source_id_by_name = {row[1]: row[0] for row in source_rows}
    now = datetime.now(UTC)
    rows = conn.execute(
        "SELECT n.source_name, n.title, n.canonical_url, n.published_at, "
        "n.category, c.line_1, c.line_2, c.line_3, c.translated_text, "
        "c.model_id, c.prompt_version "
        "FROM pipeline.news n "
        "JOIN pipeline.content_results c ON c.news_id = n.id "
        "WHERE c.status = 'SUCCESS' "
        "AND n.canonical_url LIKE 'https://%' "
        "AND NOT EXISTS (SELECT 1 FROM news x WHERE x.canonical_url = n.canonical_url)"
    ).fetchall()

    inserted = 0
    for row in rows:
        source_name, title, canonical_url, published_at, raw_category = row[:5]
        source_id = source_id_by_name.get(source_name)
        category = _category_for(raw_category)
        if source_id is None or category is None:
            continue
        lines = _lines(row)
        status = "READY" if len(lines) == 3 else "INSUFFICIENT"
        news_id = uuid4().hex
        if isinstance(published_at, datetime):
            published = published_at
        elif isinstance(published_at, str):
            try:
                published = datetime.fromisoformat(published_at)
            except ValueError:
                published = now
        else:
            published = now
        if published.tzinfo is None:
            published = published.replace(tzinfo=UTC)
        now_iso = now.isoformat()
        conn.execute(
            "INSERT INTO news (id, source_id, title, canonical_url, published_at, "
            "collected_at, category, original_language, content_hash, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                news_id,
                source_id,
                title,
                canonical_url,
                published.isoformat(),
                now_iso,
                category,
                _source_language(source_name),
                sha256(canonical_url.encode()).hexdigest(),
                now_iso,
            ),
        )
        conn.execute(
            "INSERT INTO content_results (news_id, status, summary_lines, "
            "translated_text, model_id, prompt_version, processed_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                news_id,
                status,
                json.dumps(lines[:3], ensure_ascii=False),
                row[8] or "",
                row[9],
                row[10],
                now_iso,
                now_iso,
            ),
        )
        inserted += 1
    return inserted

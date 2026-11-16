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
from typing import Any, cast
from uuid import uuid4

from dait.core.article_language import (
    allowed_summary_lines,
    is_korean_or_english_text,
    is_korean_text,
    looks_foreign_text,
)
from dait.core.config import Settings
from dait.repositories import db as db_module
from dait.repositories.db import DbConnection, transaction
from dait.schemas.news import ACTIVE_CATEGORIES, NewsCategory
from dait.services import feed_index_service

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
                feed_index_service.classify_pending(conn)
            if inserted:
                logger.info("pipeline 뉴스 동기화 완료: %d건", inserted)
        except Exception:
            logger.warning("pipeline 뉴스 동기화 실패", exc_info=True)


def _source_language(source_name: str, raw_title: str | None) -> str:
    """출처가 아니라 원문 제목의 문자 구성으로 원문 언어를 추정한다."""
    if source_name in _EN_SOURCE_NAMES:
        return "en"
    original = (raw_title or "").split(" ||| ", 1)[0].strip()
    if is_korean_text(original):
        return "ko"
    if looks_foreign_text(original):
        return "en"
    return "und"


def _publishable_lines(lines: list[str]) -> list[str]:
    """공개 가능한 한국어/영어 요약 줄만 최대 3줄 남긴다."""
    return allowed_summary_lines(lines)


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


def _parse_lines(raw: str | None) -> list[str]:
    """공개 summary_lines JSON을 문자열 목록으로 되돌린다."""
    if not raw:
        return []
    try:
        value: object = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(value, list):
        return []
    return [item for item in cast("list[object]", value) if isinstance(item, str)]


def _pipeline_row(conn: DbConnection, canonical_url: str) -> tuple[Any, ...] | None:
    """canonical_url의 최신 SUCCESS pipeline 행을 읽는다."""
    return conn.execute(
        "SELECT n.source_name, n.title, n.canonical_url, n.published_at, "
        "n.category, c.line_1, c.line_2, c.line_3, c.translated_text, "
        "c.model_id, c.prompt_version "
        "FROM pipeline.news n "
        "JOIN pipeline.content_results c ON c.news_id = n.id "
        "WHERE c.status = 'SUCCESS' AND n.canonical_url = ? "
        "ORDER BY n.published_at DESC LIMIT 1",
        (canonical_url,),
    ).fetchone()


def _repair_public_rows(conn: DbConnection, now: datetime) -> int:
    """이미 공개된 요약을 한국어/영어 1~3줄 규칙에 맞게 복구한다."""
    rows = conn.execute(
        "SELECT n.id, n.title, n.canonical_url, n.original_language, c.status, "
        "c.summary_lines, c.translated_text "
        "FROM news n "
        "JOIN content_results c ON c.news_id = n.id "
        "WHERE c.status IN ('READY', 'INSUFFICIENT', 'PENDING') "
        "AND n.canonical_url LIKE 'https://%' "
        "AND EXISTS ("
        "SELECT 1 FROM pipeline.news pn "
        "JOIN pipeline.content_results pc ON pc.news_id = pn.id "
        "WHERE pn.canonical_url = n.canonical_url AND pc.status = 'SUCCESS'"
        ")"
    ).fetchall()
    changed = 0
    now_iso = now.isoformat()
    for (
        public_id,
        current_title,
        canonical_url,
        original_language,
        status,
        summary_raw,
        translated_raw,
    ) in rows:
        stored_lines = allowed_summary_lines(_parse_lines(summary_raw))
        stored_valid = status == "READY" and bool(stored_lines)
        stored_has_korean = any(is_korean_text(line) for line in stored_lines)
        stored_needs_language = (
            status == "READY"
            and original_language in ("ko", "und")
            and bool(stored_lines)
            and not stored_has_korean
        )
        translated_ok = not translated_raw or is_korean_or_english_text(translated_raw)
        needs_check = (
            status != "READY"
            or not stored_valid
            or stored_needs_language
            or (original_language not in ("ko", "und") and not translated_ok)
        )
        if not needs_check:
            continue
        pipeline_row = _pipeline_row(conn, canonical_url)
        if pipeline_row is None:
            continue
        source_name, raw_title = pipeline_row[0], pipeline_row[1]
        lines = _publishable_lines(_lines(pipeline_row))
        valid_ready = bool(lines)
        language = _source_language(source_name, raw_title)
        title = raw_title.split(" ||| ", 1)[0].strip() if raw_title else raw_title
        translated = pipeline_row[8] if isinstance(pipeline_row[8], str) else ""
        safe_translated = (
            translated if translated and is_korean_text(translated) else " ".join(lines)
        )
        if valid_ready:
            new_summary = json.dumps(lines, ensure_ascii=False)
            unchanged = (
                status == "READY"
                and summary_raw == new_summary
                and translated_raw == safe_translated
                and original_language == language
                and current_title == title
            )
            if unchanged:
                continue
            conn.execute(
                "UPDATE news SET title = ?, original_language = ? WHERE id = ?",
                (title, language, public_id),
            )
            conn.execute(
                "UPDATE content_results SET status = 'READY', summary_lines = ?, "
                "translated_text = ?, model_id = ?, prompt_version = ?, "
                "processed_at = ?, updated_at = ? WHERE news_id = ?",
                (
                    new_summary,
                    safe_translated,
                    pipeline_row[9],
                    pipeline_row[10],
                    now_iso,
                    now_iso,
                    public_id,
                ),
            )
            changed += 1
            continue
        already_hidden = status == "PENDING" and summary_raw in (None, "[]") and not translated_raw
        if not already_hidden:
            conn.execute(
                "UPDATE content_results SET status = 'PENDING', summary_lines = '[]', "
                "translated_text = NULL, model_id = NULL, prompt_version = NULL, "
                "processed_at = ?, updated_at = ? WHERE news_id = ?",
                (now_iso, now_iso, public_id),
            )
            changed += 1
    return changed


def sync_pipeline_news(conn: DbConnection) -> int:
    """처리 완료된 pipeline 기사를 public news/content_results에 복사한다.

    입력: conn (호출자가 연 트랜잭션 연결)
    출력: 새로 삽입하고 복구한 행 수
    기능: canonical_url 중복은 삽입하지 않는다. SUCCESS가 아니거나 공개 가능한
          한국어/영어 요약이 없으면 다음 동기화에서 다시 시도한다.
    """
    source_rows = conn.execute("SELECT id, name FROM sources").fetchall()
    source_id_by_name = {row[1]: row[0] for row in source_rows}
    now = datetime.now(UTC)
    repaired = _repair_public_rows(conn, now)
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
        source_name, raw_title, canonical_url, published_at, raw_category = row[:5]
        # pipeline은 외국어 기사 제목을 "원문 ||| 한국어번역"으로 저장한다.
        # 공개 제목은 원문 부분만 사용하고 번역은 translated_text가 담당한다.
        title = raw_title.split(" ||| ", 1)[0].strip() if raw_title else raw_title
        source_id = source_id_by_name.get(source_name)
        category = _category_for(raw_category)
        if source_id is None or category is None:
            continue
        lines = _publishable_lines(_lines(row))
        if not lines:
            continue
        status = "READY"
        language = _source_language(source_name, raw_title)
        translated_raw = row[8] if isinstance(row[8], str) else ""
        translated_text = (
            translated_raw if translated_raw and is_korean_text(translated_raw) else " ".join(lines)
        )
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
                language,
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
                json.dumps(lines, ensure_ascii=False),
                translated_text,
                row[9],
                row[10],
                now_iso,
                now_iso,
            ),
        )
        inserted += 1
    return inserted + repaired


_dispatch_lock = threading.Lock()
_sync_workers: list[threading.Thread] = []


def request_sync(settings: Settings) -> None:
    """Schedule saved-article synchronization without delaying a list request."""
    if db_module.db_dialect(settings.database_url) != "postgres":
        return
    if time.monotonic() - _state["last_sync_monotonic"] < _SYNC_INTERVAL_SECONDS:
        return
    with _dispatch_lock:
        if _sync_workers and _sync_workers[0].is_alive():
            return
        _sync_workers[:] = [threading.Thread(target=sync_if_needed, args=(settings,), daemon=True)]
        _sync_workers[0].start()

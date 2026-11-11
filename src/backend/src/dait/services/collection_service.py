"""FR-PIPE-01 뉴스 수집: 승인 출처의 RSS/Atom 피드를 안전하게 가져와 저장한다.

수집은 jobs/job_attempts로 추적하고, canonical URL·내용 해시로 중복을 제거한다.
피드 항목은 아직 PENDING 상태이며 AI 처리(번역·요약)는 별도 단계가 담당한다.
"""

import hashlib
import uuid
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, Protocol, cast

import feedparser  # pyright: ignore[reportMissingTypeStubs]
import httpx

from dait.core.config import Settings
from dait.core.url_safety import (
    FetchedBody,
    FetchFailedError,
    Resolver,
    UnsafeUrlError,
    canonicalize_url,
    fetch_public_bytes,
    validate_public_https_url,
)
from dait.repositories import job_repository, news_repository, source_repository
from dait.repositories.db import DB_ERRORS, DB_INTEGRITY_ERRORS, transaction
from dait.schemas.pipeline import (
    CollectionSummary,
    FeedEntry,
    JobKind,
    JobStatus,
    StepName,
)
from dait.services import robots_service

MAX_ITEMS_PER_SOURCE = 100
MAX_ATTEMPTS = 3
_COLLECT_KIND = JobKind.COLLECT.value
_COLLECT_STEP = StepName.COLLECT.value

Fetcher = Callable[[str], FetchedBody]


def _dedupe_key(source_id: str, now: datetime) -> str:
    """같은 출처·같은 시간 창의 중복 수집을 막는 키를 만든다."""
    return f"collect:{source_id}:{now.strftime('%Y%m%d%H')}"


def _content_hash(title: str, summary: str | None) -> str:
    """내용 해시: URL이 달라도 같은 내용이면 잡아내는 2단계 dedupe 키."""
    return hashlib.sha256(f"{title}\n{summary or ''}".encode()).hexdigest()


def _entry_published_at(entry: Mapping[str, Any], fallback: datetime) -> datetime:
    """피드 항목의 발행 시각을 꺼낸다. 없거나 해석 불가면 수집 시각을 쓴다."""
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed is not None:
        try:
            import time

            return datetime.fromtimestamp(time.mktime(parsed), tz=UTC)
        except (OverflowError, OSError, ValueError):
            pass
    return fallback


def _to_feed_entry(entry: Mapping[str, Any], now: datetime) -> FeedEntry | None:
    """feedparser 항목을 검증된 FeedEntry로 바꾼다. 형식이 안 맞으면 None."""
    title = str(entry.get("title") or "").strip()
    link = str(entry.get("link") or "").strip()
    if not title or not link:
        return None
    summary = entry.get("summary") or entry.get("description")
    return FeedEntry(
        title=title[:500],
        url=link,
        published_at=_entry_published_at(entry, now),
        summary=str(summary)[:4000] if summary else None,
    )


class _FeedResult(Protocol):
    """feedparser 결과 중 이 모듈이 쓰는 부분만 타입으로 고정한다."""

    entries: Sequence[Mapping[str, Any]]


def _parse_feed(body: bytes) -> list[Mapping[str, Any]]:
    """피드 본문을 파싱해 항목 목록으로 돌려준다."""
    parsed = cast(_FeedResult, feedparser.parse(body))  # pyright: ignore[reportUnknownMemberType]
    return list(parsed.entries[:MAX_ITEMS_PER_SOURCE])


def _fetch_feed(url: str, fetcher: Fetcher | None, resolver: Resolver | None) -> FetchedBody:
    """피드 URL을 안전하게 가져온다. 주입된 fetcher가 있으면 그것을 쓴다."""
    if fetcher is not None:
        return fetcher(url)
    return fetch_public_bytes(httpx.Client(timeout=10.0), url, resolver=resolver)


def _run_source(
    settings: Settings,
    source: source_repository.SourceRow,
    dedupe_key: str,
    now: datetime,
    fetcher: Fetcher | None,
    resolver: Resolver | None,
) -> CollectionSummary:
    """출처 하나의 수집을 실행하고 결과를 jobs에 기록한다."""
    with transaction(settings.database_url) as conn:
        job = job_repository.create_job(conn, None, _COLLECT_KIND, dedupe_key, now, now)
        if job is None:
            existing = job_repository.get_by_dedupe_key(conn, dedupe_key)
            status = existing.status if existing else JobStatus.PENDING.value
            return CollectionSummary(
                source_id=source.id,
                status="SKIPPED",
                fetched=0,
                inserted=0,
                duplicates=0,
                rejected=0,
                error_code=f"ALREADY_{status}",
            )
        job_repository.update_status(conn, job.id, JobStatus.RUNNING.value, now, None)

    try:
        counts = _collect_one(settings, source, now, fetcher, resolver)
    except (UnsafeUrlError, FetchFailedError) as exc:
        return _record_failure(settings, source.id, job.id, now, exc)
    except (OSError, ValueError, RuntimeError, *DB_ERRORS):
        return _record_failure(settings, source.id, job.id, now, None)

    fetched, inserted, duplicates, rejected = counts
    with transaction(settings.database_url) as conn:
        job_repository.update_status(conn, job.id, JobStatus.SUCCEEDED.value, None, now)
        job_repository.record_attempt(conn, job.id, _COLLECT_STEP, 1, None, now)
    return CollectionSummary(
        source_id=source.id,
        status="SUCCEEDED",
        fetched=fetched,
        inserted=inserted,
        duplicates=duplicates,
        rejected=rejected,
        error_code=None,
    )


def _record_failure(
    settings: Settings, source_id: str, job_id: str, now: datetime, exc: Exception | None
) -> CollectionSummary:
    """수집 실패를 attempts와 최종 상태로 기록한다."""
    error_code = (
        "UNSAFE_URL"
        if isinstance(exc, UnsafeUrlError)
        else "FETCH_FAILED"
        if isinstance(exc, FetchFailedError)
        else "INTERNAL"
    )
    with transaction(settings.database_url) as conn:
        attempts = job_repository.count_attempts(conn, job_id, _COLLECT_STEP) + 1
        job_repository.record_attempt(conn, job_id, _COLLECT_STEP, attempts, error_code, now)
        status = (
            JobStatus.DEAD_LETTER.value if attempts >= MAX_ATTEMPTS else JobStatus.RETRYING.value
        )
        job_repository.update_status(
            conn, job_id, status, None, now if status == JobStatus.DEAD_LETTER.value else None
        )
    return CollectionSummary(
        source_id=source_id,
        status="FAILED",
        fetched=0,
        inserted=0,
        duplicates=0,
        rejected=0,
        error_code=error_code,
    )


def _collect_one(
    settings: Settings,
    source: source_repository.SourceRow,
    now: datetime,
    fetcher: Fetcher | None,
    resolver: Resolver | None,
) -> tuple[int, int, int, int]:
    """robots 확인→피드 fetch→정규화→dedupe→저장. (fetched, inserted, dup, rejected) 반환."""
    if not robots_service.check_robots(
        source.base_url, source.base_url, fetch=fetcher, resolver=resolver
    ):
        raise UnsafeUrlError
    body = _fetch_feed(source.base_url, fetcher, resolver)
    entries = _parse_feed(body.body)
    fetched = len(entries)
    inserted = duplicates = rejected = 0
    with transaction(settings.database_url) as conn:
        for entry in entries:
            try:
                feed_entry = _to_feed_entry(entry, now)
                if feed_entry is None:
                    rejected += 1
                    continue
                url = validate_public_https_url(feed_entry.url, resolver)
                canonical = canonicalize_url(url)
                if (
                    news_repository.find_id_by_canonical_url(conn, canonical) is not None
                    or news_repository.find_id_by_content_hash(
                        conn, _content_hash(feed_entry.title, feed_entry.summary)
                    )
                    is not None
                ):
                    duplicates += 1
                    continue
                news_id = uuid.uuid4().hex
                news_repository.insert_news(
                    conn,
                    news_id,
                    source.id,
                    feed_entry.title,
                    canonical,
                    feed_entry.published_at or now,
                    now,
                    "AI",
                    "ko",
                    _content_hash(feed_entry.title, feed_entry.summary),
                )
                news_repository.insert_pending_content(conn, news_id, now)
                inserted += 1
            except DB_INTEGRITY_ERRORS:
                duplicates += 1  # canonical_url unique 경합도 중복으로 센다.
            except (UnsafeUrlError, ValueError):
                rejected += 1
        source_repository.touch_robots_checked(conn, source.id, now)
    return fetched, inserted, duplicates, rejected


def run_collection(
    settings: Settings,
    *,
    source_ids: list[str] | None = None,
    now: datetime | None = None,
    fetcher: Fetcher | None = None,
    resolver: Resolver | None = None,
) -> list[CollectionSummary]:
    """활성 출처 전체(또는 지정 출처)의 수집을 실행한다.

    입력: settings, source_ids (None이면 전체 활성 출처), now (UTC, 테스트 주입용),
          fetcher·resolver (테스트용 주입)
    출력: CollectionSummary 목록 (출처별 결과)
    기능: 한 출처의 실패가 다른 출처 수집을 막지 않는다(부분 실패 허용).
          같은 시간 창의 재실행은 dedupe_key로 SKIPPED된다.
    """
    current = now if now is not None else datetime.now(UTC)
    with transaction(settings.database_url) as conn:
        sources = source_repository.list_enabled(conn)
    if source_ids is not None:
        wanted = set(source_ids)
        sources = [s for s in sources if s.id in wanted]
    summaries: list[CollectionSummary] = []
    for source in sources:
        summaries.append(
            _run_source(
                settings, source, _dedupe_key(source.id, current), current, fetcher, resolver
            )
        )
    return summaries

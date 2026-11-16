"""Fresh public counts and account-scoped read history, outside shared caches."""

from dait.core.config import Settings
from dait.core.errors import NewsNotFoundError
from dait.repositories import interest_repository, news_repository
from dait.repositories.db import transaction
from dait.repositories.interest_matching import KEYWORDS
from dait.schemas.news import NewsActivity
from dait.services.news_search_service import normalize_query


def activity(
    settings: Settings,
    user_id: str,
    query: str,
    ids: list[str],
    personalized: bool = False,
    language: str | None = None,
) -> NewsActivity:
    """Count visible articles and return read IDs only for the requested page."""
    normalized = normalize_query(query)
    with transaction(settings.database_url) as conn:
        all_saved = tuple(c for c in interest_repository.list_codes(conn, user_id) if c in KEYWORDS)
        saved = tuple(
            c for c in all_saved if not language or c.startswith("en.") == (language == "en")
        )
        scope = saved if personalized and all_saved else None
        counts, interest_counts = news_repository.public_news_counts(
            conn, normalized, scope, saved, language
        )
        read_ids: list[str] = []
        if ids:
            placeholders = ",".join("?" for _ in ids)
            rows = conn.execute(
                f"SELECT news_id FROM news_reads WHERE user_id = ? AND news_id IN ({placeholders})",  # noqa: S608 - bound placeholders only
                (user_id, *ids),
            ).fetchall()
            read_ids = [str(row[0]) for row in rows]
    return NewsActivity(
        total=sum(counts.values()),
        counts=counts,
        read_ids=read_ids,
        interest_counts=interest_counts,
    )


def read_state(settings: Settings, user_id: str, ids: list[str]) -> list[str]:
    """Read receipts without rerunning topic counts."""
    if not ids:
        return []
    placeholders = ",".join("?" for _ in ids)
    with transaction(settings.database_url) as conn:
        rows = conn.execute(
            f"SELECT news_id FROM news_reads WHERE user_id = ? AND news_id IN ({placeholders})",  # noqa: S608
            (user_id, *ids),
        ).fetchall()
    return [str(row[0]) for row in rows]


def mark_read(settings: Settings, user_id: str, news_id: str) -> None:
    """Record a public article once, with ownership from authentication."""
    with transaction(settings.database_url) as conn:
        if news_repository.get_public_news(conn, news_id) is None:
            raise NewsNotFoundError
        conn.execute(
            "INSERT INTO news_reads (user_id, news_id) VALUES (?, ?) ON CONFLICT DO NOTHING",
            (user_id, news_id),
        )

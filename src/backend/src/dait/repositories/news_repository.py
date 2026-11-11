"""뉴스 저장소 — SQLite 기반 원문·처리 결과 영속화.

- `articles` 테이블: canonical URL을 PK로 사용해 중복 수집을 방지한다.
- 처리 결과(summary_lines, translated_title, engine, model_id)는 JSON으로 저장한다.
- 테스트에서는 `":memory:"` 경로로 주입한다.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    url TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    body_text TEXT NOT NULL,
    category TEXT NOT NULL,
    is_foreign INTEGER NOT NULL DEFAULT 0,
    published_at TEXT NOT NULL DEFAULT '',
    collected_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    summary_lines TEXT NOT NULL DEFAULT '[]',
    translated_title TEXT,
    engine TEXT NOT NULL DEFAULT 'none',
    model_id TEXT NOT NULL DEFAULT '',
    processed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
"""


class NewsRepository:
    """스레드 안전한 SQLite 뉴스 저장소."""

    def __init__(self, db_path: str | Path = "news.db") -> None:
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    @staticmethod
    def _now() -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def insert_articles(
        self,
        articles: list[dict[str, object]],
    ) -> int:
        """canonical URL 기준 upsert. 새로 삽입된 행 수를 반환한다."""
        inserted = 0
        with self._lock:
            for a in articles:
                cur = self._conn.execute(
                    """INSERT OR IGNORE INTO articles
                       (url, title, body_text, category, is_foreign,
                        published_at, collected_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        a["url"], a["title"], a["body_text"], a["category"],
                        1 if a["is_foreign"] else 0, a.get("published_at", ""),
                        self._now(),
                    ),
                )
                inserted += cur.rowcount
            self._conn.commit()
        return inserted

    def save_processed(
        self,
        url: str,
        *,
        status: str,
        summary_lines: list[str],
        translated_title: str | None,
        engine: str,
        model_id: str,
    ) -> None:
        with self._lock:
            self._conn.execute(
                """UPDATE articles SET status=?, summary_lines=?,
                   translated_title=?, engine=?, model_id=?, processed_at=?
                   WHERE url=?""",
                (
                    status, json.dumps(summary_lines, ensure_ascii=False),
                    translated_title, engine, model_id, self._now(), url,
                ),
            )
            self._conn.commit()

    def list_articles(
        self, category: str | None = None, *, limit: int = 100
    ) -> list[dict[str, object]]:
        """처리 완료(READY/INSUFFICIENT) 기사를 최신순으로 반환한다."""
        sql = """SELECT url, title, body_text, category, is_foreign,
                        published_at, status, summary_lines, translated_title,
                        engine, model_id, processed_at
                 FROM articles
                 WHERE status IN ('READY','INSUFFICIENT')"""
        params: list[object] = []
        if category:
            sql += " AND category = ?"
            params.append(category)
        sql += " ORDER BY published_at DESC, collected_at DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def existing_urls(self, urls: list[str]) -> set[str]:
        """이미 저장된 URL 집합을 반환한다(처리 여부 무관)."""
        if not urls:
            return set()
        marks = ",".join("?" for _ in urls)
        with self._lock:
            rows = self._conn.execute(
                f"SELECT url FROM articles WHERE url IN ({marks})", urls
            ).fetchall()
        return {r["url"] for r in rows}

    def pending_urls(self, urls: list[str]) -> set[str]:
        """아직 처리되지 않은(PENDING) URL 집합을 반환한다."""
        if not urls:
            return set()
        marks = ",".join("?" for _ in urls)
        with self._lock:
            rows = self._conn.execute(
                f"SELECT url FROM articles WHERE status='PENDING' AND url IN ({marks})",
                urls,
            ).fetchall()
        return {r["url"] for r in rows}

    def category_counts(self) -> dict[str, int]:
        """분류별 처리 완료 기사 수."""
        with self._lock:
            rows = self._conn.execute(
                """SELECT category, COUNT(*) AS n FROM articles
                   WHERE status IN ('READY','INSUFFICIENT')
                   GROUP BY category"""
            ).fetchall()
        return {r["category"]: r["n"] for r in rows}

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, object]:
        return {
            "url": row["url"],
            "title": row["title"],
            "body_text": row["body_text"],
            "category": row["category"],
            "is_foreign": bool(row["is_foreign"]),
            "published_at": row["published_at"],
            "status": row["status"],
            "summary_lines": json.loads(row["summary_lines"]),
            "translated_title": row["translated_title"],
            "engine": row["engine"],
            "model_id": row["model_id"],
        }

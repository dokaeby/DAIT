"""기존 SQLite 결과 조회와 통합 저장을 담당한다. 원본은 읽기 전용이다."""

import json
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from pydantic import ValidationError

from dait.repositories.db import DbConnection
from dait.schemas.legacy_news import LegacyNews


def read_results(path: Path) -> Iterator[LegacyNews]:
    """개인 DB나 토큰은 읽지 않고 성공한 기사만 모델로 검증한다."""
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT n.id,n.canonical_url,n.source_name,n.title,n.category,n.published_at,"
            "c.translated_text,c.line_1,c.line_2,c.line_3 FROM news n "
            "JOIN content_results c ON n.id=c.news_id WHERE c.status='SUCCESS'"
        )
        for row in rows:
            values = dict(row)
            values["summary_lines"] = [values.pop(f"line_{i}") for i in range(1, 4)]
            try:
                yield LegacyNews.model_validate(values)
            except ValidationError:
                continue  # 공개 계약을 어기는 결과는 가져오지 않는다.
    finally:
        conn.close()


def insert_result(conn: DbConnection, item: LegacyNews) -> None:
    """URL 기준 멱등 삽입으로 기존 계정과 이미 저장된 기사를 보존한다."""
    now = datetime.now(UTC).isoformat()
    base_url = f"https://{item.canonical_url.host}/"
    source_id = str(uuid5(NAMESPACE_URL, base_url))
    conn.execute(
        "INSERT INTO sources (id,name,kind,base_url,priority,enabled,created_at,updated_at) "
        "VALUES (?,?,'RSS',?,100,TRUE,?,?) ON CONFLICT DO NOTHING",
        (source_id, item.source_name, base_url, now, now),
    )
    source = conn.execute("SELECT id FROM sources WHERE base_url=?", (base_url,)).fetchone()
    if source is None:
        return
    conn.execute(
        "INSERT INTO news (id,source_id,title,canonical_url,published_at,collected_at,"
        "category,original_language,created_at) VALUES (?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT DO NOTHING",
        (
            item.id,
            source[0],
            item.title,
            str(item.canonical_url),
            item.published_at.isoformat(),
            now,
            "POLITICS" if item.category == "SOCIETY" else item.category,
            "en" if item.source_name in {"TechCrunch", "The Verge", "MIT Tech Review"} else "und",
            now,
        ),
    )
    article = conn.execute(
        "SELECT id FROM news WHERE canonical_url=?", (str(item.canonical_url),)
    ).fetchone()
    if article is None:
        return
    conn.execute(
        "INSERT INTO content_results (news_id,translated_text,summary_lines,status,updated_at) "
        "VALUES (?,?,?,'READY',?) ON CONFLICT DO NOTHING",
        (article[0], item.translated_text, json.dumps(item.summary_lines, ensure_ascii=False), now),
    )

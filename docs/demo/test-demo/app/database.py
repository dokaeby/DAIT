"""SQLite schema and seed data for the standalone DAIT demo."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

DEMO_USER_ID = "usr_demo_local"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT,
    status TEXT NOT NULL CHECK (status IN ('ACTIVE','LOCKED','DELETION_PENDING','DELETED')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS auth_identities (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    provider_subject TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (provider, provider_subject)
);

CREATE TABLE IF NOT EXISTS refresh_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    family_id TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_refresh_sessions_family ON refresh_sessions(family_id);

CREATE TABLE IF NOT EXISTS user_settings (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    default_count INTEGER NOT NULL CHECK (default_count IN (5, 10)),
    categories TEXT NOT NULL CHECK (json_valid(categories)),
    keywords TEXT NOT NULL CHECK (json_valid(keywords)),
    source_ids TEXT NOT NULL CHECK (json_valid(source_ids)),
    in_app_notice INTEGER NOT NULL CHECK (in_app_notice IN (0, 1)),
    email_notice INTEGER NOT NULL CHECK (email_notice IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schedules (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    local_time TEXT NOT NULL,
    timezone TEXT NOT NULL,
    enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
    criteria_json TEXT NOT NULL CHECK (json_valid(criteria_json)),
    next_run_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_schedules_user ON schedules(user_id);
CREATE INDEX IF NOT EXISTS idx_schedules_next_run ON schedules(next_run_at);

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('RSS','API','OFFICIAL_HTML')),
    base_url TEXT NOT NULL UNIQUE,
    priority INTEGER NOT NULL,
    enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
    robots_checked_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sources_priority ON sources(priority);
CREATE INDEX IF NOT EXISTS idx_sources_enabled ON sources(enabled);

CREATE TABLE IF NOT EXISTS news (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(id),
    title TEXT NOT NULL,
    canonical_url TEXT NOT NULL UNIQUE,
    published_at TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    category TEXT NOT NULL,
    original_language TEXT NOT NULL,
    content_hash TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_news_title ON news(title);
CREATE INDEX IF NOT EXISTS idx_news_published ON news(published_at);
CREATE INDEX IF NOT EXISTS idx_news_category ON news(category);
CREATE INDEX IF NOT EXISTS idx_news_content_hash ON news(content_hash);

CREATE TABLE IF NOT EXISTS content_results (
    news_id TEXT PRIMARY KEY REFERENCES news(id) ON DELETE CASCADE,
    extracted_text TEXT,
    translated_text TEXT,
    summary_lines TEXT CHECK (summary_lines IS NULL OR json_valid(summary_lines)),
    status TEXT NOT NULL CHECK (status IN ('PENDING','READY','FAILED','INSUFFICIENT')),
    error_code TEXT,
    prompt_version TEXT,
    model_id TEXT,
    processed_at TEXT,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_content_results_status ON content_results(status);

CREATE TABLE IF NOT EXISTS news_relations (
    id TEXT PRIMARY KEY,
    news_id TEXT NOT NULL REFERENCES news(id) ON DELETE CASCADE,
    related_news_id TEXT NOT NULL REFERENCES news(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    score REAL NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (news_id, related_news_id),
    CHECK (news_id <> related_news_id)
);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    schedule_id TEXT REFERENCES schedules(id) ON DELETE SET NULL,
    kind TEXT NOT NULL,
    dedupe_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED','DEAD_LETTER')),
    scheduled_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_scheduled ON jobs(scheduled_at);

CREATE TABLE IF NOT EXISTS job_attempts (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    step TEXT NOT NULL,
    attempt_no INTEGER NOT NULL CHECK (attempt_no > 0),
    error_code TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (job_id, step, attempt_no)
);

CREATE TABLE IF NOT EXISTS notification_deliveries (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    schedule_id TEXT REFERENCES schedules(id) ON DELETE SET NULL,
    news_id TEXT REFERENCES news(id) ON DELETE SET NULL,
    channel TEXT NOT NULL CHECK (channel IN ('IN_APP','EMAIL')),
    dedupe_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (status IN ('PENDING','SENT','FAILED','SKIPPED')),
    sent_at TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_deliveries_status ON notification_deliveries(status);

CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    actor_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    event TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT,
    request_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_logs(event);
CREATE INDEX IF NOT EXISTS idx_audit_request ON audit_logs(request_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);
"""

NOW = "2026-11-06T00:00:00Z"


def connect(db_path: Path) -> sqlite3.Connection:
    """Open a row-mapped SQLite connection with referential integrity enabled."""
    connection = sqlite3.connect(db_path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(db_path: Path) -> None:
    """Create the full local schema and seed deterministic demo records."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as connection:
        connection.executescript(SCHEMA)
        connection.execute(
            "INSERT OR IGNORE INTO users VALUES (?, ?, NULL, 'ACTIVE', ?, ?, NULL)",
            (DEMO_USER_ID, "demo@dait.local", NOW, NOW),
        )
        connection.execute(
            "INSERT OR IGNORE INTO user_settings VALUES (?, 10, ?, ?, ?, 1, 0, ?, ?)",
            (
                DEMO_USER_ID,
                json.dumps(["AI"], ensure_ascii=False),
                json.dumps(["멀티모달", "AI 에이전트", "오픈소스 LLM"], ensure_ascii=False),
                json.dumps(["src_openai", "src_anthropic"], ensure_ascii=False),
                NOW,
                NOW,
            ),
        )
        connection.executemany(
            "INSERT OR IGNORE INTO sources VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)",
            [
                ("src_openai", "OpenAI Newsroom", "OFFICIAL_HTML", "https://openai.com/news", 1, NOW, NOW, NOW),
                ("src_anthropic", "Anthropic News", "OFFICIAL_HTML", "https://www.anthropic.com/news", 2, NOW, NOW, NOW),
                ("src_arxiv", "arXiv AI", "RSS", "https://arxiv.org", 3, NOW, NOW, NOW),
            ],
        )
        connection.executemany(
            "INSERT OR IGNORE INTO news VALUES (?, ?, ?, ?, ?, ?, 'AI', ?, ?, ?)",
            [
                (
                    "news_openai_001",
                    "src_openai",
                    "OpenAI, 차세대 멀티모달 모델 공개",
                    "https://openai.com/news/example-multimodal-model",
                    "2026-11-04T00:30:00Z",
                    "2026-11-04T00:32:00Z",
                    "en",
                    "hash-openai-001",
                    NOW,
                ),
                (
                    "news_anthropic_002",
                    "src_anthropic",
                    "Anthropic, 안전한 AI 에이전트 도구 공개",
                    "https://www.anthropic.com/news/example-agent-tools",
                    "2026-11-03T23:00:00Z",
                    "2026-11-03T23:03:00Z",
                    "en",
                    "hash-anthropic-002",
                    NOW,
                ),
                (
                    "news_arxiv_003",
                    "src_arxiv",
                    "오픈소스 LLM 평가 벤치마크 연구",
                    "https://arxiv.org/abs/2611.00003",
                    "2026-11-02T08:00:00Z",
                    "2026-11-02T08:04:00Z",
                    "en",
                    "hash-arxiv-003",
                    NOW,
                ),
            ],
        )
        connection.executemany(
            "INSERT OR IGNORE INTO content_results VALUES (?, ?, ?, ?, ?, ?, 'summary-v1', 'demo-model', ?, ?)",
            [
                (
                    "news_openai_001",
                    "OpenAI announced a multimodal model.",
                    "OpenAI는 텍스트, 이미지, 음성을 함께 처리하는 새로운 모델을 발표했습니다.",
                    json.dumps([
                        "장문 추론과 복합 도구 호출 정확도가 향상됐다.",
                        "텍스트·이미지·음성을 하나의 흐름에서 처리한다.",
                        "개발자 API는 단계적으로 제공될 예정이다.",
                    ], ensure_ascii=False),
                    "READY",
                    None,
                    "2026-11-04T00:35:14Z",
                    "2026-11-04T00:35:14Z",
                ),
                (
                    "news_anthropic_002",
                    "Anthropic released safer agent tools.",
                    "Anthropic은 안전 장치를 포함한 AI 에이전트 도구를 공개했습니다.",
                    json.dumps([
                        "에이전트 도구에 권한 제한 기능이 추가됐다.",
                        "실행 기록과 승인 단계를 관리할 수 있다.",
                        "기업용 기능은 순차적으로 배포된다.",
                    ], ensure_ascii=False),
                    "READY",
                    None,
                    "2026-11-03T23:10:00Z",
                    "2026-11-03T23:10:00Z",
                ),
                (
                    "news_arxiv_003",
                    None,
                    None,
                    json.dumps([
                        "공개된 초록만으로 평가 결과를 정리했다.",
                        "전체 본문 확인이 필요하다.",
                        "요약 정보가 제한적일 수 있다.",
                    ], ensure_ascii=False),
                    "INSUFFICIENT",
                    "CONTENT_INSUFFICIENT",
                    "2026-11-02T08:10:00Z",
                    "2026-11-02T08:10:00Z",
                ),
            ],
        )
        connection.executemany(
            "INSERT OR IGNORE INTO news_relations VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("rel_001", "news_openai_001", "news_anthropic_002", "AI 에이전트와 도구 사용", 0.82, NOW),
                ("rel_002", "news_openai_001", "news_arxiv_003", "모델 평가 주제", 0.71, NOW),
            ],
        )
        connection.execute(
            "INSERT OR IGNORE INTO schedules VALUES (?, ?, '08:30', 'Asia/Seoul', 1, ?, ?, ?, ?)",
            (
                "sch_demo_0830",
                DEMO_USER_ID,
                json.dumps(
                    {
                        "keywords": ["멀티모달", "AI 에이전트"],
                        "source_ids": ["src_openai", "src_anthropic"],
                        "categories": ["AI"],
                    },
                    ensure_ascii=False,
                ),
                "2026-11-06T23:30:00Z",
                NOW,
                NOW,
            ),
        )


def list_news(
    db_path: Path, *, query: str | None, sort: str, page_size: int
) -> list[dict[str, object]]:
    """Return visible news rows with decoded summaries."""
    filters = ["n.category = 'AI'", "c.status IN ('READY', 'INSUFFICIENT')"]
    parameters: list[object] = []
    if query:
        filters.append("(LOWER(n.title) LIKE LOWER(?) OR LOWER(c.summary_lines) LIKE LOWER(?))")
        pattern = f"%{query}%"
        parameters.extend((pattern, pattern))
    order = (
        "c.status = 'READY' DESC, s.priority ASC, n.published_at DESC, n.id ASC"
        if sort == "rank"
        else "n.published_at DESC, n.id ASC"
    )
    parameters.append(page_size)
    sql = f"""
        SELECT n.id, n.title, n.published_at, n.category, n.canonical_url,
               s.name AS source_name, s.priority AS source_priority,
               c.summary_lines, c.status AS processing_status
          FROM news AS n
          JOIN sources AS s ON s.id = n.source_id
          JOIN content_results AS c ON c.news_id = n.id
         WHERE {' AND '.join(filters)}
         ORDER BY {order}
         LIMIT ?
    """
    with connect(db_path) as connection:
        rows = connection.execute(sql, parameters).fetchall()
    return [
        {
            **dict(row),
            "summary_lines": json.loads(row["summary_lines"]),
        }
        for row in rows
    ]


def get_news_detail(db_path: Path, news_id: str) -> dict[str, object] | None:
    """Return one article with processing details and related news."""
    with connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT n.*, s.name AS source_name, s.kind AS source_type,
                   c.summary_lines, c.translated_text, c.status AS content_status,
                   c.processed_at, c.prompt_version, c.model_id
              FROM news AS n
              JOIN sources AS s ON s.id = n.source_id
              JOIN content_results AS c ON c.news_id = n.id
             WHERE n.id = ? AND c.status IN ('READY', 'INSUFFICIENT')
            """,
            (news_id,),
        ).fetchone()
        if row is None:
            return None
        related = connection.execute(
            """
            SELECT n.id, n.title, s.name AS source_name, n.published_at,
                   r.reason, r.score
              FROM news_relations AS r
              JOIN news AS n ON n.id = r.related_news_id
              JOIN sources AS s ON s.id = n.source_id
             WHERE r.news_id = ?
             ORDER BY r.score DESC, n.id ASC
            """,
            (news_id,),
        ).fetchall()
    article = dict(row)
    article["summary_lines"] = json.loads(row["summary_lines"])
    article["related_news"] = [dict(item) for item in related]
    return article

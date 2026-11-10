"""news·sources·content_results·news_relations 조회. 공개 목록·상세·관련 뉴스를 담당한다."""

import json
import sqlite3
from datetime import datetime
from typing import NamedTuple, cast

from dait.schemas.news import PUBLIC_STATUSES

_STATUS_VALUES = tuple(status.value for status in PUBLIC_STATUSES)


class NewsListRow(NamedTuple):
    """목록 조회 한 행: 카드 표시와 정렬에 필요한 값만 담는다."""

    id: str
    title: str
    source_name: str
    published_at: datetime
    category: str
    summary_lines: str | None
    status: str
    canonical_url: str
    source_priority: int


class NewsDetailRow(NamedTuple):
    """상세 조회 한 행: 기사·콘텐츠·출처 정보를 함께 담는다."""

    id: str
    title: str
    source_name: str
    source_kind: str
    published_at: datetime
    original_language: str
    category: str
    canonical_url: str
    extracted_text: str | None
    translated_text: str | None
    summary_lines: str | None
    status: str
    error_code: str | None
    prompt_version: str | None
    model_id: str | None
    processed_at: datetime | None


class RelatedRow(NamedTuple):
    """관련 뉴스 한 행."""

    id: str
    title: str
    source_name: str
    published_at: datetime
    reason: str
    score: float


def _escape_like(text: str) -> str:
    """LIKE 패턴의 와일드카드 문자를 이스케이프한다.

    입력: text (사용자 검색어)
    출력: str ('\\', '%', '_'가 이스케이프된 문자열)
    기능: 검색어가 패턴으로 해석되지 않게 ESCAPE '\\' 절과 함께 쓴다.
    """
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _public_status_clause(alias: str = "c") -> str:
    """공개 가능 상태 조건절을 만든다.

    입력: alias (content_results를 가리키는 테이블 별칭)
    출력: str (별칭.status IN (...))
    기능: 상태 값은 Enum 상수에서만 오므로 문자열 연결이 안전하다.
    """
    quoted = ", ".join(f"'{value}'" for value in _STATUS_VALUES)
    return f"{alias}.status IN ({quoted})"


def list_public_news(
    conn: sqlite3.Connection,
    category: str,
    query: str,
    sort: str,
    limit: int,
    offset: int,
) -> list[NewsListRow]:
    """공개 가능한 뉴스 목록을 규칙 순서로 조회한다.

    입력: conn (연결), category (카테고리), query (정규화된 검색어, 빈 문자열이면 전체),
          sort ("rank" 또는 "latest"), limit·offset (페이지)
    출력: NewsListRow 목록
    기능: rank는 품질(READY 우선)→발행 시각→출처 우선순위→ID 순,
          latest는 발행 시각→ID 순. FAILED·PENDING은 제외한다.
    """
    clauses = ["n.category = ?", _public_status_clause(), "n.canonical_url LIKE 'https://%'"]
    params: list[str | int] = [category]
    if query:
        pattern = f"%{_escape_like(query.lower())}%"
        like = "(lower(n.title) LIKE ? ESCAPE '\\' OR lower(c.summary_lines) LIKE ? ESCAPE '\\')"
        clauses.append(like)
        params.extend([pattern, pattern])
    if sort == "latest":
        order = "n.published_at DESC, n.id ASC"
    else:
        order = (
            "CASE c.status WHEN 'READY' THEN 0 ELSE 1 END, "
            "n.published_at DESC, s.priority ASC, n.id ASC"
        )
    sql = (
        "SELECT n.id, n.title, s.name, n.published_at, n.category, "  # noqa: S608 - 상수 절만 결합
        "c.summary_lines, c.status, n.canonical_url, s.priority "
        "FROM news n "
        "JOIN sources s ON s.id = n.source_id "
        "JOIN content_results c ON c.news_id = n.id "
        f"WHERE {' AND '.join(clauses)} "
        f"ORDER BY {order} LIMIT ? OFFSET ?"
    )
    params.extend([limit, offset])
    rows = conn.execute(sql, params).fetchall()
    return [
        NewsListRow(
            id=row[0],
            title=row[1],
            source_name=row[2],
            published_at=datetime.fromisoformat(row[3]),
            category=row[4],
            summary_lines=row[5],
            status=row[6],
            canonical_url=row[7],
            source_priority=row[8],
        )
        for row in rows
    ]


def count_public_news(conn: sqlite3.Connection, category: str, query: str) -> int:
    """현재 조건에서 화면에 표시 가능한 전체 건수를 센다.

    입력: conn (연결), category, query (정규화된 검색어)
    출력: int (total_visible)
    기능: 목록과 같은 필터를 쓰되 정렬·페이지는 적용하지 않는다.
    """
    clauses = ["n.category = ?", _public_status_clause(), "n.canonical_url LIKE 'https://%'"]
    params: list[str | int] = [category]
    if query:
        pattern = f"%{_escape_like(query.lower())}%"
        like = "(lower(n.title) LIKE ? ESCAPE '\\' OR lower(c.summary_lines) LIKE ? ESCAPE '\\')"
        clauses.append(like)
        params.extend([pattern, pattern])
    sql = (
        "SELECT COUNT(*) FROM news n "  # noqa: S608 - 상수 절만 결합
        "JOIN sources s ON s.id = n.source_id "
        "JOIN content_results c ON c.news_id = n.id "
        f"WHERE {' AND '.join(clauses)}"
    )
    row = conn.execute(sql, params).fetchone()
    return int(row[0]) if row else 0


def has_recent_job_failures(conn: sqlite3.Connection, since_iso: str) -> bool:
    """최근 작업 실패가 있는지 확인한다(목록의 partial 표시용).

    입력: conn (연결), since_iso (기준 시각 ISO 문자열)
    출력: bool
    기능: FAILED·DEAD_LETTER 작업이 있으면 True. 정상 기사는 지우지 않고 안내만 한다.
    """
    row = conn.execute(
        "SELECT 1 FROM jobs WHERE status IN ('FAILED', 'DEAD_LETTER') "
        "AND finished_at IS NOT NULL AND finished_at > ? LIMIT 1",
        (since_iso,),
    ).fetchone()
    return row is not None


def get_public_news(conn: sqlite3.Connection, news_id: str) -> NewsDetailRow | None:
    """공개 가능한 뉴스 한 건의 상세 행을 조회한다.

    입력: conn (연결), news_id (불투명 뉴스 ID)
    출력: NewsDetailRow 또는 None (없거나 비공개 상태)
    기능: 존재 여부와 공개 가능 여부를 한 번에 판단해 정보 누출을 막는다.
    """
    row = conn.execute(
        "SELECT n.id, n.title, s.name, s.kind, n.published_at, n.original_language, "  # noqa: S608 - 상수 절만 결합
        "n.category, n.canonical_url, c.extracted_text, c.translated_text, "
        "c.summary_lines, c.status, c.error_code, c.prompt_version, c.model_id, "
        "c.processed_at "
        "FROM news n "
        "JOIN sources s ON s.id = n.source_id "
        "JOIN content_results c ON c.news_id = n.id "
        f"WHERE n.id = ? AND {_public_status_clause()} AND n.category = 'AI' "
        "AND n.canonical_url LIKE 'https://%'",
        (news_id,),
    ).fetchone()
    if row is None:
        return None
    return NewsDetailRow(
        id=row[0],
        title=row[1],
        source_name=row[2],
        source_kind=row[3],
        published_at=datetime.fromisoformat(row[4]),
        original_language=row[5],
        category=row[6],
        canonical_url=row[7],
        extracted_text=row[8],
        translated_text=row[9],
        summary_lines=row[10],
        status=row[11],
        error_code=row[12],
        prompt_version=row[13],
        model_id=row[14],
        processed_at=datetime.fromisoformat(row[15]) if row[15] else None,
    )


def list_related_news(conn: sqlite3.Connection, news_id: str, limit: int) -> list[RelatedRow]:
    """상세 화면의 관련 뉴스를 점수 순으로 조회한다.

    입력: conn (연결), news_id (기준 뉴스), limit (최대 건수)
    출력: RelatedRow 목록
    기능: 자기 자신·비공개(FAILED/PENDING) 기사는 제외한다.
    """
    rows = conn.execute(
        "SELECT r.related_news_id, rn.title, rs.name, rn.published_at, r.reason, r.score "  # noqa: S608 - 상수 절만 결합
        "FROM news_relations r "
        "JOIN news rn ON rn.id = r.related_news_id "
        "JOIN sources rs ON rs.id = rn.source_id "
        "JOIN content_results rc ON rc.news_id = rn.id "
        f"WHERE r.news_id = ? AND rn.id != ? AND {_public_status_clause('rc')} "
        "ORDER BY r.score DESC, rn.published_at DESC LIMIT ?",
        (news_id, news_id, limit),
    ).fetchall()
    return [
        RelatedRow(
            id=row[0],
            title=row[1],
            source_name=row[2],
            published_at=datetime.fromisoformat(row[3]),
            reason=row[4],
            score=float(row[5]),
        )
        for row in rows
    ]


def find_id_by_canonical_url(conn: sqlite3.Connection, canonical_url: str) -> str | None:
    """canonical URL로 기존 기사를 찾는다(dedupe 1단계).

    입력: conn (연결), canonical_url (정규화된 URL)
    출력: 기사 id 또는 None
    기능: 같은 URL의 기사는 한 번만 저장한다.
    """
    row = conn.execute("SELECT id FROM news WHERE canonical_url = ?", (canonical_url,)).fetchone()
    return str(row[0]) if row else None


def find_id_by_content_hash(conn: sqlite3.Connection, content_hash: str) -> str | None:
    """내용 해시로 기존 기사를 찾는다(dedupe 2단계).

    입력: conn (연결), content_hash (본문 정규화 해시)
    출력: 기사 id 또는 None
    기능: URL이 달라도 내용이 같으면 중복 수집하지 않는다.
    """
    row = conn.execute("SELECT id FROM news WHERE content_hash = ?", (content_hash,)).fetchone()
    return str(row[0]) if row else None


def insert_news(
    conn: sqlite3.Connection,
    news_id: str,
    source_id: str,
    title: str,
    canonical_url: str,
    published_at: datetime,
    collected_at: datetime,
    category: str,
    original_language: str,
    content_hash: str | None,
) -> None:
    """수집한 기사를 저장한다.

    입력: conn (트랜잭션 연결), 기사 필드들
    출력: 없음
    기능: canonical_url unique 제약이 최종 중복 방어선이다.
    """
    conn.execute(
        "INSERT INTO news (id, source_id, title, canonical_url, published_at, "
        "collected_at, category, original_language, content_hash, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            news_id,
            source_id,
            title,
            canonical_url,
            published_at.isoformat(),
            collected_at.isoformat(),
            category,
            original_language,
            content_hash,
            collected_at.isoformat(),
        ),
    )


def insert_pending_content(conn: sqlite3.Connection, news_id: str, updated_at: datetime) -> None:
    """수집 직후 content_results를 PENDING으로 만든다.

    입력: conn, news_id, updated_at
    출력: 없음
    기능: AI 처리(번역·요약)가 끝나기 전까지 공개 목록에 나오지 않는다.
    """
    conn.execute(
        "INSERT INTO content_results (news_id, status, updated_at) VALUES (?, 'PENDING', ?)",
        (news_id, updated_at.isoformat()),
    )


def list_enabled_source_ids(conn: sqlite3.Connection) -> list[str]:
    """설정에서 선택할 수 있는 활성 승인 출처 ID를 읽는다.

    입력: conn (연결)
    출력: str 목록
    기능: 비활성·미승인 출처는 사용자 설정에 저장할 수 없다.
    """
    rows = conn.execute("SELECT id FROM sources WHERE enabled = 1 ORDER BY priority, id").fetchall()
    return [row[0] for row in rows]


def parse_summary_lines(raw: str | None) -> list[str]:
    """저장된 요약 JSON 텍스트를 문자열 목록으로 되돌린다.

    입력: raw (content_results.summary_lines)
    출력: str 목록 (파싱 실패·비목록이면 빈 목록)
    기능: DB 경계 값을 응답 모델이 요구하는 형태로만 변환한다.
    """
    if not raw:
        return []
    try:
        value: object = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(value, list):
        return []
    items = cast("list[object]", value)
    return [item[:500] for item in items if isinstance(item, str)][:3]

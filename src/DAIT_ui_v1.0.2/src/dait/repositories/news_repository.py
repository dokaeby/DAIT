"""기사·저장 요약 조회 SQL. 경로를 인자로 받아 기존 DB와 테스트 격리를 보존합니다."""
import sqlite3
from contextlib import closing

# 기능: 카테고리를 결합한 기사 행을 최신순으로 조회한다.
# 입력:
#   db_path: 조회할 SQLite DB 경로.
#   limit: 최대 조회 수(-1이면 제한 없음).
# 출력: (ID, 제목, 출처, 시각, 카테고리, 해외 여부, 설명) 튜플 목록.
def latest_rows(db_path, limit):
    # 읽기 전용 연결: DB가 없을 때 빈 DB를 만들지 않습니다.
    with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)) as db:
        articles = db.execute("""
            SELECT a.id, a.title, a.source, a.published_at,
                   GROUP_CONCAT(c.category, ' · ') AS categories, a.is_foreign, a.summary
            FROM articles a LEFT JOIN article_categories c ON c.article_id = a.id
            GROUP BY a.id
            ORDER BY a.published_at DESC, a.id ASC LIMIT ?
        """, (limit,)).fetchall()
    return articles

# 기능: 관심 카테고리가 하나 이상 일치하는 기사를 최신순으로 조회한다.
# 입력:
#   db_path: 조회할 SQLite DB 경로.
#   interests: 사용자 관심 카테고리(없으면 기본 관심사 사용).
#   limit: 최대 조회 수(-1이면 제한 없음).
# 출력: (ID, 제목, 출처, 시각, 카테고리, 해외 여부, 설명) 튜플 목록.
def recommended_rows(db_path, interests, limit):
    placeholders = ", ".join("?" for _ in interests)
    with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)) as db:
        articles = db.execute(f"""
            SELECT a.id, a.title, a.source, a.published_at,
                   GROUP_CONCAT(c.category, ' · ') AS categories, a.is_foreign, a.summary
            FROM articles a LEFT JOIN article_categories c ON c.article_id = a.id
            WHERE EXISTS (SELECT 1 FROM article_categories matched
                          WHERE matched.article_id = a.id AND matched.category IN ({placeholders}))
            GROUP BY a.id
            ORDER BY a.published_at DESC, a.id ASC LIMIT ?
        """, (*interests, limit)).fetchall()
    return articles

# 기능: 기사와 연결된 카테고리를 상세 조회한다.
# 입력:
#   db_path: 조회할 SQLite DB 경로.
#   article_id: 기사 식별자.
# 출력: (제목, 출처, 시각, 설명, 본문, URL, 해외 여부, 카테고리) 또는 None.
def get_article(db_path, article_id):
    with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)) as db:
        return db.execute("""
            SELECT a.title, a.source, a.published_at, a.summary, a.content,
                   a.original_url, a.is_foreign, GROUP_CONCAT(c.category, ' · ')
            FROM articles a LEFT JOIN article_categories c ON c.article_id = a.id
            WHERE a.id = ? GROUP BY a.id
        """, (article_id,)).fetchone()

# 기능: 등록된 기사 카테고리를 중복 없이 조회한다.
# 입력:
#   db_path: 조회할 SQLite DB 경로.
# 출력: 이름순 카테고리 문자열 목록.
def categories(db_path):
    with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)) as db:
        return [row[0] for row in db.execute("SELECT DISTINCT category FROM article_categories ORDER BY category")]


# 기능: 기사별 원문 URL을 조회한다.
# 입력:
#   db_path: 조회할 SQLite DB 경로.
# 출력: 기사 ID를 키로 하는 URL 사전.
def original_urls(db_path):
    with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)) as db:
        return dict(db.execute("SELECT id,original_url FROM articles"))


# 기능: 기사의 가장 최근 국내 요약 기록을 읽는다.
# 입력:
#   db_path: 조회할 SQLite DB 경로.
#   article_id: 기사 식별자.
# 출력: (상태, 문장 JSON, 입력 해시, 모델, 검토 여부) 또는 None.
def summary_record(db_path, article_id):
    with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)) as db:
        return db.execute("""
                SELECT status, lines_json, input_hash, model, reviewed
                FROM summary_tests WHERE article_id = ?
                ORDER BY rowid DESC LIMIT 1
            """, (article_id,)).fetchone()

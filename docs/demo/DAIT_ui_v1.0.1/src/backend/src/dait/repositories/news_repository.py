"""기사·저장 요약 조회 SQL. 경로를 인자로 받아 기존 DB와 테스트 격리를 보존합니다."""
import sqlite3
from contextlib import closing

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

def get_article(db_path, article_id):
    with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)) as db:
        return db.execute("""
            SELECT a.title, a.source, a.published_at, a.summary, a.content,
                   a.original_url, a.is_foreign, GROUP_CONCAT(c.category, ' · ')
            FROM articles a LEFT JOIN article_categories c ON c.article_id = a.id
            WHERE a.id = ? GROUP BY a.id
        """, (article_id,)).fetchone()

def categories(db_path):
    with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)) as db:
        return [row[0] for row in db.execute("SELECT DISTINCT category FROM article_categories ORDER BY category")]


def original_urls(db_path):
    with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)) as db:
        return dict(db.execute("SELECT id,original_url FROM articles"))


def summary_record(db_path, article_id):
    with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)) as db:
        return db.execute("""
                SELECT status, lines_json, input_hash, model, reviewed
                FROM summary_tests WHERE article_id = ?
                ORDER BY rowid DESC LIMIT 1
            """, (article_id,)).fetchone()

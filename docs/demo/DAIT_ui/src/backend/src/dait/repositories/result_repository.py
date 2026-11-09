"""해외 처리 결과 저장 형식·읽기 전용 조회."""
import json
import sqlite3
from contextlib import closing

def create_table(db):
    db.execute("""CREATE TABLE IF NOT EXISTS foreign_translations (
        run_id TEXT NOT NULL, article_id TEXT NOT NULL, model TEXT NOT NULL,
        original_title TEXT NOT NULL, original_description TEXT NOT NULL,
        source TEXT NOT NULL, original_url TEXT NOT NULL,
        input_hash TEXT NOT NULL, status TEXT NOT NULL, title_ko TEXT NOT NULL,
        lines_json TEXT NOT NULL, error TEXT NOT NULL, elapsed_seconds REAL NOT NULL,
        reviewed INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (run_id, article_id))""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_foreign_article ON foreign_translations(article_id)")

def latest_translation(db_path, article_id):
    if not db_path.is_file():
        return None
    with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        row = db.execute("SELECT * FROM foreign_translations WHERE article_id=? ORDER BY rowid DESC LIMIT 1", (article_id,)).fetchone()
        return dict(row) if row else None


def create_results_table(db):
    db.execute("""CREATE TABLE IF NOT EXISTS summary_tests (
        run_id TEXT NOT NULL, article_id TEXT NOT NULL, model TEXT NOT NULL,
        title TEXT NOT NULL, source TEXT NOT NULL, original_url TEXT NOT NULL,
        input_text TEXT NOT NULL, input_hash TEXT NOT NULL,
        status TEXT NOT NULL, lines_json TEXT NOT NULL, error TEXT NOT NULL,
        elapsed_seconds REAL NOT NULL, reviewed INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (run_id, article_id))""")


def save_result(summary_db, translation_db, article, kind, model, run_id, text, digest, status, lines, title_ko, error, elapsed):
    if kind == "foreign":
        with closing(sqlite3.connect(translation_db, timeout=10)) as db, db:
            create_table(db)
            db.execute("""INSERT INTO foreign_translations
                (run_id,article_id,model,original_title,original_description,source,original_url,input_hash,status,title_ko,lines_json,error,elapsed_seconds)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (run_id, article["id"], model, article["title"], article["summary"], article["source"],
                 article["original_url"] or "", digest, status, title_ko, json.dumps(lines, ensure_ascii=False), error, elapsed))
    else:
        with closing(sqlite3.connect(summary_db, timeout=10)) as db, db:
            create_results_table(db)
            db.execute("""INSERT INTO summary_tests
                (run_id,article_id,model,title,source,original_url,input_text,input_hash,status,lines_json,error,elapsed_seconds)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (run_id, article["id"], model, article["title"], article["source"], article["original_url"] or "",
                 text, digest, status, json.dumps(lines, ensure_ascii=False), error, elapsed))

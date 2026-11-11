"""해외 처리 결과 저장 형식·읽기 전용 조회."""
import json
import sqlite3
from contextlib import closing

# 기능: 해외 기사 번역 결과 테이블과 조회 인덱스를 준비한다.
# 입력:
#   db: 열린 SQLite 연결.
# 출력: None. 전달받은 연결에서 스키마를 생성한다.
def create_table(db):
    db.execute("""CREATE TABLE IF NOT EXISTS foreign_translations (
        run_id TEXT NOT NULL, article_id TEXT NOT NULL, model TEXT NOT NULL,
        original_title TEXT NOT NULL, original_description TEXT NOT NULL,
        source TEXT NOT NULL, original_url TEXT NOT NULL,
        input_hash TEXT NOT NULL, status TEXT NOT NULL, title_ko TEXT NOT NULL,
        lines_json TEXT NOT NULL, error TEXT NOT NULL, elapsed_seconds REAL NOT NULL,
        reviewed INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (run_id, article_id))""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_foreign_article ON foreign_translations(article_id)")

# 기능: 기사의 가장 최근 해외 번역 기록을 읽는다.
# 입력:
#   db_path: 조회할 SQLite DB 경로.
#   article_id: 기사 식별자.
# 출력: 번역 기록 사전 또는 None.
def latest_translation(db_path, article_id):
    if not db_path.is_file():
        return None
    with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        row = db.execute("SELECT * FROM foreign_translations WHERE article_id=? ORDER BY rowid DESC LIMIT 1", (article_id,)).fetchone()
        return dict(row) if row else None


# 기능: 국내 기사 요약 결과 테이블을 준비한다.
# 입력:
#   db: 열린 SQLite 연결.
# 출력: None. 전달받은 연결에서 스키마를 생성한다.
def create_results_table(db):
    db.execute("""CREATE TABLE IF NOT EXISTS summary_tests (
        run_id TEXT NOT NULL, article_id TEXT NOT NULL, model TEXT NOT NULL,
        title TEXT NOT NULL, source TEXT NOT NULL, original_url TEXT NOT NULL,
        input_text TEXT NOT NULL, input_hash TEXT NOT NULL,
        status TEXT NOT NULL, lines_json TEXT NOT NULL, error TEXT NOT NULL,
        elapsed_seconds REAL NOT NULL, reviewed INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (run_id, article_id))""")


# 기능: 국내 요약 또는 해외 번역 결과와 오류 이력을 해당 DB에 저장한다.
# 입력:
#   summary_db: 국내 요약 DB 경로.
#   translation_db: 해외 번역 DB 경로.
#   article: 기사 ID·제목·RSS 설명 등의 필드를 담은 사전.
#   kind: 기사 처리 종류(domestic/foreign).
#   model: 사용할 모델 이름.
#   run_id: 생성 실행 식별자.
#   text: 처리할 입력 텍스트.
#   digest: 입력 또는 모델 식별 해시.
#   status: 처리 상태 또는 HTTP 상태 코드.
#   lines: 요약 문장 목록.
#   title_ko: 한국어 번역 제목.
#   error: 저장할 오류 메시지.
#   elapsed: 처리 소요 시간(초).
# 출력: None. 결과 행을 추가하고 커밋한다.
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

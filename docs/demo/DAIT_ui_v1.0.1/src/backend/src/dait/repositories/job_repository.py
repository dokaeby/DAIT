"""요약 대기열 SQL. 상태 표시와 생성 실행은 서비스에서 담당합니다."""
import json
import sqlite3
from contextlib import closing


def connect(queue_db):
    return sqlite3.connect(queue_db, timeout=10)


def initialize(queue_db):
    with closing(connect(queue_db)) as db, db:
        db.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, article_id TEXT NOT NULL, input_hash TEXT NOT NULL,
            model TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued', attempts INTEGER NOT NULL DEFAULT 0,
            next_try REAL NOT NULL DEFAULT 0, error TEXT NOT NULL DEFAULT '',
            updated REAL NOT NULL, UNIQUE(article_id,input_hash,model,kind))""")



def sync_candidates(queue_db, candidates, model, now, new_id):
    active = []
    with closing(connect(queue_db)) as db, db:
        for article, kind, reusable, digest in candidates:
            key = (article["id"], digest, model, kind)
            row = db.execute("SELECT id,status FROM jobs WHERE article_id=? AND input_hash=? AND model=? AND kind=?", key).fetchone()
            job_id = row[0] if row else new_id()
            active.append(job_id)
            if row is None:
                db.execute("INSERT INTO jobs(id,article_id,input_hash,model,kind,payload,status,updated) VALUES(?,?,?,?,?,?,?,?)",
                           (job_id, *key, json.dumps(article, ensure_ascii=False), "done" if reusable else "queued", now()))
            elif reusable and row[1] != "done":
                db.execute("UPDATE jobs SET status='done',error='',updated=? WHERE id=?", (now(), job_id))
            elif not reusable and row[1] == "done":
                db.execute("UPDATE jobs SET status='queued',attempts=0,next_try=0,updated=? WHERE id=?", (now(), job_id))
        # 수집 시 교체된 기사·이전 입력은 더 이상 생성하지 않습니다.
        for job_id, in db.execute("SELECT id FROM jobs WHERE status IN ('queued','retry','done','failed')").fetchall():
            if job_id not in active:
                db.execute("UPDATE jobs SET status='obsolete',updated=? WHERE id=?", (now(), job_id))
        for job_id in active:
            db.execute("UPDATE jobs SET status='queued',updated=? WHERE id=? AND status='obsolete'", (now(), job_id))


def claim(queue_db, now):
    with closing(connect(queue_db)) as db, db:
        row = db.execute("SELECT id,payload,kind,attempts FROM jobs WHERE status IN ('queued','retry') AND next_try<=? ORDER BY updated,id LIMIT 1", (now(),)).fetchone()
        if row is not None:
            db.execute("UPDATE jobs SET status='running',attempts=attempts+1,updated=? WHERE id=?", (now(), row[0]))
        return row


def save_outcome(queue_db, job_id, state, error, next_try, updated):
    with closing(connect(queue_db)) as db, db:
        db.execute("UPDATE jobs SET status=?,error=?,next_try=?,updated=? WHERE id=?",
                   (state, error, next_try, updated, job_id))


def recover_running(queue_db, updated, next_try=None):
    with closing(connect(queue_db)) as db, db:
        if next_try is None:
            db.execute("UPDATE jobs SET status=CASE WHEN attempts>=3 THEN 'failed' ELSE 'retry' END,updated=? WHERE status='running'", (updated,))
        else:
            db.execute("UPDATE jobs SET status=CASE WHEN attempts>=3 THEN 'failed' ELSE 'retry' END,next_try=?,updated=? WHERE status='running'", (next_try, updated))


def statistics(queue_db):
    with closing(connect(queue_db)) as db:
        counts = dict(db.execute("SELECT status,COUNT(*) FROM jobs WHERE status!='obsolete' GROUP BY status"))
        revision = db.execute("SELECT COALESCE(MAX(updated),0) FROM jobs").fetchone()[0]
    return counts, revision


def lookup(queue_db, job_id, now):
    with closing(connect(queue_db)) as db:
        row = db.execute("SELECT status,error,attempts,next_try,updated,id FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            return None, 0
        updated, record_id = row[4:]
        ahead = db.execute("""SELECT COUNT(*) FROM jobs WHERE id!=? AND
            (status='running' OR (status IN ('queued','retry') AND next_try<=? AND
            (updated<? OR (updated=? AND id<?))))""",
            (record_id, now, updated, updated, record_id)).fetchone()[0]
        return row, ahead


def current_job_id(queue_db, article_id, digest, model, kind):
    with closing(sqlite3.connect(queue_db.as_uri() + "?mode=ro", uri=True, timeout=10)) as db:
        row = db.execute("SELECT id FROM jobs WHERE article_id=? AND input_hash=? AND model=? AND kind=? AND status!='obsolete'",
                         (article_id, digest, model, kind)).fetchone()
    return row[0] if row else None


def request_article(queue_db, article_id):
    with closing(connect(queue_db)) as db, db:
        row = db.execute("SELECT id,status FROM jobs WHERE article_id=? AND status!='obsolete' ORDER BY updated DESC LIMIT 1", (article_id,)).fetchone()
        if row is None:
            raise ValueError("요약 대기열을 준비하고 있습니다. 잠시 후 다시 시도해주세요.")
        if row[1] in ("failed", "retry", "queued"):
            db.execute("""UPDATE jobs SET status='queued',
                attempts=CASE WHEN status='failed' THEN 0 ELSE attempts END,
                error='',next_try=0,updated=0 WHERE id=?""", (row[0],))
        return row[0]

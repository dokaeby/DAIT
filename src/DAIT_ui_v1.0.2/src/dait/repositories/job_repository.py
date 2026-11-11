"""요약 대기열 SQL. 상태 표시와 생성 실행은 서비스에서 담당합니다."""
import json
import sqlite3
from contextlib import closing


# 기능: 요약 대기열 SQLite 연결을 연다.
# 입력:
#   queue_db: 대기열 DB 경로.
# 출력: sqlite3.Connection 객체(호출자가 닫아야 함).
def connect(queue_db):
    return sqlite3.connect(queue_db, timeout=10)


# 기능: 요약 대기열 테이블을 준비한다.
# 입력:
#   queue_db: 대기열 DB 경로.
# 출력: None. 테이블이 없으면 생성한다.
def initialize(queue_db):
    with closing(connect(queue_db)) as db, db:
        db.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, article_id TEXT NOT NULL, input_hash TEXT NOT NULL,
            model TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued', attempts INTEGER NOT NULL DEFAULT 0,
            next_try REAL NOT NULL DEFAULT 0, error TEXT NOT NULL DEFAULT '',
            updated REAL NOT NULL, UNIQUE(article_id,input_hash,model,kind))""")



# 기능: 기사 입력·모델별 작업을 동기화하고 이전 입력의 작업을 만료 처리한다.
# 입력:
#   queue_db: 대기열 DB 경로.
#   candidates: 기사·종류·재사용 여부·입력 해시의 후보 목록.
#   model: 사용할 모델 이름.
#   now: 현재 시각(lookup) 또는 현재 Unix 시각을 반환하는 콜백.
#   new_id: 새 작업 ID를 만드는 콜백.
# 출력: None. 대기열 상태를 저장한다.
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


# 기능: 실행 가능한 다음 작업을 선택하고 실행 중으로 표시한다.
# 입력:
#   queue_db: 대기열 DB 경로.
#   now: 현재 시각(lookup) 또는 현재 Unix 시각을 반환하는 콜백.
# 출력: (작업 ID, 기사 JSON, 종류, 이전 시도 횟수) 또는 None.
def claim(queue_db, now):
    with closing(connect(queue_db)) as db, db:
        row = db.execute("SELECT id,payload,kind,attempts FROM jobs WHERE status IN ('queued','retry') AND next_try<=? ORDER BY updated,id LIMIT 1", (now(),)).fetchone()
        if row is not None:
            db.execute("UPDATE jobs SET status='running',attempts=attempts+1,updated=? WHERE id=?", (now(), row[0]))
        return row


# 기능: 작업 결과와 오류·재시도 시각을 저장한다.
# 입력:
#   queue_db: 대기열 DB 경로.
#   job_id: 작업 식별자.
#   state: 저장할 작업 상태.
#   error: 저장할 오류 메시지.
#   next_try: 다음 재시도 시각(Unix 초).
#   updated: 최종 갱신 시각(Unix 초).
# 출력: None. 대기열 행을 갱신한다.
def save_outcome(queue_db, job_id, state, error, next_try, updated):
    with closing(connect(queue_db)) as db, db:
        db.execute("UPDATE jobs SET status=?,error=?,next_try=?,updated=? WHERE id=?",
                   (state, error, next_try, updated, job_id))


# 기능: 중단된 실행 작업을 재시도 또는 최종 실패 상태로 복구한다.
# 입력:
#   queue_db: 대기열 DB 경로.
#   updated: 최종 갱신 시각(Unix 초).
#   next_try: 다음 재시도 시각(Unix 초).
# 출력: None. 대기열 상태를 갱신한다.
def recover_running(queue_db, updated, next_try=None):
    with closing(connect(queue_db)) as db, db:
        if next_try is None:
            db.execute("UPDATE jobs SET status=CASE WHEN attempts>=3 THEN 'failed' ELSE 'retry' END,updated=? WHERE status='running'", (updated,))
        else:
            db.execute("UPDATE jobs SET status=CASE WHEN attempts>=3 THEN 'failed' ELSE 'retry' END,next_try=?,updated=? WHERE status='running'", (next_try, updated))


# 기능: 만료되지 않은 작업의 상태별 개수와 최신 갱신 시각을 조회한다.
# 입력:
#   queue_db: 대기열 DB 경로.
# 출력: (상태별 개수 사전, 최신 갱신 시각) 튜플.
def statistics(queue_db):
    with closing(connect(queue_db)) as db:
        counts = dict(db.execute("SELECT status,COUNT(*) FROM jobs WHERE status!='obsolete' GROUP BY status"))
        revision = db.execute("SELECT COALESCE(MAX(updated),0) FROM jobs").fetchone()[0]
    return counts, revision


# 기능: 작업 상태와 현재 작업보다 먼저 처리될 작업 수를 조회한다.
# 입력:
#   queue_db: 대기열 DB 경로.
#   job_id: 작업 식별자.
#   now: 현재 시각(lookup) 또는 현재 Unix 시각을 반환하는 콜백.
# 출력: (상태 행 또는 None, 앞선 작업 수) 튜플.
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


# 기능: 현재 기사 입력·모델·종류와 일치하는 유효 작업을 찾는다.
# 입력:
#   queue_db: 대기열 DB 경로.
#   article_id: 기사 식별자.
#   digest: 입력 또는 모델 식별 해시.
#   model: 사용할 모델 이름.
#   kind: 기사 처리 종류(domestic/foreign).
# 출력: 작업 ID 문자열 또는 None.
def current_job_id(queue_db, article_id, digest, model, kind):
    with closing(sqlite3.connect(queue_db.as_uri() + "?mode=ro", uri=True, timeout=10)) as db:
        row = db.execute("SELECT id FROM jobs WHERE article_id=? AND input_hash=? AND model=? AND kind=? AND status!='obsolete'",
                         (article_id, digest, model, kind)).fetchone()
    return row[0] if row else None


# 기능: 기사 작업을 우선 처리하도록 조정하고 최종 실패 시 시도 횟수를 초기화한다.
# 입력:
#   queue_db: 대기열 DB 경로.
#   article_id: 기사 식별자.
# 출력: 작업 ID 문자열. 작업이 없으면 ValueError.
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

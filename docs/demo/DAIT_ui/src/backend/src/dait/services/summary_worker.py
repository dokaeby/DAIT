"""서버 수명 동안 저장된 기사를 점검하는 단일 요약 작업자.

대기열은 재시작 후에도 보존하며, 화면 조회는 AI 생성을 호출하지 않습니다.
"""
import json
from functools import wraps
import logging
import sqlite3
import sys
import threading
import time
import uuid
from contextlib import closing
from pathlib import Path


from dait.services import foreign_content as foreign
from dait.pipelines.summarize_domestic import input_for, plan
from dait.pipelines.summary_generation import NEWS_DB, RESULT_DB, create_results_table
from dait.services.summary_provider import MODEL, generate, generate_translation

from dait.core.config import QUEUE_DB
from dait.repositories import job_repository, result_repository
logger = logging.getLogger(__name__)
_stop = threading.Event()
_thread = None
_lifecycle = threading.Lock()
_queue_lock = threading.RLock()


def synchronized(function):
    @wraps(function)
    def call(*args, **kwargs):
        with _queue_lock:
            return function(*args, **kwargs)
    return call


def connect():
    return job_repository.connect(QUEUE_DB)


def initialize():
    return job_repository.initialize(QUEUE_DB)


@synchronized
def reconcile():
    """기사·입력·모델별 한 건만 등록하고 기존 정상 결과를 재사용합니다."""
    if not NEWS_DB.is_file():
        return
    candidates = [(a, "domestic", reusable) for a, _, reusable in plan(MODEL)]
    with closing(sqlite3.connect(NEWS_DB.as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        overseas = [dict(r) for r in db.execute(
            "SELECT id,title,summary,source,original_url FROM articles WHERE is_foreign=1 ORDER BY published_at DESC,id")]
    for article in overseas:
        row = foreign.latest_record(article["id"])
        result = foreign.get_translation(article["id"], article["title"], article["summary"])
        reusable = bool(row and row["model"] == MODEL and result["status"] in ("generated", "insufficient"))
        candidates.append((article, "foreign", reusable))
    records = [(article, kind, reusable, input_for(article)[1]) for article, kind, reusable in candidates]
    job_repository.sync_candidates(QUEUE_DB, records, MODEL, time.time, lambda: uuid.uuid4().hex)


def save_result(article, kind, status, lines, title_ko, error, elapsed):
    run_id = uuid.uuid4().hex
    text, digest = input_for(article)
    return result_repository.save_result(RESULT_DB, foreign.TRANSLATION_DB, article, kind,
                                         MODEL, run_id, text, digest, status, lines, title_ko, error, elapsed)


def process_one():
    with _queue_lock:
        row = job_repository.claim(QUEUE_DB, time.time)
        if row is None:
            return False
        job_id, payload, kind, attempts = row
    article = json.loads(payload)
    started = time.monotonic()
    status, lines, title_ko, error = "error", [], "", ""
    try:
        if kind == "foreign":
            status, title_ko, lines = generate_translation(article, MODEL, 600)
        elif not (article["summary"] or "").strip():
            status = "insufficient"
        else:
            status, lines = generate(article, MODEL, 600)
    except Exception as exc:
        error = str(exc)
        logger.warning("요약 생성 실패 article=%s: %s", article["id"], exc)
    with _queue_lock:
        # 실패도 별도 이력으로 보존합니다. 저장이 실패하면 성공 처리하지 않습니다.
        try:
            save_result(article, kind, status, lines, title_ko, error, round(time.monotonic() - started, 2))
        except Exception as exc:
            status, error = "error", f"결과 DB 저장 실패: {exc}"
            logger.exception("요약 결과 저장 실패")
        attempts += 1
        state = "done" if status in ("generated", "insufficient") else "failed" if attempts >= 3 else "retry"
        job_repository.save_outcome(QUEUE_DB, job_id, state, error,
                                    time.time() + (60 if attempts == 1 else 300), time.time())
    return True


def run():
    # Windows OS 잠금은 프로세스 종료 시 해제됩니다. 여러 서버 프로세스도 한 작업자만 처리합니다.
    import msvcrt
    lock_file = None
    try:
        lock_file = open(QUEUE_DB.with_suffix(".lock"), "a+b")
        if lock_file.tell() == 0:
            lock_file.write(b"0")
            lock_file.flush()
        lock_file.seek(0)
        try:
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            logger.info("다른 서버 프로세스의 요약 작업자를 사용합니다.")
            return
        initialize()
        job_repository.recover_running(QUEUE_DB, time.time())
        try:
            reconcile()
        except Exception:
            logger.exception("초기 기사 점검 실패; 다음 점검에서 재시도합니다.")
        scanner = threading.Thread(target=scan, name="dait-summary-scanner", daemon=True)
        scanner.start()
        while not _stop.is_set():
            try:
                if process_one():
                    if _stop.wait(1):
                        break
                    continue
            except Exception:
                logger.exception("백그라운드 요약 점검 실패")
                try:
                    with _queue_lock:
                        job_repository.recover_running(QUEUE_DB, time.time(), time.time() + 60)
                except sqlite3.Error:
                    logger.exception("중단된 작업 복구 실패; 다음 서버 시작 시 재개합니다.")
            _stop.wait(10)
    finally:
        if lock_file is not None:
            lock_file.close()


def scan():
    while not _stop.wait(10):
        try:
            reconcile()
        except Exception:
            logger.exception("기사 DB 변경 및 저장 요약 점검 실패")


def start():
    global _thread
    with _lifecycle:
        if _thread is not None and _thread.is_alive():
            return
        _stop.clear()
        _thread = threading.Thread(target=run, name="dait-summary-worker", daemon=True)
        _thread.start()


def stop():
    _stop.set()
    if _thread is not None:
        _thread.join(timeout=1)


def batch_status():
    if not QUEUE_DB.is_file():
        return {"status": "starting", "processed": 0, "message": "저장된 기사의 요약 상태를 확인하고 있습니다."}
    counts, revision = job_repository.statistics(QUEUE_DB)
    done, failed = counts.get("done", 0), counts.get("failed", 0)
    waiting = sum(counts.get(s, 0) for s in ("queued", "running", "retry"))
    return {"status": "running" if waiting else "error" if failed else "completed", "processed": done,
            "pending": waiting, "failed": failed, "revision": revision,
            "message": f"요약 준비: 처리 완료·재사용 {done}건 / 대기·처리 중 {waiting}건 / 재시도 종료 {failed}건"}


def get(job_id):
    if not QUEUE_DB.is_file():
        return None
    row, ahead = job_repository.lookup(QUEUE_DB, job_id, time.time())
    if row is None:
        return None
    status, error, attempts, next_try, updated, record_id = row
    if status == "done":
        message = "요약 처리가 완료되었습니다."
    elif status == "running":
        message = "이 기사의 AI 요약을 생성하고 있습니다."
    elif status == "retry" and next_try > time.time():
        message = f"재시도 대기 중입니다. 약 {max(1, int(next_try - time.time()))}초 후 처리 대상이 됩니다. (실패 {attempts}/3회)"
    elif status in ("queued", "retry"):
        message = f"요약 처리 순서를 기다리고 있습니다. 앞선 작업 {ahead}건이 있습니다."
    elif status == "obsolete":
        message = "기사 정보가 변경되었습니다. 상세 화면을 다시 열어주세요."
    else:
        message = "최대 재시도 횟수에 도달했습니다. Ollama 실행을 확인한 뒤 다시 요청해주세요."
    return {"status": "completed" if status == "done" else "error" if status in ("failed", "obsolete") else "running",
            "state": status, "attempts": attempts, "ahead": ahead, "message": message}


def article_state(article_id, title, description, is_foreign=False):
    """현재 기사 입력에 해당하는 대기열 상태만 읽습니다."""
    if not QUEUE_DB.is_file():
        return None
    digest = input_for({"title": title, "summary": description})[1]
    job_id = job_repository.current_job_id(QUEUE_DB, article_id, digest, MODEL, "foreign" if is_foreign else "domestic")
    return get(job_id) if job_id else None


def request(article_id=None):
    """기존 버튼과 API는 새 작업자를 사용하며 별도 생성 스레드를 만들지 않습니다."""
    initialize()
    if article_id is None:
        return "background-batch"
    # 명시적 요청은 현재 생성 중인 작업 다음에 우선 처리합니다.
    with _queue_lock:
        return job_repository.request_article(QUEUE_DB, article_id)

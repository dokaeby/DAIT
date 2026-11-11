import sqlite3
import threading
from contextlib import closing
from unittest.mock import Mock

import pytest

from backend.pipelines import collect_news
from backend.services import summary_worker as worker


# 기능: 테스트 기사를 저장하고 요약 대기열을 동기화한다.
# 입력:
#   article: 테스트용 기사 사전을 제공하는 fixture.
# 출력: None.
def prepare(article):
    collect_news.save_articles([article])
    worker.initialize()
    worker.reconcile()


# 기능: 정상 저장 요약 재사용 동작을 검증한다.
# 입력:
#   article: 테스트용 기사 사전을 제공하는 fixture.
#   monkeypatch: 속성·환경을 임시 대체하는 pytest fixture.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-AI-009")
def test_valid_saved_summary_reused(article, monkeypatch):
    prepare(article)
    fake = Mock(return_value=("generated", ["하나", "둘", "셋"]))
    monkeypatch.setattr(worker, "generate", fake)
    assert worker.process_one()
    worker.reconcile()
    assert not worker.process_one()
    assert fake.call_count == 1


# 기능: 빈 설명에서 모델 호출 방지 동작을 검증한다.
# 입력:
#   article: 테스트용 기사 사전을 제공하는 fixture.
#   monkeypatch: 속성·환경을 임시 대체하는 pytest fixture.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-AI-003")
def test_blank_input_does_not_call_model(article, monkeypatch):
    prepare({**article, "summary": []})
    fake = Mock()
    monkeypatch.setattr(worker, "generate", fake)
    worker.process_one()
    fake.assert_not_called()
    with closing(sqlite3.connect(worker.RESULT_DB)) as db:
        assert db.execute("SELECT status FROM summary_tests").fetchone()[0] == "insufficient"


# 기능: 실패 이력 보존과 재시도 횟수 제한 동작을 검증한다.
# 입력:
#   runtime: 격리된 DB·고정 시각·서비스 묶음.
#   article: 테스트용 기사 사전을 제공하는 fixture.
#   monkeypatch: 속성·환경을 임시 대체하는 pytest fixture.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-RETRY-001", "UT-RETRY-003")
def test_failure_history_and_retry_budget(runtime, article, monkeypatch):
    prepare(article)
    monkeypatch.setattr(worker, "generate", Mock(side_effect=ConnectionError("fake outage")))
    assert worker.process_one()
    assert not worker.process_one()
    runtime.clock.now += 60
    assert worker.process_one()
    assert not worker.process_one()
    runtime.clock.now += 300
    assert worker.process_one()
    assert not worker.process_one()
    with closing(worker.connect()) as db:
        assert db.execute("SELECT status,attempts FROM jobs").fetchone() == (
            "failed",
            3,
        )
    with closing(sqlite3.connect(worker.RESULT_DB)) as db:
        assert (
            db.execute("SELECT COUNT(*) FROM summary_tests WHERE status='error'").fetchone()[0] == 3
        )


# 기능: 저장 실패 시 완료 상태 방지 동작을 검증한다.
# 입력:
#   article: 테스트용 기사 사전을 제공하는 fixture.
#   monkeypatch: 속성·환경을 임시 대체하는 pytest fixture.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.extension
def test_storage_failure_never_marks_done(article, monkeypatch):
    prepare(article)
    monkeypatch.setattr(worker, "generate", lambda *a: ("generated", ["a", "b", "c"]))
    monkeypatch.setattr(
        worker,
        "save_result",
        Mock(side_effect=sqlite3.OperationalError("fake failure")),
    )
    worker.process_one()
    with closing(worker.connect()) as db:
        assert db.execute("SELECT status FROM jobs").fetchone()[0] == "retry"


# 기능: 대기열 중복 방지와 수동 재시도의 실패 횟수 초기화 동작을 검증한다.
# 입력:
#   article: 테스트용 기사 사전을 제공하는 fixture.
#   runtime: 격리된 DB·고정 시각·서비스 묶음.
#   monkeypatch: 속성·환경을 임시 대체하는 pytest fixture.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.extension
def test_reconcile_deduplicates_and_manual_retry_resets_failed(article, runtime, monkeypatch):
    prepare(article)
    worker.reconcile()
    with closing(worker.connect()) as db, db:
        assert db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1
        db.execute("UPDATE jobs SET status='failed',attempts=3,error='fake failure'")
    job_id = worker.request(article["id"])
    with closing(worker.connect()) as db:
        assert db.execute(
            "SELECT status,attempts,next_try,error FROM jobs WHERE id=?", (job_id,)
        ).fetchone() == ("queued", 0, 0, "")


# 기능: 대기열 오류의 사용자 안내 변환 동작을 검증한다.
# 입력:
#   article: 테스트용 기사 사전을 제공하는 fixture.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-DETAIL-010")
def test_queue_error_is_generalized(article):
    prepare(article)
    with closing(worker.connect()) as db, db:
        db.execute("UPDATE jobs SET status='failed',error='private SQL or token'")
        job_id = db.execute("SELECT id FROM jobs").fetchone()[0]
    assert "private SQL or token" not in worker.get(job_id)["message"]


# 기능: 동일 작업의 동시 중복 실행 방지 동작을 검증한다.
# 입력:
#   article: 테스트용 기사 사전을 제공하는 fixture.
#   monkeypatch: 속성·환경을 임시 대체하는 pytest fixture.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-RETRY-004")
def test_same_job_cannot_run_twice_concurrently(article, monkeypatch):
    prepare(article)
    entered, release = threading.Event(), threading.Event()

    # 기능: 동시 실행 검증을 위해 이벤트로 대기하는 모의 요약을 생성한다.
    # 입력:
    #   args: 명령행 옵션 객체 또는 전달할 위치 인자.
    # 출력: (generated, 세 문장 목록) 튜플.
    def generate(*args):
        entered.set()
        assert release.wait(5), "Test synchronization timed out"
        return "generated", ["하나", "둘", "셋"]

    fake = Mock(side_effect=generate)
    monkeypatch.setattr(worker, "generate", fake)
    result = []
    thread = threading.Thread(target=lambda: result.append(worker.process_one()))
    thread.start()
    try:
        assert entered.wait(5), "Worker did not start"
        worker.reconcile()
        assert worker.process_one() is False
    finally:
        release.set()
        thread.join(timeout=5)
    assert not thread.is_alive()
    assert result == [True]
    assert fake.call_count == 1

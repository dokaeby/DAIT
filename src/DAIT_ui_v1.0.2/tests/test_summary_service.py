"""공통 대기열의 재사용·중복 방지·재시도 한도를 임시 DB로 확인합니다."""
import json
import sqlite3
import tempfile
import unittest
from contextlib import ExitStack, closing
from pathlib import Path
from unittest.mock import patch

from backend.services import summary_service as service
from backend.services import summary_provider
from backend import news as app

worker = service.worker


class SummaryWorkerTests(unittest.TestCase):
    # 기능: 테스트별 임시 DB와 기본 데이터를 준비한다.
    # 입력:
    #   self: 현재 인스턴스.
    # 출력: None. 테스트 인스턴스 상태를 초기화한다.
    def setUp(self):
        self.stack = ExitStack()
        directory = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        for name, value in (("QUEUE_DB", directory / "queue.db"),
                            ("RESULT_DB", directory / "summary.db"),
                            ("NEWS_DB", directory / "news.db")):
            self.stack.enter_context(patch.object(worker, name, value))
        with closing(sqlite3.connect(worker.NEWS_DB)) as db, db:
            db.execute("CREATE TABLE articles(id,title,summary,source,original_url,is_foreign,published_at)")
        self.article = dict(id="one", title="제목", summary="설명", source="출처", original_url="https://example.com")
        worker.initialize()

    # 기능: 테스트에서 대체한 설정을 복구하고 임시 자원을 정리한다.
    # 입력:
    #   self: 현재 인스턴스.
    # 출력: None.
    def tearDown(self):
        self.stack.close()

    # 기능: 모의 기사 계획과 재사용 조건으로 요약 대기열을 준비한다.
    # 입력:
    #   self: 현재 인스턴스.
    #   reusable: 재사용 가능한 결과를 준비할지 여부.
    # 출력: None.
    def enqueue(self, reusable=False):
        with patch.object(worker, "plan", return_value=[(self.article, "generated" if reusable else "missing", reusable)]):
            worker.reconcile()

    # 기능: 동기화의 저장 결과 재사용과 작업 중복 방지 동작을 검증한다.
    # 입력:
    #   self: 현재 인스턴스.
    # 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
    def test_reconcile_reuses_and_deduplicates(self):
        self.enqueue(reusable=True)
        self.enqueue(reusable=True)
        with closing(worker.connect()) as db:
            self.assertEqual(db.execute("SELECT status,COUNT(*) FROM jobs GROUP BY status").fetchall(), [("done", 1)])
        with patch.object(worker, "generate") as generate:
            self.assertFalse(worker.process_one())
            generate.assert_not_called()

    # 기능: 성공 결과 저장과 중복 생성 방지 동작을 검증한다.
    # 입력:
    #   self: 현재 인스턴스.
    # 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
    def test_success_is_saved_and_not_generated_again(self):
        self.enqueue()
        with patch.object(worker, "generate", return_value=("generated", ["첫째", "둘째", "셋째"])) as generate:
            self.assertTrue(worker.process_one())
            self.assertFalse(worker.process_one())
            self.assertEqual(generate.call_count, 1)
        with closing(sqlite3.connect(worker.RESULT_DB)) as db:
            status, lines = db.execute("SELECT status,lines_json FROM summary_tests").fetchone()
        self.assertEqual(status, "generated")
        self.assertEqual(json.loads(lines), ["첫째", "둘째", "셋째"])

    # 기능: 세 번 실패 후 재시도 중단과 이력 보존 동작을 검증한다.
    # 입력:
    #   self: 현재 인스턴스.
    # 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
    def test_failure_stops_after_three_attempts_and_preserves_history(self):
        self.enqueue()
        with patch.object(worker, "generate", side_effect=ValueError("실패")) as generate:
            for _ in range(3):
                with closing(worker.connect()) as db, db:
                    db.execute("UPDATE jobs SET next_try=0")
                self.assertTrue(worker.process_one())
            self.assertFalse(worker.process_one())
            self.assertEqual(generate.call_count, 3)
        with closing(worker.connect()) as db:
            self.assertEqual(db.execute("SELECT status,attempts FROM jobs").fetchone(), ("failed", 3))
        with closing(sqlite3.connect(worker.RESULT_DB)) as db:
            self.assertEqual(db.execute("SELECT status,COUNT(*) FROM summary_tests GROUP BY status").fetchall(), [("error", 3)])

    # 기능: 결과 저장 실패의 성공 처리 방지 동작을 검증한다.
    # 입력:
    #   self: 현재 인스턴스.
    # 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
    def test_result_storage_failure_is_not_success(self):
        self.enqueue()
        with patch.object(worker, "generate", return_value=("generated", ["첫째", "둘째", "셋째"])), patch.object(worker, "save_result", side_effect=sqlite3.OperationalError("저장 실패")):
            worker.process_one()
        with closing(worker.connect()) as db:
            self.assertEqual(db.execute("SELECT status FROM jobs").fetchone()[0], "retry")

    # 기능: 작업자의 공급자 결과 저장 동작을 검증한다.
    # 입력:
    #   self: 현재 인스턴스.
    # 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
    def test_provider_result_is_saved_by_worker(self):
        self.enqueue()
        class Provider:
            # 기능: 작업자 검증을 위한 모의 공급자 요약 또는 실패를 제공한다.
            # 입력:
            #   self: 현재 인스턴스.
            #   article: 테스트용 기사 사전을 제공하는 fixture.
            #   model: 사용할 모델 이름.
            #   timeout: 생성 요청 제한 시간(초).
            # 출력: 성공 시 (generated, 문장 목록), 실패 시 예외.
            def summarize(self, article, model, timeout):
                return "generated", ["첫째", "둘째", "셋째"]
        with patch.object(summary_provider, "get_provider", return_value=Provider()):
            worker.process_one()
        with closing(worker.connect()) as db:
            self.assertEqual(db.execute("SELECT status FROM jobs").fetchone()[0], "done")
        with closing(sqlite3.connect(worker.RESULT_DB)) as db:
            self.assertEqual(json.loads(db.execute("SELECT lines_json FROM summary_tests").fetchone()[0]), ["첫째", "둘째", "셋째"])

    # 기능: 공급자 실패 기록과 재시도 동작을 검증한다.
    # 입력:
    #   self: 현재 인스턴스.
    # 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
    def test_provider_failure_is_recorded_and_retried(self):
        self.enqueue()
        class Provider:
            # 기능: 작업자 검증을 위한 모의 공급자 요약 또는 실패를 제공한다.
            # 입력:
            #   self: 현재 인스턴스.
            #   article: 테스트용 기사 사전을 제공하는 fixture.
            #   model: 사용할 모델 이름.
            #   timeout: 생성 요청 제한 시간(초).
            # 출력: 성공 시 (generated, 문장 목록), 실패 시 예외.
            def summarize(self, article, model, timeout):
                raise ConnectionError("엔진 연결 실패")
        with patch.object(summary_provider, "get_provider", return_value=Provider()):
            worker.process_one()
        with closing(worker.connect()) as db:
            self.assertEqual(db.execute("SELECT status,attempts FROM jobs").fetchone(), ("retry", 1))
        with closing(sqlite3.connect(worker.RESULT_DB)) as db:
            self.assertEqual(db.execute("SELECT status,error FROM summary_tests").fetchone(), ("error", "엔진 연결 실패"))

    # 기능: 카드의 저장 요약 이스케이프 표시 동작을 검증한다.
    # 입력:
    #   self: 현재 인스턴스.
    # 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
    def test_card_shows_escaped_saved_summary(self):
        articles = [("1", "제목", "출처", "2026-11-09", "기타", 0, "설명")]
        summary = {"status": "generated", "lines": ["첫째", "둘째", "<셋째>"], "message": "검토 전"}
        with patch.object(app, "get_ai_summary", return_value=summary), patch.object(app, "available_categories", return_value=["기타"]):
            page = app.page(articles)
        self.assertIn("&lt;셋째&gt;", page)


if __name__ == "__main__":
    unittest.main()

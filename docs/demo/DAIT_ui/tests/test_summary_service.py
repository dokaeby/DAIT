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

    def tearDown(self):
        self.stack.close()

    def enqueue(self, reusable=False):
        with patch.object(worker, "plan", return_value=[(self.article, "generated" if reusable else "missing", reusable)]):
            worker.reconcile()

    def test_reconcile_reuses_and_deduplicates(self):
        self.enqueue(reusable=True)
        self.enqueue(reusable=True)
        with closing(worker.connect()) as db:
            self.assertEqual(db.execute("SELECT status,COUNT(*) FROM jobs GROUP BY status").fetchall(), [("done", 1)])
        with patch.object(worker, "generate") as generate:
            self.assertFalse(worker.process_one())
            generate.assert_not_called()

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

    def test_result_storage_failure_is_not_success(self):
        self.enqueue()
        with patch.object(worker, "generate", return_value=("generated", ["첫째", "둘째", "셋째"])), patch.object(worker, "save_result", side_effect=sqlite3.OperationalError("저장 실패")):
            worker.process_one()
        with closing(worker.connect()) as db:
            self.assertEqual(db.execute("SELECT status FROM jobs").fetchone()[0], "retry")

    def test_provider_result_is_saved_by_worker(self):
        self.enqueue()
        class Provider:
            def summarize(self, article, model, timeout):
                return "generated", ["첫째", "둘째", "셋째"]
        with patch.object(summary_provider, "get_provider", return_value=Provider()):
            worker.process_one()
        with closing(worker.connect()) as db:
            self.assertEqual(db.execute("SELECT status FROM jobs").fetchone()[0], "done")
        with closing(sqlite3.connect(worker.RESULT_DB)) as db:
            self.assertEqual(json.loads(db.execute("SELECT lines_json FROM summary_tests").fetchone()[0]), ["첫째", "둘째", "셋째"])

    def test_provider_failure_is_recorded_and_retried(self):
        self.enqueue()
        class Provider:
            def summarize(self, article, model, timeout):
                raise ConnectionError("엔진 연결 실패")
        with patch.object(summary_provider, "get_provider", return_value=Provider()):
            worker.process_one()
        with closing(worker.connect()) as db:
            self.assertEqual(db.execute("SELECT status,attempts FROM jobs").fetchone(), ("retry", 1))
        with closing(sqlite3.connect(worker.RESULT_DB)) as db:
            self.assertEqual(db.execute("SELECT status,error FROM summary_tests").fetchone(), ("error", "엔진 연결 실패"))

    def test_card_shows_escaped_saved_summary(self):
        articles = [("1", "제목", "출처", "2026-11-09", "기타", 0, "설명")]
        summary = {"status": "generated", "lines": ["첫째", "둘째", "<셋째>"], "message": "검토 전"}
        with patch.object(app, "get_ai_summary", return_value=summary), patch.object(app, "available_categories", return_value=["기타"]):
            page = app.page(articles)
        self.assertIn("&lt;셋째&gt;", page)


if __name__ == "__main__":
    unittest.main()

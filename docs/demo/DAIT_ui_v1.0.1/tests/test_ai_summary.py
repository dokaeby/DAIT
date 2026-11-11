"""요약 연결의 예외 처리와 HTTP 응답을 임시 DB로 검증합니다."""
import hashlib
import json
import sqlite3
from contextlib import closing
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

from backend import news as app


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "summaries.db"
        self.override = patch.object(app, "SUMMARY_DB", self.path)
        self.override.start()
        self.article = ("테스트 <제목>", "테스트 출처", "2026-11-08T12:00:00+00:00",
                        "테스트 설명", "", "https://example.com/article", 0, "인공지능")
        self.hash = hashlib.sha256(json.dumps({"title": self.article[0], "rss_description": self.article[3]}, ensure_ascii=False).encode()).hexdigest()

    def tearDown(self):
        self.override.stop()
        self.temp.cleanup()

    def save(self, status="generated", lines=None, input_hash=None):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS summary_tests (article_id TEXT, status TEXT, lines_json TEXT, input_hash TEXT, model TEXT, reviewed INTEGER)")
            db.execute("INSERT INTO summary_tests VALUES (?, ?, ?, ?, ?, ?)",
                       ("test-id", status, json.dumps(lines if lines is not None else ["첫 문장.", "둘째 문장.", "셋째 문장."]), input_hash or self.hash, "test-model", 0))

    def test_missing_and_generated(self):
        self.assertEqual(app.get_ai_summary("test-id", self.article)["status"], "missing")
        self.assertFalse(self.path.exists())
        self.save()
        result = app.get_ai_summary("test-id", self.article)
        self.assertEqual(len(result["lines"]), 3)
        self.assertIn("검토 전", result["message"])
        self.assertEqual(app.get_ai_summary("other-id", self.article)["status"], "missing")

    def test_states_and_latest_failure(self):
        self.save()
        self.save("error", [])
        self.assertEqual(app.get_ai_summary("test-id", self.article)["status"], "error")
        self.save("insufficient", [])
        self.assertEqual(app.get_ai_summary("test-id", self.article)["status"], "insufficient")
        self.save(lines=["같음", "같음", "같음"])
        self.assertEqual(app.get_ai_summary("test-id", self.article)["status"], "invalid")
        self.save(input_hash="old-input")
        self.assertEqual(app.get_ai_summary("test-id", self.article)["status"], "stale")

    def test_http_summary_and_escape(self):
        self.save(lines=["<script>문장</script>", "둘째 문장.", "셋째 문장."])
        server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with patch.object(app, "get_article", return_value=self.article):
                url = f"http://127.0.0.1:{server.server_port}/article/test-id"
                with urllib.request.urlopen(url + "?format=json") as response:
                    data = json.load(response)
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                    self.assertEqual(data["ai_summary"]["status"], "generated")
                with urllib.request.urlopen(url) as response:
                    output = response.read().decode()
                    self.assertIn("&lt;script&gt;문장&lt;/script&gt;", output)
                    self.assertNotIn("<script>문장</script>", output)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()

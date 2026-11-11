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
    # 기능: 테스트별 임시 DB와 기본 데이터를 준비한다.
    # 입력:
    #   self: 현재 인스턴스.
    # 출력: None. 테스트 인스턴스 상태를 초기화한다.
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "summaries.db"
        self.override = patch.object(app, "SUMMARY_DB", self.path)
        self.override.start()
        self.article = ("테스트 <제목>", "테스트 출처", "2026-11-08T12:00:00+00:00",
                        "테스트 설명", "", "https://example.com/article", 0, "인공지능")
        self.hash = hashlib.sha256(json.dumps({"title": self.article[0], "rss_description": self.article[3]}, ensure_ascii=False).encode()).hexdigest()

    # 기능: 테스트에서 대체한 설정을 복구하고 임시 자원을 정리한다.
    # 입력:
    #   self: 현재 인스턴스.
    # 출력: None.
    def tearDown(self):
        self.override.stop()
        self.temp.cleanup()

    # 기능: 지정한 상태와 내용으로 테스트용 요약 또는 번역 기록을 저장한다.
    # 입력:
    #   self: 현재 인스턴스.
    #   status: 기록하거나 검증할 요약 상태.
    #   lines: 요약 문장 목록.
    #   input_hash: 저장할 입력 해시(없으면 현재 입력에서 계산).
    # 출력: None. 임시 DB에 결과 행을 추가한다.
    def save(self, status="generated", lines=None, input_hash=None):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS summary_tests (article_id TEXT, status TEXT, lines_json TEXT, input_hash TEXT, model TEXT, reviewed INTEGER)")
            db.execute("INSERT INTO summary_tests VALUES (?, ?, ?, ?, ?, ?)",
                       ("test-id", status, json.dumps(lines if lines is not None else ["첫 문장.", "둘째 문장.", "셋째 문장."]), input_hash or self.hash, "test-model", 0))

    # 기능: 미생성 상태와 정상 저장 요약 표시 동작을 검증한다.
    # 입력:
    #   self: 현재 인스턴스.
    # 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
    def test_missing_and_generated(self):
        self.assertEqual(app.get_ai_summary("test-id", self.article)["status"], "missing")
        self.assertFalse(self.path.exists())
        self.save()
        result = app.get_ai_summary("test-id", self.article)
        self.assertEqual(len(result["lines"]), 3)
        self.assertIn("검토 전", result["message"])
        self.assertEqual(app.get_ai_summary("other-id", self.article)["status"], "missing")

    # 기능: 요약 상태와 가장 최근 실패 기록 반영 동작을 검증한다.
    # 입력:
    #   self: 현재 인스턴스.
    # 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
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

    # 기능: HTTP 요약 응답과 HTML 이스케이프 동작을 검증한다.
    # 입력:
    #   self: 현재 인스턴스.
    # 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
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

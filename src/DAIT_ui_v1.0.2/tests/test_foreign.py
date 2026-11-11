"""해외 기사 한국어 결과와 목록·상세 연결을 임시 DB로 점검합니다."""
import json
import sqlite3
import tempfile
import threading
import unittest
import urllib.request
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from backend import news as app
from backend.services import foreign_content as store


class ForeignTests(unittest.TestCase):
    # 기능: 테스트별 임시 DB와 기본 데이터를 준비한다.
    # 입력:
    #   self: 현재 인스턴스.
    # 출력: None. 테스트 인스턴스 상태를 초기화한다.
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "foreign.db"
        self.override = patch.object(store, "TRANSLATION_DB", self.path)
        self.override.start()
        self.article = ("Original title", "테스트 언론사", "2026-11-08T12:00:00+00:00",
                        "Original RSS description.", "", "https://example.com/news", 1, "인공지능")

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
    #   title: 저장할 한국어 번역 제목.
    #   lines: 요약 문장 목록.
    #   stale: 오래된 입력 해시로 기록할지 여부.
    # 출력: None. 임시 DB에 결과 행을 추가한다.
    def save(self, status="generated", title="한국어 <제목>", lines=None, stale=False):
        with closing(sqlite3.connect(self.path)) as db:
            store.create_table(db)
            run = str(db.execute("SELECT count(*) FROM foreign_translations").fetchone()[0])
            db.execute("INSERT INTO foreign_translations (run_id,article_id,model,original_title,original_description,source,original_url,input_hash,status,title_ko,lines_json,error,elapsed_seconds) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (run, "foreign-id", "test-model", self.article[0], self.article[3], self.article[1], self.article[5],
                        "stale" if stale else store.input_for(self.article[0], self.article[3])[1], status, title,
                        json.dumps(["첫 문장.", "둘째 문장.", "셋째 문장."] if lines is None else lines), "", 0))
            db.commit()

    # 기능: 현재 테스트 기사의 저장된 번역 상태를 조회한다.
    # 입력:
    #   self: 현재 인스턴스.
    # 출력: 화면 표시용 번역 상태 사전.
    def read(self):
        return store.get_translation("foreign-id", self.article[0], self.article[3])

    # 기능: 미생성 상태와 정상 저장 요약 표시 동작을 검증한다.
    # 입력:
    #   self: 현재 인스턴스.
    # 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
    def test_missing_and_generated(self):
        self.assertEqual(self.read()["status"], "missing")
        self.assertFalse(self.path.exists())
        self.save()
        self.assertEqual(self.read()["title_ko"], "한국어 <제목>")
        self.assertEqual(len(self.read()["lines"]), 3)
        self.assertIn("검토 전", self.read()["message"])
        self.assertEqual(store.get_translation("other-id", self.article[0], self.article[3])["status"], "missing")

    # 기능: 정보 부족·최신 실패·오래된 번역 처리 동작을 검증한다.
    # 입력:
    #   self: 현재 인스턴스.
    # 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
    def test_insufficient_latest_error_and_stale(self):
        self.save("insufficient", lines=[])
        self.assertTrue(self.read()["title_ko"])
        self.assertEqual(self.read()["lines"], [])
        self.save("error", title="", lines=[])
        self.assertEqual(self.read()["status"], "error")
        self.assertIsNone(self.read()["title_ko"])
        self.save(stale=True)
        self.assertEqual(self.read()["status"], "stale")

    # 기능: 잘못된 번역 언어와 중복 문장 거부 동작을 검증한다.
    # 입력:
    #   self: 현재 인스턴스.
    # 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
    def test_invalid_language_and_duplicate_lines(self):
        self.save(title="English only")
        self.assertEqual(self.read()["status"], "invalid")
        self.save(lines=["같음", "같음", "같음"])
        self.assertEqual(self.read()["status"], "invalid")

    # 기능: 목록과 HTTP 상세의 동일 기사 결과 동작을 검증한다.
    # 입력:
    #   self: 현재 인스턴스.
    # 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
    def test_listing_and_http_same_article(self):
        self.save()
        listing = [("foreign-id", self.article[0], self.article[1], self.article[2], self.article[7], 1, self.article[3])]
        output = app.page(listing, "user1")
        self.assertIn("한국어 &lt;제목&gt;", output)
        self.assertIn('/article/foreign-id', output)
        server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with patch.object(app, "get_article", return_value=self.article):
                url = f"http://127.0.0.1:{server.server_port}/article/foreign-id"
                with urllib.request.urlopen(url + "?format=json") as response:
                    result = json.load(response)
                self.assertEqual(result["title"], "한국어 <제목>")
                self.assertEqual(result["original_title"], self.article[0])
                self.assertEqual(result["description"], self.article[3])
                self.assertEqual(result["original_url"], self.article[5])
                self.assertEqual(len(result["ai_summary"]["lines"]), 3)
                with urllib.request.urlopen(url) as response:
                    detail = response.read().decode()
                self.assertIn("한국어 &lt;제목&gt;", detail)
                self.assertIn("원문 제목: Original title", detail)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()

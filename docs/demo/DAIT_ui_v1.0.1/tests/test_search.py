"""키워드 검색 범위, 결과 제한, 계정 전환을 임시 DB로 점검합니다."""
import http.client
import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode

from backend import news as app


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "news.db"
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("CREATE TABLE articles (id TEXT,title TEXT,source TEXT,published_at TEXT,summary TEXT,is_foreign INTEGER)")
            db.execute("CREATE TABLE article_categories (article_id TEXT,category TEXT)")
            for index in range(1, 15):
                description = {1: "rare cloud", 2: "100% progress", 3: "under_score"}.get(index, "일반 설명")
                db.execute("INSERT INTO articles VALUES (?,?,?,?,?,?)", (f"a{index:02d}", f"기사 {index}", "테스트 출처", f"2026-11-{index:02d}T00:00:00+00:00", description, 0))
                db.execute("INSERT INTO article_categories VALUES (?,?)", (f"a{index:02d}", "인공지능" if index % 2 else "보안"))
            db.commit()
        self.override = patch.object(app, "DB", self.path)
        self.override.start()

    def tearDown(self):
        self.override.stop()
        self.temp.cleanup()

    def test_search_before_limit_and_scope(self):
        self.assertEqual(len(app.latest_articles()), 10)
        self.assertNotIn("a01", [row[0] for row in app.latest_articles()])
        self.assertEqual([row[0] for row in app.latest_articles("RARE cloud")], ["a01"])
        self.assertEqual([row[0] for row in app.recommended_articles("user1", "rare")], ["a01"])
        self.assertEqual(app.recommended_articles("user2", "rare"), [])
        self.assertEqual(app.latest_articles("does-not-exist"), [])

    def test_literal_characters_and_normalization(self):
        self.assertEqual([row[0] for row in app.latest_articles("%")], ["a02"])
        self.assertEqual([row[0] for row in app.latest_articles("_")], ["a03"])
        self.assertEqual(app.normalize_query("  RARE  \n cloud  "), "RARE cloud")
        with self.assertRaises(ValueError):
            app.normalize_query("가" * 201)

    def test_foreign_title_and_escaping(self):
        rows = [("f", "English title", "출처", "2026-11-08", "기타", 1, "English RSS")]
        with patch.object(app, "get_translation", return_value={"title_ko": "번역된 한국어 제목"}):
            self.assertEqual(app.filter_articles(rows, "한국어"), rows)
            self.assertEqual(app.filter_articles(rows, "English 한국어"), rows)
        output = app.page([], query='"><script>')
        self.assertIn("&lt;script&gt;", output)
        self.assertNotIn('value=""><script>', output)

    def test_http_user_switch_and_logout(self):
        server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port)
        try:
            connection.request("GET", "/?q=rare", headers={"Cookie": "dait_user=user2"})
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertIn("관심사와 검색어에 모두 일치하는 기사가 없습니다.", response.read().decode())
            for name in ("user1", "user2", "user3"):
                body = urlencode({"user": name, "password": "1234", "q": "rare"})
                connection.request("POST", "/login", body=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
                response = connection.getresponse()
                self.assertEqual(response.status, 303)
                self.assertEqual(response.headers["Location"], "/")
                self.assertIn("dait_user=" + name, response.headers["Set-Cookie"])
                response.read()
            body = urlencode({"user": "user1", "password": "wrong", "q": "rare"})
            connection.request("POST", "/login", body=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
            response = connection.getresponse()
            self.assertEqual(response.status, 401)
            self.assertIsNone(response.getheader("Set-Cookie"))
            response.read()
            body = urlencode({"user": "user1", "password": "1234", "q": "한" * 200})
            connection.request("POST", "/login", body=body, headers={"Content-Type": "application/x-www-form-urlencoded", "Cookie": "dait_user=user2"})
            response = connection.getresponse()
            self.assertEqual(response.status, 303)
            self.assertEqual(response.headers["Location"], "/?" + urlencode({"q": "한" * 200}))
            response.read()
            connection.request("POST", "/logout", body="q=rare")
            response = connection.getresponse()
            self.assertEqual(response.headers["Location"], "/")
            self.assertIn("Max-Age=0", response.headers["Set-Cookie"])
            response.read()
        finally:
            connection.close()
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()

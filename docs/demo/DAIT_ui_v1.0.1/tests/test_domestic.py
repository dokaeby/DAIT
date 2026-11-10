"""국내 전체 요약의 재사용·재처리 조건을 임시 DB로 검증합니다."""
import json
import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.pipelines import summarize_domestic as batch


class DomesticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.news = self.root / "news.db"
        self.results = self.root / "results.db"
        self.patches = [patch.object(batch, "NEWS_DB", self.news), patch.object(batch, "RESULT_DB", self.results)]
        for item in self.patches:
            item.start()
        with closing(sqlite3.connect(self.news)) as db, db:
            db.execute("CREATE TABLE articles (id TEXT,title TEXT,source TEXT,original_url TEXT,summary TEXT,is_foreign INTEGER,published_at TEXT)")
            db.executemany("INSERT INTO articles VALUES (?,?,?,?,?,?,?)", [
                ("domestic", "국내 기사", "출처", "https://example.com/a", "기사 설명", 0, "2026-11-08"),
                ("blank", "설명 없음", "출처", "https://example.com/b", "", 0, "2026-11-07"),
                ("foreign", "해외 기사", "출처", "https://example.com/c", "설명", 1, "2026-11-09"),
            ])

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def save(self, status="generated", model="qwen3:4b", changed=False, lines=None):
        article = batch.plan(model)[0][0]
        text, digest = batch.input_for(article)
        with closing(sqlite3.connect(self.results)) as db, db:
            batch.create_results_table(db)
            run_id = str(db.execute("SELECT count(*) FROM summary_tests").fetchone()[0])
            db.execute("INSERT INTO summary_tests (run_id,article_id,model,title,source,original_url,input_text,input_hash,status,lines_json,error,elapsed_seconds) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                       (run_id, article["id"], model, article["title"], article["source"], article["original_url"], text,
                        "old" if changed else digest, status, json.dumps(lines if lines is not None else ["하나", "둘", "셋"]), "", 0))

    def test_selection_without_writes(self):
        items = batch.plan("qwen3:4b")
        self.assertEqual([a["id"] for a, _, _ in items], ["domestic", "blank"])
        self.assertFalse(self.results.exists())

    def test_reuse_and_force(self):
        self.save()
        self.assertTrue(batch.plan("qwen3:4b")[0][2])
        self.assertFalse(batch.plan("qwen3:4b", force=True)[0][2])
        self.assertFalse(batch.plan("different-model")[0][2])
        self.save("insufficient", lines=[])
        self.assertTrue(batch.plan("qwen3:4b")[0][2])

    def test_latest_error_stale_invalid(self):
        self.save()
        self.save("error", lines=[])
        self.assertEqual(batch.plan("qwen3:4b")[0][1:], ("error", False))
        self.save(changed=True)
        self.assertEqual(batch.plan("qwen3:4b")[0][1:], ("stale", False))
        self.save(lines=["중복", "중복", "중복"])
        self.assertEqual(batch.plan("qwen3:4b")[0][1:], ("invalid", False))


if __name__ == "__main__":
    unittest.main()

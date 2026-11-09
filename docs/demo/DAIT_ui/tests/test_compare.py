"""검색 비교의 벡터 검증·순위 결합·색인 무효화를 모델 없이 점검합니다."""
import json
import math
import sys
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from backend.pipelines import search_compare as search


class CompareTests(unittest.TestCase):
    def test_vectors_and_cosine(self):
        vector = search.unit_vector([3, 4])
        self.assertAlmostEqual(sum(x*x for x in vector), 1)
        self.assertAlmostEqual(search.cosine(vector, vector), 1)
        self.assertAlmostEqual(search.cosine([1, 0], [0, 1]), 0)
        for invalid in ([], [0, 0], [math.nan], [True], ["1"]):
            with self.assertRaises(ValueError):
                search.unit_vector(invalid)
        with self.assertRaises(ValueError):
            search.cosine([1], [1, 0])

    def test_hybrid_ranking(self):
        ranks = search.fuse(["keyword", "both"], ["semantic", "both"])
        self.assertEqual(ranks[0][0], "both")
        self.assertEqual(len(ranks), 3)
        self.assertEqual(search.fuse([], []), [])
        self.assertEqual(search.fuse(["only"], [])[0][0], "only")

    def test_keyword_and_cache_invalidation(self):
        articles = [{"id": "a", "text": "TSMC 반도체 cloud"}, {"id": "b", "text": "security"}]
        self.assertEqual([a["id"] for a in search.keyword_rank(articles, "tsmc cloud")], ["a"])
        article = {"input_hash": "new"}
        row = {"input_hash": "new", "model_digest": "version1", "vector_json": json.dumps([1, 0])}
        self.assertEqual(search.cached_vector(article, row, "version1"), [1, 0])
        self.assertIsNone(search.cached_vector(article, row, "version2"))
        self.assertIsNone(search.cached_vector({"input_hash": "changed"}, row, "version1"))
        self.assertIsNone(search.cached_vector(article, {**row, "vector_json": "invalid"}))

    def test_embedding_response_contract(self):
        from unittest.mock import Mock
        encoder = SimpleNamespace(max_seq_length=10,
            tokenizer=Mock(return_value={"input_ids": [1, 2, 3]}),
            encode=Mock(return_value=SimpleNamespace(tolist=lambda: [3, 4])))
        self.assertEqual(search.embed("기사", encoder), [0.6, 0.8])
        encoder.encode.assert_called_once_with("기사", normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
        encoder.tokenizer.return_value = {"input_ids": list(range(11))}
        with self.assertRaises(ValueError):
            search.embed("너무 긴 기사", encoder)
        self.assertEqual(encoder.encode.call_count, 1)

    def test_e5_input_prefixes(self):
        self.assertEqual(search.embedding_text("검색어", search.DEFAULT_MODEL, "query"), "query: 검색어")
        self.assertEqual(search.embedding_text("기사", search.DEFAULT_MODEL, "passage"), "passage: 기사")
        self.assertEqual(search.embedding_text("기사", "BAAI/bge-m3", "passage"), "기사")

    def test_cpu_model_load_and_version_identity(self):
        from unittest.mock import Mock
        encoder = SimpleNamespace(max_seq_length=8192)
        download = Mock(return_value="cache/snapshots/commit1")
        factory = Mock(return_value=encoder)
        with patch.dict(sys.modules, {"huggingface_hub": SimpleNamespace(snapshot_download=download),
                                     "sentence_transformers": SimpleNamespace(SentenceTransformer=factory)}):
            with patch.object(search, "version", return_value="test-version"):
                loaded, first = search.load_encoder("test/model", "commit1", offline=True)
                self.assertIs(loaded, encoder)
                self.assertTrue(first.startswith("st:"))
                self.assertEqual(download.call_args.kwargs["local_files_only"], True)
                self.assertIn("*.safetensors", download.call_args.kwargs["allow_patterns"])
                self.assertNotIn("pytorch_model.bin", download.call_args.kwargs["allow_patterns"])
                factory.assert_called_with("cache/snapshots/commit1", device="cpu", local_files_only=True, trust_remote_code=False)
                self.assertEqual(search.load_encoder("test/model", "commit1", offline=True)[1], first)
            with patch.object(search, "version", return_value="changed-version"):
                self.assertNotEqual(search.load_encoder("test/model", "commit1", offline=True)[1], first)

    def test_display_scores_include_keyword_below_threshold(self):
        articles = [dict(id=key, title=key, source="출처", url="https://example.com", text=text, input_hash=key)
                    for key, text in (("keyword", "literal"), ("semantic", "other"))]
        saved = {key: {"input_hash": key, "model_digest": "version", "vector_json": json.dumps(vector)}
                 for key, vector in (("keyword", [0, 1]), ("semantic", [1, 0]))}
        args = SimpleNamespace(query="literal", user=None, model="test", revision="main", offline=True, min_score=0.35)
        with patch.object(search, "corpus", return_value=articles), patch.object(search, "cache", return_value=saved), patch.object(search, "embed", return_value=[1, 0]):
            result = search.evaluate(args, encoder_bundle=(object(), "version"))
        self.assertEqual(result["keyword"][0]["cosine"], 0)
        self.assertEqual(result["semantic"][0]["cosine"], 1)
        hybrid = {row["id"]: row for row in result["hybrid"]}
        self.assertEqual(hybrid["keyword"]["cosine"], 0)
        self.assertEqual(result["candidate_count"], 2)


if __name__ == "__main__":
    unittest.main()

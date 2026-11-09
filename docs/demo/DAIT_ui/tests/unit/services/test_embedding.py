import json
import math
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.pipelines import search_compare as search


@pytest.mark.extension
@pytest.mark.parametrize("vector", [[], [0, 0], [math.nan], [math.inf], [True], ["x"]])
def test_invalid_vectors_rejected(vector):
    with pytest.raises(ValueError):
        search.unit_vector(vector)


@pytest.mark.extension
def test_cosine_and_rrf():
    assert search.cosine([1, 0], [1, 0]) == 1
    assert search.cosine([1, 0], [0, 1]) == 0
    assert search.fuse(["keyword", "both"], ["semantic", "both"])[0][0] == "both"


@pytest.mark.extension
def test_e5_prefixes_and_changed_model_invalidates_cache():
    assert search.embedding_text("AI", search.DEFAULT_MODEL, "query") == "query: AI"
    assert search.embedding_text("AI", search.DEFAULT_MODEL, "passage") == "passage: AI"
    article = dict(input_hash="same")
    row = dict(input_hash="same", model_digest="old", vector_json=json.dumps([1, 0]))
    assert search.cached_vector(article, row, "new") is None
    assert search.cached_vector(article, row, "old") == [1, 0]


@pytest.mark.extension
def test_fake_encoder_never_loads_model():
    encoder = SimpleNamespace(
        max_seq_length=10,
        tokenizer=Mock(return_value={"input_ids": [1, 2]}),
        encode=Mock(return_value=SimpleNamespace(tolist=lambda: [3, 4])),
    )
    assert search.embed("AI", encoder) == [0.6, 0.8]
    assert encoder.encode.call_count == 1


@pytest.mark.extension
def test_keyword_result_keeps_real_similarity(monkeypatch):
    articles = [
        dict(
            id=k,
            title=k,
            source="source",
            url="https://example.com",
            text=text,
            input_hash=k,
        )
        for k, text in (("keyword", "literal"), ("semantic", "other"))
    ]
    vectors = {
        k: dict(input_hash=k, model_digest="version", vector_json=json.dumps(v))
        for k, v in (("keyword", [0, 1]), ("semantic", [1, 0]))
    }
    monkeypatch.setattr(search, "corpus", lambda *a, **kw: articles)
    monkeypatch.setattr(search, "cache", lambda *a, **kw: vectors)
    monkeypatch.setattr(search, "embed", lambda *a, **kw: [1, 0])
    args = SimpleNamespace(
        query="literal",
        user=None,
        model="fake",
        revision="main",
        offline=True,
        min_score=0.35,
    )
    result = search.evaluate(args, encoder_bundle=(object(), "version"))
    scores = {item["id"]: item["cosine"] for item in result["hybrid"]}
    assert scores == {"keyword": 0, "semantic": 1}

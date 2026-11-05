from pathlib import Path
from time import perf_counter
from urllib.parse import urlsplit

from flask import Flask, jsonify, render_template, request
import chromadb
from sentence_transformers import SentenceTransformer

app = Flask(__name__)
client = chromadb.PersistentClient(path=str(Path(__file__).parent / "news_db"))
collection = client.get_or_create_collection("articles")
model = SentenceTransformer("intfloat/multilingual-e5-small", local_files_only=True)
model.max_seq_length = 256
model.encode(["워밍업"])


def article(meta, doc=""):
    meta = meta or {}
    url = meta.get("url", "")
    try:
        valid_url = urlsplit(url).scheme in ("http", "https")
    except ValueError:
        valid_url = False
    if not valid_url:
        url = ""
    return {"title": meta.get("title", "제목 없음"), "url": url,
            "source": meta.get("source", "출처 미상"),
            "published": meta.get("published", ""),
            "collected_at": meta.get("collected_at", ""),
            "summary": (doc or "")[:300]}


@app.get("/")
def home():
    total = collection.count()
    saved = collection.get(include=["metadatas", "documents"], limit=10) if total else {}
    articles = [article(meta, doc) for meta, doc in zip(
        saved.get("metadatas") or [], saved.get("documents") or [])]
    return render_template("index.html", total=total, articles=articles,
                           collection_info=collection.metadata or {})


@app.post("/search")
def search():
    started = perf_counter()
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="검색 요청 형식을 확인해 주세요."), 400
    query, limit = data.get("query", ""), data.get("limit", 10)
    if not isinstance(query, str) or not query.strip():
        return jsonify(error="검색어를 입력해 주세요."), 400
    if type(limit) is not int or not 1 <= limit <= 50:
        return jsonify(error="게시물 수는 1~50 사이의 정수로 선택해 주세요."), 400
    query = query.strip()
    if len(query) > 200:
        return jsonify(error="검색어는 200자 이내로 입력해 주세요."), 400
    total = collection.count()
    results = []
    if total:
        embeddings = model.encode([query], normalize_embeddings=True).tolist()
        result = collection.query(query_embeddings=embeddings, n_results=min(limit, total),
                                  include=["metadatas", "documents", "distances"])
        space = (collection.metadata or {}).get("hnsw:space", "l2")
        for meta, doc, distance in zip(result["metadatas"][0],
                                       result["documents"][0], result["distances"][0]):
            item = article(meta, doc)
            # 기본 제곱 L2 거리: 정규화된 벡터의 cosine = 1 - L2² / 2.
            score = 1 - float(distance) / 2 if space == "l2" else 1 - float(distance)
            item["similarity"] = round(max(0.0, min(1.0, score)), 4)
            results.append(item)
    return jsonify(results=results, total=total, limit=limit,
                   elapsed_ms=round((perf_counter() - started) * 1000, 1))


if __name__ == "__main__":
    app.run(debug=True)

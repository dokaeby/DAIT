"""로컬 임베딩 색인을 만들고 키워드 검색과 혼합 검색을 비교합니다."""
from dait.core.config import ensure_runtime_dirs
import argparse
import hashlib
import json
import math
import sqlite3
import sys
import time
import uuid
from contextlib import closing
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from dait.core.config import REPORTS_DIR as BASE
from dait.news import DB as NEWS_DB, USERS, normalize_query
from dait.services.foreign_content import get_translation

from dait.core.config import INDEX_DB
from dait.core.config import EMBEDDING_MODEL as DEFAULT_MODEL


def load_encoder(model, revision="main", offline=False):
    # 상태 조회와 단위 테스트는 대형 라이브러리나 모델을 로드하지 않습니다.
    try:
        from huggingface_hub import snapshot_download
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise ValueError("가상환경에서 python -m pip install -r requirements.txt 를 먼저 실행하세요.") from exc
    print(f"Sentence Transformers 모델 로드 중: {model} (CPU)", flush=True)
    weights = ["*.safetensors"]
    if model == "BAAI/bge-m3":
        weights.append("pytorch_model.bin")
    snapshot = snapshot_download(
        repo_id=model, revision=revision, local_files_only=offline,
        allow_patterns=weights + ["*.json", "*.txt", "*.model", "*.bpe", "vocab.*"],
        ignore_patterns=["onnx/*", "openvino/*"],
    )
    encoder = SentenceTransformer(snapshot, device="cpu", local_files_only=True, trust_remote_code=False)
    identity = {"backend": "sentence-transformers", "model": model, "commit": Path(snapshot).name,
                "device": "cpu", "normalize": True, "max_seq_length": encoder.max_seq_length,
                "input_format": "e5-query-passage-v1" if model == DEFAULT_MODEL else "plain-v1",
                "packages": {name: version(name) for name in ("sentence-transformers", "transformers", "torch")}}
    digest = "st:" + hashlib.sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).hexdigest()
    return encoder, digest


def unit_vector(vector):
    if not isinstance(vector, list) or not vector or not all(type(x) in (float, int) and math.isfinite(x) for x in vector):
        raise ValueError("유효한 숫자 벡터가 아닙니다.")
    norm = math.sqrt(sum(x * x for x in vector))
    if not math.isfinite(norm) or norm == 0:
        raise ValueError("벡터 크기가 유효하지 않습니다.")
    return [x / norm for x in vector]


def embedding_text(text, model, role):
    return f"{role}: {text}" if model == DEFAULT_MODEL else text


def embed(text, encoder):
    tokens = encoder.tokenizer(text, add_special_tokens=True, truncation=False)["input_ids"]
    if len(tokens) > encoder.max_seq_length:
        raise ValueError(f"입력이 모델 한도({encoder.max_seq_length} 토큰)를 초과했습니다. 입력 분할이 필요합니다.")
    vector = encoder.encode(text, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
    return unit_vector(vector.tolist())


def corpus(user=None, interests=None):
    with closing(sqlite3.connect(NEWS_DB.as_uri() + "?mode=ro", uri=True)) as db:
        rows = db.execute("""
            SELECT a.id,a.title,a.source,a.published_at,a.summary,a.is_foreign,
                   GROUP_CONCAT(c.category, ' · '),a.original_url
            FROM articles a LEFT JOIN article_categories c ON c.article_id=a.id
            GROUP BY a.id ORDER BY a.published_at DESC,a.id ASC
        """).fetchall()
    articles = []
    selected = USERS.get(user, ()) if interests is None else tuple(interests)
    for article_id, title, source, published, description, foreign, categories, url in rows:
        if user and selected and not set(selected).intersection((categories or "").split(" · ")):
            continue
        translated = get_translation(article_id, title, description)["title_ko"] if foreign else None
        text = "\n".join((title or "", description or "", translated or ""))
        articles.append({"id": article_id, "title": translated or title, "source": source,
                         "published_at": published, "url": url, "text": text, "categories": categories or "",
                         "input_hash": hashlib.sha256(text.encode("utf-8")).hexdigest()})
    return articles


def keyword_rank(articles, query):
    terms = normalize_query(query).casefold().split()
    return [a for a in articles if all(term in a["text"].casefold() for term in terms)]


def cosine(left, right):
    if len(left) != len(right):
        raise ValueError("벡터 차원이 다릅니다. 같은 모델로 색인을 다시 만드세요.")
    return max(-1.0, min(1.0, sum(a * b for a, b in zip(left, right))))


def fuse(keyword_ids, semantic_ids, k=60):
    scores = {}
    for ranking in (keyword_ids, semantic_ids):
        for rank, article_id in enumerate(ranking, 1):
            scores[article_id] = scores.get(article_id, 0) + 1 / (k + rank)
    # 동일 점수는 각 목록에 먼저 등장한 기사 순서를 유지합니다.
    return sorted(scores.items(), key=lambda item: -item[1])


def cache(model):
    if not INDEX_DB.is_file():
        return {}
    with closing(sqlite3.connect(INDEX_DB.as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        return {row["article_id"]: dict(row) for row in db.execute("SELECT * FROM embeddings WHERE model=?", (model,))}


def cached_vector(article, row, digest=None):
    if not row or row["input_hash"] != article["input_hash"] or (digest and row["model_digest"] != digest):
        return None
    try:
        return unit_vector(json.loads(row["vector_json"]))
    except (ValueError, TypeError):
        return None


def build(args, encoder_bundle=None, progress=print):
    articles = corpus()
    model = args.model
    saved = cache(model)
    valid = sum(cached_vector(a, saved.get(a["id"])) is not None for a in articles)
    progress(f"현재 기사: {len(articles)}개 / 입력 일치 색인: {valid}개 / 미생성·변경·오류: {len(articles)-valid}개")
    if args.status:
        progress("모델을 로드하지 않는 상태 확인입니다. 모델·라이브러리 버전 변경 여부는 생성·비교 실행 시 확인합니다.")
        return 0
    if not articles:
        raise ValueError("색인할 기사가 없습니다. 1단계 수집 결과를 확인하세요.")
    encoder, digest = encoder_bundle or load_encoder(model, args.revision, args.offline)
    pending = [a for a in articles if args.force or cached_vector(a, saved.get(a["id"]), digest) is None]
    progress(f"재사용: {len(articles)-len(pending)}개 / 생성 대상: {len(pending)}개")
    with closing(sqlite3.connect(INDEX_DB)) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS embeddings (
            article_id TEXT NOT NULL, model TEXT NOT NULL, model_digest TEXT NOT NULL,
            input_hash TEXT NOT NULL, input_text TEXT NOT NULL, vector_json TEXT NOT NULL,
            updated_at TEXT NOT NULL, PRIMARY KEY(article_id,model))""")
        for index, article in enumerate(pending, 1):
            progress(f"[{index}/{len(pending)}] {article['title']}")
            text = embedding_text(article["text"], model, "passage")
            vector = embed(text, encoder)
            db.execute("INSERT OR REPLACE INTO embeddings VALUES (?,?,?,?,?,?,?)",
                       (article["id"], model, digest, article["input_hash"], article["text"], json.dumps(vector), datetime.now(timezone.utc).isoformat()))
            db.commit()
    progress(f"색인 완료: {len(articles)}개 기사")
    return 0


def evaluate(args, encoder_bundle=None):
    query = normalize_query(args.query)
    if not query:
        raise ValueError("비교할 검색어를 입력하세요.")
    selected = getattr(args, "interests", None)
    if selected is None:
        selected = USERS.get(args.user, ())
    articles = corpus(args.user, selected)
    category = getattr(args, "category", "")
    if category:
        articles = [a for a in articles if category in a.get("categories", "").split(" · ")]
    if not articles:
        raise ValueError("현재 사용자 조건에 해당하는 기사가 없습니다.")
    start = time.perf_counter()
    model = args.model
    encoder, digest = encoder_bundle or load_encoder(model, args.revision, args.offline)
    model_load_seconds = time.perf_counter() - start
    saved = cache(model)
    vectors = {a["id"]: cached_vector(a, saved.get(a["id"]), digest) for a in articles}
    missing = [key for key, vector in vectors.items() if vector is None]
    if missing:
        raise ValueError(f"대상 기사 중 {len(missing)}개의 색인이 없거나 변경되었습니다. 색인을 먼저 생성·갱신하세요.")
    start = time.perf_counter()
    keywords = keyword_rank(articles, query)
    keyword_seconds = time.perf_counter() - start
    start = time.perf_counter()
    query_vector = embed(embedding_text(query, model, "query"), encoder)
    query_seconds = time.perf_counter() - start
    start = time.perf_counter()
    semantic = [(a["id"], cosine(query_vector, vectors[a["id"]])) for a in articles]
    semantic.sort(key=lambda item: -item[1])
    # 임계값 아래의 키워드 일치 기사에도 실제 코사인 값을 표시합니다.
    semantic_scores = dict(semantic)
    semantic = [(key, score) for key, score in semantic if score >= args.min_score][:20]
    keyword_ids = [a["id"] for a in keywords[:20]]
    hybrid = fuse(keyword_ids, [key for key, _ in semantic])[:10]
    ranking_seconds = time.perf_counter() - start
    by_id = {a["id"]: a for a in articles}
    def entry(article, **scores):
        return {key: article[key] for key in ("id", "title", "source", "url")} | scores
    result = {
        "query": query, "user": args.user or "비로그인", "category": category, "interests": list(selected), "model": model, "model_digest": digest,
        "backend": "sentence-transformers", "device": "cpu", "revision": args.revision,
        "model_load_seconds": round(model_load_seconds, 4),
        "candidate_count": len(articles), "min_cosine": args.min_score, "rrf_k": 60,
        "keyword_seconds": round(keyword_seconds, 4), "query_embedding_seconds": round(query_seconds, 4),
        "hybrid_ranking_seconds": round(ranking_seconds, 4),
        "keyword": [entry(a, cosine=semantic_scores[a["id"]]) for a in keywords[:10]],
        "semantic": [entry(by_id[key], cosine=score) for key, score in semantic[:10]],
        "hybrid": [entry(by_id[key], rrf_score=round(score, 6), cosine=semantic_scores.get(key)) for key, score in hybrid],
    }
    overlap = len({a["id"] for a in result["keyword"]} & {a["id"] for a in result["hybrid"]})
    result["overlap_count"] = overlap
    return result


def compare(args):
    result = evaluate(args)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]
    output = BASE / f"comparison_{run_id}.txt"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, label in (("keyword", "키워드 검색"), ("hybrid", "키워드+임베딩 검색")):
        print(f"\n{label}: {len(result[name])}개")
        for rank, row in enumerate(result[name], 1):
            print(f"{rank}. {row['title']}\n   {row['url']}")
    print(f"\n공통 기사: {result['overlap_count']}개 / 비교 보고서: {output}")
    print("코사인 유사도와 RRF 점수는 정확도 확률이 아닙니다. 기사 내용을 보고 관련성을 직접 비교하세요.")
    return 0


def main():
    ensure_runtime_dirs()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    index = commands.add_parser("build", help="전체 기사 색인을 생성합니다.")
    index.add_argument("--status", action="store_true")
    index.add_argument("--force", action="store_true")
    comparison = commands.add_parser("compare", help="같은 검색어의 두 검색 결과를 비교합니다.")
    comparison.add_argument("--query", required=True)
    comparison.add_argument("--user", choices=tuple(USERS))
    comparison.add_argument("--min-score", type=float, default=0.35)
    for subcommand in (index, comparison):
        subcommand.add_argument("--model", default=DEFAULT_MODEL)
        subcommand.add_argument("--revision", default="main", help="Hugging Face 모델의 태그 또는 커밋")
        subcommand.add_argument("--offline", action="store_true", help="다운로드된 모델 캐시만 사용합니다.")
    args = parser.parse_args()
    if args.command == "compare" and not -1 <= args.min_score <= 1:
        parser.error("min-score는 -1부터 1까지여야 합니다.")
    try:
        return build(args) if args.command == "build" else compare(args)
    except KeyboardInterrupt:
        print("중단했습니다. 완료된 색인은 보존되며 같은 build 명령으로 이어서 처리할 수 있습니다.")
        return 1
    except (OSError, sqlite3.Error, ValueError, TypeError, KeyError, AttributeError, RuntimeError, ImportError) as exc:
        print(f"처리 실패: {exc}\n가상환경 패키지·모델 다운로드 상태·기사 DB와 색인 상태를 확인하세요.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

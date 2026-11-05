import os
import shutil
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import feedparser
import chromadb
from sentence_transformers import SentenceTransformer

DB_PATH = str(Path(__file__).parent / "news_db")

FEEDS = {
    "연합뉴스": "https://www.yna.co.kr/rss/news.xml",
    "한겨레": "https://www.hani.co.kr/rss/home.xml",
    "경향신문": "https://www.khan.co.kr/rss/rssdata/total_news.xml",
    "BBC News": "https://feeds.bbci.co.uk/news/rss.xml",
    "Reuters": "https://www.reutersagency.com/feed/?best-topics=top-news&post_type=best",
}

MODEL_NAME = "intfloat/multilingual-e5-small"


def reset_database():
    if os.path.exists(DB_PATH):
        shutil.rmtree(DB_PATH)
        print("기존 DB를 삭제했습니다.")


def article_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def make_embedding_text(article: dict) -> str:
    title = article.get("title", "").strip()
    summary = article.get("summary", "").strip()

    # 제목 + 요약 앞부분만 사용해 입력 길이를 줄임
    return f"{title}\n{summary[:500]}"[:800]


def ingest():
    started = perf_counter()
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_or_create_collection("articles")

    model = SentenceTransformer(
        MODEL_NAME,
        local_files_only=True,
    )
    model.max_seq_length = 256

    new_articles = []

    for source, rss_url in FEEDS.items():
        print(f"{source} 수집 중...")
        feed = feedparser.parse(rss_url)

        for entry in feed.entries:
            url = entry.get("link", "")
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            published = entry.get("published", "")

            if not url or not title:
                continue

            new_articles.append({
                "id": article_id(url),
                "source": source,
                "title": title,
                "url": url,
                "summary": summary,
                "published": published,
                "collected_at": datetime.now(timezone.utc).isoformat(),
            })

    existing_ids = set(collection.get()["ids"])
    unique_articles = []
    for article in new_articles:
        if article["id"] in existing_ids:
            continue
        existing_ids.add(article["id"])
        unique_articles.append(article)
    new_articles = unique_articles

    if not new_articles:
        collection.modify(metadata={
            **(collection.metadata or {}),
            "last_collected_at": datetime.now(timezone.utc).isoformat(),
            "collection_duration_seconds": round(perf_counter() - started, 2),
        })
        print("새로 저장할 기사가 없습니다.")
        print(f"현재 저장된 기사 수: {collection.count()}")
        return

    texts = [make_embedding_text(article) for article in new_articles]

    embeddings = model.encode(
        texts,
        batch_size=32,
        normalize_embeddings=True,
        show_progress_bar=True,
    ).tolist()

    collection.add(
        ids=[article["id"] for article in new_articles],
        documents=texts,
        embeddings=embeddings,
        metadatas=[
            {
                "title": article["title"],
                "url": article["url"],
                "source": article["source"],
                "published": article["published"],
                "collected_at": article["collected_at"],
            }
            for article in new_articles
        ],
    )

    collection.modify(metadata={
        **(collection.metadata or {}),
        "last_collected_at": datetime.now(timezone.utc).isoformat(),
        "collection_duration_seconds": round(perf_counter() - started, 2),
    })
    print(f"{len(new_articles)}개 기사를 새로 저장했습니다.")
    print(f"현재 저장된 기사 수: {collection.count()}")


if __name__ == "__main__":
    if "--reset" in sys.argv:
        reset_database()

    ingest()

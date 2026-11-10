"""공개 RSS에서 DAIT 화면 테스트용 실제 기사 50개를 수집합니다."""
import argparse
import hashlib
import html
import json
import re
import sqlite3
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

from dait.core.config import NEWS_DB as OUTPUT, ensure_runtime_dirs
FEEDS = [
    ("전자신문", "etnews.com", False, "https://rss.etnews.com/Section901.xml"),
    ("전자신문", "etnews.com", False, "https://rss.etnews.com/03.xml"),
    ("전자신문", "etnews.com", False, "https://rss.etnews.com/04045.xml"),
    ("전자신문", "etnews.com", False, "https://rss.etnews.com/04046.xml"),
    ("TechCrunch", "techcrunch.com", True, "https://techcrunch.com/feed/"),
    ("The Verge", "theverge.com", True, "https://www.theverge.com/rss/index.xml"),
]
KEYWORDS = {
    "인공지능": ["인공지능", "생성형", "챗봇", "머신러닝", "딥러닝", "ai", "artificial intelligence", "chatgpt", "llm"],
    "보안": ["보안", "해킹", "랜섬웨어", "사이버", "security", "cyber", "ransomware", "hack"],
    "클라우드": ["클라우드", "cloud", "saas", "데이터센터", "data center"],
    "반도체": ["반도체", "메모리", "파운드리", "semiconductor", "chip", "nvidia", "엔비디아"],
    "개발": ["개발자", "프로그래밍", "소프트웨어", "developer", "software", "programming"],
}

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

def clean(value):
    parser = TextExtractor()
    parser.feed(value or "")
    return re.sub(r"\s+", " ", html.unescape(" ".join(parser.parts))).strip()

def value(node, *names):
    for name in names:
        element = node.find(name)
        if element is not None and element.text:
            return element.text.strip()
    return ""

def timestamp(raw):
    try:
        dt = parsedate_to_datetime(raw)
    except (ValueError, TypeError, IndexError):
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    return dt.astimezone(timezone.utc) if dt.tzinfo else None

def classify(text):
    text = text.lower()
    categories = []
    for category, words in KEYWORDS.items():
        if any(re.search(r"(?<![a-z])" + re.escape(word) + r"(?![a-z])", text) if word.isascii() else word in text for word in words):
            categories.append(category)
    return categories or ["기타"]

def collect_feed(source, domain, foreign, url):
    request = urllib.request.Request(url, headers={"User-Agent": "DAIT-test-collector/1.0 (RSS reader)"})
    with urllib.request.urlopen(request, timeout=20) as response:
        root = ET.fromstring(response.read())
    atom = "{http://www.w3.org/2005/Atom}"
    entries = root.findall(".//item") or root.findall(atom + "entry")
    articles = []
    for entry in entries:
        title = clean(value(entry, "title", atom + "title"))
        link = value(entry, "link")
        if not link:
            for item in entry.findall(atom + "link"):
                if item.get("rel", "alternate") == "alternate":
                    link = item.get("href", "")
                    break
        host = (urlparse(link).hostname or "").lower()
        date = timestamp(value(entry, "pubDate", atom + "published", atom + "updated"))
        if not title or not date or not (host == domain or host.endswith("." + domain)):
            continue
        excerpt = clean(value(entry, "description", atom + "summary", atom + "content"))
        articles.append({
            "id": hashlib.sha256(link.encode("utf-8")).hexdigest()[:16],
            "title": title, "source": source, "published_at": date.isoformat(),
            "categories": classify(title + " " + excerpt),
            "summary": [excerpt] if excerpt else [], "content": excerpt,
            "original_url": link, "is_foreign": foreign,
        })
    return articles

def save_articles(articles):
    ensure_runtime_dirs()
    # 기사와 카테고리를 한 트랜잭션에서 교체해 실패 시 기존 데이터를 보존합니다.
    with sqlite3.connect(OUTPUT) as db:
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("CREATE TABLE IF NOT EXISTS articles (id TEXT PRIMARY KEY, title TEXT NOT NULL, source TEXT NOT NULL, published_at TEXT NOT NULL, summary TEXT NOT NULL, content TEXT NOT NULL, original_url TEXT NOT NULL UNIQUE, is_foreign INTEGER NOT NULL CHECK (is_foreign IN (0, 1)))")
        db.execute("CREATE TABLE IF NOT EXISTS article_categories (article_id TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE, category TEXT NOT NULL, PRIMARY KEY (article_id, category))")
        db.execute("CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at DESC)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_article_categories_category ON article_categories(category)")
        db.execute("DELETE FROM articles")
        for article in articles:
            db.execute("INSERT INTO articles VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
                article["id"], article["title"], article["source"], article["published_at"],
                " ".join(article["summary"]), article["content"], article["original_url"], int(article["is_foreign"])))
            db.executemany("INSERT INTO article_categories VALUES (?, ?)",
                           [(article["id"], category) for category in set(article["categories"])])

def main():
    parser = argparse.ArgumentParser(description="실제 뉴스 50개를 SQLite에 저장합니다.")
    parser.add_argument("--from-json", type=Path, help="기존 수집 JSON을 사용합니다. 네트워크에 접속하지 않습니다.")
    args = parser.parse_args()
    if args.from_json:
        try:
            articles = json.loads(args.from_json.read_text(encoding="utf-8-sig"))
            if not isinstance(articles, list) or len(articles) != 50:
                raise ValueError("JSON에는 기사 50개가 있어야 합니다.")
            save_articles(articles)
        except (OSError, ValueError, TypeError, KeyError, sqlite3.Error) as exc:
            print(f"JSON 가져오기 실패: {exc}", file=sys.stderr)
            return 1
        print(f"저장 완료: {OUTPUT} (기사 {len(articles)}건)")
        return 0
    found = {}
    for source, domain, foreign, url in FEEDS:
        try:
            articles = collect_feed(source, domain, foreign, url)
            for article in articles:
                found[article["original_url"]] = article
            print(f"{source}: {len(articles)}건 확인 (중복 제거 후 총 {len(found)}건)")
        except (OSError, ValueError, ET.ParseError) as exc:
            print(f"수집 실패: {source} ({url}) - {exc}", file=sys.stderr)
    articles = sorted(found.values(), key=lambda a: a["published_at"], reverse=True)[:50]
    if len(articles) < 50:
        print(f"기사 {len(articles)}건만 수집되어 저장하지 않았습니다. 네트워크와 RSS 상태를 확인한 뒤 다시 실행하세요.", file=sys.stderr)
        return 1
    try:
        save_articles(articles)
    except sqlite3.Error as exc:
        print(f"DB 저장 실패: {exc}", file=sys.stderr)
        return 1
    print(f"저장 완료: {OUTPUT} (실제 기사 {len(articles)}건)")
    for category in KEYWORDS:
        print(f"{category}: {sum(category in a['categories'] for a in articles)}건")
    print("분류는 제목과 RSS 설명의 키워드 기준이며, 본문 대신 RSS 설명을 저장합니다.")
    return 0

if __name__ == "__main__":
    sys.exit(main())

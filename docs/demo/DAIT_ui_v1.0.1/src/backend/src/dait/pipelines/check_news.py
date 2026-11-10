"""수집한 SQLite DB를 변경하지 않고 1단계 결과를 확인합니다."""
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

from dait.core.config import NEWS_DB as DB_PATH
SOURCES = {"전자신문": "etnews.com", "TechCrunch": "techcrunch.com", "The Verge": "theverge.com"}


def main():
    if not DB_PATH.is_file():
        print(f"DB가 없습니다: {DB_PATH}\n먼저 수집 명령을 실행하세요.", file=sys.stderr)
        return 1
    try:
        with sqlite3.connect(DB_PATH.as_uri() + "?mode=ro", uri=True) as db:
            rows = db.execute("SELECT title, source, published_at, original_url FROM articles ORDER BY published_at DESC").fetchall()
            categories = db.execute("SELECT category, COUNT(*) FROM article_categories GROUP BY category ORDER BY category").fetchall()
            integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
    except sqlite3.Error as exc:
        print(f"DB 읽기 실패: {exc}", file=sys.stderr)
        return 1

    print(f"DB: {DB_PATH}\n기사 수: {len(rows)}개 / 목표 50개\nDB 무결성: {integrity}")
    print("\n출처별 기사 수:")
    for source, count in sorted(Counter(row[1] for row in rows).items()):
        print(f"  {source}: {count}개")
    for source in SOURCES:
        if not any(row[1] == source for row in rows):
            print(f"  {source}: 0개 (결과에 없음)")
    print("\n카테고리별 기사 수 (중복 가능):")
    for category, count in categories:
        print(f"  {category}: {count}개")
    print("\n최신 기사 10개 (UTC):")
    for title, source, published, url in rows[:10]:
        print(f"  {published} | {source} | {title}\n    {url}")
    invalid = []
    for title, source, published, url in rows:
        host = (urlparse(url).hostname or "").lower()
        domain = SOURCES.get(source, "")
        if not title or not published or not domain or not (host == domain or host.endswith("." + domain)):
            invalid.append(title)
    duplicate_urls = len(rows) - len({row[3] for row in rows})
    print(f"\n중복 URL: {duplicate_urls}개 / 제목·날짜·출처 링크 확인 필요: {len(invalid)}개")
    print("출처와 링크 형식 검사만 수행했습니다. 기사 실제 내용과 언론사 이용 조건은 별도 확인이 필요합니다.")
    return 0 if len(rows) == 50 and not invalid and not duplicate_urls and integrity == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())

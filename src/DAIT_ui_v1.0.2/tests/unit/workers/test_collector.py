import io
import sqlite3
from unittest.mock import Mock

import pytest

from backend.pipelines import collect_news as collector

RSS = b"""<rss><channel><item><title>AI news</title><link>https://example.com/a</link>
<pubDate>Fri, 06 Nov 2026 00:00:00 GMT</pubDate><description>AI technology</description>
</item><item><title>Other</title><link>https://evil.invalid/a</link>
<pubDate>Fri, 06 Nov 2026 00:00:00 GMT</pubDate></item></channel></rss>"""


# 기능: 피드 출처와 일치하는 기사 호스트만 허용 동작을 검증한다.
# 입력:
#   monkeypatch: 속성·환경을 임시 대체하는 pytest fixture.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-COL-001", "UT-COL-002")
def test_feed_only_accepts_matching_article_hosts(monkeypatch):
    monkeypatch.setattr(collector.urllib.request, "urlopen", lambda *a, **kw: io.BytesIO(RSS))
    articles = collector.collect_feed("test", "example.com", False, "https://example.com/feed")
    assert len(articles) == 1
    assert articles[0]["original_url"] == "https://example.com/a"


# 기능: 저장 실패 시 기존 기사 보존 동작을 검증한다.
# 입력:
#   article: 테스트용 기사 사전을 제공하는 fixture.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.extension
def test_failed_save_preserves_previous_articles(article):
    collector.save_articles([article])
    with pytest.raises(sqlite3.IntegrityError):
        collector.save_articles([article, article])
    with sqlite3.connect(collector.OUTPUT) as db:
        assert db.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 1


# 기능: 비공개 피드 호스트의 HTTP 접속 전 거부 요구사항 동작을 검증한다.
# 입력:
#   host: 검사할 피드 호스트.
#   monkeypatch: 속성·환경을 임시 대체하는 pytest fixture.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-COL-003")
@pytest.mark.spec_gap
@pytest.mark.parametrize("host", ["127.0.0.1", "10.0.0.1", "192.168.1.1"])
def test_document_private_feed_host_rejected_before_http(host, monkeypatch):
    fake = Mock(return_value=io.BytesIO(b"<rss><channel/></rss>"))
    monkeypatch.setattr(collector.urllib.request, "urlopen", fake)
    try:
        collector.collect_feed("test", host, False, f"https://{host}/feed")
    except ValueError:
        pass
    fake.assert_not_called()

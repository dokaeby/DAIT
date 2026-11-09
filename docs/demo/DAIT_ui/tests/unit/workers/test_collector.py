import io
import sqlite3
from unittest.mock import Mock

import pytest

from backend.pipelines import collect_news as collector

RSS = b"""<rss><channel><item><title>AI news</title><link>https://example.com/a</link>
<pubDate>Fri, 06 Nov 2026 00:00:00 GMT</pubDate><description>AI technology</description>
</item><item><title>Other</title><link>https://evil.invalid/a</link>
<pubDate>Fri, 06 Nov 2026 00:00:00 GMT</pubDate></item></channel></rss>"""


@pytest.mark.ut("UT-COL-001", "UT-COL-002")
def test_feed_only_accepts_matching_article_hosts(monkeypatch):
    monkeypatch.setattr(collector.urllib.request, "urlopen", lambda *a, **kw: io.BytesIO(RSS))
    articles = collector.collect_feed("test", "example.com", False, "https://example.com/feed")
    assert len(articles) == 1
    assert articles[0]["original_url"] == "https://example.com/a"


@pytest.mark.extension
def test_failed_save_preserves_previous_articles(article):
    collector.save_articles([article])
    with pytest.raises(sqlite3.IntegrityError):
        collector.save_articles([article, article])
    with sqlite3.connect(collector.OUTPUT) as db:
        assert db.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 1


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

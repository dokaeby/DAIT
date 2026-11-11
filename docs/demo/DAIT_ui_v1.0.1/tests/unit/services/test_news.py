import pytest

from backend import news
from backend.pipelines import collect_news
from frontend.views import render_cards, safe_url


@pytest.mark.ut("UT-HOME-002", "UT-HOME-004", "UT-HOME-006")
def test_list_preserves_three_articles_and_latest_order(article):
    articles = [
        {
            **article,
            "id": str(i),
            "title": "제목" * 100,
            "published_at": f"2026-11-0{i + 1}T00:00:00+00:00",
            "original_url": f"https://example.com/{i}",
        }
        for i in range(3)
    ]
    collect_news.save_articles(articles)
    rows = news.latest_articles()
    assert len(rows) == 3
    assert [r[0] for r in rows] == ["2", "1", "0"]
    assert rows[0][1] == "제목" * 100


@pytest.mark.ut("UT-HOME-005")
def test_order_deterministic(article):
    collect_news.save_articles(
        [{**article, "id": str(i), "original_url": f"https://example.com/{i}"} for i in range(12)]
    )
    orders = [[r[0] for r in news.latest_articles()] for _ in range(10)]
    assert len(orders[0]) == 10
    assert all(order == orders[0] for order in orders)


@pytest.mark.ut("UT-SEARCH-001", "UT-SEARCH-003", "UT-SEARCH-004", "UT-SEARCH-005", "UT-SEARCH-006")
@pytest.mark.parametrize(
    "query,count",
    [("openai", 1), ("OpenAI", 1), (" OpenAI ", 1), ("   ", 1), ("nonmatching", 0)],
)
def test_keyword_search(query, count, article):
    collect_news.save_articles([article])
    assert len(news.latest_articles(query)) == count


@pytest.mark.ut("UT-SEARCH-008", "UT-HOME-004", "UT-UI-005", "UT-LINK-003")
def test_card_escapes_html_and_keeps_safe_link():
    card = dict(
        id="n",
        title="<script>alert(1)</script>",
        source="source",
        date="date",
        categories="AI",
        foreign=False,
        url="https://example.com",
        summary=dict(status="generated", lines=["a", "b", "c"], message="note"),
    )
    html = render_cards([card], "", None)
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html
    assert 'rel="noopener noreferrer"' in html
    assert "data-detail" in html


@pytest.mark.ut("UT-LINK-001", "UT-LINK-002")
@pytest.mark.parametrize(
    "url",
    ["https://example.com", "javascript:alert(1)", "file:///C:/secret", "https:///bad"],
)
def test_safe_link(url):
    assert bool(safe_url(url)) == (url == "https://example.com")


@pytest.mark.ut("UT-LINK-002")
@pytest.mark.spec_gap
def test_document_rejects_http():
    assert safe_url("http://example.com") is None


@pytest.mark.ut("UT-HOME-001")
@pytest.mark.spec_gap
def test_document_excludes_unready_articles(article):
    collect_news.save_articles([article])
    assert news.latest_articles() == []  # Document requires READY-only public ranking.


@pytest.mark.ut("UT-SEARCH-002")
@pytest.mark.spec_gap
def test_document_searches_saved_ai_summary(article, runtime):
    collect_news.save_articles([article])
    runtime.worker.save_result(
        {**article, "summary": article["summary"][0]},
        "domestic",
        "generated",
        ["요약전용키워드", "둘째 문장", "셋째 문장"],
        "",
        "",
        0,
    )
    assert len(news.latest_articles("요약전용키워드")) == 1

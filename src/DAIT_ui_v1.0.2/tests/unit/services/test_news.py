import pytest

from backend import news
from backend.pipelines import collect_news
from frontend.views import render_cards, safe_url


# 기능: 기사 수 보존과 최신순 정렬 동작을 검증한다.
# 입력:
#   article: 테스트용 기사 사전을 제공하는 fixture.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
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


# 기능: 동일 시각 기사 정렬의 결정성 동작을 검증한다.
# 입력:
#   article: 테스트용 기사 사전을 제공하는 fixture.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-HOME-005")
def test_order_deterministic(article):
    collect_news.save_articles(
        [{**article, "id": str(i), "original_url": f"https://example.com/{i}"} for i in range(12)]
    )
    orders = [[r[0] for r in news.latest_articles()] for _ in range(10)]
    assert len(orders[0]) == 10
    assert all(order == orders[0] for order in orders)


# 기능: 키워드 조건별 검색 결과 동작을 검증한다.
# 입력:
#   query: 검색어 문자열.
#   count: 선택할 기사 개수.
#   article: 테스트용 기사 사전을 제공하는 fixture.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-SEARCH-001", "UT-SEARCH-003", "UT-SEARCH-004", "UT-SEARCH-005", "UT-SEARCH-006")
@pytest.mark.parametrize(
    "query,count",
    [("openai", 1), ("OpenAI", 1), (" OpenAI ", 1), ("   ", 1), ("nonmatching", 0)],
)
def test_keyword_search(query, count, article):
    collect_news.save_articles([article])
    assert len(news.latest_articles(query)) == count


# 기능: 카드 HTML 이스케이프와 안전한 원문 링크 동작을 검증한다.
# 입력: 없음.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
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


# 기능: 원문 링크 허용 여부 동작을 검증한다.
# 입력:
#   url: 조회할 피드 또는 검사할 URL.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-LINK-001", "UT-LINK-002")
@pytest.mark.parametrize(
    "url",
    ["https://example.com", "javascript:alert(1)", "file:///C:/secret", "https:///bad"],
)
def test_safe_link(url):
    assert bool(safe_url(url)) == (url == "https://example.com")


# 기능: HTTP 원문 링크 거부 요구사항 동작을 검증한다.
# 입력: 없음.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-LINK-002")
@pytest.mark.spec_gap
def test_document_rejects_http():
    assert safe_url("http://example.com") is None


# 기능: 준비되지 않은 기사 제외 요구사항 동작을 검증한다.
# 입력:
#   article: 테스트용 기사 사전을 제공하는 fixture.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-HOME-001")
@pytest.mark.spec_gap
def test_document_excludes_unready_articles(article):
    collect_news.save_articles([article])
    assert news.latest_articles() == []  # Document requires READY-only public ranking.


# 기능: 저장 AI 요약 검색 요구사항 동작을 검증한다.
# 입력:
#   article: 테스트용 기사 사전을 제공하는 fixture.
#   runtime: 격리된 DB·고정 시각·서비스 묶음.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
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

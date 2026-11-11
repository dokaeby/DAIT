from unittest.mock import Mock

import pytest

from dait.api.v1 import news_routes
from frontend.views import render_main


@pytest.mark.parametrize(
    "query,category,selected,recommended,expected_fallback",
    [
        ("", "", ("교육",), [], True),
        ("", "", ("교육",), [("matched",)], False),
        ("", "교육", ("교육",), [], False),
        ("검색어", "", ("교육",), [], False),
        ("", "", (), [], False),
    ],
)
def test_home_falls_back_only_for_empty_interest_feed(
    monkeypatch, query, category, selected, recommended, expected_fallback
):
    monkeypatch.setattr(news_routes, "user_interests", lambda user: selected)
    monkeypatch.setattr(news_routes, "display_nickname", lambda user: "사용자")
    monkeypatch.setattr(news_routes.news, "recommended_articles", lambda *args, **kwargs: recommended)
    latest = Mock(return_value=[("latest",)])
    monkeypatch.setattr(news_routes.news, "latest_articles", latest)
    page = Mock(return_value="ok")
    monkeypatch.setattr(news_routes.news, "page", page)

    news_routes.homepage(user="user", q=query, category=category, sort="latest", search_job="")

    assert page.call_args.kwargs["fallback"] is expected_fallback
    assert latest.call_count == int(expected_fallback)
    assert page.call_args.args[0] == ([("latest",)] if expected_fallback else recommended)


def test_fallback_message_is_inside_results_and_labels_latest_news():
    html = render_main([], "user", "", None, ("교육",), categories=("교육",), fallback=True)
    results = html.split('<section id="search-results"', 1)[1]
    assert "전체 최신 뉴스를 보여드리고 있어요" in results
    assert "최신 뉴스 0건" in results
    assert "표시할 최신 기사가 아직 없습니다" in results

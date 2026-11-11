"""기존 저장 결과의 멱등 이식과 실제 목록·상세 계약을 검증한다."""

from datetime import UTC, datetime

from pydantic import HttpUrl

from dait.core.config import Settings
from dait.main import create_app
from dait.repositories.db import transaction
from dait.repositories.legacy_news_repository import insert_result
from dait.schemas.legacy_news import LegacyNews
from support import as_client


def test_saved_results_produce_ten_cards_without_duplicates(settings: Settings) -> None:
    """같은 기사를 두 번 넣어도 카드와 상세의 동일성이 유지된다."""
    for _ in range(2):
        with transaction(settings.database_url) as conn:
            for index in range(12):
                insert_result(
                    conn,
                    LegacyNews(
                        id=f"legacy-{index}",
                        canonical_url=HttpUrl(f"https://example.com/news/{index}"),
                        title=f"실제 저장 형식 {index}",
                        source_name="샘플 출처",
                        category="AI",
                        published_at=datetime.now(UTC),
                        summary_lines=["요약1", "요약2", "요약3"],
                    ),
                )
    client = as_client(create_app(settings))
    result = client.request("GET", "/v1/news", params={"page_size": "10"}).json()
    assert len(result["items"]) == 10
    assert result["meta"]["total_visible"] == 10
    assert result["page"]["has_more"] is False
    assert result["page"]["next_cursor"] is None
    assert (
        client.request("GET", "/v1/news", params={"page_size": "50"}).json()["items"]
        == result["items"]
    )
    assert client.request("GET", "/v1/news", params={"cursor": "eyJvIjoxMH0="}).status_code == 422
    item = result["items"][0]
    detail = client.request("GET", "/v1/news/" + item["id"]).json()
    assert detail["content"]["summary_lines"] == item["summary_lines"]
    assert detail["source"]["original_url"] == item["original_url"]

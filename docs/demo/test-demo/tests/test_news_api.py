import json

import pytest
from app.database import initialize_database
from app.db_common import connect
from app.main import create_app

from tests.client import ASGIClient


# 입력: `tmp_path`.
# 출력: 임시 DB 경로와 테스트용 ASGI 클라이언트의 튜플.
# 동작: 격리 DB를 초기화하고 테스트용 ASGI 클라이언트를 생성한다.
def make_client(tmp_path):
    db_path = tmp_path / "dait.db"
    initialize_database(db_path)
    return db_path, ASGIClient(create_app(db_path=db_path))


# 입력: `tmp_path`.
# 출력: 반환값 없음. assertion 실패 시 테스트가 실패한다.
# 동작: 해당 이름의 테스트 시나리오와 기대 결과를 검증한다.
def test_health_and_readiness(tmp_path):
    _, client = make_client(tmp_path)

    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").json() == {
        "status": "ready",
        "dependencies": {"database": "ok", "redis": "not_used"},
    }


# 입력: `tmp_path`.
# 출력: 반환값 없음. assertion 실패 시 테스트가 실패한다.
# 동작: 해당 이름의 테스트 시나리오와 기대 결과를 검증한다.
def test_news_default_rank_and_status_filter(tmp_path):
    db_path, client = make_client(tmp_path)
    with connect(db_path) as connection:
        connection.execute(
            "UPDATE content_results SET status = 'FAILED' WHERE news_id = 'news_anthropic_002'"
        )

    response = client.get("/v1/news")

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["items"]] == ["news_openai_001", "news_arxiv_003"]
    assert [item["rank"] for item in body["items"]] == [1, 2]
    assert [item["processing_status"] for item in body["items"]] == ["READY", "INSUFFICIENT"]
    assert body["page"] == {"next_cursor": None, "has_more": False}
    assert body["meta"]["rank_basis"] == ["processing_status", "source_priority", "published_at"]


# 입력: `tmp_path`.
# 출력: 반환값 없음. assertion 실패 시 테스트가 실패한다.
# 동작: 해당 이름의 테스트 시나리오와 기대 결과를 검증한다.
def test_news_latest_search_and_empty_result(tmp_path):
    _, client = make_client(tmp_path)

    latest = client.get("/v1/news", params={"sort": "latest"}).json()["items"]
    title_match = client.get("/v1/news", params={"q": "anthropic"}).json()["items"]
    summary_match = client.get("/v1/news", params={"q": "권한 제한"}).json()["items"]
    empty = client.get("/v1/news", params={"q": "존재하지않는검색어"}).json()["items"]

    assert [item["id"] for item in latest] == [
        "news_openai_001",
        "news_anthropic_002",
        "news_arxiv_003",
    ]
    assert [item["id"] for item in title_match] == ["news_anthropic_002"]
    assert [item["id"] for item in summary_match] == ["news_anthropic_002"]
    assert empty == []


# 입력: `tmp_path`.
# 출력: 반환값 없음. assertion 실패 시 테스트가 실패한다.
# 동작: 해당 이름의 테스트 시나리오와 기대 결과를 검증한다.
def test_news_validation_rejects_bad_query(tmp_path):
    _, client = make_client(tmp_path)

    for params in (
        {"category": "POLITICS"},
        {"sort": "popular"},
        {"page_size": 0},
        {"page_size": 51},
        {"cursor": "unexpected"},
        {"q": "x" * 101},
    ):
        response = client.get("/v1/news", params=params)
        assert response.status_code == 422
        assert response.json()["code"] == "VALIDATION_ERROR"


# 입력: `tmp_path`.
# 출력: 반환값 없음. assertion 실패 시 테스트가 실패한다.
# 동작: 해당 이름의 테스트 시나리오와 기대 결과를 검증한다.
def test_news_detail_and_missing_id(tmp_path):
    _, client = make_client(tmp_path)

    response = client.get("/v1/news/news_openai_001")
    missing = client.get("/v1/news/news_missing")

    assert response.status_code == 200
    body = response.json()
    assert body["article"]["id"] == "news_openai_001"
    assert body["article"]["source_name"] == "OpenAI Newsroom"
    assert len(body["content"]["summary_lines"]) == 3
    assert body["source"]["original_url"].startswith("https://")
    assert [item["id"] for item in body["related_news"]] == [
        "news_anthropic_002",
        "news_arxiv_003",
    ]
    assert missing.status_code == 404
    assert missing.json()["code"] == "NEWS_NOT_FOUND"


# 입력: `tmp_path`.
# 출력: 반환값 없음. assertion 실패 시 테스트가 실패한다.
# 동작: 해당 이름의 테스트 시나리오와 기대 결과를 검증한다.
def test_malformed_content_returns_generalized_error(tmp_path):
    db_path, client = make_client(tmp_path)
    with connect(db_path) as connection:
        connection.execute("PRAGMA ignore_check_constraints = ON")
        connection.execute(
            "UPDATE content_results SET summary_lines = ? WHERE news_id = ?",
            ("not-json", "news_openai_001"),
        )

    response = client.get("/v1/news")

    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "INTERNAL_ERROR"
    assert "json" not in body["message"].lower()
    assert "traceback" not in response.text.lower()


@pytest.mark.parametrize(
    "stored_value",
    [json.dumps({}), json.dumps(None), json.dumps("summary"), json.dumps(["one", 2, "three"])],
)
@pytest.mark.parametrize("endpoint", ["/v1/news", "/v1/news/news_openai_001"])
# 입력: `tmp_path`, `stored_value`, `endpoint`.
# 출력: 반환값 없음. assertion 실패 시 테스트가 실패한다.
# 동작: 해당 이름의 테스트 시나리오와 기대 결과를 검증한다.
def test_wrong_summary_shape_returns_generalized_error(tmp_path, stored_value, endpoint):
    db_path, client = make_client(tmp_path)
    with connect(db_path) as connection:
        connection.execute(
            "UPDATE content_results SET summary_lines = ? WHERE news_id = ?",
            (stored_value, "news_openai_001"),
        )

    response = client.get(endpoint)

    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_ERROR"


# 입력: `tmp_path`.
# 출력: 반환값 없음. assertion 실패 시 테스트가 실패한다.
# 동작: 해당 이름의 테스트 시나리오와 기대 결과를 검증한다.
def test_unknown_error_does_not_expose_sql_or_traceback(tmp_path):
    db_path, client = make_client(tmp_path)
    moved_path = tmp_path / "moved.db"
    db_path.rename(moved_path)

    response = client.get("/v1/news")

    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_ERROR"
    assert "sql" not in response.text.lower()
    assert "traceback" not in response.text.lower()

from app.database import initialize_database
from app.main import create_app
from tests.client import ASGIClient


def make_client(tmp_path):
    db_path = tmp_path / "dait.db"
    initialize_database(db_path)
    return ASGIClient(create_app(db_path=db_path))


def test_three_pages_and_assets_are_served(tmp_path):
    client = make_client(tmp_path)

    responses = {
        path: client.get(path)
        for path in ("/", "/detail.html?id=news_openai_001", "/settings.html", "/styles.css", "/app.js")
    }

    assert all(response.status_code == 200 for response in responses.values())
    assert all("text/html" in responses[path].headers["content-type"] for path in ("/", "/detail.html?id=news_openai_001", "/settings.html"))
    assert "text/css" in responses["/styles.css"].headers["content-type"]
    assert "javascript" in responses["/app.js"].headers["content-type"]


def test_pages_have_expected_accessible_regions(tmp_path):
    client = make_client(tmp_path)

    main = client.get("/").text
    detail = client.get("/detail.html").text
    settings = client.get("/settings.html").text

    for page, name in ((main, "main"), (detail, "detail"), (settings, "settings")):
        assert f'data-page="{name}"' in page
        assert "<main" in page
        assert "<nav" in page
        assert 'aria-live="polite"' in page
        assert 'src="/app.js"' in page
    assert 'id="news-list"' in main
    assert 'id="summary-list"' in detail
    assert 'id="settings-form"' in settings


def test_frontend_calls_required_api_endpoints(tmp_path):
    script = make_client(tmp_path).get("/app.js").text

    for endpoint in (
        "/v1/news",
        "/v1/me/settings",
        "/v1/me/schedules",
    ):
        assert endpoint in script
    for function_name in ("loadNews", "loadDetail", "loadSettings", "saveSettings"):
        assert f"function {function_name}" in script


def test_frontend_contains_loading_error_retry_and_clipboard_fallback(tmp_path):
    client = make_client(tmp_path)
    pages = client.get("/").text + client.get("/detail.html").text + client.get("/settings.html").text
    script = client.get("/app.js").text

    assert "불러오는 중" in script
    assert "다시 시도" in pages
    assert "navigator.clipboard" in script
    assert "복사하지 못했습니다" in script
    assert 'id="retry-button"' in pages

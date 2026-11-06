import json
import subprocess
from pathlib import Path

from app.database import initialize_database
from app.main import create_app

from tests.client import ASGIClient


# 입력: `tmp_path`.
# 출력: 테스트용 ASGI 클라이언트.
# 동작: 격리 DB를 초기화하고 테스트용 ASGI 클라이언트를 생성한다.
def make_client(tmp_path):
    db_path = tmp_path / "dait.db"
    initialize_database(db_path)
    return ASGIClient(create_app(db_path=db_path))


# 입력: `tmp_path`.
# 출력: 반환값 없음. assertion 실패 시 테스트가 실패한다.
# 동작: 해당 이름의 테스트 시나리오와 기대 결과를 검증한다.
def test_three_pages_and_assets_are_served(tmp_path):
    client = make_client(tmp_path)

    responses = {
        path: client.get(path)
        for path in (
            "/",
            "/detail.html?id=news_openai_001",
            "/settings.html",
            "/styles.css",
            "/app.js",
        )
    }

    assert all(response.status_code == 200 for response in responses.values())
    assert all(
        "text/html" in responses[path].headers["content-type"]
        for path in ("/", "/detail.html?id=news_openai_001", "/settings.html")
    )
    assert "text/css" in responses["/styles.css"].headers["content-type"]
    assert "javascript" in responses["/app.js"].headers["content-type"]


# 입력: `tmp_path`.
# 출력: 반환값 없음. assertion 실패 시 테스트가 실패한다.
# 동작: 해당 이름의 테스트 시나리오와 기대 결과를 검증한다.
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


# 입력: `tmp_path`.
# 출력: 반환값 없음. assertion 실패 시 테스트가 실패한다.
# 동작: 해당 이름의 테스트 시나리오와 기대 결과를 검증한다.
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


# 입력: `tmp_path`.
# 출력: 반환값 없음. assertion 실패 시 테스트가 실패한다.
# 동작: 해당 이름의 테스트 시나리오와 기대 결과를 검증한다.
def test_frontend_contains_loading_error_retry_and_clipboard_fallback(tmp_path):
    client = make_client(tmp_path)
    pages = (
        client.get("/").text + client.get("/detail.html").text + client.get("/settings.html").text
    )
    script = client.get("/app.js").text

    assert "불러오는 중" in script
    assert "다시 시도" in pages
    assert "navigator.clipboard" in script
    assert "복사하지 못했습니다" in script
    assert 'id="retry-button"' in pages


# 입력: 없음.
# 출력: 반환값 없음. assertion 실패 시 테스트가 실패한다.
# 동작: 해당 이름의 테스트 시나리오와 기대 결과를 검증한다.
def test_schedule_action_reports_failure_and_does_not_run_success():
    helper_path = Path(__file__).resolve().parents[1] / "public" / "schedule-actions.js"
    program = f"""
      const {{ performScheduleAction }} = require({json.dumps(str(helper_path))});
      (async () => {{
        const events = [];
        const result = await performScheduleAction(
          async () => {{ throw new Error('network down'); }},
          async () => events.push('success'),
          (error) => events.push(error.message)
        );
        console.log(JSON.stringify({{ result, events }}));
      }})();
    """

    result = subprocess.run(["node", "-e", program], capture_output=True, text=True)

    assert result.returncode == 0
    assert json.loads(result.stdout) == {"result": False, "events": ["network down"]}

"""앱 조립 결과 테스트: 헬스체크, request_id, 오류 형식, 보안 헤더, 모드별 문서 경로."""

from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

from dait.core.config import AppEnv, Settings
from dait.core.errors import ErrorResponse
from dait.main import create_app
from dait.schemas.health import HealthResponse, KeepAliveResponse
from support import HttpClient, as_client

_SECRET_TEXT = "password=hunter2 C:/내부경로"  # noqa: S105 - 노출 여부 확인용 가짜 값


def make_client(
    tmp_path: Path,
    env: AppEnv = AppEnv.RELEASE,
    db: str = "ok.db",
    routes: Mapping[str, Callable[..., object]] | None = None,
) -> HttpClient:
    """임시 DB를 쓰는 앱의 테스트 클라이언트를 만든다(서버 오류도 응답으로 받는다)."""
    settings = Settings(app_env=env, database_url=f"sqlite:///{tmp_path / db}")
    app = create_app(settings)
    for path, endpoint in (routes or {}).items():
        app.add_api_route(path, endpoint)
    return as_client(app)


def test_healthz_ok(tmp_path: Path) -> None:
    """/healthz가 200과 ok를 돌려준다."""
    response = make_client(tmp_path).request("GET", "/healthz")
    assert response.status_code == 200
    assert HealthResponse.model_validate_json(response.text).status == "ok"


def test_readyz_ok(tmp_path: Path) -> None:
    """/readyz가 DB가 열리면 200과 ready를 돌려준다."""
    response = make_client(tmp_path).request("GET", "/readyz")
    assert response.status_code == 200
    assert HealthResponse.model_validate_json(response.text).status == "ready"


def test_readyz_db_down_returns_503_without_path(tmp_path: Path) -> None:
    """DB가 열리지 않으면 503 NOT_READY이고 경로·sqlite 문구를 노출하지 않는다."""
    response = make_client(tmp_path, db="no_dir/x.db").request("GET", "/readyz")
    assert response.status_code == 503
    error = ErrorResponse.model_validate_json(response.text)
    assert error.code == "NOT_READY"
    assert "no_dir" not in response.text
    assert "sqlite" not in response.text.lower()


def test_keepalive_ok_even_when_db_down(tmp_path: Path) -> None:
    """/v1/internal/keepalive는 DB가 죽어 있어도 200을 돌려준다(스핀다운 방지용)."""
    response = make_client(tmp_path, db="no_dir/x.db").request("GET", "/v1/internal/keepalive")
    assert response.status_code == 200
    body = KeepAliveResponse.model_validate_json(response.text)
    assert body.status == "ok"
    assert body.service == "dait"
    assert body.time


def test_request_id_in_header_and_body(tmp_path: Path) -> None:
    """오류 본문의 request_id가 응답 헤더와 같다."""
    response = make_client(tmp_path).request("GET", "/없는경로")
    error = ErrorResponse.model_validate_json(response.text)
    assert error.request_id == response.headers["X-Request-ID"]
    assert error.code == "HTTP_404"


def test_valid_request_id_is_kept(tmp_path: Path) -> None:
    """형식이 맞는 X-Request-ID는 그대로 쓴다."""
    response = make_client(tmp_path).request("GET", "/healthz", headers={"X-Request-ID": "abc-123"})
    assert response.headers["X-Request-ID"] == "abc-123"


@pytest.mark.parametrize("bad", ["a b", "x" * 65, "id\r\nSet-Cookie: x", "<script>"])
def test_bad_request_id_is_replaced(tmp_path: Path, bad: str) -> None:
    """위험한 X-Request-ID는 버리고 새로 만든다."""
    response = make_client(tmp_path).request(
        "GET", "/healthz", headers={"X-Request-ID": bad.split("\r")[0]}
    )
    assert response.headers["X-Request-ID"] != bad
    assert len(response.headers["X-Request-ID"]) <= 64


def test_security_headers_present(tmp_path: Path) -> None:
    """보안 헤더가 응답에 붙는다."""
    headers = make_client(tmp_path).request("GET", "/healthz").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert "max-age" in headers["Strict-Transport-Security"]
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert headers["X-Frame-Options"] == "DENY"


def test_release_has_no_docs(tmp_path: Path) -> None:
    """release에서는 docs/redoc/openapi가 404다."""
    client = make_client(tmp_path)
    assert client.request("GET", "/docs").status_code == 404
    assert client.request("GET", "/redoc").status_code == 404
    assert client.request("GET", "/openapi.json").status_code == 404


def test_debug_has_docs(tmp_path: Path) -> None:
    """debug에서는 openapi.json이 열린다."""
    assert make_client(tmp_path, AppEnv.DEBUG).request("GET", "/openapi.json").status_code == 200


def test_unhandled_error_is_generic_500(tmp_path: Path) -> None:
    """처리되지 않은 예외는 내부 정보 없이 500으로 나간다."""

    def boom() -> None:
        raise RuntimeError(_SECRET_TEXT)

    response = make_client(tmp_path, routes={"/boom": boom}).request("GET", "/boom")
    assert response.status_code == 500
    assert ErrorResponse.model_validate_json(response.text).code == "INTERNAL_ERROR"
    assert "hunter2" not in response.text
    assert "Traceback" not in response.text
    assert "X-Request-ID" in response.headers


def test_validation_error_does_not_echo_input(tmp_path: Path) -> None:
    """검증 오류는 입력값을 되돌려 주지 않는다."""

    def echo(number: int) -> int:
        return number

    response = make_client(tmp_path, routes={"/echo": echo}).request(
        "GET", "/echo", params={"number": "SECRET-XYZ"}
    )
    assert response.status_code == 422
    assert ErrorResponse.model_validate_json(response.text).code == "VALIDATION_ERROR"
    assert "SECRET-XYZ" not in response.text


def test_oversized_body_returns_413(tmp_path: Path) -> None:
    """본문이 1MiB를 넘으면 413이다."""
    response = make_client(tmp_path).request("POST", "/healthz", content=b"x" * 1_048_577)
    assert response.status_code == 413
    assert ErrorResponse.model_validate_json(response.text).code == "PAYLOAD_TOO_LARGE"


def test_cors_allows_only_listed_origin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """허용 목록의 출처에만 CORS 헤더가 붙는다."""
    monkeypatch.setenv("CORS_ORIGINS", '["https://dait.example.com"]')
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'c.db'}")
    client = as_client(create_app(Settings()))
    ok = client.request("GET", "/healthz", headers={"Origin": "https://dait.example.com"})
    bad = client.request("GET", "/healthz", headers={"Origin": "https://evil.example.com"})
    assert ok.headers["access-control-allow-origin"] == "https://dait.example.com"
    assert "access-control-allow-origin" not in bad.headers

"""예약 검색 화면 브라우저 자동화 공통 준비 (Chromium·WebKit=Safari 엔진).

임시 sqlite DB에 마이그레이션을 적용하고 기사 3건을 넣은 뒤 실제 서버(uvicorn)를 띄운다.
실행: .venv/bin/python -m pytest tests/frontend/ui -q
(최초 1회: python -m playwright install chromium webkit)
"""

import json
import os
import secrets
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Generator, Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, Playwright, sync_playwright

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "src" / "backend"
TICK_SECRET = "ui-tick-secret-" + secrets.token_hex(8)
PASSWORD = "Str0ng!Passw0rd-xyz"  # noqa: S105 - 임시 DB에만 있는 테스트 계정 비밀번호
NOW = "2026-01-01T00:00:00+00:00"


@dataclass(frozen=True)
class Server:
    base: str
    db_path: Path


def _seed(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO sources (id, name, kind, base_url, priority, enabled, created_at, "
            "updated_at) VALUES ('src1', '테스트통신', 'RSS', 'https://example.com/feed', "
            "10, 1, ?, ?)",
            (NOW, NOW),
        )
        for index, title in enumerate(["HBM 증산 경쟁", "AI 에이전트 공개", "클라우드 요금"]):
            news_id = f"news{index:02d}"
            conn.execute(
                "INSERT INTO news (id, source_id, title, canonical_url, published_at, "
                "collected_at, category, original_language, created_at) "
                "VALUES (?, 'src1', ?, ?, ?, ?, 'AI', 'ko', ?)",
                (
                    news_id,
                    title,
                    f"https://example.com/a{index}",
                    f"2026-01-0{index + 1}T00:00:00+00:00",
                    NOW,
                    NOW,
                ),
            )
            conn.execute(
                "INSERT INTO content_results (news_id, summary_lines, status, updated_at) "
                "VALUES (?, '[\"요약\"]', 'READY', ?)",
                (news_id, NOW),
            )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture(scope="session")
def server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Server]:
    tmp = tmp_path_factory.mktemp("dait-ui")
    db_path = tmp / "ui.db"
    env = {
        **os.environ,
        "APP_ENV": "debug",
        "DATABASE_URL": f"sqlite:///{db_path}",
        "JWT_SECRET": "ui-test-jwt-" + secrets.token_hex(16),
        "SCHEDULER_TICK_SECRET": TICK_SECRET,
        "PYTHONPATH": "src",
    }
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND,
        env=env,
        check=True,
        capture_output=True,
    )
    _seed(db_path)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = int(sock.getsockname()[1])
    process = subprocess.Popen(  # noqa: S603 - 고정된 인자로 로컬 테스트 서버 실행
        [sys.executable, "-m", "uvicorn", "dait.main:create_app", "--factory", "--port", str(port)],
        cwd=BACKEND,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                with urllib.request.urlopen(base + "/healthz", timeout=1):  # noqa: S310 - 로컬
                    break
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.2)
        yield Server(base, db_path)
    finally:
        process.terminate()
        process.wait(timeout=10)


@pytest.fixture(scope="session")
def playwright() -> Iterator[Playwright]:
    with sync_playwright() as instance:
        yield instance


@pytest.fixture(scope="session", params=["chromium", "webkit"])
def browser(request: pytest.FixtureRequest, playwright: Playwright) -> Iterator[Browser]:
    launched = getattr(playwright, str(request.param)).launch()
    yield launched
    launched.close()


def _post(url: str, body: dict[str, object], headers: dict[str, str] | None = None) -> dict:
    request = urllib.request.Request(  # noqa: S310 - 로컬 테스트 서버
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
        return json.loads(response.read() or b"{}")


def tick(server: Server, now: str) -> dict:
    """cron이 보내는 것과 같은 tick을 보낸다."""
    return _post(
        server.base + "/v1/internal/scheduler/tick",
        {"now": now},
        {"Authorization": f"Bearer {TICK_SECRET}"},
    )


@pytest.fixture
def member(server: Server, browser: Browser) -> Generator[Page]:
    """새 회원으로 가입·로그인한 페이지(토큰은 app.js와 같은 localStorage 키에 넣는다)."""
    email = f"ui{secrets.token_hex(4)}@example.com"
    signup = _post(
        server.base + "/v1/auth/signup",
        {
            "email": email,
            "password": PASSWORD,
            "password_confirm": PASSWORD,
            "terms_accepted": True,
        },
    )
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.goto(server.base + "/")
    page.evaluate(
        "t => { localStorage.setItem('dait_access_token', t.access_token);"
        " localStorage.setItem('dait_refresh_token', t.refresh_token); }",
        signup["tokens"],
    )
    yield page
    context.close()

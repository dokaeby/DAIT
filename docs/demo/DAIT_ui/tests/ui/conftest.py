"""KAN-10 UI 자동화 테스트 환경 (14_UI_자동화_test_procedure 기준, Playwright + pytest).

실제 data/ 폴더를 쓰지 않도록 임시 프로젝트 루트(DAIT_PROJECT_ROOT)에 고정 기사 seed와 빈 회원 DB를 만들고,
그 위에서 FastAPI 서버를 띄워 브라우저로 조작합니다.
실행: python -m pytest tests/ui -q   (최초 1회: python -m playwright install chromium)
"""

import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Generator
from pathlib import Path

import pytest
from playwright.sync_api import BrowserContext, Page

PROJECT = Path(__file__).resolve().parents[2]
ASSETS = Path("src/frontend/src/frontend/assets")
UI_PASSWORD = "ui-test-pass"  # 임시 DB에만 존재하는 테스트 계정 비밀번호

SEED_ARTICLES = [
    ("ui_001", "HBM 증산 경쟁 본격화", ["반도체"], "2026-11-08T22:00:00+00:00", "HBM 공급 확대"),
    (
        "ui_002",
        "새 AI 에이전트 공개",
        ["인공지능"],
        "2026-11-08T21:00:00+00:00",
        "에이전트 기능 소개",
    ),
    ("ui_003", "클라우드 요금 개편", ["클라우드"], "2026-11-08T20:00:00+00:00", "요금제 변경"),
    ("ui_004", "보안 패치 긴급 배포", ["보안"], "2026-11-08T19:00:00+00:00", "취약점 대응"),
]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _seed(root: Path, env: dict[str, str]) -> None:
    (root / ASSETS).parent.mkdir(parents=True)
    shutil.copytree(PROJECT / ASSETS, root / ASSETS)
    articles = [
        dict(
            id=i,
            title=t,
            source="UI 테스트 출처",
            published_at=p,
            summary=[s],
            content=s,
            original_url=f"https://example.com/ui/{i}",
            is_foreign=False,
            categories=c,
        )
        for i, t, c, p, s in SEED_ARTICLES
    ]
    code = (
        "import json,sys; from dait.pipelines import collect_news; "
        "collect_news.save_articles(json.loads(sys.stdin.read()))"
    )
    subprocess.run(
        [sys.executable, "-c", code],
        input=json.dumps(articles),
        text=True,
        env=env,
        cwd=PROJECT,
        check=True,
    )


@pytest.fixture(scope="session")
def server_url(tmp_path_factory: pytest.TempPathFactory) -> Generator[str]:
    root = tmp_path_factory.mktemp("dait-ui-root")
    env = {
        **os.environ,
        "DAIT_PROJECT_ROOT": str(root),
        "PYTHONPATH": os.pathsep.join([str(PROJECT), str(PROJECT / "src/backend/src")]),
    }
    _seed(root, env)
    port = _free_port()
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "dait.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=PROJECT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                with urllib.request.urlopen(url + "/", timeout=1):
                    break
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.2)
        else:
            raise RuntimeError("UI 테스트 서버가 시작되지 않았습니다.")
        yield url
    finally:
        process.terminate()
        process.wait(timeout=10)


@pytest.fixture(scope="session")
def base_url(server_url: str) -> str:
    return server_url


def sign_in(context: BrowserContext, base_url: str) -> str:
    """테스트마다 새 회원을 만들어 서로 영향을 주지 않게 합니다."""
    user = "ui" + secrets.token_hex(4)
    form = {"user": user, "password": UI_PASSWORD, "password_confirm": UI_PASSWORD}
    assert context.request.post(base_url + "/signup", form=form).status == 201
    login = context.request.post(
        base_url + "/login", form={"user": user, "password": UI_PASSWORD}, max_redirects=0
    )
    assert login.status == 303
    return user


@pytest.fixture
def member_page(page: Page, base_url: str) -> Page:
    sign_in(page.context, base_url)
    return page

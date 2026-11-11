"""Per-test DBs, deterministic IDs/clock, and deny-by-default I/O boundaries."""

import itertools
import json
import platform
import smtplib
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import types
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import unquote, urlsplit

import pytest

_results = {}


# 기능: 단위 테스트 역순 실행 옵션을 등록한다.
# 입력:
#   parser: pytest 명령행 옵션 파서.
# 출력: None.
def pytest_addoption(parser):
    parser.addoption("--reverse-unit-order", action="store_true", default=False)


# 기능: 실행 순서를 조정하고 테스트별 문서 ID 추적 정보를 등록한다.
# 입력:
#   items: 수집된 pytest 테스트 목록.
# 출력: None. 테스트 목록과 추적 사전을 갱신한다.
def pytest_collection_modifyitems(items):
    if items and items[0].config.getoption("--reverse-unit-order"):
        items.reverse()
    for item in items:
        ids = [value for mark in item.iter_markers("ut") for value in mark.args]
        _results[item.nodeid] = {
            "nodeid": item.nodeid,
            "ut_ids": ids,
            "spec_gap": item.get_closest_marker("spec_gap") is not None,
            "outcome": "not_run",
        }
        item.user_properties.append(("UT_IDS", ",".join(ids)))


# 기능: 실행 단계의 결과와 실패 내용을 추적 사전에 기록한다.
# 입력:
#   report: pytest 실행 단계 보고서.
# 출력: None.
def pytest_runtest_logreport(report):
    if report.when == "call" or report.failed:
        _results[report.nodeid]["outcome"] = (
            "error" if report.failed and report.when != "call" else report.outcome
        )
        if report.failed:
            _results[report.nodeid]["failure"] = str(report.longrepr)


# 기능: 세션에서 수집한 테스트 결과를 JSON 파일로 저장한다.
# 입력:
#   session: pytest 세션.
# 출력: None. .tmp/test-results/cases.json을 기록한다.
def pytest_sessionfinish(session):
    output = session.config.rootpath / ".tmp" / "test-results"
    output.mkdir(parents=True, exist_ok=True)
    (output / "cases.json").write_text(
        json.dumps(list(_results.values()), ensure_ascii=False, indent=2), encoding="utf-8"
    )


# 기능: 임시 DB·고정 시각을 제공하고 외부 I/O와 실제 DB 접근을 차단한다.
# 입력:
#   tmp_path: 테스트별 임시 디렉터리.
#   monkeypatch: 속성·환경을 임시 대체하는 pytest fixture.
# 출력: 격리된 실행 환경 묶음을 yield하고 종료 시 캐시를 정리한다.
@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path, monkeypatch):
    # 기능: 단위 테스트에서 금지된 외부 I/O 시도를 차단한다.
    # 입력:
    #   args: 명령행 옵션 객체 또는 전달할 위치 인자.
    #   kwargs: 전달할 키워드 인자.
    # 출력: 반환 없이 AssertionError를 발생시킨다.
    def deny(*args, **kwargs):
        raise AssertionError("Unit test attempted forbidden external I/O")

    # Windows asyncio uses an internal loopback socketpair for event-loop wakeup.
    # Permit only its construction, never application HTTP or arbitrary connects.
    internal_pair = threading.local()
    original_pair = socket.socketpair

    # 기능: 이벤트 루프 내부 소켓 쌍 생성 중에만 네트워크 예외를 허용한다.
    # 입력:
    #   args: 명령행 옵션 객체 또는 전달할 위치 인자.
    #   kwargs: 전달할 키워드 인자.
    # 출력: 내부 통신용 소켓 쌍.
    def make_pair(*args, **kwargs):
        internal_pair.active = True
        try:
            return original_pair(*args, **kwargs)
        finally:
            internal_pair.active = False

    for name in ("connect", "connect_ex", "bind", "listen"):
        original = getattr(socket.socket, name)

        # 기능: 내부 소켓 쌍 생성 외의 소켓 연결·대기를 차단한다.
        # 입력:
        #   self: 현재 인스턴스.
        #   args: 명령행 옵션 객체 또는 전달할 위치 인자.
        #   _original: 대체 전 소켓 메서드.
        #   kwargs: 전달할 키워드 인자.
        # 출력: 허용된 원래 메서드의 결과 또는 AssertionError.
        def guarded_socket(self, *args, _original=original, **kwargs):
            if getattr(internal_pair, "active", False):
                return _original(self, *args, **kwargs)
            return deny()

        monkeypatch.setattr(socket.socket, name, guarded_socket)
    monkeypatch.setattr(socket, "socketpair", make_pair)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)
    monkeypatch.setattr(urllib.request, "urlopen", deny)
    monkeypatch.setattr(smtplib, "SMTP", deny)
    monkeypatch.setattr(smtplib, "SMTP_SSL", deny)
    monkeypatch.setattr(subprocess, "Popen", deny)
    monkeypatch.setattr(platform, "machine", lambda: "AMD64")
    for name, attributes in (
        ("huggingface_hub", ["snapshot_download"]),
        ("sentence_transformers", ["SentenceTransformer"]),
    ):
        module = types.ModuleType(name)
        for attribute in attributes:
            setattr(module, attribute, deny)
        monkeypatch.setitem(sys.modules, name, module)

    original_connect = sqlite3.connect

    # 기능: 테스트 임시 폴더 또는 메모리 DB에만 SQLite 연결을 허용한다.
    # 입력:
    #   database: 접속할 SQLite 경로 또는 메모리 DB 이름.
    #   args: 명령행 옵션 객체 또는 전달할 위치 인자.
    #   kwargs: 전달할 키워드 인자.
    # 출력: sqlite3.Connection 또는 범위 밖 접근 시 AssertionError.
    def guarded_connect(database, *args, **kwargs):
        raw = str(database)
        if raw != ":memory:":
            candidate = unquote(urlsplit(raw).path) if raw.startswith("file:") else raw
            if candidate.startswith("/") and len(candidate) > 2 and candidate[2] == ":":
                candidate = candidate[1:]
            resolved = Path(candidate).resolve()
            if not resolved.is_relative_to(tmp_path.resolve()):
                raise AssertionError("Unit test DB access outside per-test temporary directory")
        return original_connect(database, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", guarded_connect)
    temporary_directory = tempfile.TemporaryDirectory

    # 기능: 테스트용 임시 폴더가 현재 테스트 폴더 안에 만들어지도록 한다.
    # 입력:
    #   args: 명령행 옵션 객체 또는 전달할 위치 인자.
    #   kwargs: 전달할 키워드 인자.
    # 출력: TemporaryDirectory 컨텍스트 관리자.
    def nested_temporary_directory(*args, **kwargs):
        kwargs.setdefault("dir", tmp_path)
        return temporary_directory(*args, **kwargs)

    monkeypatch.setattr(tempfile, "TemporaryDirectory", nested_temporary_directory)
    from backend import news, paths, users
    from backend.pipelines import (
        collect_news,
    )
    from backend.services import summary_worker

    mapping = {
        "NEWS_DB": tmp_path / "news.db",
        "DB": tmp_path / "news.db",
        "DB_PATH": tmp_path / "news.db",
        "OUTPUT": tmp_path / "news.db",
        "SUMMARY_DB": tmp_path / "summary.db",
        "RESULT_DB": tmp_path / "summary.db",
        "TRANSLATION_DB": tmp_path / "foreign.db",
        "USER_DB": tmp_path / "users.db",
        "INDEX_DB": tmp_path / "index.db",
        "QUEUE_DB": tmp_path / "queue.db",
        "DATA_DIR": tmp_path,
        "REPORTS_DIR": tmp_path / "reports",
        "BASE": tmp_path / "reports",
    }
    for name, module in list(sys.modules.items()):
        if name.startswith(("backend.", "dait.")) and module is not None:
            for attribute, value in mapping.items():
                if hasattr(module, attribute):
                    monkeypatch.setattr(module, attribute, value)
    paths.ensure_runtime_dirs()
    monkeypatch.setattr(summary_worker, "start", Mock())
    monkeypatch.setattr(summary_worker, "stop", Mock())
    counter = itertools.count(1)
    monkeypatch.setattr(
        summary_worker.uuid,
        "uuid4",
        lambda: SimpleNamespace(hex=f"{next(counter):032x}"),
    )
    clock = SimpleNamespace(now=1_790_000_000.0)
    fake_time = SimpleNamespace(time=lambda: clock.now, monotonic=lambda: clock.now)
    monkeypatch.setattr(summary_worker, "time", fake_time)
    monkeypatch.setattr(users, "time", fake_time)
    monkeypatch.setattr(users.secrets, "token_urlsafe", lambda count: f"T{next(counter):042d}")

    class FixedDateTime(datetime):
        # 기능: 테스트 고정 시각을 지정 시간대로 변환한다.
        # 입력:
        #   cls: 현재 클래스.
        #   tz: 반환 시각의 시간대(없으면 UTC).
        # 출력: 고정 시각의 datetime 객체.
        @classmethod
        def now(cls, tz=None):
            return cls.fromtimestamp(clock.now, tz or UTC)

    monkeypatch.setattr(users, "datetime", FixedDateTime)
    users.password_hasher.cache_clear()
    users.dummy_password_hash.cache_clear()
    collect_news.save_articles([])
    users.initialize_auth_db()
    yield SimpleNamespace(root=tmp_path, clock=clock, news=news, users=users, worker=summary_worker)
    users.password_hasher.cache_clear()
    users.dummy_password_hash.cache_clear()


# 기능: 자동 격리 fixture의 실행 환경을 테스트에 제공한다.
# 입력:
#   isolated_runtime: 격리된 DB·시각·서비스를 제공하는 fixture.
# 출력: 임시 폴더·시각·서비스를 담은 SimpleNamespace.
@pytest.fixture
def runtime(isolated_runtime):
    return isolated_runtime


# 기능: 수집기·저장소·화면 테스트에서 공유할 표본 기사를 만든다.
# 입력: 없음.
# 출력: 기사 필드와 카테고리를 담은 사전.
@pytest.fixture
def article():
    return dict(
        id="news_openai_001",
        title="OpenAI AI 소식",
        source="테스트 출처",
        published_at="2026-11-06T00:00:00+00:00",
        summary=["새 기술 발표 설명"],
        content="새 기술 발표 설명",
        original_url="https://example.com/news/1",
        is_foreign=False,
        categories=["인공지능"],
    )

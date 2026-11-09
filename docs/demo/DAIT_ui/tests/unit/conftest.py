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


def pytest_addoption(parser):
    parser.addoption("--reverse-unit-order", action="store_true", default=False)


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


def pytest_runtest_logreport(report):
    if report.when == "call" or report.failed:
        _results[report.nodeid]["outcome"] = (
            "error" if report.failed and report.when != "call" else report.outcome
        )
        if report.failed:
            _results[report.nodeid]["failure"] = str(report.longrepr)


def pytest_sessionfinish(session):
    output = session.config.rootpath / ".tmp" / "test-results"
    output.mkdir(parents=True, exist_ok=True)
    (output / "cases.json").write_text(
        json.dumps(list(_results.values()), ensure_ascii=False, indent=2), encoding="utf-8"
    )


@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path, monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("Unit test attempted forbidden external I/O")

    # Windows asyncio uses an internal loopback socketpair for event-loop wakeup.
    # Permit only its construction, never application HTTP or arbitrary connects.
    internal_pair = threading.local()
    original_pair = socket.socketpair

    def make_pair(*args, **kwargs):
        internal_pair.active = True
        try:
            return original_pair(*args, **kwargs)
        finally:
            internal_pair.active = False

    for name in ("connect", "connect_ex", "bind", "listen"):
        original = getattr(socket.socket, name)

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


@pytest.fixture
def runtime(isolated_runtime):
    return isolated_runtime


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

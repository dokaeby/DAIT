"""core/logging 마스킹과 모드별 로그 설정 테스트."""

import json
import logging
import sys
from collections.abc import Iterator

import pytest
from pydantic import BaseModel

from dait.core.config import AppEnv, Settings
from dait.core.logging import JsonFormatter, MaskingFilter, configure_logging, mask_sensitive

_SECRET_TEXT = "password=hunter2 경로 C:/secret"  # noqa: S105 - 마스킹 확인용 가짜 값


class _Line(BaseModel):
    level: str
    request_id: str
    message: str
    error: str | None = None


@pytest.fixture(autouse=True)
def _restore_root_logger() -> Iterator[None]:
    """루트 로거 설정을 테스트 뒤에 되돌려 다른 테스트에 새지 않게 한다."""
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    yield
    root.handlers[:] = handlers
    root.setLevel(level)


@pytest.mark.parametrize(
    ("raw", "secret"),
    [
        ("login password=hunter2 failed", "hunter2"),
        ('{"password": "hunter2"}', "hunter2"),
        ("Authorization: Bearer abc.def-123", "abc.def-123"),
        ("token=abcdef123456", "abcdef123456"),
        ("user usera@example.com signed up", "usera@example.com"),
    ],
)
def test_sensitive_values_are_masked(raw: str, secret: str) -> None:
    """민감정보가 마스킹된다."""
    assert secret not in mask_sensitive(raw)


def test_plain_text_is_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    """일반 문장은 바뀌지 않는다."""
    assert mask_sensitive("서버가 시작되었습니다") == "서버가 시작되었습니다"


def test_log_args_are_masked() -> None:
    """로그 인자로 들어온 비밀번호도 가려진다."""
    record = logging.LogRecord("t", logging.WARNING, "f", 1, "입력 %s", ("password=hunter2",), None)
    MaskingFilter().filter(record)
    assert "hunter2" not in record.getMessage()


def test_json_log_keeps_only_error_type() -> None:
    """JSON 로그에는 예외 종류만 남는다."""
    try:
        raise ValueError(_SECRET_TEXT)  # noqa: TRY301 - 예외 로그 모양 확인용
    except ValueError:
        record = logging.LogRecord("t", logging.ERROR, "f", 1, "실패", None, sys.exc_info())
    line = _Line.model_validate(json.loads(JsonFormatter().format(record)))
    assert line.error == "ValueError"
    assert "hunter2" not in line.model_dump_json()


def test_release_logs_warning_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """release는 WARNING 이상 JSON 로그다."""
    monkeypatch.setenv("APP_ENV", "release")
    configure_logging(Settings())
    root = logging.getLogger()
    assert root.level == logging.WARNING
    assert not root.isEnabledFor(logging.INFO)
    named = [h for h in root.handlers if h.get_name() == "dait"]
    assert len(named) == 1
    assert isinstance(named[0].formatter, JsonFormatter)


def test_debug_logs_debug_without_duplicate_handlers(monkeypatch: pytest.MonkeyPatch) -> None:
    """debug는 DEBUG 수준이고 핸들러가 중복되지 않는다."""
    monkeypatch.setenv("APP_ENV", AppEnv.DEBUG.value)
    configure_logging(Settings())
    configure_logging(Settings())
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert len([h for h in root.handlers if h.get_name() == "dait"]) == 1

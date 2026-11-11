import socket
import sqlite3

import pytest

from backend import news
from frontend import views


@pytest.mark.ut("UT-UI-006")
@pytest.mark.parametrize(
    "status,expected",
    [
        ("queued", "대기"),
        ("running", "생성 중"),
        ("retry", "재시도"),
        ("failed", "종료"),
        ("insufficient", "정보 부족"),
        ("generated", "생성"),
    ],
)
def test_state_has_text_not_only_color(status, expected):
    assert expected in views.summary_status(dict(status=status))[1]


@pytest.mark.ut("UT-UI-001", "UT-UI-002", "UT-UI-004")
def test_main_has_named_search_and_sort():
    html = news.page([])
    assert "DAIT" in html
    assert 'role="search"' in html
    assert 'id="sort"' in html
    assert 'for="sort"' in html


@pytest.mark.extension
def test_network_guard_is_active():
    with socket.socket() as connection:
        with pytest.raises(AssertionError, match="forbidden"):
            connection.connect(("127.0.0.1", 11434))


@pytest.mark.extension
def test_real_database_is_denied():
    with pytest.raises(AssertionError, match="outside"):
        sqlite3.connect("C:/DAIT_test/DAIT_ui/data/users.db")

import socket
import sqlite3

import pytest

from backend import news
from frontend import views


# 기능: 요약 상태의 텍스트 안내 동작을 검증한다.
# 입력:
#   status: 기록하거나 검증할 요약 상태.
#   expected: 기대하는 검증 결과.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
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


# 기능: 검색·정렬 요소의 접근 가능한 이름 동작을 검증한다.
# 입력: 없음.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-UI-001", "UT-UI-002", "UT-UI-004")
def test_main_has_named_search_and_sort():
    html = news.page([])
    assert "DAIT" in html
    assert 'role="search"' in html
    assert 'id="sort"' in html
    assert 'for="sort"' in html


# 기능: 단위 테스트 외부 네트워크 차단 동작을 검증한다.
# 입력: 없음.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.extension
def test_network_guard_is_active():
    with socket.socket() as connection:
        with pytest.raises(AssertionError, match="forbidden"):
            connection.connect(("127.0.0.1", 11434))


# 기능: 실제 DB 접근 차단 동작을 검증한다.
# 입력: 없음.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.extension
def test_real_database_is_denied():
    with pytest.raises(AssertionError, match="outside"):
        sqlite3.connect("C:/DAIT_test/DAIT_ui/data/users.db")

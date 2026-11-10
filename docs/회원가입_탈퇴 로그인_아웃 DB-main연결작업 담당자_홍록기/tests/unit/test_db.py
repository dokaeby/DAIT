"""repositories/db 연결·트랜잭션 테스트 (외래키, 롤백, 경로 파싱)."""

import sqlite3
from pathlib import Path

import pytest

from dait.repositories.db import connect, ping, sqlite_path, transaction


@pytest.fixture
def url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'test.db'}"


def test_sqlite_path_is_extracted() -> None:
    """DATABASE_URL에서 파일 경로를 꺼낸다."""
    assert sqlite_path("sqlite:///./dait.db") == "./dait.db"


def test_non_sqlite_url_raises_value_error() -> None:
    """sqlite가 아니면 ValueError다."""
    with pytest.raises(ValueError, match="sqlite"):
        sqlite_path("postgresql://x")


def test_foreign_keys_on_for_each_connection(url: str) -> None:
    """연결마다 외래키 검사가 켜져 있다."""
    connection = connect(url)
    try:
        assert connection.execute("PRAGMA foreign_keys").fetchone() == (1,)
    finally:
        connection.close()


def _insert_orphan_child(url: str) -> None:
    """부모 없는 자식 행을 넣는다(외래키 위반)."""
    with transaction(url) as conn:
        conn.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
        conn.execute(
            "CREATE TABLE child (id INTEGER PRIMARY KEY, "
            "parent_id INTEGER NOT NULL REFERENCES parent(id) ON DELETE CASCADE)"
        )
        conn.execute("INSERT INTO child (parent_id) VALUES (?)", (999,))


def _insert_then_fail(url: str) -> None:
    """행을 넣은 직후 예외를 낸다(롤백 확인용)."""
    with transaction(url) as conn:
        conn.execute("INSERT INTO t (id) VALUES (1)")
        raise RuntimeError


def test_foreign_key_violation_is_rejected(url: str) -> None:
    """외래키 위반 행은 거부된다."""
    with pytest.raises(sqlite3.IntegrityError):
        _insert_orphan_child(url)


def test_rollback_on_error(url: str) -> None:
    """예외가 나면 롤백된다."""
    with transaction(url) as conn:
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
    with pytest.raises(RuntimeError):
        _insert_then_fail(url)
    with transaction(url) as conn:
        assert conn.execute("SELECT COUNT(*) FROM t").fetchone() == (0,)


def test_commit_on_success(url: str) -> None:
    """정상 종료하면 커밋된다."""
    with transaction(url) as conn:
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO t (id) VALUES (1)")
    with transaction(url) as conn:
        assert conn.execute("SELECT COUNT(*) FROM t").fetchone() == (1,)


def test_ping_fails_on_unopenable_path(tmp_path: Path) -> None:
    """열 수 없는 경로는 ping에서 sqlite 오류가 난다."""
    with pytest.raises(sqlite3.Error):
        ping(f"sqlite:///{tmp_path / 'no_dir' / 'x.db'}")

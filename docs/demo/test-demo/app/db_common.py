"""Shared SQLite connection setup for the DAIT demo."""

from __future__ import annotations

import sqlite3
from pathlib import Path


# 입력: `db_path`.
# 출력: `sqlite3.Connection` 값.
# 동작: Row 매핑과 외래 키 검사를 활성화한 SQLite 연결을 생성한다.
def connect(db_path: Path) -> sqlite3.Connection:
    """Open a row-mapped SQLite connection with referential integrity enabled."""
    connection = sqlite3.connect(db_path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

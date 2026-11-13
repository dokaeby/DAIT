"""0008 마이그레이션: 소셜 연결 테이블, 비밀번호 없는 계정, 롤백 보호를 확인한다."""

import sqlite3
from pathlib import Path

import pytest
from alembic import command

from support import alembic_config

_NOW = "2026-11-13T00:00:00+00:00"


def _insert_user(db: Path, user_id: str, password_hash: str | None) -> None:
    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, status, role, created_at) "
            "VALUES (?, ?, ?, 'ACTIVE', 'USER', ?)",
            (user_id, f"{user_id}@example.com", password_hash, _NOW),
        )


def _insert_identity(db: Path, identity_id: str, user_id: str, subject: str) -> None:
    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO social_identities (id, user_id, provider, subject, created_at) "
            "VALUES (?, ?, 'GOOGLE', ?, ?)",
            (identity_id, user_id, subject, _NOW),
        )


def test_passwordless_user_and_unique_google_subject(tmp_path: Path, db_url: str) -> None:
    db = tmp_path / "test.db"
    _insert_user(db, "u1", None)
    _insert_user(db, "u2", "$argon2id$fake")
    _insert_identity(db, "i1", "u1", "sub-1")
    with pytest.raises(sqlite3.IntegrityError):  # 같은 구글 계정을 다른 사용자에 연결 불가
        _insert_identity(db, "i2", "u2", "sub-1")
    with pytest.raises(sqlite3.IntegrityError):  # 한 사용자에 구글 계정 둘 연결 불가
        _insert_identity(db, "i3", "u1", "sub-2")
    assert db_url.endswith("test.db")


def test_downgrade_refuses_to_drop_passwordless_accounts(tmp_path: Path, db_url: str) -> None:
    db = tmp_path / "test.db"
    _insert_user(db, "u1", None)
    with pytest.raises(RuntimeError, match="NOT NULL"):
        command.downgrade(alembic_config(db_url), "0007_merge_schedule_onboarding")


def test_downgrade_then_upgrade_round_trip(tmp_path: Path, db_url: str) -> None:
    db = tmp_path / "test.db"
    _insert_user(db, "u1", "$argon2id$fake")
    config = alembic_config(db_url)
    command.downgrade(config, "0007_merge_schedule_onboarding")
    command.upgrade(config, "head")
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone() == (1,)

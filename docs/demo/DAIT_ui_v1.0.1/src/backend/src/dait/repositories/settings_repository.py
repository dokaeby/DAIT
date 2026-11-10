"""설정·예약 소식함 저장소. 회원 DB(users.db)에 별도 테이블로 둡니다.

소유자는 username_key로 구분합니다. DB 회원과 user1~3 테스트 계정을 같은 방식으로 다루기 위해서입니다.
"""

import sqlite3
from collections.abc import Generator
from contextlib import closing, contextmanager

from dait.core.config import USER_DB
from dait.schemas import Digest, DigestItem, UserSettings

MAX_DIGESTS_PER_USER = 30


@contextmanager
def _connect() -> Generator[sqlite3.Connection]:
    USER_DB.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(USER_DB, timeout=10)) as db:
        db.execute("PRAGMA foreign_keys=ON")
        _ensure_tables(db)
        yield db


def _ensure_tables(db: sqlite3.Connection) -> None:
    db.execute("""CREATE TABLE IF NOT EXISTS user_settings (
        owner_key TEXT PRIMARY KEY,
        settings_json TEXT NOT NULL,
        saved_at INTEGER NOT NULL,
        last_run_at INTEGER NOT NULL DEFAULT 0
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS digests (
        id TEXT PRIMARY KEY,
        owner_key TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        manual INTEGER NOT NULL CHECK (manual IN (0,1)),
        seen INTEGER NOT NULL DEFAULT 0 CHECK (seen IN (0,1))
    )""")
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_digests_owner ON digests(owner_key, created_at DESC)"
    )
    db.execute("""CREATE TABLE IF NOT EXISTS digest_items (
        digest_id TEXT NOT NULL REFERENCES digests(id) ON DELETE CASCADE,
        position INTEGER NOT NULL,
        article_id TEXT NOT NULL,
        title TEXT NOT NULL,
        source TEXT NOT NULL,
        published_at TEXT NOT NULL,
        categories TEXT NOT NULL,
        reason TEXT NOT NULL,
        PRIMARY KEY (digest_id, position)
    )""")


def load_settings(owner_key: str) -> tuple[UserSettings, int, int] | None:
    """(설정, 저장 시각, 마지막 예약 실행 시각). 저장한 적 없으면 None."""
    with _connect() as db:
        row = db.execute(
            "SELECT settings_json, saved_at, last_run_at FROM user_settings WHERE owner_key=?",
            (owner_key,),
        ).fetchone()
    if row is None:
        return None
    return UserSettings.model_validate_json(row[0]), int(row[1]), int(row[2])


def save_settings(owner_key: str, settings: UserSettings, saved_at: int) -> None:
    with _connect() as db, db:
        db.execute(
            """INSERT INTO user_settings (owner_key, settings_json, saved_at) VALUES (?,?,?)
               ON CONFLICT(owner_key) DO UPDATE SET settings_json=excluded.settings_json, saved_at=excluded.saved_at""",
            (owner_key, settings.model_dump_json(), saved_at),
        )


def scheduled_owners() -> list[tuple[str, UserSettings, int, int]]:
    with _connect() as db:
        rows = db.execute(
            "SELECT owner_key, settings_json, saved_at, last_run_at FROM user_settings"
        ).fetchall()
    return [
        (row[0], UserSettings.model_validate_json(row[1]), int(row[2]), int(row[3])) for row in rows
    ]


def add_digest(owner_key: str, digest: Digest, scheduled_for: int | None) -> bool:
    """소식을 저장합니다. 예약 실행이면 같은 예약 시각으로 두 번 저장되지 않게 막고 False를 돌려줍니다."""
    with _connect() as db, db:
        db.execute("BEGIN IMMEDIATE")
        if scheduled_for is not None:
            row = db.execute(
                "SELECT last_run_at FROM user_settings WHERE owner_key=?", (owner_key,)
            ).fetchone()
            if row is None or int(row[0]) >= scheduled_for:
                return False
            db.execute(
                "UPDATE user_settings SET last_run_at=? WHERE owner_key=?",
                (scheduled_for, owner_key),
            )
        db.execute(
            "INSERT INTO digests (id, owner_key, created_at, manual, seen) VALUES (?,?,?,?,0)",
            (digest.id, owner_key, digest.created_at, int(digest.manual)),
        )
        db.executemany(
            "INSERT INTO digest_items VALUES (?,?,?,?,?,?,?,?)",
            [
                (
                    digest.id,
                    index,
                    i.article_id,
                    i.title,
                    i.source,
                    i.published_at,
                    i.categories,
                    i.reason,
                )
                for index, i in enumerate(digest.items)
            ],
        )
        db.execute(
            """DELETE FROM digests WHERE owner_key=? AND id NOT IN (
                   SELECT id FROM digests WHERE owner_key=? ORDER BY created_at DESC, rowid DESC LIMIT ?)""",
            (owner_key, owner_key, MAX_DIGESTS_PER_USER),
        )
    return True


def list_digests(owner_key: str) -> list[Digest]:
    with _connect() as db:
        heads = db.execute(
            "SELECT id, created_at, manual, seen FROM digests WHERE owner_key=? ORDER BY created_at DESC, rowid DESC",
            (owner_key,),
        ).fetchall()
        digests: list[Digest] = []
        for digest_id, created_at, manual, seen in heads:
            items = db.execute(
                """SELECT article_id, title, source, published_at, categories, reason
                   FROM digest_items WHERE digest_id=? ORDER BY position""",
                (digest_id,),
            ).fetchall()
            digests.append(
                Digest(
                    id=digest_id,
                    created_at=int(created_at),
                    manual=bool(manual),
                    seen=bool(seen),
                    items=tuple(
                        DigestItem(
                            article_id=r[0],
                            title=r[1],
                            source=r[2],
                            published_at=r[3],
                            categories=r[4],
                            reason=r[5],
                        )
                        for r in items
                    ),
                )
            )
    return digests


def unseen_count(owner_key: str) -> int:
    with _connect() as db:
        row = db.execute(
            "SELECT COUNT(*) FROM digests WHERE owner_key=? AND seen=0", (owner_key,)
        ).fetchone()
    return int(row[0]) if row else 0


def mark_seen(owner_key: str) -> None:
    with _connect() as db, db:
        db.execute("UPDATE digests SET seen=1 WHERE owner_key=?", (owner_key,))

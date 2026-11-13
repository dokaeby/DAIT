"""DATABASE_URL 스킴에 따라 sqlite(로컬)/postgres(서버) 백엔드를 고른다.

저장소·서비스는 이 모듈의 connect/transaction/ping만 호출하고,
실제 드라이버 차이는 db_sqlite.py / db_postgres.py 두 벌이 담당한다.
"""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager

import psycopg

from dait.repositories import db_postgres, db_sqlite

# 드라이버별 예외를 한 계약으로 모은다. 서비스는 이 튜플만 잡으면 된다.
DB_ERRORS: tuple[type[Exception], ...] = (sqlite3.Error, psycopg.Error)
DB_INTEGRITY_ERRORS: tuple[type[Exception], ...] = (
    sqlite3.IntegrityError,
    psycopg.errors.IntegrityError,
)

# 저장소·서비스가 받는 연결 타입. 백엔드별 실제 타입의 합집합이다.
DbConnection = sqlite3.Connection | db_postgres.PgConnection
DbCursor = sqlite3.Cursor | db_postgres.PgCursor

_POSTGRES_PREFIXES = ("postgresql://", "postgres://", "postgresql+psycopg://")


# 입력: DATABASE_URL 문자열.
# 출력: postgres 또는 sqlite 백엔드 이름.
# 동작: URL 스킴으로 실행 환경의 DB 드라이버를 선택한다.
def db_dialect(database_url: str) -> str:
    """DATABASE_URL이 어느 백엔드로 가야 하는지 판별한다.

    입력: database_url (환경변수 DATABASE_URL 문자열)
    출력: "postgres" 또는 "sqlite"
    기능: postgresql://, postgres://, postgresql+psycopg://는 postgres,
          그 외는 sqlite로 본다(잘못된 스킴은 sqlite 쪽 검증이 ValueError로 거부).
    """
    if database_url.startswith(_POSTGRES_PREFIXES):
        return "postgres"
    return "sqlite"


# 입력: DATABASE_URL 문자열.
# 출력: 선택한 백엔드의 열린 DB 연결.
# 동작: URL 스킴에 맞는 PostgreSQL 또는 SQLite 연결 생성을 위임한다.
def connect(database_url: str) -> DbConnection:
    """DATABASE_URL에 맞는 백엔드 연결을 만든다.

    입력: database_url
    출력: DbConnection (호출한 쪽이 닫아야 함)
    기능: 스킴만 보고 sqlite/postgres 백엔드로 위임한다.
    """
    if db_dialect(database_url) == "postgres":
        return db_postgres.connect(database_url)
    return db_sqlite.connect(database_url)


@contextmanager
# 입력: DATABASE_URL 문자열.
# 출력: with 블록에서 사용하는 트랜잭션 연결.
# 동작: 선택한 백엔드의 commit·rollback·close 경계를 제공한다.
def transaction(database_url: str) -> Generator[DbConnection]:
    """백엔드에 맞는 트랜잭션 컨텍스트를 연다.

    입력: database_url
    출력: Generator[DbConnection] (with 블록 안에서 쓸 연결)
    기능: commit/rollback/close는 각 백엔드가 동일하게 처리한다.
    """
    if db_dialect(database_url) == "postgres":
        with db_postgres.transaction(database_url) as conn:
            yield conn
        return
    with db_sqlite.transaction(database_url) as conn:
        yield conn


# 입력: DATABASE_URL 문자열.
# 출력: 반환값 없음.
# 동작: 선택한 DB 백엔드에 연결해 간단한 질의 가능 여부를 확인한다.
def ping(database_url: str) -> None:
    """선택된 백엔드로 DB 연결을 확인한다.

    입력: database_url
    출력: 없음
    기능: 실패하면 각 드라이버의 오류가 올라간다(/readyz에서 DB_ERRORS로 감싼다).
    """
    if db_dialect(database_url) == "postgres":
        db_postgres.ping(database_url)
        return
    db_sqlite.ping(database_url)


# 하위 호환: 기존 테스트·호출부가 repositories.db.sqlite_path를 쓴다.
sqlite_path = db_sqlite.sqlite_path

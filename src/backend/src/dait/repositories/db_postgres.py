"""PostgreSQL(psycopg3) 백엔드. sqlite 백엔드와 같은 connect/transaction/ping API를 제공한다.

입력: postgresql://, postgres://, postgresql+psycopg:// 형식의 DATABASE_URL
출력: DB-API와 유사한 PgConnection (execute/executemany/commit/rollback/close)
기능: 저장소 SQL은 `?` 플레이스홀더를 쓰므로 `%s`로 변환하고, 작은따옴표 안의
      `?`와 `%`는 건드리지 않는다. fetch 결과의 datetime은 ISO 문자열로
      정규화해 sqlite 경로와 같은 모양으로 돌려준다.
"""

from collections.abc import Generator, Iterable
from contextlib import contextmanager
from datetime import date, datetime, time
from typing import Any, cast

import psycopg
from psycopg.abc import Query, QueryNoTemplate
from psycopg.rows import tuple_row

_BUSY_TIMEOUT_MS = 5000  # 다른 트랜잭션이 잠근 행을 기다리는 최대 시간.


def _to_psycopg_url(database_url: str) -> str:
    """DATABASE_URL을 psycopg 접속 문자열로 정규화한다.

    입력: database_url (postgresql://, postgres://, postgresql+psycopg://)
    출력: str (psycopg.connect가 받는 URI)
    기능: `postgres://`와 SQLAlchemy형 `+psycopg` 표기를 libpq URI로 맞춘다.
    """
    if database_url.startswith("postgresql+psycopg://"):
        return "postgresql://" + database_url.removeprefix("postgresql+psycopg://")
    if database_url.startswith("postgres://"):
        return "postgresql://" + database_url.removeprefix("postgres://")
    return database_url


def translate_sql(sql: str) -> str:
    """`?` 플레이스홀더를 `%s`로, 리터럴 `%`를 `%%`로 변환한다.

    입력: sql (저장소가 작성한 ? 형식 SQL)
    출력: str (psycopg가 받는 pyformat SQL)
    기능: 작은따옴표 문자열 리터럴 안의 문자와 '' 이스케이프는 그대로 둔다.
    """
    out: list[str] = []
    in_str = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        if ch == "'":
            # '' 는 문자열 안의 따옴표 이스케이프이므로 상태를 두 번 뒤집어 상쇄한다.
            if in_str and i + 1 < len(sql) and sql[i + 1] == "'":
                out.append("''")
                i += 2
                continue
            in_str = not in_str
            out.append(ch)
        elif ch == "?" and not in_str:
            out.append("%s")
        elif ch == "%":
            # psycopg는 리터럴 %도 %%로 요구한다. 문자열 안의 %도 변환 대상이다.
            out.append("%%")
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def _normalize(value: object) -> object:
    """psycopg가 돌려주는 값을 sqlite 경로와 같은 모양으로 바꾼다.

    입력: value (커서가 반환한 단일 컬럼 값)
    출력: 변환된 값 (datetime/date/time은 ISO 문자열, 나머지는 그대로)
    기능: 저장소는 모든 시각을 ISO 문자열로 읽고 쓴다. bool/int/str은
          양쪽 드라이버가 같은 파이썬 타입으로 주므로 손대지 않는다.
    """
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (date, time)):
        return value.isoformat()
    return value


class PgCursor:
    """psycopg 커서를 감싸 fetch 결과의 시각 값을 ISO 문자열로 정규화한다."""

    def __init__(self, cursor: psycopg.Cursor[tuple[Any, ...]]) -> None:
        self._cursor = cursor

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    def fetchone(self) -> tuple[Any, ...] | None:
        row = self._cursor.fetchone()
        return None if row is None else tuple(_normalize(v) for v in row)

    def fetchall(self) -> list[tuple[Any, ...]]:
        return [tuple(_normalize(v) for v in row) for row in self._cursor.fetchall()]

    def __iter__(self) -> Generator[tuple[Any, ...]]:
        for row in self._cursor:
            yield tuple(_normalize(v) for v in row)


class PgConnection:
    """psycopg 연결을 감싼 DB-API 유사 연결. SQL 번역과 행 정규화를 담당한다."""

    def __init__(self, connection: psycopg.Connection[tuple[Any, ...]]) -> None:
        self._connection = connection

    def execute(self, sql: str, parameters: Iterable[Any] = ()) -> PgCursor:
        # psycopg3는 str을 LiteralString으로 요구해 타입 캐스트가 필요하다(런타임 동작은 동일).
        query = cast(QueryNoTemplate, translate_sql(sql))
        cursor = self._connection.execute(query, tuple(parameters))
        return PgCursor(cursor)

    def executemany(self, sql: str, seq_of_parameters: Iterable[Iterable[Any]]) -> PgCursor:
        query = cast(Query, translate_sql(sql))
        cursor = self._connection.cursor()
        cursor.executemany(query, [tuple(p) for p in seq_of_parameters])
        return PgCursor(cursor)

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()


def connect(database_url: str) -> PgConnection:
    """PostgreSQL 연결을 만든다.

    입력: database_url (postgresql:// 등 URI)
    출력: PgConnection (호출한 쪽이 닫아야 함)
    기능: 외래키는 항상 강제되므로 sqlite의 PRAGMA 같은 별도 설정이 없다.
          autocommit은 끄고 명시적 commit/rollback으로 트랜잭션을 관리한다.
    """
    connection = psycopg.connect(
        _to_psycopg_url(database_url),
        autocommit=False,
        row_factory=tuple_row,
        options=f"-c lock_timeout={_BUSY_TIMEOUT_MS}",
    )
    return PgConnection(connection)


@contextmanager
def transaction(database_url: str) -> Generator[PgConnection]:
    """한 의미 단위의 쓰기를 묶는 트랜잭션 컨텍스트(sqlite 백엔드와 같은 계약).

    입력: database_url
    출력: Generator[PgConnection]
    기능: 블록이 끝나면 commit, 예외가 나면 rollback 후 예외를 그대로 올린다.
    """
    connection = connect(database_url)
    try:
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def ping(database_url: str) -> None:
    """DB가 열리고 질의가 되는지 확인한다(/readyz에서 사용).

    입력: database_url
    출력: 없음
    기능: SELECT 1을 실행한다. 실패하면 psycopg.Error가 올라간다.
    """
    connection = connect(database_url)
    try:
        connection.execute("SELECT 1")
    finally:
        connection.close()

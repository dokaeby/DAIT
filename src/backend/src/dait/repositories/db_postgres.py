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


# 입력: 지원하는 PostgreSQL DATABASE_URL.
# 출력: psycopg가 받을 수 있는 표준 PostgreSQL URL.
# 동작: 별칭 스킴과 SQLAlchemy 드라이버 표기를 libpq 형식으로 정규화한다.
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


# 입력: 저장소의 물음표 플레이스홀더 SQL.
# 출력: psycopg용 플레이스홀더 SQL.
# 동작: 문자열 리터럴을 보존하며 물음표와 퍼센트 문자를 변환한다.
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


# 입력: PostgreSQL 커서가 반환한 단일 값.
# 출력: SQLite 경로와 같은 형태로 정규화된 값.
# 동작: 날짜·시간 타입만 ISO 문자열로 바꾸고 나머지는 유지한다.
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

    # 입력: psycopg 튜플 커서.
    # 출력: 행 값을 정규화하는 커서 래퍼.
    # 동작: 원본 커서를 저장해 공통 DB 커서 계약으로 감싼다.
    def __init__(self, cursor: psycopg.Cursor[tuple[Any, ...]]) -> None:
        self._cursor = cursor

    @property
    # 입력: 없음.
    # 출력: 마지막 SQL이 영향을 준 행 수.
    # 동작: 원본 psycopg 커서의 행 수를 그대로 제공한다.
    def rowcount(self) -> int:
        return self._cursor.rowcount

    # 입력: 없음.
    # 출력: 정규화된 다음 행 또는 없음.
    # 동작: 한 행의 날짜·시간 값을 공통 문자열 형식으로 바꾼다.
    def fetchone(self) -> tuple[Any, ...] | None:
        row = self._cursor.fetchone()
        return None if row is None else tuple(_normalize(v) for v in row)

    # 입력: 없음.
    # 출력: 정규화된 남은 모든 행.
    # 동작: 각 행의 날짜·시간 값을 공통 문자열 형식으로 바꾼다.
    def fetchall(self) -> list[tuple[Any, ...]]:
        return [tuple(_normalize(v) for v in row) for row in self._cursor.fetchall()]

    # 입력: 없음.
    # 출력: 정규화된 행을 순서대로 내는 반복자.
    # 동작: 원본 커서를 순회하며 각 행의 값을 공통 형식으로 바꾼다.
    def __iter__(self) -> Generator[tuple[Any, ...]]:
        for row in self._cursor:
            yield tuple(_normalize(v) for v in row)


class PgConnection:
    """psycopg 연결을 감싼 DB-API 유사 연결. SQL 번역과 행 정규화를 담당한다."""

    # 입력: 열린 psycopg 연결.
    # 출력: 공통 DB 연결 래퍼.
    # 동작: SQL 번역과 결과 정규화에 사용할 원본 연결을 저장한다.
    def __init__(self, connection: psycopg.Connection[tuple[Any, ...]]) -> None:
        self._connection = connection

    # 입력: 공통 형식 SQL과 바인딩 매개변수.
    # 출력: 결과를 정규화하는 PostgreSQL 커서.
    # 동작: SQL 플레이스홀더를 변환한 뒤 매개변수 바인딩으로 실행한다.
    def execute(self, sql: str, parameters: Iterable[Any] = ()) -> PgCursor:
        # psycopg3는 str을 LiteralString으로 요구해 타입 캐스트가 필요하다(런타임 동작은 동일).
        query = cast(QueryNoTemplate, translate_sql(sql))
        cursor = self._connection.execute(query, tuple(parameters))
        return PgCursor(cursor)

    # 입력: 공통 형식 SQL과 여러 매개변수 묶음.
    # 출력: 실행 결과를 감싼 PostgreSQL 커서.
    # 동작: SQL을 한 번 변환해 여러 바인딩 값으로 반복 실행한다.
    def executemany(self, sql: str, seq_of_parameters: Iterable[Iterable[Any]]) -> PgCursor:
        query = cast(Query, translate_sql(sql))
        cursor = self._connection.cursor()
        cursor.executemany(query, [tuple(p) for p in seq_of_parameters])
        return PgCursor(cursor)

    # 입력: 없음.
    # 출력: 반환값 없음.
    # 동작: 현재 PostgreSQL 트랜잭션을 확정한다.
    def commit(self) -> None:
        self._connection.commit()

    # 입력: 없음.
    # 출력: 반환값 없음.
    # 동작: 현재 PostgreSQL 트랜잭션을 되돌린다.
    def rollback(self) -> None:
        self._connection.rollback()

    # 입력: 없음.
    # 출력: 반환값 없음.
    # 동작: 원본 PostgreSQL 연결을 닫는다.
    def close(self) -> None:
        self._connection.close()


# 입력: PostgreSQL DATABASE_URL.
# 출력: 공통 계약으로 감싼 PostgreSQL 연결.
# 동작: 수동 트랜잭션과 잠금 제한 시간을 적용해 psycopg 연결을 만든다.
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
# 입력: PostgreSQL DATABASE_URL.
# 출력: with 블록에서 사용하는 PostgreSQL 연결.
# 동작: 성공 시 커밋하고 실패 시 롤백한 뒤 연결을 닫는다.
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


# 입력: PostgreSQL DATABASE_URL.
# 출력: 반환값 없음.
# 동작: 연결 후 SELECT 1을 실행해 PostgreSQL 준비 상태를 확인한다.
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

"""sqlite 연결을 만들고 트랜잭션 경계를 제공한다. 테이블별 SQL은 각 repository가 맡는다."""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager

_SQLITE_PREFIX = "sqlite:///"
_URL_MESSAGE = "sqlite:/// 형식의 DATABASE_URL이 필요합니다."
_BUSY_TIMEOUT_SECONDS = 5.0  # 다른 연결이 잠근 DB를 기다리는 최대 시간. 무한 대기를 막는다.


def sqlite_path(database_url: str) -> str:
    """DATABASE_URL에서 파일 경로를 꺼낸다.

    입력: database_url (sqlite:///경로 형식 문자열)
    출력: str (sqlite3.connect에 넘길 경로, 예: ./dait.db 또는 :memory:)
    기능: sqlite:/// 로 시작하지 않으면 ValueError.
    """
    if not database_url.startswith(_SQLITE_PREFIX):
        raise ValueError(_URL_MESSAGE)
    return database_url.removeprefix(_SQLITE_PREFIX)


def connect(database_url: str) -> sqlite3.Connection:
    """외래키 검사를 켠 sqlite 연결을 만든다.

    입력: database_url (sqlite:///경로 형식 문자열)
    출력: sqlite3.Connection (호출한 쪽이 닫아야 함)
    기능: sqlite는 연결마다 외래키 검사가 꺼져 있어 매번 켠다.
          탈퇴 시 ON DELETE CASCADE가 동작하기 위한 전제 조건이다.
    """
    connection = sqlite3.connect(sqlite_path(database_url), timeout=_BUSY_TIMEOUT_SECONDS)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def transaction(database_url: str) -> Generator[sqlite3.Connection]:
    """한 의미 단위의 쓰기를 묶는 트랜잭션 컨텍스트.

    입력: database_url (sqlite:///경로 형식 문자열)
    출력: Generator[sqlite3.Connection]  (with 블록 안에서 쓸 연결)
    기능: 블록이 끝나면 commit, 예외가 나면 rollback 후 예외를 그대로 올린다.
          어느 쪽이든 연결을 닫는다.
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
    """DB가 열리고 질의가 되는지 확인한다.

    입력: database_url (sqlite:///경로 형식 문자열)
    출력: 없음
    기능: SELECT 1을 실행한다. 실패하면 sqlite3.Error가 올라간다(/readyz에서 사용).
    """
    connection = connect(database_url)
    try:
        connection.execute("SELECT 1")
    finally:
        connection.close()

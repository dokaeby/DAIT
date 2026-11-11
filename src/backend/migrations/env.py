"""Alembic 실행 환경. DB 주소를 Settings에서 읽고 SQLite batch 모드를 켠다."""

from alembic import context
from sqlalchemy import create_engine

from dait.core.config import get_settings

config = context.config

# ORM 모델이 없고 마이그레이션을 직접 작성하므로 autogenerate용 metadata는 쓰지 않는다.
TARGET_METADATA = None


def _database_url() -> str:
    """마이그레이션을 실행할 DB 주소를 정한다.

    입력: 없음(alembic 옵션 sqlalchemy.url 또는 환경변수 DATABASE_URL)
    출력: str (sqlite:///경로 형식 주소)
    기능: 테스트가 옵션으로 직접 넘긴 주소를 우선하고, 없으면 앱과 같은 Settings에서 읽는다.
    """
    return config.get_main_option("sqlalchemy.url") or get_settings().database_url


def run_migrations_offline() -> None:
    """DB에 연결하지 않고 SQL 문만 출력하는 방식으로 마이그레이션을 실행한다.

    입력: 없음(Settings의 DATABASE_URL)
    출력: 없음(SQL이 표준 출력으로 나감)
    기능: render_as_batch로 SQLite의 ALTER 제한을 우회하는 형태로 SQL을 만든다.
    """
    context.configure(
        url=_sqlalchemy_url(),
        target_metadata=TARGET_METADATA,
        literal_binds=True,
        render_as_batch=_is_sqlite(),
    )
    with context.begin_transaction():
        context.run_migrations()


def _sqlalchemy_url() -> str:
    """SQLAlchemy용 접속 주소를 만든다.

    입력: 없음(Settings의 DATABASE_URL)
    출력: str (create_engine이 받는 주소)
    기능: 앱은 psycopg3를 쓰지만 SQLAlchemy 기본 드라이버는 psycopg2라
          postgresql://를 postgresql+psycopg://로 바꿔 준다.
    """
    url = _database_url()
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    return url


def _is_sqlite() -> bool:
    """현재 DATABASE_URL이 sqlite인지 판별한다(render_as_batch 판단용)."""
    return _database_url().startswith("sqlite:///")


def run_migrations_online() -> None:
    """DB에 연결해 마이그레이션을 실행한다.

    입력: 없음(Settings의 DATABASE_URL)
    출력: 없음(DB 스키마가 바뀜)
    기능: 한 번의 실행을 한 트랜잭션으로 묶고 끝나면 연결을 닫는다.
          render_as_batch는 SQLite의 ALTER 제한 우회용이라 PostgreSQL에서는 끈다.
    """
    engine = create_engine(_sqlalchemy_url())
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=TARGET_METADATA,
            render_as_batch=_is_sqlite(),
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

"""앱 시작 시 Alembic 마이그레이션을 head까지 적용한다.

Render 무료 플랜은 preDeploy 명령을 실행하지 않으므로 배포 시 스키마가
바뀌지 않는 문제가 있었다. 시작 시 자동 적용으로 그 공백을 메운다.
이미 head면 아무것도 하지 않고 끝나므로 매 시작마다 호출해도 안전하다.
"""

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parents[3]


def run_migrations(database_url: str) -> None:
    """DATABASE_URL에 대해 `alembic upgrade head`를 1회 실행한다.

    입력: database_url (Settings.database_url과 동일한 연결 문자열)
    출력: 없음 (스키마가 head로 맞춰진다)
    기능: 실패하면 예외가 올라가 앱 시작이 거부된다(fail fast).
          sqlalchemy.url을 명시해 env.py가 Settings를 다시 읽지 않게 한다.
    """
    config = Config(str(_BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")
    logger.info("DB 마이그레이션 확인 완료: %s", database_url.split("://", 1)[0])

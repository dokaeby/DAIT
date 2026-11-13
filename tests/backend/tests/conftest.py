"""모든 테스트 공통 준비: 실제 .env와 셸 환경변수가 테스트에 섞이지 않게 한다."""

from pathlib import Path

import pytest
from alembic import command

from dait.core.config import Settings, get_settings
from dait.services import cache_retry_service
from support import alembic_config

TEST_JWT_SECRET = "unit-test-secret-0123456789-abcdefghijklmnop"  # noqa: S105 - 테스트 전용 가짜 키


# 입력: pytest 환경 격리 도구와 테스트별 임시 폴더.
# 출력: 반환값 없음.
# 동작: 실제 .env 영향을 제거하고 모든 테스트에 안전한 기본 설정을 주입한다.
@pytest.fixture(autouse=True)
def _isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """빈 임시 폴더에서 실행하고 앱 환경변수를 테스트용으로 고정한다.

    pydantic-settings가 현재 폴더의 .env를 읽으므로, 폴더를 바꿔 개발자의 .env를 건드리지 않는다.
    """
    monkeypatch.chdir(tmp_path)
    # app.api.main이 임포트 시 load_dotenv()로 실제 .env를 환경에 올리므로 설정 필드 전부를 지운다.
    for name in (field.upper() for field in Settings.model_fields):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)
    get_settings.cache_clear()  # env.py와 앱이 쓰는 캐시가 테스트 사이에 남지 않게 한다.
    cache_retry_service.clear_memory_state()  # 모듈 레벨 캐시·락도 테스트 간 격리한다.


@pytest.fixture
def db_url(tmp_path: Path) -> str:
    """마이그레이션을 끝까지 적용한 임시 sqlite DB 주소."""
    url = f"sqlite:///{tmp_path / 'test.db'}"
    command.upgrade(alembic_config(url), "head")
    return url


@pytest.fixture
def settings(db_url: str) -> Settings:
    """위 DB를 가리키는 테스트용 설정(서명 키는 환경변수에서 읽는다)."""
    return Settings(database_url=db_url)

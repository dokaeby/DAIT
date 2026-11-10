"""core/config 설정 검증 테스트 (시작 거부, 기본값, 불변성)."""

import pytest
from pydantic import ValidationError

from dait.core.config import AppEnv, Settings


def test_default_is_release(monkeypatch: pytest.MonkeyPatch) -> None:
    """APP_ENV 기본값은 release다."""
    monkeypatch.delenv("APP_ENV", raising=False)
    assert Settings().app_env is AppEnv.RELEASE


def test_unknown_app_env_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """알 수 없는 APP_ENV는 시작을 거부한다."""
    monkeypatch.setenv("APP_ENV", "test")
    with pytest.raises(ValidationError):
        Settings()


def test_docs_enabled_only_in_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    """debug만 문서를 연다."""
    monkeypatch.setenv("APP_ENV", "debug")
    assert Settings().docs_enabled is True
    monkeypatch.setenv("APP_ENV", "release")
    assert Settings().docs_enabled is False


def test_non_sqlite_database_url_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """sqlite가 아닌 DATABASE_URL은 거부한다."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pw@host/db")
    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.parametrize("origins", ['["*"]', '["ftp://a.com"]', '["a.com"]'])
def test_cors_wildcard_and_non_http_rejected(monkeypatch: pytest.MonkeyPatch, origins: str) -> None:
    """CORS 와일드카드와 http(s) 아닌 값은 거부한다."""
    monkeypatch.setenv("CORS_ORIGINS", origins)
    with pytest.raises(ValidationError):
        Settings()


def test_cors_valid_origin_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    """정상 CORS 출처는 통과한다."""
    monkeypatch.setenv("CORS_ORIGINS", '["https://dait.example.com"]')
    assert Settings().cors_origins == ["https://dait.example.com"]


def test_settings_are_frozen(monkeypatch: pytest.MonkeyPatch) -> None:
    """설정 객체는 변경할 수 없다."""
    monkeypatch.delenv("APP_ENV", raising=False)
    settings = Settings()
    with pytest.raises(ValidationError):
        settings.app_env = AppEnv.DEBUG


def test_missing_jwt_secret_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """서명 키가 없으면 시작을 거부한다."""
    monkeypatch.delenv("JWT_SECRET")
    with pytest.raises(ValidationError):
        Settings()


def test_short_jwt_secret_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """서명 키가 32자보다 짧으면 시작을 거부한다."""
    monkeypatch.setenv("JWT_SECRET", "x" * 31)
    with pytest.raises(ValidationError):
        Settings()


def test_jwt_secret_never_appears_in_repr_or_dump() -> None:
    """서명 키는 repr, 문자열, JSON 덤프 어디에도 나오지 않는다."""
    settings = Settings()
    secret = settings.jwt_secret.get_secret_value()
    assert secret not in repr(settings)
    assert secret not in str(settings)
    assert secret not in settings.model_dump_json()


def test_token_lifetime_defaults_and_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    """토큰 수명 기본값은 15분·14일이고 범위를 벗어나면 거부한다."""
    settings = Settings()
    assert (settings.access_token_minutes, settings.refresh_token_days) == (15, 14)
    monkeypatch.setenv("ACCESS_TOKEN_MINUTES", "0")
    with pytest.raises(ValidationError):
        Settings()

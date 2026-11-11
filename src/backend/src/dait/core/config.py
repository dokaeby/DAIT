"""앱 설정(환경변수)을 한 곳에서 검증해 제공한다. 비즈니스 규칙은 두지 않는다."""

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(StrEnum):
    """실행 모드. debug와 release 두 값만 허용한다."""

    DEBUG = "debug"
    RELEASE = "release"


_DB_URL_MESSAGE = (
    "DATABASE_URL은 sqlite:/// (로컬), postgresql:// 또는 postgres:// (서버) 형식이어야 합니다."
)
_CORS_MESSAGE = "CORS_ORIGINS에는 와일드카드 없이 http(s) 출처만 넣을 수 있습니다."
_RELEASE_CSP = "default-src 'none'; frame-ancestors 'none'"
# debug에서만 열리는 /docs(Swagger UI)가 CDN 스크립트를 쓰므로 그 범위만 허용한다.
_DEBUG_CSP = (
    "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "img-src 'self' data: https://fastapi.tiangolo.com; frame-ancestors 'none'"
)


class Settings(BaseSettings):
    """환경변수에서 읽는 앱 설정. 잘못된 값이면 생성 시점에 예외가 나 서버가 시작되지 않는다."""

    # extra="ignore": 팀 공용 .env에 다른 파트 키(REDIS_URL 등)가 있어도 시작이 막히지 않게 한다.
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", frozen=True
    )

    app_env: AppEnv = AppEnv.RELEASE  # 기본값이 release여야 설정 누락 시에도 안전하다.
    database_url: str = Field(
        default="sqlite:///./dait_integrated.db", min_length=10, max_length=500
    )
    legacy_news_db: Path = Path("dait.db")
    redis_url: str | None = Field(default=None, max_length=500)  # 비어 있으면 메모리 fallback
    cors_origins: list[str] = Field(default_factory=list, max_length=20)
    # 빈 기본값은 min_length 검증(BaseSettings는 기본값도 검증)에 걸려, 키가 없으면 시작이 거부된다.
    jwt_secret: SecretStr = Field(default=SecretStr(""), min_length=32, max_length=256)
    access_token_minutes: int = Field(default=15, ge=1, le=1440)  # 짧을수록 탈취 피해가 적다.
    refresh_token_days: int = Field(default=14, ge=1, le=90)

    @field_validator("database_url")
    @classmethod
    def _check_database_url(cls, value: str) -> str:
        """DATABASE_URL이 지원하는 DB 형식인지 확인한다.

        입력: value (환경변수 DATABASE_URL 문자열)
        출력: 검증을 통과한 같은 문자열
        기능: sqlite(로컬 개발)와 postgresql/postgres(서버 운영)만 허용한다.
              실제 백엔드 선택은 repositories.db.db_dialect가 스킴으로 판별한다.
        """
        if not value.startswith(
            ("sqlite:///", "postgresql://", "postgres://", "postgresql+psycopg://")
        ):
            raise ValueError(_DB_URL_MESSAGE)
        return value

    @field_validator("cors_origins")
    @classmethod
    def _check_cors_origins(cls, value: list[str]) -> list[str]:
        """CORS 허용 출처에 와일드카드나 http(s) 아닌 값이 없는지 확인한다.

        입력: value (환경변수 CORS_ORIGINS의 JSON 배열)
        출력: 검증을 통과한 같은 목록
        기능: "*"를 포함하거나 http://, https://로 시작하지 않는 항목이 있으면 ValueError.
        """
        for origin in value:
            if origin == "*" or not origin.startswith(("http://", "https://")):
                raise ValueError(_CORS_MESSAGE)
        return value

    @property
    def docs_enabled(self) -> bool:
        """API 문서(/docs, /redoc, /openapi.json)를 열지 여부.

        입력: 없음(self.app_env)
        출력: bool (debug면 True)
        기능: release에서는 문서 경로를 만들지 않기 위해 False를 돌려준다.
        """
        return self.app_env is AppEnv.DEBUG

    @property
    def content_security_policy(self) -> str:
        """응답에 붙일 Content-Security-Policy 값.

        입력: 없음(self.app_env)
        출력: str (CSP 헤더 값)
        기능: release는 모든 리소스를 막고, debug는 문서 화면에 필요한 범위만 연다.
        """
        return _DEBUG_CSP if self.docs_enabled else _RELEASE_CSP


@lru_cache
def get_settings() -> Settings:
    """프로세스 전체에서 쓰는 설정 객체를 한 번만 만들어 돌려준다.

    입력: 없음(환경변수와 .env 파일)
    출력: Settings (불변 설정)
    기능: 검증에 실패하면 ValidationError가 그대로 올라가 시작을 거부한다(fail fast).
    """
    return Settings()

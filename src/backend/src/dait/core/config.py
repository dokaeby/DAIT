"""환경설정: pydantic-settings 기반 불변 Settings 로더.

저장소 루트 `.env`와 `src/backend/config/.env`를 함께 읽으며, 두 파일이
공존하면 `src/backend/config/.env`가 우선한다. secret은 `SecretStr`로 감싸
repr·로그·오류 메시지에 값이 노출되지 않도록 한다.
"""

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parents[3]
_REPO_ROOT = Path(__file__).resolve().parents[5]


class Settings(BaseSettings):
    """DAIT 백엔드 실행 설정. 모든 필드는 불변이며 기본값은 안전한 값이다."""

    model_config = SettingsConfigDict(
        env_file=(_REPO_ROOT / ".env", _BACKEND_ROOT / "config" / ".env"),
        env_file_encoding="utf-8",
        frozen=True,
        extra="ignore",
    )

    app_env: str = "dev"
    xai_api_key: SecretStr = SecretStr("")
    grok_model: str = "grok-beta"
    xai_base_url: str = "https://api.x.ai/v1"
    grok_timeout_seconds: float = 30.0
    grok_max_tokens: int = 1200
    min_summary_content_length: int = 80
    summary_max_body_chars: int = 6000

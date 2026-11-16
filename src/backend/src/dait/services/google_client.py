"""구글 token 엔드포인트 호출. 외부 통신은 이 인터페이스 뒤에 두어 테스트가 가짜로 바꾼다."""

from typing import Protocol

import httpx
from pydantic import ValidationError

from dait.core.config import Settings
from dait.schemas.social import GoogleTokenResponse

# 사용자 입력으로 만들지 않는 고정 주소(SSRF 차단). https만 쓴다.
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105 - 공개 URL이지 비밀값이 아님
_TIMEOUT_SECONDS = 5.0
_MAX_RESPONSE_BYTES = 64 * 1024


class GoogleUnavailableError(Exception):
    """구글이 응답하지 않거나 인증 코드를 거부했을 때(재시도하지 않는다)."""


class GoogleClient(Protocol):
    """구글과 통신하는 부분만 정의한다. 서비스는 이 계약만 안다."""

    def fetch_id_token(self, code: str, code_verifier: str) -> str: ...


class HttpxGoogleClient:
    """httpx로 구글에 인증 코드를 id_token으로 교환한다."""

    # 입력: 구글 클라이언트 설정이 담긴 앱 설정.
    # 출력: 초기화된 클라이언트.
    # 동작: 설정을 보관만 하고 네트워크는 호출 때 사용한다.
    def __init__(self, settings: Settings) -> None:
        """클라이언트를 만든다.

        입력: settings (GOOGLE_* 값이 든 설정)
        출력: 없음
        기능: 값 검증은 Settings가 이미 끝냈다.
        """
        self._settings = settings

    # 입력: 구글이 준 1회용 인증 코드와 PKCE verifier.
    # 출력: 구글이 서명해 보낸 id_token 원문.
    # 동작: HTTPS로 코드를 교환하고 응답을 모델로 검증한다. 모든 실패를 한 예외로 모은다.
    def fetch_id_token(self, code: str, code_verifier: str) -> str:
        """인증 코드를 id_token으로 교환한다.

        입력: code (구글 인증 코드), code_verifier (우리가 보관한 PKCE 원문)
        출력: str (id_token)
        기능: 타임아웃 5초, 응답 64KB 제한, 리다이렉트 불허, 재시도 없음.
              실패는 GoogleUnavailableError(내부 원인은 로그·응답에 싣지 않는다).
        """
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": code_verifier,
            "client_id": self._settings.google_client_id or "",
            "client_secret": self._settings.google_client_secret.get_secret_value(),
            "redirect_uri": self._settings.google_redirect_uri or "",
        }
        try:
            response = httpx.post(
                GOOGLE_TOKEN_URL, data=data, timeout=_TIMEOUT_SECONDS, follow_redirects=False
            )
            response.raise_for_status()
            if len(response.content) > _MAX_RESPONSE_BYTES:
                raise GoogleUnavailableError
            return GoogleTokenResponse.model_validate_json(response.content).id_token
        except (httpx.HTTPError, ValidationError) as exc:
            raise GoogleUnavailableError from exc

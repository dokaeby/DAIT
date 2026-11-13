"""소셜(구글) 로그인 경계 모델: 구글 응답, 대기 중 로그인 상태, 교환 요청, DB 연결 행."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class SocialProvider(StrEnum):
    """지원하는 소셜 공급자. DB CHECK 제약과 같은 값만 둔다."""

    GOOGLE = "GOOGLE"


class SocialIdentityRecord(BaseModel):
    """social_identities 테이블 한 행."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1, max_length=36)
    user_id: str = Field(min_length=1, max_length=36)
    provider: SocialProvider
    subject: str = Field(min_length=1, max_length=255)
    created_at: datetime


class OAuthPending(BaseModel):
    """로그인 시작 시 Redis에 잠깐 보관하는 값. callback에서 한 번만 꺼낸다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    nonce: str = Field(min_length=20, max_length=128)
    code_verifier: str = Field(min_length=43, max_length=128)  # RFC 7636 길이 범위


class GoogleTokenResponse(BaseModel):
    """구글 token 엔드포인트 응답 중 쓰는 값. 나머지 필드(access_token 등)는 버린다."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    id_token: str = Field(min_length=10, max_length=8192)


class GoogleIdClaims(BaseModel):
    """id_token 본문 중 검증에 쓰는 값. 이름·사진 같은 다른 개인정보는 버린다."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    iss: Literal["https://accounts.google.com", "accounts.google.com"]
    aud: str = Field(min_length=1, max_length=255)
    sub: str = Field(min_length=1, max_length=255)
    exp: int
    nonce: str = Field(min_length=1, max_length=128)
    email: str = Field(min_length=3, max_length=254)
    email_verified: bool


class ExchangeRequest(BaseModel):
    """화면이 callback 뒤 받은 1회용 교환 코드를 토큰으로 바꿀 때 보내는 요청."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: SecretStr = Field(min_length=20, max_length=128)

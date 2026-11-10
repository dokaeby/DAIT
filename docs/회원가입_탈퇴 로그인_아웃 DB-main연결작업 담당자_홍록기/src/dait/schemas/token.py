"""refresh_tokens 테이블 한 행 모델. 토큰 원문은 어디에도 두지 않고 해시만 가진다."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RefreshTokenRecord(BaseModel):
    """저장할 refresh 토큰 정보."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1, max_length=36)
    user_id: str = Field(min_length=1, max_length=36)
    family_id: str = Field(min_length=1, max_length=36)  # 같은 로그인에서 회전된 토큰들의 묶음
    token_hash: str = Field(min_length=64, max_length=64)
    expires_at: datetime
    created_at: datetime


class StoredRefreshToken(BaseModel):
    """DB에서 읽은 refresh 토큰 상태. 회전·재사용 판단에만 쓴다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    user_id: str
    family_id: str
    expires_at: datetime
    revoked_at: datetime | None

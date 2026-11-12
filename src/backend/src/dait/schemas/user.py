"""사용자 모델: DB에서 읽는 레코드와 응답용 공개 모델을 분리한다."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from dait.schemas.nickname import Nickname


class UserStatus(StrEnum):
    """계정 상태. 지금은 정상 계정만 있다."""

    ACTIVE = "ACTIVE"


class UserRole(StrEnum):
    """역할. 모든 보호 라우트는 기본 거부이고 이 값으로 허용 범위를 정한다."""

    USER = "USER"
    ADMIN = "ADMIN"


class UserRecord(BaseModel):
    """users 테이블 한 행. 비밀번호 해시는 repr·로그에 나오지 않게 한다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1, max_length=36)
    email: str = Field(min_length=3, max_length=254)
    password_hash: str = Field(min_length=1, max_length=255, repr=False)
    status: UserStatus
    role: UserRole
    created_at: datetime
    nickname: Nickname | None = None


class UserPublic(BaseModel):
    """응답에 내보내는 사용자 정보. 해시 같은 내부 값은 없다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    email: str
    status: UserStatus
    role: UserRole
    nickname: Nickname | None = None

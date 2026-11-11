"""이메일 2차 인증의 요청·응답·저장 모델. 입력 검증은 모두 여기서 한다."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# challenge_id는 secrets.token_urlsafe(32)로 만든 43자다. 범위를 두어 이상한 입력을 일찍 거른다.
_CHALLENGE_MIN = 20
_CHALLENGE_MAX = 128
CODE_PATTERN = r"^[0-9]{6}$"  # 앞자리 0도 코드의 일부라 숫자가 아닌 문자열로 다룬다.


class TwoFactorRequired(BaseModel):
    """비밀번호는 맞았지만 코드 확인이 남았다는 로그인 응답. 토큰은 아직 없다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["TWO_FACTOR_REQUIRED"] = "TWO_FACTOR_REQUIRED"
    challenge_id: str = Field(min_length=_CHALLENGE_MIN, max_length=_CHALLENGE_MAX)
    expires_in_seconds: int = Field(ge=1)
    resend_after_seconds: int = Field(ge=0)


class VerifyRequest(BaseModel):
    """메일로 받은 코드 확인 요청. 코드는 repr에 찍히지 않게 한다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    challenge_id: str = Field(min_length=_CHALLENGE_MIN, max_length=_CHALLENGE_MAX)
    code: str = Field(pattern=CODE_PATTERN, repr=False)


class ResendRequest(BaseModel):
    """코드 재발송 요청."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    challenge_id: str = Field(min_length=_CHALLENGE_MIN, max_length=_CHALLENGE_MAX)


class ResendResponse(BaseModel):
    """재발송 결과. 새 코드가 메일로 나갔고 다음 재발송까지 기다릴 시간을 알린다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    result: Literal["sent"] = "sent"
    resend_after_seconds: int = Field(ge=0)


class ChallengeRecord(BaseModel):
    """two_factor_challenges 한 행. 코드 원문은 없고 키를 섞은 해시만 있다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str = Field(
        min_length=64, max_length=64
    )  # challenge_id의 SHA-256. 원문은 저장하지 않는다.
    user_id: str = Field(min_length=1, max_length=36)
    code_hash: str = Field(min_length=64, max_length=64, repr=False)
    expires_at: datetime
    attempts: int = Field(ge=0)
    resend_count: int = Field(ge=0)
    last_sent_at: datetime
    created_at: datetime

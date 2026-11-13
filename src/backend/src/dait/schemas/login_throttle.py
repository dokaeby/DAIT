"""로그인 실패 제한의 기존 Redis JSON 경계를 검증한다."""

from pydantic import BaseModel, ConfigDict, Field


# 입력: Redis에 저장된 f·lf·lu JSON 필드.
# 출력: 검증된 불변 로그인 실패 상태.
# 동작: 실패 횟수와 UTC 타임스탬프의 타입·범위를 경계에서 검증한다.
class LoginFailureState(BaseModel):
    """실패 횟수와 UTC 타임스탬프를 기존 키 이름으로 읽는다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    failures: int = Field(alias="f", strict=True, ge=0)
    last_failure: float = Field(alias="lf", allow_inf_nan=False)
    locked_until: float | None = Field(alias="lu", default=None, allow_inf_nan=False)

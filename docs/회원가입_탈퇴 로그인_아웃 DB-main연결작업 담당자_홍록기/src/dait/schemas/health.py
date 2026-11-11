"""상태 확인(/healthz, /readyz) 응답 모델."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """상태 확인 응답. 운영 정보는 담지 않고 상태 문자열만 낸다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["ok", "ready"]

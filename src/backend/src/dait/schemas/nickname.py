"""닉네임의 표시값과 중복 비교 규칙을 공유한다."""

import unicodedata
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

_CONTROL_CHARACTERS = "nickname contains control characters"


def normalize_nickname(value: object) -> object:
    """호환 문자와 앞뒤 공백을 정규화하고 제어문자를 거부한다."""
    if not isinstance(value, str):
        return value
    normalized = unicodedata.normalize("NFKC", value).strip()
    if any(unicodedata.category(char).startswith("C") for char in normalized):
        raise ValueError(_CONTROL_CHARACTERS)
    return normalized


Nickname = Annotated[str, Field(min_length=2, max_length=30), BeforeValidator(normalize_nickname)]


class NicknameAvailability(BaseModel):
    """닉네임 중복 확인 결과. 계정 정보는 반환하지 않는다."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    nickname: Nickname
    available: bool

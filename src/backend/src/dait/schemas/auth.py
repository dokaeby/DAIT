"""가입·로그인 요청과 응답 모델. 입력 검증은 모두 여기서 한다."""

import hmac
from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

from dait.schemas.interest import (
    MAX_INTERESTS,
    InterestCode,
    InterestItem,
    check_no_duplicates,
    empty_interests,
    empty_items,
)
from dait.schemas.nickname import Nickname
from dait.schemas.user import UserPublic

_EMAIL_MAX_LENGTH = 254  # RFC 5321 기준 주소 최대 길이
_LENGTH_HINT = "비밀번호 (8~128자)"
_EMAIL_TOO_LONG = "email too long"
_MISMATCH = "password mismatch"
_TERMS = "terms not accepted"


class SignupRequest(BaseModel):
    """회원가입 요청. 알 수 없는 필드는 거부한다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    email: EmailStr
    nickname: Nickname | None = None
    # SecretStr: 실수로 로그·repr에 찍혀도 *** 로만 보이게 한다.
    password: SecretStr = Field(min_length=8, max_length=128, description=_LENGTH_HINT)
    password_confirm: SecretStr = Field(min_length=8, max_length=128)
    terms_accepted: bool
    # 선택 필드: 보내지 않으면 관심사 없이 가입한다(관심사 기능이 빠져도 가입 요청은 그대로 통한다).
    interests: list[InterestCode] = Field(default_factory=empty_interests, max_length=MAX_INTERESTS)

    @field_validator("nickname", mode="before")
    @classmethod
    def _empty_nickname(cls, value: object) -> object:
        """빈 선택 입력은 이메일 표시를 뜻한다."""
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("interests")
    @classmethod
    def _no_duplicate_interests(cls, value: list[InterestCode]) -> list[InterestCode]:
        """가입 시 보낸 관심사에 중복이 없는지 확인한다.

        입력: value (관심사 코드 목록)
        출력: 같은 목록
        기능: 중복이면 ValueError (422).
        """
        return check_no_duplicates(value)

    @field_validator("email")
    @classmethod
    def _check_email_length(cls, value: str) -> str:
        """이메일이 254자를 넘지 않는지 확인한다.

        입력: value (형식 검증을 통과한 이메일)
        출력: 같은 이메일
        기능: 254자를 넘으면 ValueError (UT-AUTH-002 경계).
        """
        if len(value) > _EMAIL_MAX_LENGTH:
            raise ValueError(_EMAIL_TOO_LONG)
        return value

    @model_validator(mode="after")
    def _check_confirm_and_terms(self) -> Self:
        """비밀번호 확인 일치와 약관 동의를 확인한다.

        입력: 없음(이미 검증된 필드들)
        출력: self
        기능: 두 비밀번호가 다르거나 약관 미동의면 ValueError. 비교는 상수 시간으로 한다.
        """
        same = hmac.compare_digest(
            self.password.get_secret_value().encode(),
            self.password_confirm.get_secret_value().encode(),
        )
        if not same:
            raise ValueError(_MISMATCH)
        if not self.terms_accepted:
            raise ValueError(_TERMS)
        return self


class LoginRequest(BaseModel):
    """로그인 요청."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    email: EmailStr
    password: SecretStr = Field(min_length=1, max_length=128)


class TokenPair(BaseModel):
    """발급된 토큰 한 쌍. 원문은 이 응답에서만 볼 수 있다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 - 인증 방식 이름이지 비밀값이 아님


class AuthResponse(BaseModel):
    """가입·로그인 응답: 사용자 정보, 토큰, 저장된 관심사."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    user: UserPublic
    tokens: TokenPair
    # 메인 화면이 로그인 직후 바로 쓰도록 DB의 관심사를 함께 내려준다(없으면 빈 목록).
    interests: list[InterestItem] = Field(default_factory=empty_items)


class RefreshRequest(BaseModel):
    """토큰 갱신 요청. refresh 토큰도 로그에 찍히지 않게 SecretStr로 받는다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    refresh_token: SecretStr = Field(min_length=20, max_length=256)


class WithdrawRequest(BaseModel):
    """회원탈퇴 요청. 본인 확인을 위해 비밀번호를 다시 받는다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    password: SecretStr = Field(min_length=1, max_length=128)


class ResultResponse(BaseModel):
    """내용 없이 처리 결과만 알리는 응답."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    result: Literal["done"] = "done"


class SessionResponse(BaseModel):
    """로그인 상태 확인 응답. 로그아웃 상태면 user가 없다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    authenticated: bool
    user: UserPublic | None = None
    interests: list[InterestItem] = Field(default_factory=empty_items)

"""테스트 로그인과 기존 기능 연결에 사용하는 요청·응답 구조."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationInfo, field_validator


class LoginForm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user: str = Field(min_length=1, max_length=30)
    password: SecretStr = Field(min_length=1, max_length=128)
    q: str = Field(default="", max_length=200)

    @field_validator("q")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        return " ".join(value.split())


class AuthState(BaseModel):
    logged_in: bool
    user: str | None = None
    interests: list[str] = Field(default_factory=list)


class InterestSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    categories: list[Annotated[str, Field(min_length=1, max_length=40)]] = Field(min_length=1, max_length=100)

    @field_validator("categories")
    @classmethod
    def unique_categories(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))


class InterestState(BaseModel):
    user: str
    available: list[str]
    selected: list[str]


class InterestSaved(BaseModel):
    message: str
    selected: list[str]
    redirect: str = "/"


class SignupForm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user: str = Field(min_length=1, max_length=30)
    password: SecretStr = Field(min_length=5, max_length=128)
    password_confirm: SecretStr = Field(min_length=5, max_length=128)

    @field_validator("user")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if not value.strip() or any(char.isspace() or ord(char) < 32 for char in value):
            raise ValueError("아이디는 공백 없이 입력해주세요.")
        return value

    @field_validator("password_confirm")
    @classmethod
    def confirm_password(cls, value: SecretStr, info: ValidationInfo) -> SecretStr:
        password = info.data.get("password")
        if password is not None and value.get_secret_value() != password.get_secret_value():
            raise ValueError("비밀번호가 일치 하지 않습니다. 다시 입력해주세요")
        return value


class RegisteredUser(BaseModel):
    id: int
    username: str
    created_at: str


class SignupResult(BaseModel):
    message: str
    user: RegisteredUser


class SearchJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["build", "compare", "integrated"] = "integrated"
    query: str = Field(default="", max_length=200)
    min_score: float = Field(default=0.35, ge=-1, le=1, allow_inf_nan=False)
    category: str = Field(default="", max_length=40)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        return " ".join(value.split())


class SummaryJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    article_path: str = Field(min_length=10, max_length=2048, pattern=r"^/article/.+")

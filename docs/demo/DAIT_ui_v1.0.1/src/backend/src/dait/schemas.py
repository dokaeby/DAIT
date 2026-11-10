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

    nickname: str = Field(default="", max_length=30)
    user: str = Field(min_length=1, max_length=30)
    password: SecretStr = Field(min_length=5, max_length=128)
    password_confirm: SecretStr = Field(min_length=5, max_length=128)

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, value: str) -> str:
        value = value.strip()
        if any(ord(char) < 32 for char in value):
            raise ValueError("닉네임을 입력해주세요.")
        return value

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


# --- KAN-10: 설정·카테고리 표시 순서·선호 검색어·예약 알림 ---
MAX_KEYWORDS = 3
KEYWORD_MAX_LENGTH = 30
DigestSource = Literal["interests", "keywords"]


class ScheduleSettings(BaseModel):
    """예약 알림. 시간대는 화면에서 선택 가능한 Asia/Seoul만 받습니다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: bool = True
    time: str = Field(default="08:30", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    timezone: Literal["Asia/Seoul"] = "Asia/Seoul"
    # 파이썬 weekday 기준: 월=0 … 일=6
    days: tuple[Annotated[int, Field(ge=0, le=6)], ...] = (0, 1, 2, 3, 4, 5, 6)
    sources: tuple[DigestSource, ...] = Field(default=("interests", "keywords"), min_length=1)
    max_items: Literal[5, 10, 20] = 10

    @field_validator("days")
    @classmethod
    def sorted_days(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        return tuple(sorted(set(value)))

    @field_validator("sources")
    @classmethod
    def unique_sources(cls, value: tuple[DigestSource, ...]) -> tuple[DigestSource, ...]:
        return tuple(dict.fromkeys(value))


class UserSettings(BaseModel):
    """설정 화면 전체 저장 단위. 화면과 API가 같은 모델을 씁니다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    keywords: tuple[Annotated[str, Field(max_length=200)], ...] = Field(default=(), max_length=20)
    category_order: tuple[Annotated[str, Field(min_length=1, max_length=40)], ...] = Field(default=(), max_length=100)
    hidden_categories: tuple[Annotated[str, Field(min_length=1, max_length=40)], ...] = Field(default=(), max_length=100)
    display_count: Literal[5, 10] = 10
    in_app_notification: bool = True
    email_notification: bool = False
    schedule: ScheduleSettings = ScheduleSettings()

    @field_validator("keywords")
    @classmethod
    def clean_keywords(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        # 공백 정리 후 대소문자 무시 중복 제거. 4개 이상은 저장하지 않고 오류로 돌려보냅니다.
        seen: set[str] = set()
        words: list[str] = []
        for raw in value:
            word = " ".join(raw.split())
            if not word or word.casefold() in seen:
                continue
            if len(word) > KEYWORD_MAX_LENGTH:
                raise ValueError(f"선호 검색어는 {KEYWORD_MAX_LENGTH}자 이하로 입력해주세요.")
            seen.add(word.casefold())
            words.append(word)
        if len(words) > MAX_KEYWORDS:
            raise ValueError(f"선호 검색어는 최대 {MAX_KEYWORDS}개까지 저장할 수 있습니다.")
        return tuple(words)

    @field_validator("category_order", "hidden_categories")
    @classmethod
    def unique_categories(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(value))


class SettingsState(BaseModel):
    settings: UserSettings
    available_categories: list[str]
    next_run: str | None


class DigestItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    article_id: str
    title: str
    source: str
    published_at: str
    categories: str
    reason: str


class Digest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    created_at: int
    manual: bool
    seen: bool
    items: tuple[DigestItem, ...]


class InboxState(BaseModel):
    unseen: int
    digests: list[Digest]

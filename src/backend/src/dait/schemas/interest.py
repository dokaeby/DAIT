"""관심사 코드(15개)와 카탈로그·요청·응답 모델. 코드 철자는 README 6.2절 표로 고정한다."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_INTERESTS = 30  # 소주제 전체 선택까지 허용
_DUPLICATE_MESSAGE = "duplicate interest"


class InterestCode(StrEnum):
    """선택할 수 있는 관심사 소주제. `대주제.소주제` 형식의 영문 고정 코드다."""

    AI_MODELS = "ai.models"
    AI_AGENTS = "ai.agents"
    AI_DEVTOOLS = "ai.devtools"
    AI_OPENSOURCE = "ai.opensource"
    AI_INFRA = "ai.infra"
    ECONOMY_INDUSTRY = "economy.industry"
    ECONOMY_BUSINESS = "economy.business"
    ECONOMY_STARTUPS = "economy.startups"
    ECONOMY_MARKETS = "economy.markets"
    ECONOMY_JOBS = "economy.jobs"
    SOCIETY_POLICY = "society.policy"
    SOCIETY_EDUCATION = "society.education"
    SOCIETY_HEALTH = "society.health"
    SOCIETY_CLIMATE = "society.climate"
    SOCIETY_CULTURE = "society.culture"
    EN_AI_MODELS = "en.ai.models"
    EN_AI_AGENTS = "en.ai.agents"
    EN_AI_DEVTOOLS = "en.ai.devtools"
    EN_AI_OPENSOURCE = "en.ai.opensource"
    EN_AI_INFRA = "en.ai.infra"
    EN_ECONOMY_INDUSTRY = "en.economy.industry"
    EN_ECONOMY_BUSINESS = "en.economy.business"
    EN_ECONOMY_STARTUPS = "en.economy.startups"
    EN_ECONOMY_MARKETS = "en.economy.markets"
    EN_ECONOMY_JOBS = "en.economy.jobs"
    EN_SOCIETY_POLICY = "en.society.policy"
    EN_SOCIETY_EDUCATION = "en.society.education"
    EN_SOCIETY_HEALTH = "en.society.health"
    EN_SOCIETY_CLIMATE = "en.society.climate"
    EN_SOCIETY_CULTURE = "en.society.culture"


# 한글 이름은 표시용이라 바뀌어도 저장된 코드는 영향을 받지 않는다.
INTEREST_NAMES: dict[InterestCode, str] = {
    InterestCode.EN_AI_MODELS: "Models & Research",
    InterestCode.EN_AI_AGENTS: "AI Agents",
    InterestCode.EN_AI_DEVTOOLS: "Developer Tools",
    InterestCode.EN_AI_OPENSOURCE: "Open Source & Local Models",
    InterestCode.EN_AI_INFRA: "AI Infrastructure",
    InterestCode.EN_ECONOMY_INDUSTRY: "Industry Trends",
    InterestCode.EN_ECONOMY_BUSINESS: "Corporate & Management",
    InterestCode.EN_ECONOMY_STARTUPS: "Startups & Ventures",
    InterestCode.EN_ECONOMY_MARKETS: "Finance & Markets",
    InterestCode.EN_ECONOMY_JOBS: "Jobs & Employment",
    InterestCode.EN_SOCIETY_POLICY: "Policy & Administration",
    InterestCode.EN_SOCIETY_EDUCATION: "Education",
    InterestCode.EN_SOCIETY_HEALTH: "Health & Medicine",
    InterestCode.EN_SOCIETY_CLIMATE: "Environment & Climate",
    InterestCode.EN_SOCIETY_CULTURE: "Culture & Content",
    InterestCode.AI_MODELS: "모델·연구",
    InterestCode.AI_AGENTS: "AI 에이전트",
    InterestCode.AI_DEVTOOLS: "개발 도구",
    InterestCode.AI_OPENSOURCE: "오픈소스·로컬 모델",
    InterestCode.AI_INFRA: "AI 인프라",
    InterestCode.ECONOMY_INDUSTRY: "산업 동향",
    InterestCode.ECONOMY_BUSINESS: "기업·경영",
    InterestCode.ECONOMY_STARTUPS: "스타트업·투자",
    InterestCode.ECONOMY_MARKETS: "금융시장",
    InterestCode.ECONOMY_JOBS: "일자리",
    InterestCode.SOCIETY_POLICY: "정책·제도",
    InterestCode.SOCIETY_EDUCATION: "교육",
    InterestCode.SOCIETY_HEALTH: "건강·의료",
    InterestCode.SOCIETY_CLIMATE: "환경·기후",
    InterestCode.SOCIETY_CULTURE: "문화·콘텐츠",
}
GROUP_NAMES: dict[str, str] = {"ai": "AI•인공지능", "economy": "경제·비즈니스", "society": "사회·문화"}

GROUP_NAMES.update(
    {
        "en_ai": "AI & Technology (English)",
        "en_economy": "Economy & Business (English)",
        "en_society": "Society & Culture (English)",
    }
)


class InterestItem(BaseModel):
    """화면에 보여 줄 관심사 한 개: 저장 코드, 한글 이름, 대주제."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: InterestCode
    name: str
    group: str


def empty_interests() -> list[InterestCode]:
    """빈 관심사 목록을 만든다.

    입력: 없음
    출력: list[InterestCode] (새 빈 목록)
    기능: 필드 기본값 공장으로 써서 pyright가 요소 타입을 알게 한다.
    """
    return []


def empty_items() -> list[InterestItem]:
    """빈 관심사 항목 목록을 만든다.

    입력: 없음
    출력: list[InterestItem] (새 빈 목록)
    기능: 응답 모델의 기본값 공장으로 써서 pyright가 요소 타입을 알게 한다.
    """
    return []


def check_no_duplicates(values: list[InterestCode]) -> list[InterestCode]:
    """관심사 목록에 같은 코드가 두 번 들어 있지 않은지 확인한다.

    입력: values (이미 Enum 검증을 통과한 코드 목록)
    출력: 같은 목록
    기능: 중복이 있으면 ValueError (요청 모델 검증에서 422가 된다).
    """
    if len(set(values)) != len(values):
        raise ValueError(_DUPLICATE_MESSAGE)
    return values


class InterestGroup(BaseModel):
    """대주제 한 개와 그 아래 소주제들(대주제를 누르면 소주제가 보이는 화면용)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    group: str
    group_name: str
    interests: list[InterestItem]


class CatalogResponse(BaseModel):
    """선택 가능한 관심사 전체를 대주제별로 묶은 응답."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    groups: list[InterestGroup]


class MyInterestsResponse(BaseModel):
    """내 관심사 응답. 카탈로그 순서로 정렬되어 나간다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    interests: list[InterestItem]


class InterestsUpdateRequest(BaseModel):
    """내 관심사 전체 교체 요청. 빈 목록은 선택 해제다."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    interests: list[InterestCode] = Field(default_factory=empty_interests, max_length=MAX_INTERESTS)

    @field_validator("interests")
    @classmethod
    def _no_duplicates(cls, value: list[InterestCode]) -> list[InterestCode]:
        """중복 코드를 거부한다.

        입력: value (코드 목록)
        출력: 같은 목록
        기능: check_no_duplicates에 맡긴다.
        """
        return check_no_duplicates(value)

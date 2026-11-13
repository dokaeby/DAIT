"""Shared, explicit keyword rules for the fifteen supported news topics."""

from dait.repositories.news_language import NEWS_LANGUAGE_SQL

MATCHING_VERSION = "topics-v2-financing"

KEYWORDS = {
    "ai.models": ("언어모델", "언어 모델", "llm", "gpt", "모델 학습", "인공지능 연구"),
    "ai.agents": ("에이전트", "ai agent", "인공지능 비서", "자율 에이전트"),
    "ai.devtools": ("개발 도구", "개발도구", "코딩", "copilot", "커서", "개발자"),
    "ai.opensource": ("오픈소스", "오픈 소스", "로컬 모델", "로컬모델", "ollama", "라마"),
    "ai.infra": ("gpu", "데이터센터", "데이터 센터", "반도체", "ai 인프라"),
    "economy.industry": ("산업", "제조", "공급망", "수출", "생산"),
    "economy.business": ("기업", "경영", "실적", "매출", "인수", "합병"),
    "economy.startups": ("스타트업", "벤처", "창업", "투자 유치", "투자유치"),
    "economy.markets": ("금융", "증시", "주식", "금리", "환율", "증권"),
    "economy.jobs": ("일자리", "고용", "채용", "취업", "노동"),
    "society.policy": ("정책", "행정", "정부", "법안", "규제"),
    "society.education": ("교육", "학교", "학생", "대학", "교사"),
    "society.health": ("건강", "의료", "병원", "질병", "치료"),
    "society.climate": ("환경", "기후", "탄소", "온난화", "재생에너지"),
    "society.culture": ("문화", "콘텐츠", "영화", "음악", "공연", "게임"),
}
KEYWORDS["ai.models"] += (
    "language model",
    "llm",
    "model training",
)
KEYWORDS["en.ai.models"] = KEYWORDS["ai.models"]
KEYWORDS["ai.agents"] += (
    "ai agent",
    "ai assistant",
)
KEYWORDS["en.ai.agents"] = KEYWORDS["ai.agents"]
KEYWORDS["ai.devtools"] += (
    "developer",
    "coding",
    "copilot",
)
KEYWORDS["en.ai.devtools"] = KEYWORDS["ai.devtools"]
KEYWORDS["ai.opensource"] += (
    "open source",
    "open-source",
    "local model",
)
KEYWORDS["en.ai.opensource"] = KEYWORDS["ai.opensource"]
KEYWORDS["ai.infra"] += (
    "gpu",
    "data center",
    "semiconductor",
)
KEYWORDS["en.ai.infra"] = KEYWORDS["ai.infra"]
KEYWORDS["economy.industry"] += (
    "industry",
    "manufacturing",
    "supply chain",
)
KEYWORDS["en.economy.industry"] = KEYWORDS["economy.industry"]
KEYWORDS["economy.business"] += (
    "corporate",
    "company",
    "revenue",
    "earnings",
)
KEYWORDS["en.economy.business"] = KEYWORDS["economy.business"]
KEYWORDS["economy.startups"] += (
    "startup",
    "venture",
    "funding",
    "자금 조달",
    "자금조달",
    "자본 조달",
    "자본조달",
    "투자금",
    "financing",
    "fundraising",
    "fund-raising",
    "valuation",
    "capital raise",
)
KEYWORDS["en.economy.startups"] = KEYWORDS["economy.startups"]
KEYWORDS["economy.markets"] += (
    "finance",
    "stock",
    "interest rate",
)
KEYWORDS["en.economy.markets"] = KEYWORDS["economy.markets"]
KEYWORDS["economy.jobs"] += (
    "employment",
    "hiring",
    "jobs",
)
KEYWORDS["en.economy.jobs"] = KEYWORDS["economy.jobs"]
KEYWORDS["society.policy"] += (
    "policy",
    "government",
    "regulation",
)
KEYWORDS["en.society.policy"] = KEYWORDS["society.policy"]
KEYWORDS["society.education"] += (
    "education",
    "school",
    "university",
)
KEYWORDS["en.society.education"] = KEYWORDS["society.education"]
KEYWORDS["society.health"] += (
    "health",
    "medicine",
    "hospital",
)
KEYWORDS["en.society.health"] = KEYWORDS["society.health"]
KEYWORDS["society.climate"] += (
    "climate",
    "environment",
    "carbon",
)
KEYWORDS["en.society.climate"] = KEYWORDS["society.climate"]
KEYWORDS["society.culture"] += (
    "culture",
    "film",
    "music",
    "gaming",
)
KEYWORDS["en.society.culture"] = KEYWORDS["society.culture"]
GROUPS = {"ai": "AI", "economy": "ECONOMY", "society": "POLITICS"}


def interest_clause(codes: tuple[str, ...]) -> tuple[str, list[str]]:
    """OR topics together; bound parameters preserve literal keyword matching."""
    clauses: list[str] = []
    params: list[str] = []
    for code in codes:
        words = KEYWORDS.get(code)
        if not words:
            continue
        matches = []
        base_code = code.removeprefix("en.")
        params.append(GROUPS[base_code.split(".")[0]])
        for word in words:
            matches.append("(lower(n.title) LIKE ? OR lower(c.summary_lines) LIKE ?)")
            params.extend([f"%{word.lower()}%"] * 2)
        clauses.append(
            "(n.category = ? AND "
            + (f"({NEWS_LANGUAGE_SQL}) = 'en' AND " if code.startswith("en.") else "")
            + "("
            + " OR ".join(matches)
            + "))"
        )
    return "(" + " OR ".join(clauses) + ")" if clauses else "1=0", params

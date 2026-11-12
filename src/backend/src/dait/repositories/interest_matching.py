"""Shared, explicit keyword rules for the fifteen supported news topics."""

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
        params.append(GROUPS[code.split(".")[0]])
        for word in words:
            matches.append("(lower(n.title) LIKE ? OR lower(c.summary_lines) LIKE ?)")
            params.extend([f"%{word.lower()}%"] * 2)
        clauses.append("(n.category = ? AND (" + " OR ".join(matches) + "))")
    return "(" + " OR ".join(clauses) + ")" if clauses else "1=0", params

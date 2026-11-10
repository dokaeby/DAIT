"""Category taxonomy, keyword matching, and 17 official media source definitions."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

type CategoryType = Literal["AI", "ECONOMY", "SOCIETY"]
CATEGORIES: tuple[CategoryType, ...] = ("AI", "ECONOMY", "SOCIETY")


class TaxonomyModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class SubtopicGroup(TaxonomyModel):
    category: CategoryType
    label: str = Field(min_length=1, max_length=100)
    keywords: tuple[str, ...] = Field(min_length=1)


class MediaSourceSpec(TaxonomyModel):
    source_name: str = Field(min_length=1, max_length=200)
    region: Literal["DOMESTIC", "GLOBAL"]
    official_url: HttpUrl
    feed_url: HttpUrl
    allowed_host: str = Field(min_length=1, max_length=255)
    allowed_hosts: tuple[str, ...] = Field(min_length=1)
    default_category: CategoryType = "AI"
    priority: int = Field(strict=True, ge=0)


SUBTOPIC_GROUPS: tuple[SubtopicGroup, ...] = (
    # 1. AI: 모델·연구, AI 에이전트, 개발 도구, 오픈소스·로컬 모델, AI 인프라
    SubtopicGroup(
        category="AI",
        label="모델·연구",
        keywords=(
            "모델·연구",
            "파운데이션 모델",
            "멀티모달",
            "추론",
            "벤치마크",
            "시각 이해",
            "클로드",
            "플래시",
            "트랜스포머",
            "재학습",
            "알고리즘",
            "llm",
            "gpt",
            "claude",
            "gemini",
            "딥러닝",
            "강화학습",
            "humanoid",
            "model",
        ),
    ),
    SubtopicGroup(
        category="AI",
        label="AI 에이전트",
        keywords=(
            "ai 에이전트",
            "에이전트",
            "자율 에이전트",
            "멀티 에이전트",
            "워크플로우",
            "오케스트레이션",
            "보안관제",
            "siem",
            "observability",
            "비서",
            "자동화",
            "추천 ai",
            "assistant",
            "agent",
            "봇",
        ),
    ),
    SubtopicGroup(
        category="AI",
        label="개발 도구",
        keywords=(
            "개발 도구",
            "코딩",
            "코드 생성",
            "디버깅",
            "컴파일러",
            "앱",
            "솔루션",
            "소프트웨어",
            "플랫폼",
            "sdk",
            "api",
            "프레임워크",
            "ide",
            "tools",
        ),
    ),
    SubtopicGroup(
        category="AI",
        label="오픈소스·로컬 모델",
        keywords=(
            "오픈소스·로컬 모델",
            "오픈소스",
            "로컬 모델",
            "로컬 ai",
            "온디바이스",
            "경량화",
            "양자화",
            "파인튜닝",
            "가중치",
            "스파크",
            "llama",
            "huggingface",
            "open source",
        ),
    ),
    SubtopicGroup(
        category="AI",
        label="AI 인프라",
        keywords=(
            "ai 인프라",
            "gpu",
            "npu",
            "가속기",
            "데이터센터",
            "클라우드",
            "반도체",
            "메모리",
            "플래시 메모리",
            "엔비디아",
            "nvidia",
            "rtx",
            "hbm",
            "추론 서버",
            "통합플랫폼",
            "data center",
            "data centers",
            "chips",
        ),
    ),
    # 2. ECONOMY: 산업 동향, 기업·경영, 스타트업·투자, 금융시장, 일자리
    SubtopicGroup(
        category="ECONOMY",
        label="산업 동향",
        keywords=(
            "산업 동향",
            "토큰 요금제",
            "종량제",
            "과금",
            "요금제",
            "피싱",
            "통신사",
            "시장",
            "공급망",
            "제조",
            "장비",
            "국산",
            "수출",
            "수입",
            "상용화",
            "점유율",
            "생태계",
        ),
    ),
    SubtopicGroup(
        category="ECONOMY",
        label="기업·경영",
        keywords=(
            "기업·경영",
            "삼성",
            "현대차",
            "실적",
            "매출",
            "수익성",
            "영업이익",
            "인수합병",
            "파트너십",
            "경영",
            "사업화",
            "운영 경쟁력",
            "거버넌스",
            "그룹",
        ),
    ),
    SubtopicGroup(
        category="ECONOMY",
        label="스타트업·투자",
        keywords=(
            "스타트업·투자",
            "스타트업",
            "투자",
            "벤처캐피탈",
            "시리즈",
            "유니콘",
            "펀딩",
            "기업가치",
            "데모데이",
            "ipo",
            "raises",
            "valuation",
            "billion",
        ),
    ),
    SubtopicGroup(
        category="ECONOMY",
        label="금융시장",
        keywords=(
            "금융시장",
            "증시",
            "주가",
            "금리",
            "환율",
            "채권",
            "핀테크",
            "자산운용",
            "시가총액",
            "과세",
            "국세청",
            "세금",
        ),
    ),
    SubtopicGroup(
        category="ECONOMY",
        label="일자리",
        keywords=(
            "일자리",
            "연봉",
            "직장인",
            "직원",
            "근로소득",
            "복지",
            "소득세",
            "고용",
            "채용",
            "노동",
            "인력",
            "직무",
            "임금",
            "재교육",
            "생산성",
        ),
    ),
    # 3. SOCIETY: 정책·제도, 교육, 건강·의료, 환경·기후, 문화·콘텐츠
    SubtopicGroup(
        category="SOCIETY",
        label="정책·제도",
        keywords=(
            "정책·제도",
            "공공",
            "개발사업",
            "규제",
            "규제특구",
            "법안",
            "기본법",
            "가이드라인",
            "개인정보",
            "유출",
            "저작권",
            "윤리",
            "정부",
            "policy",
            "bill",
            "midterms",
        ),
    ),
    SubtopicGroup(
        category="SOCIETY",
        label="교육",
        keywords=(
            "교육",
            "대학",
            "학교",
            "디지털 교과서",
            "학습",
            "재학습",
            "에듀테크",
            "인재",
            "커리큘럼",
            "연구진",
        ),
    ),
    SubtopicGroup(
        category="SOCIETY",
        label="건강·의료",
        keywords=(
            "건강·의료",
            "건강",
            "검진",
            "안구건조증",
            "의료",
            "병원",
            "진단",
            "신약",
            "바이오",
            "헬스케어",
            "임상",
            "환자",
            "health",
        ),
    ),
    SubtopicGroup(
        category="SOCIETY",
        label="환경·기후",
        keywords=(
            "환경·기후",
            "기후",
            "탄소",
            "친환경",
            "재생에너지",
            "에너지",
            "환절기",
            "건조한",
            "자외선",
            "sunlight",
            "energy",
            "기상",
            "전력망",
            "지속가능",
        ),
    ),
    SubtopicGroup(
        category="SOCIETY",
        label="문화·콘텐츠",
        keywords=(
            "문화·콘텐츠",
            "블루 아카이브",
            "스토리",
            "이벤트",
            "콘텐츠",
            "미디어",
            "창작",
            "웹툰",
            "게임",
            "음악",
            "영상",
            "예술",
            "호텔",
            "우승",
        ),
    ),
)

# 국내 14곳 + 해외 3곳 (총 17개 공식 언론사 및 실제 RSS 피드)
OFFICIAL_MEDIA_SOURCES: tuple[MediaSourceSpec, ...] = (
    # 국내 14곳
    MediaSourceSpec(
        source_name="지디넷코리아",
        region="DOMESTIC",
        official_url=HttpUrl("https://zdnet.co.kr"),
        feed_url=HttpUrl("https://feeds.feedburner.com/zdkorea"),
        allowed_host="zdnet.co.kr",
        allowed_hosts=("feeds.feedburner.com", "zdnet.co.kr", "www.zdnet.co.kr"),
        default_category="AI",
        priority=1,
    ),
    MediaSourceSpec(
        source_name="디지털투데이",
        region="DOMESTIC",
        official_url=HttpUrl("https://www.digitaltoday.co.kr"),
        feed_url=HttpUrl("https://www.digitaltoday.co.kr/rss/allArticle.xml"),
        allowed_host="www.digitaltoday.co.kr",
        allowed_hosts=("www.digitaltoday.co.kr", "digitaltoday.co.kr"),
        default_category="AI",
        priority=2,
    ),
    MediaSourceSpec(
        source_name="AI타임스",
        region="DOMESTIC",
        official_url=HttpUrl("https://www.aitimes.com"),
        feed_url=HttpUrl("https://www.aitimes.com/rss/allArticle.xml"),
        allowed_host="www.aitimes.com",
        allowed_hosts=("www.aitimes.com", "aitimes.com"),
        default_category="AI",
        priority=3,
    ),
    MediaSourceSpec(
        source_name="전자신문",
        region="DOMESTIC",
        official_url=HttpUrl("https://www.etnews.com"),
        feed_url=HttpUrl("https://rss.etnews.com/Section901.xml"),
        allowed_host="www.etnews.com",
        allowed_hosts=("rss.etnews.com", "www.etnews.com", "etnews.com"),
        default_category="AI",
        priority=4,
    ),
    MediaSourceSpec(
        source_name="블로터",
        region="DOMESTIC",
        official_url=HttpUrl("https://www.bloter.net"),
        feed_url=HttpUrl("https://www.bloter.net/rss/allArticle.xml"),
        allowed_host="www.bloter.net",
        allowed_hosts=("www.bloter.net", "bloter.net"),
        default_category="ECONOMY",
        priority=5,
    ),
    MediaSourceSpec(
        source_name="바이라인네트워크",
        region="DOMESTIC",
        official_url=HttpUrl("https://byline.network"),
        feed_url=HttpUrl("https://byline.network/feed/"),
        allowed_host="byline.network",
        allowed_hosts=("byline.network", "www.byline.network"),
        default_category="AI",
        priority=6,
    ),
    MediaSourceSpec(
        source_name="IT조선",
        region="DOMESTIC",
        official_url=HttpUrl("https://it.chosun.com"),
        feed_url=HttpUrl("https://it.chosun.com/rss/allArticle.xml"),
        allowed_host="it.chosun.com",
        allowed_hosts=("it.chosun.com", "www.chosun.com"),
        default_category="AI",
        priority=7,
    ),
    MediaSourceSpec(
        source_name="디지털데일리",
        region="DOMESTIC",
        official_url=HttpUrl("https://www.ddaily.co.kr"),
        feed_url=HttpUrl("https://www.ddaily.co.kr/rss.xml"),
        allowed_host="www.ddaily.co.kr",
        allowed_hosts=("www.ddaily.co.kr", "ddaily.co.kr", "m.ddaily.co.kr"),
        default_category="ECONOMY",
        priority=8,
    ),
    MediaSourceSpec(
        source_name="테크M",
        region="DOMESTIC",
        official_url=HttpUrl("https://www.techm.kr"),
        feed_url=HttpUrl("https://www.techm.kr/rss/allArticle.xml"),
        allowed_host="www.techm.kr",
        allowed_hosts=("www.techm.kr", "techm.kr"),
        default_category="SOCIETY",
        priority=9,
    ),
    MediaSourceSpec(
        source_name="한국경제",
        region="DOMESTIC",
        official_url=HttpUrl("https://www.hankyung.com"),
        feed_url=HttpUrl("https://www.hankyung.com/feed/it"),
        allowed_host="www.hankyung.com",
        allowed_hosts=("www.hankyung.com", "hankyung.com"),
        default_category="ECONOMY",
        priority=10,
    ),
    MediaSourceSpec(
        source_name="매일경제",
        region="DOMESTIC",
        official_url=HttpUrl("https://www.mk.co.kr"),
        feed_url=HttpUrl("https://www.mk.co.kr/rss/30100041/"),
        allowed_host="www.mk.co.kr",
        allowed_hosts=("www.mk.co.kr", "mk.co.kr"),
        default_category="ECONOMY",
        priority=11,
    ),
    MediaSourceSpec(
        source_name="서울경제",
        region="DOMESTIC",
        official_url=HttpUrl("https://www.sedaily.com"),
        feed_url=HttpUrl("https://www.sedaily.com/rss/business"),
        allowed_host="www.sedaily.com",
        allowed_hosts=("www.sedaily.com", "sedaily.com"),
        default_category="ECONOMY",
        priority=12,
    ),
    MediaSourceSpec(
        source_name="연합뉴스",
        region="DOMESTIC",
        official_url=HttpUrl("https://www.yna.co.kr"),
        feed_url=HttpUrl("https://www.yna.co.kr/rss/industry.xml"),
        allowed_host="www.yna.co.kr",
        allowed_hosts=("www.yna.co.kr", "yna.co.kr"),
        default_category="SOCIETY",
        priority=13,
    ),
    MediaSourceSpec(
        source_name="뉴시스",
        region="DOMESTIC",
        official_url=HttpUrl("https://www.newsis.com"),
        feed_url=HttpUrl("https://www.newsis.com/RSS/industry.xml"),
        allowed_host="www.newsis.com",
        allowed_hosts=("www.newsis.com", "newsis.com"),
        default_category="SOCIETY",
        priority=14,
    ),
    # 해외 3곳
    MediaSourceSpec(
        source_name="TechCrunch",
        region="GLOBAL",
        official_url=HttpUrl("https://techcrunch.com"),
        feed_url=HttpUrl("https://techcrunch.com/category/artificial-intelligence/feed/"),
        allowed_host="techcrunch.com",
        allowed_hosts=("techcrunch.com", "www.techcrunch.com"),
        default_category="AI",
        priority=15,
    ),
    MediaSourceSpec(
        source_name="MIT Tech Review",
        region="GLOBAL",
        official_url=HttpUrl("https://www.technologyreview.com"),
        feed_url=HttpUrl("https://www.technologyreview.com/feed/"),
        allowed_host="www.technologyreview.com",
        allowed_hosts=("www.technologyreview.com", "technologyreview.com"),
        default_category="AI",
        priority=16,
    ),
    MediaSourceSpec(
        source_name="The Verge",
        region="GLOBAL",
        official_url=HttpUrl("https://www.theverge.com"),
        feed_url=HttpUrl("https://www.theverge.com/rss/index.xml"),
        allowed_host="www.theverge.com",
        allowed_hosts=("www.theverge.com", "theverge.com"),
        default_category="SOCIETY",
        priority=17,
    ),
)

OFFICIAL_SOURCE_NAMES: frozenset[str] = frozenset(
    spec.source_name for spec in OFFICIAL_MEDIA_SOURCES
)
DOMESTIC_SOURCE_NAMES: frozenset[str] = frozenset(
    spec.source_name for spec in OFFICIAL_MEDIA_SOURCES if spec.region == "DOMESTIC"
)
GLOBAL_SOURCE_NAMES: frozenset[str] = frozenset(
    spec.source_name for spec in OFFICIAL_MEDIA_SOURCES if spec.region == "GLOBAL"
)


def match_category(
    title: str,
    content: str | None = None,
    default: CategoryType = "AI",
) -> CategoryType:
    """Classify an article into AI, ECONOMY, or SOCIETY based on title and body keywords."""
    normalized_title = title.casefold()
    normalized_body = (content or "").casefold()

    ai_score = 0
    economy_score = 0
    society_score = 0

    for group in SUBTOPIC_GROUPS:
        matches = 0
        for keyword in group.keywords:
            token = keyword.casefold()
            if token in normalized_title:
                matches += 3
            if token in normalized_body:
                matches += 1
        if group.category == "AI":
            ai_score += matches
        elif group.category == "ECONOMY":
            economy_score += matches
        else:
            society_score += matches

    if ai_score == 0 and economy_score == 0 and society_score == 0:
        return default
    if economy_score > ai_score and economy_score >= society_score:
        return "ECONOMY"
    if society_score > ai_score and society_score > economy_score:
        return "SOCIETY"
    return "AI"


def matches_subtopic_or_query(category: CategoryType, query_q: str | None, searchable: str) -> bool:
    """Check whether searchable text matches query_q directly or via a subtopic keyword group."""
    if query_q is None:
        return True
    lowered_text = searchable.casefold()
    lowered_q = query_q.casefold()
    if lowered_q in lowered_text:
        return True
    for group in SUBTOPIC_GROUPS:
        if group.category == category and group.label.casefold() == lowered_q:
            return any(keyword.casefold() in lowered_text for keyword in group.keywords)
    return False

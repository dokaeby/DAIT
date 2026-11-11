"""사용자별 관심사를 읽고 현재 제공하는 카테고리만 저장합니다."""
from dait import news
from dait.repositories.user_repository import load_interests, save_interests


UI_INTERESTS = [
    "모델·연구",
    "AI 에이전트",
    "개발 도구",
    "오픈소스·로컬 모델",
    "AI 인프라",
    "산업 동향",
    "기업·경영",
    "스타트업·투자",
    "금융시장",
    "일자리",
    "정책·제도",
    "교육",
    "건강·의료",
    "환경·기후",
    "문화·콘텐츠"
]


# 기능: 설정 화면에서 선택 가능한 관심 카테고리를 제공한다.
# 입력: 없음.
# 출력: 카테고리 문자열 튜플.
def category_options() -> tuple[str, ...]:
    return tuple(UI_INTERESTS)


# 기능: 사용자에게 저장된 화면용 관심 카테고리를 조회한다.
# 입력:
#   user (str | None): 현재 사용자 이름(비로그인은 None).
# 출력: 카테고리 문자열 튜플.
def selected_ui_interests(user: str | None) -> tuple[str, ...]:
    if user is None:
        return ()
    return tuple(value for value in load_interests(user, news.USERS) if value in UI_INTERESTS)


# 기능: 저장된 화면 관심사를 기사 검색용 카테고리로 변환한다.
# 입력:
#   user (str | None): 현재 사용자 이름(비로그인은 None).
# 출력: 기사 검색에 사용할 카테고리 튜플.
def user_interests(user: str | None) -> tuple[str, ...]:
    if user is None:
        return ()
    stored = load_interests(user, news.USERS)
    selected = set(stored)
    ui_selected = tuple(category for category in UI_INTERESTS if category in selected)
    if ui_selected:
        return ui_selected
    available = set(news.available_categories())
    return tuple(category for category in stored if category in available)


# 기능: 로그인 사용자의 관심사 초기 설정 필요 여부를 확인한다.
# 입력:
#   user (str | None): 현재 사용자 이름(비로그인은 None).
# 출력: 초기 설정이 필요하면 True, 아니면 False.
def needs_interest_onboarding(user: str | None) -> bool:
    # 로그인 직후 안내 여부만 판단합니다. 미설정이어도 다른 화면 진입은 허용합니다.
    return user is not None and not load_interests(user, news.USERS)


# 기능: 선택 가능한 관심사인지 검사한 뒤 사용자별로 저장한다.
# 입력:
#   user (str): 현재 사용자 이름(비로그인은 None).
#   categories (list[str]): 카테고리 목록.
# 출력: 저장한 카테고리 튜플. 잘못된 선택 시 ValueError.
def update_interests(user: str, categories: list[str]) -> tuple[str, ...]:
    if not categories:
        raise ValueError("관심 카테고리를 한 개 이상 선택해주세요.")
    if not set(categories).issubset(set(category_options())):
        raise ValueError("선택할 수 없는 카테고리가 있습니다. 화면을 새로고침해주세요.")
    legacy = [value for value in load_interests(user, news.USERS) if value not in UI_INTERESTS]
    save_interests(user, legacy + categories, news.USERS)
    return tuple(categories)

"""사용자별 관심사를 읽고 현재 제공하는 카테고리만 저장합니다."""
from dait import news
from dait.repositories.user_repository import load_interests, save_interests


def category_options() -> tuple[str, ...]:
    return tuple(news.available_categories())


def user_interests(user: str | None) -> tuple[str, ...]:
    if user is None:
        return ()
    available = set(category_options())
    return tuple(category for category in load_interests(user, news.USERS) if category in available)


def needs_interest_onboarding(user: str | None) -> bool:
    # 로그인 직후 안내 여부만 판단합니다. 미설정이어도 다른 화면 진입은 허용합니다.
    return user is not None and not user_interests(user)


def update_interests(user: str, categories: list[str]) -> tuple[str, ...]:
    if not categories:
        raise ValueError("관심 카테고리를 한 개 이상 선택해주세요.")
    if not set(categories).issubset(set(category_options())):
        raise ValueError("선택할 수 없는 카테고리가 있습니다. 화면을 새로고침해주세요.")
    return save_interests(user, categories, news.USERS)

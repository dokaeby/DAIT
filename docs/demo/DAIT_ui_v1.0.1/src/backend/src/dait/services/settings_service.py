"""KAN-10 설정 화면 유스케이스: 설정 저장, 카테고리 표시 순서, 선호 검색어, 예약 알림 소식함.

규칙 함수(카테고리 정렬·검색어 일치·예약 시각 계산·소식 고르기)는 I/O 없이 두어 단위 테스트를 쉽게 합니다.
"""

import logging
import secrets
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from typing import NamedTuple

from dait import news
from dait.repositories import settings_repository
from dait.repositories.user_repository import username_key
from dait.schemas import Digest, DigestItem, InboxState, SettingsState, UserSettings
from dait.services.preference_service import category_options, user_interests

logger = logging.getLogger(__name__)
# Asia/Seoul은 서머타임이 없어 고정 오프셋으로 충분합니다. Windows에 tzdata가 없어도 동작합니다.
KST = timezone(timedelta(hours=9), "KST")
WEEKDAYS = ("월", "화", "수", "목", "금", "토", "일")


class ArticleRow(NamedTuple):
    """news_repository가 돌려주는 기사 행과 같은 순서입니다."""

    id: str
    title: str
    source: str
    published_at: str
    categories: str | None
    is_foreign: int
    description: str | None


class MainPreferences(NamedTuple):
    """메인 화면에 적용할 개인 설정."""

    keywords: tuple[str, ...]
    display_count: int
    category_order: tuple[str, ...]
    hidden_categories: tuple[str, ...]
    inbox_unseen: int


# ---- 순수 규칙 ----


def order_categories(
    available: Sequence[str], settings: UserSettings, include_hidden: bool = False
) -> list[str]:
    """저장한 순서대로, 순서에 없는 새 카테고리는 뒤에 원래 순서로 붙입니다."""
    rank = {name: index for index, name in enumerate(settings.category_order)}
    ordered = sorted(
        available, key=lambda name: (rank.get(name, len(rank)), list(available).index(name))
    )
    if include_hidden:
        return ordered
    hidden = set(settings.hidden_categories)
    return [name for name in ordered if name not in hidden]


def keyword_hits(text: str, keywords: Sequence[str]) -> list[str]:
    folded = text.casefold()
    return [word for word in keywords if word.casefold() in folded]


def _at(day: datetime, clock: str) -> datetime:
    hour, minute = (int(part) for part in clock.split(":"))
    return day.replace(hour=hour, minute=minute, second=0, microsecond=0)


def due_at(settings: UserSettings, now: datetime) -> datetime | None:
    """오늘 지난 예약 시각 중 가장 최근 것. 오늘 지난 시각이 없으면 None."""
    schedule = settings.schedule
    if not schedule.enabled:
        return None
    local = now.astimezone(KST)
    if local.weekday() not in schedule.days:
        return None
    passed = [_at(local, clock) for clock in schedule.times if _at(local, clock) <= local]
    return max(passed) if passed else None


def is_due(settings: UserSettings, saved_at: int, last_run_at: int, now: datetime) -> bool:
    # 저장하기 전에 이미 지난 시각은 실행하지 않습니다. 예약을 바꾸자마자 소식이 쏟아지는 것을 막습니다.
    planned = due_at(settings, now)
    if planned is None:
        return False
    stamp = int(planned.timestamp())
    return stamp > last_run_at and stamp >= saved_at


def next_run(settings: UserSettings, now: datetime) -> datetime | None:
    schedule = settings.schedule
    if not schedule.enabled or not schedule.days or not schedule.times:
        return None
    local = now.astimezone(KST)
    for offset in range(8):
        day = local + timedelta(days=offset)
        if day.weekday() not in schedule.days:
            continue
        upcoming = [_at(day, clock) for clock in schedule.times if _at(day, clock) > local]
        if upcoming:
            return min(upcoming)
    return None


def format_run(moment: datetime | None) -> str | None:
    if moment is None:
        return None
    local = moment.astimezone(KST)
    return f"{local.month}/{local.day}({WEEKDAYS[local.weekday()]}) {local:%H:%M} KST"


def _published_ts(raw: str) -> int:
    try:
        moment = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return 0
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return int(moment.timestamp())


def pick_digest_items(
    rows: Sequence[ArticleRow], interests: Sequence[str], settings: UserSettings, since: int
) -> tuple[DigestItem, ...]:
    """지난 소식 이후 새 기사 중 관심 카테고리 또는 선호 검색어와 맞는 것을 최신순으로 고릅니다."""
    sources = settings.schedule.sources
    picked: list[DigestItem] = []
    for row in sorted(rows, key=lambda r: r.published_at, reverse=True):
        if _published_ts(row.published_at) <= since:
            continue
        reasons: list[str] = []
        categories = [c for c in (row.categories or "").split(" · ") if c]
        if "interests" in sources:
            matched = [c for c in categories if c in interests]
            if matched:
                reasons.append(f"관심 카테고리 '{', '.join(matched)}'와 일치")
        if "keywords" in sources:
            words = keyword_hits(f"{row.title}\n{row.description or ''}", settings.keywords)
            if words:
                reasons.append(f"선호 검색어 '{', '.join(words)}' 포함")
        if not reasons:
            continue
        picked.append(
            DigestItem(
                article_id=row.id,
                title=row.title,
                source=row.source,
                published_at=row.published_at,
                categories=row.categories or "기타",
                reason=" · ".join(reasons),
            )
        )
        if len(picked) >= settings.schedule.max_items:
            break
    return tuple(picked)


# ---- 유스케이스 ----


def load_settings(user: str) -> UserSettings:
    stored = settings_repository.load_settings(username_key(user))
    return stored[0] if stored else UserSettings()


def available_categories() -> list[str]:
    return list(news.available_categories())


def orderable_categories(user: str) -> list[str]:
    """메인 칩으로 보이는 카테고리: 선택한 관심사, 없으면 기사 카테고리 전체(news.page와 같은 규칙)."""
    return list(user_interests(user)) or available_categories()


def settings_state(user: str, now: datetime) -> SettingsState:
    stored = settings_repository.load_settings(username_key(user))
    settings = stored[0] if stored else UserSettings()
    return SettingsState(
        settings=settings,
        saved=stored is not None,
        available_categories=order_categories(
            orderable_categories(user), settings, include_hidden=True
        ),
        next_run=format_run(next_run(settings, now)),
    )


def save_settings(user: str, settings: UserSettings, now: datetime) -> SettingsState:
    # 관심사를 바꾸면 순서 목록에 예전 카테고리가 남을 수 있어, 화면에 나올 수 있는 이름 전체를 허용합니다.
    available = set(available_categories()) | set(category_options())
    unknown = (set(settings.category_order) | set(settings.hidden_categories)) - available
    if unknown:
        raise ValueError("선택할 수 없는 카테고리가 있습니다. 화면을 새로고침해주세요.")
    settings_repository.save_settings(username_key(user), settings, int(now.timestamp()))
    return settings_state(user, now)


def main_preferences(user: str | None) -> MainPreferences | None:
    if user is None:
        return None
    settings = load_settings(user)
    unseen = (
        settings_repository.unseen_count(username_key(user)) if settings.in_app_notification else 0
    )
    return MainPreferences(
        keywords=settings.keywords,
        display_count=settings.display_count,
        category_order=settings.category_order,
        hidden_categories=settings.hidden_categories,
        inbox_unseen=unseen,
    )


def _article_rows() -> list[ArticleRow]:
    # news_repository는 타입 표기가 없는 기존 모듈이라 여기서 ArticleRow로 형태를 고정합니다.
    rows: list[tuple[str, str, str, str, str | None, int, str | None]] = (
        news.news_repository.latest_rows(news.DB, -1)  # pyright: ignore[reportUnknownMemberType]
    )
    return [ArticleRow(*row) for row in rows]


def create_digest(
    user: str, settings: UserSettings, now: datetime, since: int, scheduled_for: int | None
) -> Digest | None:
    digest = Digest(
        id=f"d{int(now.timestamp())}{secrets.token_hex(4)}",
        created_at=int(now.timestamp()),
        manual=scheduled_for is None,
        seen=False,
        items=pick_digest_items(_article_rows(), user_interests(user), settings, since),
    )
    saved = settings_repository.add_digest(username_key(user), digest, scheduled_for)
    return digest if saved else None


def run_now(user: str, now: datetime) -> Digest | None:
    """'지금 한 번 받아보기': 시간 조건 없이 현재 맞는 기사를 바로 소식함에 넣습니다."""
    return create_digest(user, load_settings(user), now, since=0, scheduled_for=None)


def run_due_schedules(now: datetime) -> int:
    """예약 시각이 된 계정마다 소식을 하나씩 만듭니다. 만든 개수를 돌려줍니다."""
    created = 0
    for owner_key, settings, saved_at, last_run_at in settings_repository.scheduled_owners():
        if not is_due(settings, saved_at, last_run_at, now):
            continue
        planned = due_at(settings, now)
        if planned is None:
            continue
        # owner_key는 정규화된 아이디라 관심사 조회에 그대로 쓸 수 있습니다.
        if create_digest(
            owner_key, settings, now, since=last_run_at, scheduled_for=int(planned.timestamp())
        ):
            created += 1
            logger.info("예약 소식 생성: %s", owner_key)
    return created


def inbox(user: str) -> InboxState:
    owner = username_key(user)
    return InboxState(
        unseen=settings_repository.unseen_count(owner),
        digests=settings_repository.list_digests(owner),
    )


def mark_inbox_seen(user: str) -> None:
    settings_repository.mark_seen(username_key(user))

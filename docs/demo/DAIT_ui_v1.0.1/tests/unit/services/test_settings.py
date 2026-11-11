"""KAN-10 설정·카테고리 표시 순서·선호 검색어·예약 알림 단위 테스트."""

from datetime import UTC, datetime

import pytest
from backend.main import app
from backend.pipelines import collect_news
from dait.repositories import settings_repository
from dait.schemas import ScheduleSettings, UserSettings
from dait.services import settings_service
from dait.services.settings_service import ArticleRow
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend import news

# 2026-11-09(월) 08:40 KST
MONDAY_0840_KST = datetime(2026, 11, 8, 23, 40, tzinfo=UTC)


def make_article(index, title, categories, published_at, summary="설명"):
    return dict(
        id=f"news_{index:03d}",
        title=title,
        source="테스트 출처",
        published_at=published_at,
        summary=[summary],
        content=summary,
        original_url=f"https://example.com/news/{index}",
        is_foreign=False,
        categories=categories,
    )


@pytest.fixture
def articles(runtime):
    collect_news.save_articles(
        [
            make_article(1, "HBM 증산 소식", ["반도체"], "2026-11-08T22:00:00+00:00"),
            make_article(2, "새 AI 모델 공개", ["인공지능"], "2026-11-08T21:00:00+00:00"),
            make_article(3, "클라우드 요금 개편", ["클라우드"], "2026-11-08T20:00:00+00:00"),
            make_article(
                4,
                "보안 패치 안내",
                ["보안"],
                "2026-11-08T19:00:00+00:00",
                summary="HBM 공급망 보안",
            ),
        ]
    )


@pytest.fixture
def client(runtime):
    with TestClient(app) as value:
        yield value


def login(client, user="user1"):
    response = client.post(
        "/login", data=dict(user=user, password=news.TEST_PASSWORD), follow_redirects=False
    )
    assert response.status_code == 303


# ---- 모델 검증 ----


def test_keywords_are_trimmed_and_deduplicated():
    settings = UserSettings(keywords=("  HBM  ", "hbm", "AI   에이전트", ""))
    assert settings.keywords == ("HBM", "AI 에이전트")


def test_more_than_three_keywords_is_rejected():
    with pytest.raises(ValidationError, match="최대 3개"):
        UserSettings(keywords=("a", "b", "c", "d"))


def test_long_keyword_is_rejected():
    with pytest.raises(ValidationError, match="30자"):
        UserSettings(keywords=("가" * 31,))


@pytest.mark.parametrize("value", ["24:00", "8:30", "08:60", "08:15", "아침"])
def test_invalid_schedule_time_is_rejected(value):
    with pytest.raises(ValidationError):
        ScheduleSettings(times=(value,))


def test_schedule_needs_a_source_and_known_fields():
    with pytest.raises(ValidationError):
        ScheduleSettings(sources=())
    with pytest.raises(ValidationError):
        UserSettings.model_validate({"unknown": 1})


# ---- 순수 규칙 ----


def test_categories_follow_saved_order_and_hide():
    settings = UserSettings(category_order=("반도체", "인공지능"), hidden_categories=("기타",))
    available = ["기타", "보안", "반도체", "인공지능"]
    assert settings_service.order_categories(available, settings) == ["반도체", "인공지능", "보안"]
    assert settings_service.order_categories(available, settings, include_hidden=True) == [
        "반도체",
        "인공지능",
        "기타",
        "보안",
    ]


def test_keyword_hits_ignore_case():
    assert settings_service.keyword_hits("SK하이닉스 hbm4 양산", ("HBM", "엔비디아")) == ["HBM"]


def test_schedule_is_due_once_after_its_time():
    settings = UserSettings(schedule=ScheduleSettings(times=("08:30",), days=(0,)))
    saved_at = int(datetime(2026, 11, 8, 12, 0, tzinfo=UTC).timestamp())
    planned = settings_service.due_at(settings, MONDAY_0840_KST)
    assert planned is not None and planned.strftime("%H:%M") == "08:30"
    assert settings_service.is_due(settings, saved_at, 0, MONDAY_0840_KST)
    assert not settings_service.is_due(
        settings, saved_at, int(planned.timestamp()), MONDAY_0840_KST
    )


def test_schedule_not_due_on_other_day_before_time_disabled_or_saved_later():
    saved_at = int(datetime(2026, 11, 8, 12, 0, tzinfo=UTC).timestamp())
    base = ScheduleSettings(times=("08:30",), days=(0,))
    assert not settings_service.is_due(
        UserSettings(schedule=base.model_copy(update={"days": (1,)})), saved_at, 0, MONDAY_0840_KST
    )
    assert not settings_service.is_due(
        UserSettings(schedule=base.model_copy(update={"times": ("09:00",)})),
        saved_at,
        0,
        MONDAY_0840_KST,
    )
    assert not settings_service.is_due(
        UserSettings(schedule=base.model_copy(update={"enabled": False})),
        saved_at,
        0,
        MONDAY_0840_KST,
    )
    # 08:35에 저장했다면 오늘 08:30은 이미 지난 시각이라 실행하지 않습니다.
    saved_after = int(datetime(2026, 11, 8, 23, 35, tzinfo=UTC).timestamp())
    assert not settings_service.is_due(UserSettings(schedule=base), saved_after, 0, MONDAY_0840_KST)


def test_next_run_skips_to_next_selected_day():
    settings = UserSettings(schedule=ScheduleSettings(times=("08:30",), days=(2,)))
    assert (
        settings_service.format_run(settings_service.next_run(settings, MONDAY_0840_KST))
        == "11/11(수) 08:30 KST"
    )
    assert (
        settings_service.next_run(
            UserSettings(schedule=ScheduleSettings(enabled=False)), MONDAY_0840_KST
        )
        is None
    )


def test_digest_picks_new_matching_articles_with_reasons():
    rows = [
        ArticleRow("a", "HBM 증산", "출처", "2026-11-08T22:00:00+00:00", "반도체", 0, ""),
        ArticleRow("b", "AI 모델", "출처", "2026-11-08T21:00:00+00:00", "인공지능", 0, ""),
        ArticleRow("c", "관계없는 기사", "출처", "2026-11-08T20:00:00+00:00", "클라우드", 0, ""),
        ArticleRow("d", "HBM 옛 기사", "출처", "2026-11-01T00:00:00+00:00", "반도체", 0, ""),
    ]
    settings = UserSettings(keywords=("HBM",))
    since = int(datetime(2026, 11, 5, tzinfo=UTC).timestamp())
    items = settings_service.pick_digest_items(rows, ("인공지능",), settings, since)
    assert [item.article_id for item in items] == ["a", "b"]
    assert "선호 검색어 'HBM'" in items[0].reason
    assert "관심 카테고리 '인공지능'" in items[1].reason
    only_keywords = UserSettings(
        keywords=("HBM",), schedule=ScheduleSettings(sources=("keywords",))
    )
    assert [
        i.article_id
        for i in settings_service.pick_digest_items(rows, ("인공지능",), only_keywords, since)
    ] == ["a"]


# ---- API·화면 ----


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/settings"),
        ("PUT", "/api/settings"),
        ("GET", "/api/inbox"),
        ("POST", "/api/inbox/run"),
    ],
)
def test_settings_api_requires_login(client, method, path):
    response = client.request(
        method, path, json=UserSettings().model_dump(mode="json") if method == "PUT" else None
    )
    assert response.status_code == 401


@pytest.mark.parametrize("path", ["/settings", "/inbox"])
def test_settings_pages_redirect_guests(client, path):
    assert client.get(path, follow_redirects=False).status_code == 303


def test_settings_are_saved_and_restored(client, articles):
    login(client)
    body = UserSettings(
        keywords=(" HBM ", "hbm", "클라우드"),
        category_order=("반도체", "인공지능"),
        hidden_categories=("보안",),
        display_count=5,
        schedule=ScheduleSettings(times=("09:00", "18:30"), days=(0, 2)),
    ).model_dump(mode="json")
    body["keywords"] = [" HBM ", "hbm", "클라우드"]
    response = client.put("/api/settings", json=body)
    assert response.status_code == 200
    saved = client.get("/api/settings").json()
    assert saved["settings"]["keywords"] == ["HBM", "클라우드"]
    assert saved["settings"]["schedule"]["times"] == ["09:00", "18:30"]
    # 순서 목록은 메인 칩과 같이 선택한 관심 카테고리만 보여줍니다(user1: 인공지능).
    assert saved["available_categories"] == ["인공지능"]
    assert saved["settings"]["category_order"] == ["반도체", "인공지능"]
    assert saved["saved"] is True
    page = client.get("/settings").text
    assert 'id="settings-data"' in page and '"09:00"' in page


def test_unknown_category_and_fourth_keyword_change_nothing(client, articles):
    login(client)
    assert client.put("/api/settings", json={"category_order": ["없는분야"]}).status_code == 400
    assert client.put("/api/settings", json={"keywords": ["a", "b", "c", "d"]}).status_code == 422
    assert client.put("/api/settings", json={"schedule": {"time": "25:00"}}).status_code == 422
    assert client.get("/api/settings").json()["settings"] == UserSettings().model_dump(mode="json")


def test_main_page_uses_saved_preferences(client, articles):
    login(client, "user2")  # 관심: 보안, 클라우드
    client.put(
        "/api/settings",
        json={"keywords": ["HBM"], "category_order": ["클라우드", "보안"], "display_count": 5},
    )
    html = client.get("/").text
    assert 'data-keyword="HBM"' in html
    assert html.index('data-category="클라우드"') < html.index('data-category="보안"')
    client.put("/api/settings", json={"hidden_categories": ["보안"]})
    assert 'data-category="보안"' not in client.get("/").text


def test_run_now_fills_inbox_and_opening_marks_seen(client, articles):
    login(client)
    client.put("/api/settings", json={"keywords": ["HBM"]})
    digest = client.post("/api/inbox/run").json()
    assert {item["article_id"] for item in digest["items"]} == {"news_001", "news_002", "news_004"}
    assert client.get("/api/inbox").json()["unseen"] == 1
    assert "새 1" in client.get("/").text
    page = client.get("/inbox").text
    assert "새 소식" in page and "선호 검색어 &#x27;HBM&#x27; 포함" in page
    assert client.get("/api/inbox").json()["unseen"] == 0
    assert "inbox-badge" not in client.get("/").text


def test_in_app_notification_off_hides_badge(client, articles):
    login(client)
    client.put("/api/settings", json={"in_app_notification": False})
    client.post("/api/inbox/run")
    assert "inbox-badge" not in client.get("/").text


def test_scheduler_creates_one_digest_per_slot(runtime, articles):
    owner = "user1"
    settings = UserSettings(
        keywords=("HBM",), schedule=ScheduleSettings(times=("08:30",), days=(0,))
    )
    settings_repository.save_settings(
        owner, settings, int(datetime(2026, 11, 8, 12, tzinfo=UTC).timestamp())
    )
    assert settings_service.run_due_schedules(MONDAY_0840_KST) == 1
    assert settings_service.run_due_schedules(MONDAY_0840_KST) == 0
    digests = settings_repository.list_digests(owner)
    assert len(digests) == 1 and not digests[0].manual
    assert digests[0].items[0].article_id == "news_001"


def test_inbox_keeps_latest_thirty(runtime, articles):
    for minute in range(35):
        settings_service.run_now("user1", datetime(2026, 11, 9, 0, minute, tzinfo=UTC))
    assert (
        len(settings_repository.list_digests("user1")) == settings_repository.MAX_DIGESTS_PER_USER
    )


def test_schedule_times_are_sorted_unique_and_limited_to_five():
    assert ScheduleSettings(times=("18:30", "08:00", "08:00")).times == ("08:00", "18:30")
    with pytest.raises(ValidationError):
        ScheduleSettings(times=("00:00", "01:00", "02:00", "03:00", "04:00", "05:00"))


def test_legacy_single_time_is_read_as_times():
    legacy = UserSettings.model_validate_json('{"schedule": {"time": "09:45", "days": [0]}}')
    assert legacy.schedule.times == ("09:30",)


def test_multiple_times_fire_latest_passed_slot_and_next_run():
    # 08:40 KST 월요일: 08:30은 지났고 12:00은 남았습니다.
    settings = UserSettings(schedule=ScheduleSettings(times=("08:30", "12:00", "07:00"), days=(0,)))
    planned = settings_service.due_at(settings, MONDAY_0840_KST)
    assert planned is not None and planned.strftime("%H:%M") == "08:30"
    upcoming = settings_service.next_run(settings, MONDAY_0840_KST)
    assert settings_service.format_run(upcoming) == "11/9(월) 12:00 KST"

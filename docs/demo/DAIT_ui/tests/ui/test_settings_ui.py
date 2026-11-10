"""KAN-10 설정·예약 UI 자동화 (13_UI_자동화_test_cases의 UI-AUTH-001, UI-SET-001~009, UI-STATE-004 + KAN-10 추가)."""

import pytest
from playwright.sync_api import Page, Request, expect

pytestmark = pytest.mark.ui


def put_requests(page: Page) -> list[Request]:
    requests: list[Request] = []
    page.on(
        "request",
        lambda r: (
            requests.append(r) if r.method == "PUT" and r.url.endswith("/api/settings") else None
        ),
    )
    return requests


def save(page: Page) -> None:
    page.get_by_role("button", name="설정 저장").click()
    expect(page.locator("#settings-feedback")).to_contain_text("설정을 저장했습니다")


def test_ui_auth_001_guest_cannot_open_settings(page: Page, base_url: str):
    page.goto(base_url + "/settings")
    expect(page).to_have_url(base_url + "/")
    expect(page.locator("#settings-form")).to_have_count(0)


def test_ui_set_001_screen_matches_saved_settings(member_page: Page, base_url: str):
    page = member_page
    page.goto(base_url + "/settings")
    api = page.request.get(base_url + "/api/settings").json()["settings"]
    expect(page.locator("#collection-time")).to_have_value(api["schedule"]["time"])
    expect(page.locator("#schedule-timezone")).to_have_value("Asia/Seoul")
    expect(page.locator("#display-count")).to_have_value(str(api["display_count"]))
    expect(page.locator("#schedule-enabled")).to_be_checked()
    expect(page.locator("#in-app-notification")).to_be_checked()
    expect(page.locator('[data-day="0"]')).to_have_attribute("aria-pressed", "true")


def test_ui_set_002_change_time_saves_once_and_shows_next_run(member_page: Page, base_url: str):
    page = member_page
    page.goto(base_url + "/settings")
    puts = put_requests(page)
    page.locator("#collection-time").fill("09:00")
    save(page)
    assert len(puts) == 1
    assert puts[0].post_data_json["schedule"]["time"] == "09:00"
    expect(page.locator("#schedule-preview")).to_contain_text("09:00")
    expect(page.locator("#settings-feedback")).to_contain_text("09:00 KST")


def test_ui_set_003_disabling_schedule_survives_reload(member_page: Page, base_url: str):
    page = member_page
    page.goto(base_url + "/settings")
    page.locator("label.switch-control:has(#schedule-enabled)").click()
    expect(page.locator("#schedule-state")).to_have_text("사용 안 함")
    save(page)
    page.reload()
    expect(page.locator("#schedule-enabled")).not_to_be_checked()
    expect(page.locator("#schedule-preview")).to_have_text("예약 알림을 사용하지 않습니다.")


def test_ui_set_005_keywords_are_trimmed_deduplicated_and_restored(
    member_page: Page, base_url: str
):
    page = member_page
    page.goto(base_url + "/settings")
    box = page.locator("#keyword-input")
    box.fill("  HBM  ")
    box.press("Enter")
    box.fill("hbm")
    box.press("Enter")
    expect(page.locator("#keyword-error")).to_have_text("이미 등록한 검색어입니다.")
    box.fill("AI   에이전트")
    box.press("Enter")
    save(page)
    page.reload()
    tags = page.locator("#keyword-preview .input-tag")
    expect(tags).to_have_count(2)
    expect(tags.nth(0)).to_contain_text("HBM")
    expect(tags.nth(1)).to_contain_text("AI 에이전트")


def test_ui_set_007_fourth_keyword_is_blocked_without_request(member_page: Page, base_url: str):
    page = member_page
    page.goto(base_url + "/settings")
    puts = put_requests(page)
    box = page.locator("#keyword-input")
    for word in ["가", "나", "다", "라"]:
        box.fill(word)
        box.press("Enter")
    expect(page.locator("#keyword-error")).to_have_text(
        "선호 검색어는 최대 3개까지 저장할 수 있습니다."
    )
    expect(box).to_have_attribute("aria-invalid", "true")
    assert puts == []


def test_ui_set_009_saved_values_come_back_in_a_new_page(member_page: Page, base_url: str):
    page = member_page
    page.goto(base_url + "/settings")
    page.locator("#display-count").select_option("5")
    page.locator('[data-day="6"]').click()
    save(page)
    fresh = page.context.new_page()
    fresh.goto(base_url + "/settings")
    expect(fresh.locator("#display-count")).to_have_value("5")
    expect(fresh.locator('[data-day="6"]')).to_have_attribute("aria-pressed", "false")
    fresh.close()


def test_ui_state_004_double_click_saves_once(member_page: Page, base_url: str):
    page = member_page
    page.goto(base_url + "/settings")
    puts = put_requests(page)
    page.get_by_role("button", name="설정 저장").dblclick()
    expect(page.locator("#settings-feedback")).to_contain_text("설정을 저장했습니다")
    page.wait_for_timeout(300)
    assert len(puts) == 1


def test_kan10_category_order_and_hide_apply_to_main(member_page: Page, base_url: str):
    page = member_page
    page.goto(base_url + "/settings")
    page.get_by_role("button", name="클라우드 위로").click()
    page.get_by_role("button", name="클라우드 위로").click()
    page.get_by_role("button", name="클라우드 위로").click()
    page.locator('[data-category-name="보안"] label.switch-control').click()
    expect(page.locator(".category-name").first).to_have_text("클라우드")
    save(page)
    page.goto(base_url + "/")
    chips = page.locator("[data-category]")
    expect(chips.nth(1)).to_have_text("클라우드")
    expect(page.locator('[data-category="보안"]')).to_have_count(0)


def test_kan10_keyword_chip_searches_main(member_page: Page, base_url: str):
    page = member_page
    page.goto(base_url + "/settings")
    page.locator("#keyword-input").fill("HBM")
    page.locator("#keyword-input").press("Enter")
    save(page)
    page.goto(base_url + "/")
    page.locator('[data-keyword="HBM"]').click()
    expect(page.locator("#query")).to_have_value("HBM")
    expect(page).to_have_url(base_url + "/?sort=rank&q=HBM")
    expect(page.locator(".news-title")).to_have_count(1)
    expect(page.locator(".news-title")).to_contain_text("HBM 증산")


def test_kan10_run_now_fills_inbox_and_clears_badge(member_page: Page, base_url: str):
    page = member_page
    page.goto(base_url + "/settings")
    page.locator("#keyword-input").fill("HBM")
    page.locator("#keyword-input").press("Enter")
    save(page)
    page.get_by_role("button", name="지금 한 번 받아보기").click()
    expect(page.locator("#run-feedback")).to_contain_text("1건을 넣었습니다")
    page.goto(base_url + "/")
    expect(page.locator("#inbox-nav .inbox-badge")).to_have_text("새 1")
    page.locator("#inbox-nav").click()
    expect(page.locator(".digest .status-tag")).to_have_text("새 소식")
    expect(page.locator(".digest-reason")).to_contain_text("선호 검색어 'HBM' 포함")
    page.goto(base_url + "/")
    expect(page.locator("#inbox-nav .inbox-badge")).to_have_count(0)

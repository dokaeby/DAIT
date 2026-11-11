"""KAN-10 설정·예약 UI 자동화 (13_UI_자동화_test_cases의 UI-AUTH-001, UI-SET-001~009, UI-STATE-004 + KAN-10 추가).

macOS Safari와 같은 엔진(WebKit)과 Chromium에서 모두 실행합니다.
    python -m pytest tests/ui --browser chromium --browser webkit
"""

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


def add_time(page: Page, hour: str, minute: str) -> None:
    page.locator("#schedule-hour").fill(hour)
    page.locator("#schedule-minute").select_option(minute)
    page.get_by_role("button", name="시간 추가").click()


def add_keyword(page: Page, word: str) -> None:
    page.locator("#keyword-input").fill(word)
    page.get_by_role("button", name="추가", exact=True).click()


def test_ui_auth_001_guest_cannot_open_settings(page: Page, base_url: str):
    page.goto(base_url + "/settings")
    expect(page).to_have_url(base_url + "/")
    expect(page.locator("#schedule")).to_have_count(0)


def test_ui_set_001_screen_matches_saved_settings(member_page: Page, base_url: str):
    page = member_page
    page.goto(base_url + "/settings")
    api = page.request.get(base_url + "/api/settings").json()["settings"]
    chips = page.locator("#schedule-chips .schedule-chip")
    expect(chips).to_have_count(len(api["schedule"]["times"]))
    expect(chips.first).to_contain_text(api["schedule"]["times"][0])
    expect(page.locator("#display-count")).to_have_value(str(api["display_count"]))
    expect(page.locator("#schedule-enabled")).to_be_checked()
    expect(page.locator("#in-app-notification")).to_be_checked()
    expect(page.locator('[data-day="0"]')).to_have_attribute("aria-pressed", "true")


def test_ui_set_002_add_time_saves_once_and_shows_next_run(member_page: Page, base_url: str):
    page = member_page
    page.goto(base_url + "/settings")
    puts = put_requests(page)
    add_time(page, "9", "00")
    expect(page.locator("#schedule-count")).to_have_text("2 / 5")
    save(page)
    assert len(puts) == 1
    assert puts[0].post_data_json["schedule"]["times"] == ["08:30", "09:00"]
    expect(page.locator("#schedule-preview")).to_contain_text("08:30, 09:00 KST")
    page.reload()
    expect(page.locator("#schedule-chips .schedule-chip")).to_have_count(2)


def test_ui_set_002b_time_rules_limit_and_hour_validation(member_page: Page, base_url: str):
    page = member_page
    page.goto(base_url + "/settings")
    add_time(page, "8", "30")
    expect(page.locator("#schedule-feedback")).to_have_text("이미 추가한 예약 시각입니다.")
    add_time(page, "24", "00")
    expect(page.locator("#schedule-feedback")).to_have_text(
        "시는 0부터 23까지 정수로 입력해주세요."
    )
    for hour in ["1", "2", "3", "4"]:
        add_time(page, hour, "00")
    expect(page.locator("#schedule-count")).to_have_text("5 / 5")
    expect(page.get_by_role("button", name="시간 추가")).to_be_disabled()


def test_ui_set_003_disabling_schedule_survives_reload(member_page: Page, base_url: str):
    page = member_page
    page.goto(base_url + "/settings")
    page.locator("label.switch-control:has(#schedule-enabled)").click()
    expect(page.locator("#schedule-state")).to_have_text("사용 안 함")
    save(page)
    page.reload()
    expect(page.locator("#schedule-enabled")).not_to_be_checked()
    expect(page.locator("#schedule-preview")).to_have_text("예약 수집을 사용하지 않습니다.")


def test_ui_set_005_keywords_are_trimmed_deduplicated_and_restored(
    member_page: Page, base_url: str
):
    page = member_page
    page.goto(base_url + "/settings")
    add_keyword(page, "  HBM  ")
    add_keyword(page, "hbm")
    expect(page.locator("#keyword-error")).to_have_text("이미 등록한 검색어입니다.")
    add_keyword(page, "AI   에이전트")
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
    for word in ["가", "나", "다", "라"]:
        add_keyword(page, word)
    expect(page.locator("#keyword-error")).to_have_text(
        "선호 검색어는 최대 3개까지 저장할 수 있습니다."
    )
    expect(page.locator("#keyword-input")).to_have_attribute("aria-invalid", "true")
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


def test_safari_korean_ime_enter_does_not_add_twice(member_page: Page, base_url: str):
    """Safari는 한글 조합이 끝난 뒤 keyCode 229인 Enter keydown을 보냅니다. 그 Enter로는 추가하지 않습니다."""
    page = member_page
    page.goto(base_url + "/settings")
    page.evaluate(
        """() => {
        const input = document.querySelector('#keyword-input');
        input.focus();
        input.dispatchEvent(new CompositionEvent('compositionstart', {data: ''}));
        input.value = '반도체';
        input.dispatchEvent(new CompositionEvent('compositionend', {data: '반도체'}));
        const imeEnter = new KeyboardEvent('keydown', {key: 'Enter', bubbles: true, cancelable: true});
        Object.defineProperty(imeEnter, 'keyCode', {get: () => 229});
        input.dispatchEvent(imeEnter);
    }"""
    )
    expect(page.locator("#keyword-preview .input-tag")).to_have_count(0)
    page.locator("#keyword-input").press("Enter")
    expect(page.locator("#keyword-preview .input-tag")).to_have_count(1)
    expect(page.locator("#keyword-preview .input-tag")).to_contain_text("반도체")
    page.locator("#keyword-input").press("Enter")
    expect(page.locator("#keyword-preview .input-tag")).to_have_count(1)


def test_safari_legacy_browser_schedule_is_moved_to_server(member_page: Page, base_url: str):
    """예전 v1.0.1 미리보기(localStorage) 시간을 한 번 불러와 서버에 저장하고 브라우저 값은 지웁니다."""
    page = member_page
    page.goto(base_url + "/settings")
    owner = page.locator("#schedule").get_attribute("data-schedule-owner")
    key = f"dait.schedule.preview.v1:{owner}"
    page.evaluate(
        "([k]) => localStorage.setItem(k, JSON.stringify({times: ['07:00', '21:30'], enabled: true}))",
        [key],
    )
    page.reload()
    expect(page.locator("#settings-feedback")).to_contain_text("예약 시간을 불러왔습니다")
    expect(page.locator("#schedule-chips .schedule-chip")).to_have_count(2)
    save(page)
    assert page.evaluate("([k]) => localStorage.getItem(k)", [key]) is None
    times = page.request.get(base_url + "/api/settings").json()["settings"]["schedule"]["times"]
    assert times == ["07:00", "21:30"]


def test_kan10_category_order_and_hide_apply_to_main(member_page: Page, base_url: str):
    page = member_page
    page.goto(base_url + "/settings")
    up = page.get_by_role("button", name="클라우드 위로")
    for _ in range(3):
        up.click()
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
    add_keyword(page, "HBM")
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
    add_keyword(page, "HBM")
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


def test_v101_interests_and_nickname_still_work(member_page: Page, base_url: str):
    """팀원 v1.0.1 기능(관심 카테고리 알약 저장·닉네임)이 함께 동작하는지 확인합니다."""
    page = member_page
    page.goto(base_url + "/settings")
    page.locator(".interest-pill").first.click()
    page.get_by_role("button", name="설정 완료").click()
    expect(page.locator("#interests-feedback")).to_contain_text("저장했습니다")
    page.locator("#nickname-input").fill(
        "ui" + page.locator("#schedule").get_attribute("data-schedule-owner")[-6:]
    )
    page.get_by_role("button", name="닉네임 저장").click()
    expect(page.locator("#nickname-feedback")).to_have_text("닉네임을 변경했습니다.")

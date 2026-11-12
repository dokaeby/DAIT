"""예약 검색 설정 화면 자동화 (업무 지시서 ① 완료 기준 + 결과 표시). Chromium·WebKit 모두 실행."""

import re

from playwright.sync_api import Page, expect

from conftest import Server, tick


def open_settings(page: Page, server: Server) -> None:
    page.goto(server.base + "/settings.html")
    expect(page.locator("#settings-body")).to_be_visible()


def add_keyword(page: Page, word: str) -> None:
    page.locator("#sched-kw-input").fill(word)
    page.get_by_role("button", name="추가", exact=True).click()


def test_create_schedule_persists_after_reload(member: Page, server: Server) -> None:
    open_settings(member, server)
    add_keyword(member, "HBM")
    member.locator("#sched-hour").fill("9")
    member.locator("#sched-minute").select_option("00")
    member.get_by_role("radio", name="요일 선택").click()
    member.locator('[data-weekday="0"]').click()
    member.locator('[data-weekday="2"]').click()
    member.get_by_role("button", name="예약 저장").click()
    expect(member.locator("#schedule-feedback")).to_have_text("예약을 저장했습니다.")
    member.reload()
    item = member.locator(".schedule-item").first
    expect(item).to_contain_text("월·수 09:00 · HBM")
    expect(item).to_contain_text("다음 실행")


def test_invalid_input_is_not_saved_and_reason_is_shown(member: Page, server: Server) -> None:
    open_settings(member, server)
    member.get_by_role("button", name="예약 저장").click()
    expect(member.locator("#schedule-error")).to_have_text("키워드를 1개 이상 입력해주세요.")
    add_keyword(member, "HBM")
    member.locator("#sched-hour").fill("24")
    member.get_by_role("button", name="예약 저장").click()
    expect(member.locator("#schedule-error")).to_have_text("시는 0부터 23까지 정수로 입력해주세요.")
    member.locator("#sched-hour").fill("8")
    member.get_by_role("radio", name="요일 선택").click()
    member.get_by_role("button", name="예약 저장").click()
    expect(member.locator("#schedule-error")).to_have_text("요일을 하나 이상 골라주세요.")
    member.get_by_role("radio", name="한 번만").click()
    member.get_by_role("button", name="예약 저장").click()
    expect(member.locator("#schedule-error")).to_have_text("날짜를 골라주세요.")
    expect(member.locator(".schedule-item")).to_have_text("등록된 예약이 없습니다.")


def test_edit_time_is_shown_again(member: Page, server: Server) -> None:
    open_settings(member, server)
    add_keyword(member, "HBM")
    member.get_by_role("button", name="예약 저장").click()
    expect(member.locator(".schedule-item").first).to_contain_text("매일 08:30")
    expect(member.get_by_role("button", name="수정 취소")).to_be_hidden()
    expect(member.locator("#sched-weekdays-field")).to_be_hidden()
    member.get_by_role("button", name="수정", exact=True).click()
    expect(member.get_by_role("button", name="변경 저장")).to_be_visible()
    expect(member.get_by_role("button", name="수정 취소")).to_be_visible()
    member.locator("#sched-hour").fill("18")
    member.locator("#sched-minute").select_option("00")
    member.get_by_role("button", name="변경 저장").click()
    expect(member.locator("#schedule-feedback")).to_have_text("예약을 변경했습니다.")
    member.reload()
    expect(member.locator(".schedule-item").first).to_contain_text("매일 18:00")


def test_disable_and_delete(member: Page, server: Server) -> None:
    open_settings(member, server)
    add_keyword(member, "HBM")
    member.get_by_role("button", name="예약 저장").click()
    item = member.locator(".schedule-item").first
    item.locator("label.switch-control").click()
    expect(member.locator("#schedule-feedback")).to_have_text("예약을 껐습니다. 실행하지 않습니다.")
    member.reload()
    expect(member.locator(".schedule-item").first).to_contain_text("꺼짐")
    member.once("dialog", lambda dialog: dialog.accept())
    member.locator(".schedule-item").first.get_by_role("button", name="삭제").click()
    expect(member.locator(".schedule-item")).to_have_text("등록된 예약이 없습니다.")


def test_korean_ime_enter_does_not_add_twice(member: Page, server: Server) -> None:
    open_settings(member, server)
    member.evaluate(
        """() => {
        const input = document.querySelector('#sched-kw-input');
        input.focus();
        input.dispatchEvent(new CompositionEvent('compositionstart', {data: ''}));
        input.value = '반도체';
        input.dispatchEvent(new CompositionEvent('compositionend', {data: '반도체'}));
        const ime = new KeyboardEvent('keydown', {key: 'Enter', bubbles: true, cancelable: true});
        Object.defineProperty(ime, 'keyCode', {get: () => 229});
        input.dispatchEvent(ime);
    }"""
    )
    expect(member.locator(".kw-chip")).to_have_count(0)
    member.locator("#sched-kw-input").press("Enter")
    expect(member.locator(".kw-chip")).to_have_count(1)


def test_results_show_banner_badge_and_card_then_clear(member: Page, server: Server) -> None:
    open_settings(member, server)
    add_keyword(member, "HBM")
    member.get_by_role("button", name="예약 저장").click()
    expect(member.locator(".schedule-item").first).to_contain_text("다음 실행")
    schedules = member.evaluate(
        "async () => (await (await DAIT.api('/v1/me/schedules')).json()).items"
    )
    tick(server, schedules[0]["next_run_at"])  # 브라우저와 상관없이 서버가 실행

    member.goto(server.base + "/")
    expect(member.locator("#run-banner")).to_contain_text("예약 검색 결과 1건이 도착했어요")
    expect(member.locator("#run-badge")).to_have_text("🔔 1")
    member.locator("#run-banner").get_by_role("link", name="보기").click()
    results = member.locator("#run-list .run-item").first
    expect(results).to_contain_text("검색 성공 1건")
    expect(results).to_contain_text("HBM 증산 경쟁")
    expect(results).to_contain_text("새 결과")
    member.goto(server.base + "/")
    expect(member.locator("#run-banner")).to_be_hidden()
    expect(member.locator("#run-badge")).to_be_hidden()


def test_kakao_button_says_not_ready(member: Page, server: Server) -> None:
    open_settings(member, server)
    member.get_by_role("button", name="카카오 연결하기").click()
    expect(member.locator("#kakao-feedback")).to_have_text(re.compile("준비 중"))

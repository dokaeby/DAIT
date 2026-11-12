/* 예약 검색 화면: 설정의 "예약 검색" 카드(등록·수정·켜기/끄기·삭제), "예약 검색 결과" 카드,
   메인·설정 헤더의 새 결과 배지와 메인 상단 알림 줄. app.js의 DAIT.api를 사용한다.
   macOS Safari 대응: 한글 입력 중 Enter(keyCode 229)는 무시하고, 날짜는 Intl(Asia/Seoul)로만 표시한다. */
(function () {
  "use strict";

  const TZ = "Asia/Seoul";
  const MAX_SCHEDULES = 10;
  const DAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"];
  const SEARCH_TEXT = {
    QUEUED: "검색 대기 중",
    RUNNING: "검색 중",
    NO_RESULTS: "결과 없음",
    FAILED: "검색 실패 · 다시 시도 예정",
  };
  const NOTIFY_TEXT = {
    SENT: "카카오 전송 완료",
    SKIPPED: "카카오 보내지 않음",
    FAILED: "카카오 전송 실패 · 다시 시도 예정",
    UNKNOWN: "카카오 전송 여부 확인 필요",
    NOT_CONFIGURED: "카카오 연결 전",
    PENDING: "카카오 전송 대기",
    SENDING: "카카오 전송 중",
    WAITING: "",
  };

  const $ = (id) => document.getElementById(id);

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function kst(iso, withDate) {
    const options = { timeZone: TZ, hour: "2-digit", minute: "2-digit", hour12: false };
    if (withDate) Object.assign(options, { month: "numeric", day: "numeric", weekday: "short" });
    return new Intl.DateTimeFormat("ko-KR", options).format(new Date(iso));
  }

  function todayKst() {
    // en-CA 형식은 YYYY-MM-DD라 <input type="date"> 값과 바로 비교할 수 있다.
    return new Intl.DateTimeFormat("en-CA", { timeZone: TZ }).format(new Date());
  }

  function repeatText(s) {
    if (s.repeat === "WEEKLY") return (s.weekdays || []).map((d) => DAY_NAMES[d]).join("·");
    if (s.repeat === "ONCE") return (s.run_date || "") + " 한 번";
    return "매일";
  }

  async function readJson(res) {
    try {
      return await res.json();
    } catch (_e) {
      return {};
    }
  }

  // ---- 새 결과 배지·알림 줄 (메인·설정 공통) ----

  let lastUnseen = -1;

  function renderBadge(unseen) {
    const actions = document.querySelector(".header-actions");
    if (!actions) return;
    let badge = $("run-badge");
    if (!badge) {
      badge = el("a", "run-badge");
      badge.id = "run-badge";
      badge.href = "/settings.html#schedule-results";
      actions.insertBefore(badge, actions.firstChild);
    }
    badge.hidden = !unseen;
    badge.textContent = "🔔 " + unseen;
    badge.setAttribute("aria-label", "새 예약 검색 결과 " + unseen + "건");
    const banner = $("run-banner");
    if (banner) {
      banner.hidden = !unseen;
      banner.replaceChildren(
        el("span", "", "🔔 예약 검색 결과 " + unseen + "건이 도착했어요"),
        Object.assign(el("a", "secondary-button", "보기"), { href: "/settings.html#schedule-results" })
      );
    }
  }

  async function refreshUnseen() {
    if (!DAIT.getToken("dait_access_token")) {
      renderBadge(0);
      return null;
    }
    try {
      const res = await DAIT.api("/v1/me/schedule-runs");
      if (!res.ok) {
        renderBadge(0);
        return null;
      }
      const data = await res.json();
      if (data.unseen !== lastUnseen) renderBadge(data.unseen);
      lastUnseen = data.unseen;
      return data;
    } catch (_e) {
      return null;
    }
  }

  let bannerStarted = false;
  function initBanner() {
    if (bannerStarted) return;
    bannerStarted = true;
    refreshUnseen();
    // 로그인 중이면 1분마다 확인한다. 탭이 안 보일 때는 건너뛴다.
    setInterval(() => {
      if (document.visibilityState === "visible") refreshUnseen();
    }, 60000);
  }

  // ---- 설정: 예약 검색 카드 ----

  function initSettings() {
    const form = $("schedule-form");
    if (!form) return;
    const state = { keywords: [], repeat: "DAILY", weekdays: [], editingId: null, items: [] };
    let composing = false;

    const minute = $("sched-minute");
    for (let m = 0; m < 60; m += 5) {
      const v = String(m).padStart(2, "0");
      minute.append(Object.assign(document.createElement("option"), { value: v, textContent: v + "분" }));
    }
    minute.value = "30";
    const weekdayBox = $("sched-weekdays");
    DAY_NAMES.forEach((name, index) => {
      const b = el("button", "choice-chip", name);
      b.type = "button";
      b.dataset.weekday = String(index);
      b.setAttribute("aria-pressed", "false");
      weekdayBox.append(b);
    });
    $("sched-date").min = todayKst();

    function setError(message) {
      $("schedule-error").textContent = message || "";
    }
    function setFeedback(message) {
      $("schedule-feedback").textContent = message || "";
    }

    function renderKeywords() {
      const box = $("sched-kw-chips");
      box.replaceChildren();
      if (!state.keywords.length) box.append(el("span", "field-help", "아직 추가한 키워드가 없습니다."));
      for (const word of state.keywords) {
        const chip = el("span", "kw-chip", word);
        const x = el("button", "kw-remove", "×");
        x.type = "button";
        x.dataset.removeKeyword = word;
        x.setAttribute("aria-label", word + " 삭제");
        chip.append(x);
        box.append(chip);
      }
    }

    function renderRepeat() {
      form.querySelectorAll("[data-repeat]").forEach((b) => {
        const on = b.dataset.repeat === state.repeat;
        b.setAttribute("aria-checked", String(on));
        b.classList.toggle("on", on);
      });
      weekdayBox.querySelectorAll("[data-weekday]").forEach((b) => {
        const on = state.weekdays.includes(Number(b.dataset.weekday));
        b.setAttribute("aria-pressed", String(on));
        b.classList.toggle("on", on);
      });
      $("sched-weekdays-field").hidden = state.repeat !== "WEEKLY";
      $("sched-date-field").hidden = state.repeat !== "ONCE";
    }

    function addKeyword() {
      const word = $("sched-kw-input").value.split(/\s+/).filter(Boolean).join(" ");
      if (!word) return;
      if (state.keywords.includes(word)) return setError("이미 추가한 키워드입니다.");
      if (state.keywords.length >= 20) return setError("키워드는 최대 20개까지 넣을 수 있습니다.");
      state.keywords.push(word);
      $("sched-kw-input").value = "";
      setError("");
      renderKeywords();
    }

    function resetForm() {
      state.keywords = [];
      state.repeat = "DAILY";
      state.weekdays = [];
      state.editingId = null;
      $("sched-hour").value = "8";
      minute.value = "30";
      $("sched-date").value = "";
      $("sched-enabled").checked = true;
      $("sched-save").textContent = "예약 저장";
      $("sched-cancel").hidden = true;
      setError("");
      renderKeywords();
      renderRepeat();
    }

    function validate() {
      if (!state.keywords.length) return "키워드를 1개 이상 입력해주세요.";
      const raw = String($("sched-hour").value).trim();
      const hour = Number(raw);
      // Safari의 number 입력은 글자를 받아 값이 빈 문자열이 될 수 있어 다시 확인한다.
      if (raw === "" || !Number.isInteger(hour) || hour < 0 || hour > 23) return "시는 0부터 23까지 정수로 입력해주세요.";
      if (state.repeat === "WEEKLY" && !state.weekdays.length) return "요일을 하나 이상 골라주세요.";
      if (state.repeat === "ONCE") {
        const day = $("sched-date").value;
        if (!day) return "날짜를 골라주세요.";
        const time = String(hour).padStart(2, "0") + ":" + minute.value;
        if (day < todayKst() || (day === todayKst() && time <= kst(new Date().toISOString(), false))) {
          return "지난 날짜·시각은 예약할 수 없습니다.";
        }
      }
      if (!state.editingId && state.items.length >= MAX_SCHEDULES) return "예약은 최대 10개까지 등록할 수 있습니다.";
      return "";
    }

    function body() {
      const hour = String(Number($("sched-hour").value)).padStart(2, "0");
      return {
        local_time: hour + ":" + minute.value,
        timezone: TZ,
        enabled: $("sched-enabled").checked,
        criteria: { categories: ["AI"], keywords: state.keywords, source_ids: [] },
        repeat: state.repeat,
        weekdays: state.repeat === "WEEKLY" ? state.weekdays.slice().sort() : [],
        run_date: state.repeat === "ONCE" ? $("sched-date").value : null,
      };
    }

    function startEdit(s) {
      state.editingId = s.id;
      state.keywords = (s.criteria && s.criteria.keywords ? s.criteria.keywords : []).slice();
      state.repeat = s.repeat || "DAILY";
      state.weekdays = (s.weekdays || []).slice();
      const [h, m] = s.local_time.split(":");
      $("sched-hour").value = String(Number(h));
      minute.value = minute.querySelector('option[value="' + m + '"]') ? m : "00";
      $("sched-date").value = s.run_date || "";
      $("sched-enabled").checked = s.enabled;
      $("sched-save").textContent = "변경 저장";
      $("sched-cancel").hidden = false;
      setError("");
      setFeedback("");
      renderKeywords();
      renderRepeat();
      form.scrollIntoView({ block: "start" });
    }

    async function loadSchedules() {
      const res = await DAIT.api("/v1/me/schedules");
      const list = $("schedule-list");
      if (!res.ok) {
        setFeedback("예약 목록을 불러오지 못했습니다.");
        return;
      }
      state.items = (await res.json()).items || [];
      $("schedule-count").textContent = "내 예약 " + state.items.length + "개";
      list.replaceChildren();
      if (!state.items.length) list.append(el("li", "schedule-item schedule-meta", "등록된 예약이 없습니다."));
      for (const s of state.items) {
        const li = el("li", "schedule-item" + (s.enabled ? "" : " is-off"));
        li.dataset.scheduleId = s.id;
        const meta = el("span", "schedule-meta");
        const keywords = s.criteria && s.criteria.keywords ? s.criteria.keywords.join(", ") : "";
        meta.append(el("strong", "", repeatText(s) + " " + s.local_time + (keywords ? " · " + keywords : "")));
        meta.append(el("small", "", s.enabled
          ? (s.next_run_at ? "다음 실행 " + kst(s.next_run_at, true) : "실행할 회차가 없습니다")
          : "꺼짐 · 실행하지 않음"));
        const tools = el("span", "schedule-tools");
        const toggle = el("label", "switch-control");
        const input = Object.assign(document.createElement("input"), { type: "checkbox", checked: s.enabled });
        input.setAttribute("aria-label", repeatText(s) + " " + s.local_time + " 예약 사용");
        input.dataset.toggleSchedule = s.id;
        const knob = el("span", "switch");
        knob.setAttribute("aria-hidden", "true");
        toggle.append(input, knob);
        const edit = el("button", "secondary-button", "수정");
        edit.type = "button";
        edit.dataset.editSchedule = s.id;
        const del = el("button", "danger-button", "삭제");
        del.type = "button";
        del.dataset.deleteSchedule = s.id;
        tools.append(toggle, edit, del);
        li.append(meta, tools);
        list.append(li);
      }
    }

    async function loadRuns() {
      const data = await refreshUnseen();
      const list = $("run-list");
      list.replaceChildren();
      if (!data || !data.items.length) {
        list.append(el("li", "run-item schedule-meta", "아직 실행된 예약 검색이 없습니다."));
        return;
      }
      for (const run of data.items) {
        const li = el("li", "run-item");
        const head = el("div", "run-head");
        head.append(el("strong", "", kst(run.scheduled_for, true)));
        if (!run.seen && (run.search_status === "SUCCEEDED" || run.search_status === "NO_RESULTS")) {
          head.append(el("span", "run-new", "새 결과"));
        }
        const searchText = run.search_status === "SUCCEEDED"
          ? "검색 성공 " + run.result_count + "건" : SEARCH_TEXT[run.search_status] || run.search_status;
        const notifyText = NOTIFY_TEXT[run.notify_status] || "";
        const status = el("p", "run-status" + (run.search_status === "FAILED" ? " is-error" : ""),
          searchText + (notifyText ? " · " + notifyText : ""));
        li.append(head, status);
        if (run.items.length) {
          const ol = el("ol", "run-articles");
          for (const item of run.items) {
            const a = el("a", "", item.title);
            a.href = item.url;
            a.target = "_blank";
            a.rel = "noopener noreferrer";
            const row = el("li");
            row.append(a, el("span", "run-source", " " + item.source_name));
            ol.append(row);
          }
          li.append(ol);
        }
        list.append(li);
      }
      if (data.unseen) {
        // 결과 카드를 보여줬으므로 "새" 표시를 지운다(화면의 "새 결과" 글자는 이번 방문 동안 유지).
        await DAIT.api("/v1/me/schedule-runs/seen", { method: "POST", body: "{}" });
        renderBadge(0);
        lastUnseen = 0;
      }
    }

    // 이벤트
    $("sched-kw-add").addEventListener("click", addKeyword);
    $("sched-kw-input").addEventListener("compositionstart", () => { composing = true; });
    $("sched-kw-input").addEventListener("compositionend", () => { composing = false; });
    $("sched-kw-input").addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      event.preventDefault();
      if (composing || event.isComposing || event.keyCode === 229) return;
      addKeyword();
    });
    form.addEventListener("click", (event) => {
      const b = event.target.closest("button");
      if (!b) return;
      if (b.dataset.removeKeyword !== undefined) {
        state.keywords = state.keywords.filter((k) => k !== b.dataset.removeKeyword);
        renderKeywords();
      } else if (b.dataset.repeat) {
        state.repeat = b.dataset.repeat;
        setError("");
        renderRepeat();
      } else if (b.dataset.weekday !== undefined) {
        const d = Number(b.dataset.weekday);
        state.weekdays = state.weekdays.includes(d) ? state.weekdays.filter((x) => x !== d) : state.weekdays.concat(d);
        renderRepeat();
      }
    });
    $("sched-cancel").addEventListener("click", () => {
      resetForm();
      setFeedback("수정을 취소했습니다.");
    });
    let saving = false;
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (saving) return;
      const problem = validate();
      setError(problem);
      if (problem) return;
      saving = true;
      $("sched-save").disabled = true;
      try {
        const editing = state.editingId;
        const res = await DAIT.api(editing ? "/v1/me/schedules/" + encodeURIComponent(editing) : "/v1/me/schedules", {
          method: editing ? "PATCH" : "POST",
          body: JSON.stringify(body()),
        });
        if (!res.ok) {
          const b = await readJson(res);
          setError(res.status === 401 ? "로그인이 만료되었습니다. 다시 로그인해주세요." : b.message || "저장하지 못했습니다. 입력값을 확인해주세요.");
          return;
        }
        resetForm();
        setFeedback(editing ? "예약을 변경했습니다." : "예약을 저장했습니다.");
        await loadSchedules();
      } finally {
        saving = false;
        $("sched-save").disabled = false;
      }
    });
    $("schedule-list").addEventListener("click", async (event) => {
      const b = event.target.closest("button");
      if (!b) return;
      if (b.dataset.editSchedule) {
        const s = state.items.find((x) => x.id === b.dataset.editSchedule);
        if (s) startEdit(s);
      } else if (b.dataset.deleteSchedule) {
        if (!window.confirm("이 예약을 삭제할까요?")) return;
        const res = await DAIT.api("/v1/me/schedules/" + encodeURIComponent(b.dataset.deleteSchedule), { method: "DELETE" });
        setFeedback(res.ok ? "예약을 삭제했습니다." : "삭제하지 못했습니다.");
        if (state.editingId === b.dataset.deleteSchedule) resetForm();
        await loadSchedules();
      }
    });
    $("schedule-list").addEventListener("change", async (event) => {
      const input = event.target;
      if (!input.dataset || !input.dataset.toggleSchedule) return;
      const res = await DAIT.api("/v1/me/schedules/" + encodeURIComponent(input.dataset.toggleSchedule), {
        method: "PATCH",
        body: JSON.stringify({ enabled: input.checked }),
      });
      if (!res.ok) {
        input.checked = !input.checked;
        setFeedback(res.status === 422 ? "지난 날짜의 한 번만 예약은 켤 수 없습니다. 날짜를 수정해주세요." : "변경하지 못했습니다.");
        return;
      }
      setFeedback(input.checked ? "예약을 켰습니다." : "예약을 껐습니다. 실행하지 않습니다.");
      await loadSchedules();
    });
    $("kakao-connect").addEventListener("click", () => {
      $("kakao-feedback").textContent = "카카오 연결은 준비 중입니다. 카카오 앱 등록이 끝나면 사용할 수 있습니다.";
    });

    resetForm();
    loadSchedules();
    loadRuns();
    if (location.hash === "#schedule-results") $("schedule-results").scrollIntoView();
  }

  window.DAIT.scheduleUI = { initSettings, initBanner, refreshUnseen };
  document.addEventListener("DOMContentLoaded", initBanner);
  if (document.readyState !== "loading") initBanner();
})();

const page = document.body.dataset.page;
const statusNode = document.querySelector("#page-status");
const retryButton = document.querySelector("#retry-button");
let lastRetry = null;
let currentSettings = null;

function setStatus(message, tone = "") {
  if (!statusNode) return;
  statusNode.textContent = message;
  statusNode.className = `status ${tone}`.trim();
}

function setRetry(handler) {
  lastRetry = handler;
  retryButton?.classList.toggle("hidden", !handler);
}

retryButton?.addEventListener("click", () => lastRetry?.());

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const error = new Error(body.message || "요청을 처리하지 못했습니다.");
    error.requestId = body.request_id;
    throw error;
  }
  return response.status === 204 ? null : response.json();
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function safeUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}

function formatDate(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul",
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function renderNewsCard(item) {
  const card = element("article", "news-card");
  card.append(element("div", "rank", String(item.rank).padStart(2, "0")));

  const info = element("div", "news-info");
  const meta = element("div", "meta-row");
  meta.append(
    element("span", "category-pill", "AI·기술"),
    element("span", item.is_partial ? "state-pill" : "state-pill ready", item.is_partial ? "내용 부족" : "처리 완료"),
    element("span", "", formatDate(item.published_at)),
  );
  info.append(meta, element("h2", "", item.title), element("div", "meta-row", item.source_name));
  card.append(info);

  const summary = element("ol", "summary-lines");
  item.summary_lines.forEach((line) => summary.append(element("li", "", line)));
  card.append(summary);

  const actions = element("div", "card-actions");
  const detail = element("a", "button primary", "상세 보기");
  detail.href = `/detail.html?id=${encodeURIComponent(item.id)}`;
  actions.append(detail);
  const original = safeUrl(item.original_url);
  if (original) {
    const source = element("a", "button secondary", "원문 열기");
    source.href = original;
    source.target = "_blank";
    source.rel = "noopener noreferrer";
    actions.append(source);
  }
  card.append(actions);
  return card;
}

async function loadNews() {
  const list = document.querySelector("#news-list");
  const query = document.querySelector("#search-input")?.value.trim() || "";
  const sort = document.querySelector("#sort-select")?.value || "rank";
  setStatus("뉴스를 불러오는 중입니다.");
  setRetry(null);
  list.replaceChildren();
  try {
    const params = new URLSearchParams({ sort, page_size: "10" });
    if (query) params.set("q", query);
    const data = await api(`/v1/news?${params}`);
    document.querySelector("#result-count").textContent = `${data.items.length}개의 뉴스`;
    if (!data.items.length) {
      list.append(element("div", "empty", query ? "검색 결과가 없습니다." : "아직 수집된 기사가 없습니다."));
      setStatus(query ? "다른 검색어를 입력해 보세요." : "새 뉴스가 준비되면 여기에 표시됩니다.");
      return;
    }
    data.items.forEach((item) => list.append(renderNewsCard(item)));
    setStatus(data.meta.message || "최신 AI 뉴스를 불러왔습니다.", data.meta.partial ? "" : "success");
  } catch (error) {
    setStatus(`${error.message}${error.requestId ? ` (${error.requestId})` : ""}`, "error");
    setRetry(loadNews);
  }
}

function renderProcessing(processing) {
  const target = document.querySelector("#processing-info");
  target.replaceChildren();
  const labels = { collection_status: "수집", translation_status: "번역", summary_status: "요약" };
  Object.entries(labels).forEach(([key, label]) => {
    const metric = element("div", "metric");
    metric.append(element("span", "", label), element("strong", "", processing[key]));
    target.append(metric);
  });
}

async function loadDetail(newsId) {
  const content = document.querySelector("#detail-content");
  setStatus("뉴스 상세를 불러오는 중입니다.");
  setRetry(null);
  content.classList.add("hidden");
  try {
    const data = await api(`/v1/news/${encodeURIComponent(newsId)}`);
    document.querySelector("#article-title").textContent = data.article.title;
    document.querySelector("#article-source").textContent = `${data.article.source_name} · ${data.article.original_language.toUpperCase()} 원문`;
    document.querySelector("#published-at").textContent = formatDate(data.article.published_at);
    const detailStatus = document.querySelector("#detail-status");
    detailStatus.textContent = data.content.content_status === "READY" ? "처리 완료" : "내용 부족";
    detailStatus.className = data.content.content_status === "READY" ? "state-pill ready" : "state-pill";

    const summary = document.querySelector("#summary-list");
    summary.replaceChildren(...data.content.summary_lines.map((line) => element("li", "", line)));
    document.querySelector("#translated-text").textContent = data.content.translated_text || "번역할 원문 정보가 부족합니다.";
    document.querySelector("#processed-at").textContent = data.content.processed_at ? `${formatDate(data.content.processed_at)} 처리` : "처리 대기";
    document.querySelector("#source-name").textContent = data.article.source_name;
    document.querySelector("#source-url").textContent = data.source.original_url;
    renderProcessing(data.processing);

    const sourceUrl = safeUrl(data.source.original_url);
    const sourceLink = document.querySelector("#original-link");
    if (sourceUrl) sourceLink.href = sourceUrl;
    else sourceLink.classList.add("hidden");
    document.querySelector("#copy-link").onclick = async () => {
      try {
        if (!navigator.clipboard) throw new Error("clipboard unavailable");
        await navigator.clipboard.writeText(data.source.original_url);
        setStatus("원문 링크를 복사했습니다.", "success");
      } catch {
        setStatus("복사하지 못했습니다. 원본 정보의 URL을 직접 선택해 주세요.", "error");
      }
    };

    const related = document.querySelector("#related-list");
    related.replaceChildren();
    if (!data.related_news.length) related.append(element("p", "status", "관련 뉴스가 없습니다."));
    data.related_news.forEach((item) => {
      const link = element("a", "related-item");
      link.href = `/detail.html?id=${encodeURIComponent(item.id)}`;
      link.append(element("strong", "", item.title), element("span", "", `${item.source_name} · ${formatDate(item.published_at)}`));
      related.append(link);
    });
    content.classList.remove("hidden");
    setStatus("뉴스 상세를 불러왔습니다.", "success");
  } catch (error) {
    setStatus(`${error.message}${error.requestId ? ` (${error.requestId})` : ""}`, "error");
    setRetry(() => loadDetail(newsId));
  }
}

function selectedSources() {
  return [...document.querySelectorAll('input[name="source"]:checked')].map((input) => input.value);
}

function fillSettings(settings) {
  currentSettings = settings;
  document.querySelector("#keywords-input").value = settings.keywords.join(", ");
  document.querySelector("#default-count").value = String(settings.default_count);
  document.querySelector("#in-app-notice").checked = settings.in_app_notice;
  document.querySelector("#email-notice").checked = settings.email_notice;
  document.querySelectorAll('input[name="source"]').forEach((input) => {
    input.checked = settings.source_ids.includes(input.value);
  });
}

function renderSchedules(items) {
  const list = document.querySelector("#schedule-list");
  list.replaceChildren();
  if (!items.length) list.append(element("p", "status", "등록된 예약이 없습니다."));
  items.forEach((schedule) => {
    const row = element("div", "schedule-row");
    const copy = element("div");
    copy.append(element("strong", "", `${schedule.local_time} · ${schedule.timezone}`), element("span", "", schedule.next_run_at ? `다음 실행 ${formatDate(schedule.next_run_at)}` : "다음 실행 미정"));
    const toggle = element("button", "button secondary", schedule.enabled ? "일시정지" : "활성화");
    toggle.type = "button";
    toggle.onclick = () => performScheduleAction(
      () => api(`/v1/me/schedules/${encodeURIComponent(schedule.id)}`, { method: "PATCH", body: JSON.stringify({ enabled: !schedule.enabled }) }),
      loadSettings,
      (error) => {
        setStatus(error.message, "error");
        setRetry(() => toggle.click());
      },
    );
    const remove = element("button", "button secondary", "삭제");
    remove.type = "button";
    remove.onclick = () => performScheduleAction(
      () => api(`/v1/me/schedules/${encodeURIComponent(schedule.id)}`, { method: "DELETE" }),
      loadSettings,
      (error) => {
        setStatus(error.message, "error");
        setRetry(() => remove.click());
      },
    );
    row.append(copy, toggle, remove);
    list.append(row);
  });
}

async function loadSettings() {
  setStatus("설정을 불러오는 중입니다.");
  setRetry(null);
  try {
    const [settings, schedules] = await Promise.all([
      api("/v1/me/settings"),
      api("/v1/me/schedules"),
    ]);
    fillSettings(settings);
    renderSchedules(schedules.items);
    setStatus("저장된 설정을 불러왔습니다.", "success");
  } catch (error) {
    setStatus(`${error.message}${error.requestId ? ` (${error.requestId})` : ""}`, "error");
    setRetry(loadSettings);
  }
}

async function saveSettings(event) {
  event.preventDefault();
  const keywords = document.querySelector("#keywords-input").value.split(",").map((value) => value.trim()).filter(Boolean);
  setStatus("설정을 저장하는 중입니다.");
  try {
    const settings = await api("/v1/me/settings", {
      method: "PATCH",
      body: JSON.stringify({
        default_count: Number(document.querySelector("#default-count").value),
        keywords,
        source_ids: selectedSources(),
        categories: ["AI"],
        in_app_notice: document.querySelector("#in-app-notice").checked,
        email_notice: document.querySelector("#email-notice").checked,
      }),
    });
    fillSettings(settings);
    setStatus("설정을 저장했습니다.", "success");
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function createSchedule(event) {
  event.preventDefault();
  try {
    await api("/v1/me/schedules", {
      method: "POST",
      body: JSON.stringify({
        local_time: document.querySelector("#schedule-time").value,
        timezone: "Asia/Seoul",
        enabled: true,
        criteria: {
          keywords: currentSettings?.keywords || [],
          source_ids: currentSettings?.source_ids || [],
          categories: ["AI"],
        },
      }),
    });
    await loadSettings();
    setStatus("예약을 추가했습니다.", "success");
  } catch (error) {
    setStatus(error.message, "error");
  }
}

if (page === "main") {
  document.querySelector("#news-filter").addEventListener("submit", (event) => { event.preventDefault(); loadNews(); });
  document.querySelector("#sort-select").addEventListener("change", loadNews);
  document.querySelector("#reset-button").addEventListener("click", () => {
    document.querySelector("#search-input").value = "";
    document.querySelector("#sort-select").value = "rank";
    loadNews();
  });
  loadNews();
}

if (page === "detail") {
  loadDetail(new URLSearchParams(location.search).get("id") || "news_openai_001");
}

if (page === "settings") {
  document.querySelector("#settings-form").addEventListener("submit", saveSettings);
  document.querySelector("#schedule-form").addEventListener("submit", createSchedule);
  loadSettings();
}

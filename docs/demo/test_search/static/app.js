const form = document.getElementById("search-form");
const queryInput = document.getElementById("query");
const limitSelect = document.getElementById("limit");
const limitRange = document.getElementById("limit-range");
const results = document.getElementById("results");
const status = document.getElementById("status");
const searchButton = document.getElementById("search-button");
const timing = document.getElementById("search-timing");
const dateFormat = new Intl.DateTimeFormat("ko-KR", {
  timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit",
  hour: "2-digit", minute: "2-digit", hour12: false,
});
function formatDate(value) {
  if (!value) return "기록 없음";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "날짜 확인 불가" : `${dateFormat.format(date)} KST`;
}
document.querySelectorAll("[data-date]").forEach(node => {
  node.textContent = formatDate(node.dataset.date);
  if (node.dataset.date) node.title = node.dataset.date;
});
const duration = document.getElementById("collection-duration");
if (duration.dataset.seconds !== "") {
  const seconds = Number(duration.dataset.seconds);
  if (Number.isFinite(seconds)) duration.textContent = seconds >= 60
    ? `${Math.floor(seconds / 60)}분 ${(seconds % 60).toFixed(1)}초` : `${seconds.toFixed(1)}초`;
}
limitSelect.addEventListener("change", () => { limitRange.value = limitSelect.value; });
limitRange.addEventListener("input", () => { limitSelect.value = limitRange.value; });
function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function renderCard(item, index) {
  const card = element("article", "news-card");
  const top = element("div", "card-top");
  top.append(element("span", "source", item.source), element("span", "card-number", String(index + 1).padStart(2, "0")));
  const title = element("h3");
  let url;
  try { url = new URL(item.url); } catch { /* 제목만 표시 */ }
  if (url && ["https:", "http:"].includes(url.protocol)) {
    const link = element("a", "", item.title);
    link.href = url.href; link.target = "_blank"; link.rel = "noopener noreferrer";
    title.append(link);
  } else title.textContent = item.title;
  const score = Math.max(0, Math.min(100, Number(item.similarity) * 100 || 0));
  const similarity = element("div", "similarity");
  const label = element("div", "similarity-label");
  label.append(element("span", "", "검색 유사도"), element("strong", "", `${score.toFixed(1)}%`));
  const bar = element("progress");
  bar.max = 100; bar.value = score;
  bar.setAttribute("aria-label", `검색 유사도 ${score.toFixed(1)}%`);
  similarity.append(label, bar);
  const dates = element("div", "card-dates");
  for (const [name, value] of [["발행", item.published], ["수집", item.collected_at]]) {
    const row = element("span", "", `${name} `);
    const time = element("time", "", formatDate(value));
    if (value && !Number.isNaN(new Date(value).getTime())) time.dateTime = new Date(value).toISOString();
    row.append(time); dates.append(row);
  }
  card.append(top, title, element("p", "summary", item.summary), similarity, dates);
  return card;
}
let activeRequest;
let requestId = 0;
form.addEventListener("submit", async event => {
  event.preventDefault();
  const query = queryInput.value.trim();
  if (!query) { queryInput.focus(); return; }
  const id = ++requestId;
  activeRequest?.abort();
  const controller = new AbortController();
  activeRequest = controller;
  const timeout = setTimeout(() => controller.abort(), 60000);
  searchButton.disabled = true; searchButton.textContent = "검색 중…";
  results.setAttribute("aria-busy", "true");
  status.className = ""; status.textContent = "맥락이 닮은 뉴스를 찾고 있습니다…";
  timing.hidden = true;
  try {
    const response = await fetch("/search", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, limit: Number(limitSelect.value) }), signal: controller.signal,
    });
    const data = await response.json().catch(() => { throw new Error("서버 응답을 읽지 못했습니다. 잠시 후 다시 시도해 주세요."); });
    if (!response.ok) throw new Error(data.error || "검색에 실패했습니다. 다시 시도해 주세요.");
    if (id !== requestId) return;
    document.getElementById("results-title").replaceChildren(document.createTextNode("검색 결과 "), element("span", "", `${data.results.length}건`));
    document.getElementById("results-eyebrow").textContent = "MATCHED FOR YOU";
    results.replaceChildren(...data.results.map(renderCard));
    if (!data.results.length) results.append(element("div", "empty-state", "저장된 뉴스가 없습니다. 기사를 수집한 뒤 다시 검색해 주세요."));
    status.textContent = `‘${query}’ · 최대 ${data.limit}개 요청 · 저장된 ${data.total.toLocaleString("ko-KR")}개 기사에서 검색`;
    timing.textContent = `검색 ${(data.elapsed_ms / 1000).toFixed(2)}초`; timing.hidden = false;
    document.getElementById("score-note").hidden = !data.results.length;
  } catch (error) {
    if (id !== requestId) return;
    status.className = "error";
    status.textContent = error.name === "AbortError" ? "검색 시간이 초과되었습니다. 다시 시도해 주세요." : (error.message || "서버에 연결할 수 없습니다.");
  } finally {
    clearTimeout(timeout);
    if (id === requestId) {
      searchButton.disabled = false; searchButton.textContent = "뉴스 검색 ↗";
      results.setAttribute("aria-busy", "false");
    }
  }
});
document.querySelectorAll("[data-query]").forEach(button => {
  button.addEventListener("click", () => { queryInput.value = button.dataset.query; form.requestSubmit(); });
});

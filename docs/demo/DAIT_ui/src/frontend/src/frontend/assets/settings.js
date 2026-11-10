// KAN-10 설정 화면: 서버에 저장된 값으로 시작하고, [설정 저장]에서 /api/settings로 한 번에 저장합니다.
const MAX_KEYWORDS = 3;
const DAY_NAMES = ['월', '화', '수', '목', '금', '토', '일'];
const initial = JSON.parse(document.querySelector('#settings-data').textContent);
let saved = initial.settings;
let categories = initial.available_categories;
let draft = structuredClone(saved);
let saving = false;

const $ = selector => document.querySelector(selector);
const form = $('#settings-form');
const feedback = $('#settings-feedback');
const keywordInput = $('#keyword-input');
const keywordError = $('#keyword-error');
const time = $('#collection-time');
const enabled = $('#schedule-enabled');

function setPressed(button, on) {
  button.setAttribute('aria-pressed', String(on));
  button.classList.toggle('active', on);
}

function nextRunText() {
  const schedule = draft.schedule;
  if (!schedule.enabled) return '예약 알림을 사용하지 않습니다.';
  if (!schedule.days.length) return '요일을 하나 이상 선택해주세요.';
  const days = schedule.days.length === 7 ? '매일' : '매주 ' + schedule.days.map(day => DAY_NAMES[day]).join('·');
  const changed = JSON.stringify(schedule) !== JSON.stringify(saved.schedule);
  const next = !changed && initial.next_run ? ` · 다음 실행 ${initial.next_run}` : changed ? ' · 저장하면 적용됩니다' : '';
  return `${days} ${schedule.time || '--:--'} KST${next}`;
}

function renderSchedule() {
  const schedule = draft.schedule;
  time.value = schedule.time;
  enabled.checked = schedule.enabled;
  $('#schedule-max').value = String(schedule.max_items);
  document.querySelectorAll('[data-day]').forEach(chip => setPressed(chip, schedule.days.includes(Number(chip.dataset.day))));
  document.querySelectorAll('[data-source]').forEach(chip => setPressed(chip, schedule.sources.includes(chip.dataset.source)));
  const badge = $('#schedule-state');
  badge.textContent = schedule.enabled ? '사용' : '사용 안 함';
  badge.classList.toggle('ready', schedule.enabled);
  badge.classList.toggle('pending', !schedule.enabled);
  $('#schedule-preview').textContent = nextRunText();
}

function renderKeywords() {
  const preview = $('#keyword-preview');
  preview.replaceChildren();
  for (const word of draft.keywords) {
    const tag = document.createElement('span');
    tag.className = 'input-tag';
    tag.textContent = word;
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'tag-remove';
    remove.dataset.removeKeyword = word;
    remove.setAttribute('aria-label', `${word} 삭제`);
    remove.textContent = '×';
    tag.append(remove);
    preview.append(tag);
  }
  if (!draft.keywords.length) {
    const empty = document.createElement('span');
    empty.className = 'field-help';
    empty.textContent = '등록한 선호 검색어가 없습니다.';
    preview.append(empty);
  }
  const full = draft.keywords.length >= MAX_KEYWORDS;
  keywordInput.placeholder = full ? `최대 ${MAX_KEYWORDS}개를 모두 등록했습니다` : '예: 멀티모달, AI 에이전트, HBM';
}

function orderedCategories() {
  const rank = new Map(draft.category_order.map((name, index) => [name, index]));
  const position = name => rank.get(name) ?? rank.size + categories.indexOf(name);
  return [...categories].sort((a, b) => position(a) - position(b));
}

function renderCategories() {
  const list = $('#category-order');
  list.replaceChildren();
  const ordered = orderedCategories();
  if (!ordered.length) {
    const empty = document.createElement('li');
    empty.className = 'field-help';
    empty.textContent = '표시할 카테고리가 아직 없습니다.';
    list.append(empty);
    return;
  }
  ordered.forEach((name, index) => {
    const shown = !draft.hidden_categories.includes(name);
    const row = document.createElement('li');
    row.className = 'category-row' + (shown ? '' : ' hidden-category');
    row.dataset.categoryName = name;
    row.innerHTML = `<span class="category-name"></span>
      <button type="button" class="icon-button" data-move="-1" ${index === 0 ? 'disabled' : ''}>↑</button>
      <button type="button" class="icon-button" data-move="1" ${index === ordered.length - 1 ? 'disabled' : ''}>↓</button>
      <label class="switch-control"><input class="sr-only" type="checkbox" data-show-category ${shown ? 'checked' : ''}><span class="switch" aria-hidden="true"></span></label>`;
    row.querySelector('.category-name').textContent = shown ? name : `${name} (숨김)`;
    row.querySelectorAll('[data-move]').forEach(button => button.setAttribute('aria-label', `${name} ${button.dataset.move === '-1' ? '위로' : '아래로'}`));
    row.querySelector('[data-show-category]').setAttribute('aria-label', `${name} 표시`);
    list.append(row);
  });
}

function renderAll() {
  renderSchedule();
  renderKeywords();
  renderCategories();
  $('#display-count').value = String(draft.display_count);
  $('#in-app-notification').checked = draft.in_app_notification;
  $('#email-notification').checked = draft.email_notification;
}

function changed() {
  feedback.textContent = '';
  $('#schedule-preview').textContent = nextRunText();
}

function showKeywordError(message) {
  keywordError.textContent = message;
  if (message) keywordInput.setAttribute('aria-invalid', 'true');
  else keywordInput.removeAttribute('aria-invalid');
}

function addKeyword() {
  const word = keywordInput.value.split(/\s+/).filter(Boolean).join(' ');
  showKeywordError('');
  if (!word) return;
  if (draft.keywords.some(item => item.toLowerCase() === word.toLowerCase())) return showKeywordError('이미 등록한 검색어입니다.');
  if (draft.keywords.length >= MAX_KEYWORDS) return showKeywordError(`선호 검색어는 최대 ${MAX_KEYWORDS}개까지 저장할 수 있습니다.`);
  draft.keywords = [...draft.keywords, word];
  keywordInput.value = '';
  renderKeywords();
  changed();
  keywordInput.focus();
}

function moveCategory(name, step) {
  const order = orderedCategories();
  const from = order.indexOf(name);
  const to = from + step;
  if (from < 0 || to < 0 || to >= order.length) return;
  [order[from], order[to]] = [order[to], order[from]];
  draft.category_order = order;
  renderCategories();
  const row = document.querySelector(`[data-category-name="${CSS.escape(name)}"]`);
  (row?.querySelector(`[data-move="${step}"]:not(:disabled)`) || row?.querySelector('[data-move]:not(:disabled)'))?.focus();
  changed();
}

$('#keyword-add').addEventListener('click', addKeyword);
keywordInput.addEventListener('keydown', event => {
  if (event.key === 'Enter') {
    event.preventDefault();
    addKeyword();
  }
});
keywordInput.addEventListener('input', () => showKeywordError(''));

form.addEventListener('click', event => {
  const target = event.target.closest('button');
  if (!target) return;
  if (target.dataset.removeKeyword !== undefined) {
    draft.keywords = draft.keywords.filter(word => word !== target.dataset.removeKeyword);
    renderKeywords();
    changed();
  } else if (target.dataset.day !== undefined) {
    const day = Number(target.dataset.day);
    const days = draft.schedule.days.includes(day) ? draft.schedule.days.filter(d => d !== day) : [...draft.schedule.days, day];
    draft.schedule = {...draft.schedule, days: days.sort((a, b) => a - b)};
    renderSchedule();
    changed();
  } else if (target.dataset.source !== undefined) {
    const source = target.dataset.source;
    const sources = draft.schedule.sources.includes(source) ? draft.schedule.sources.filter(s => s !== source) : [...draft.schedule.sources, source];
    if (!sources.length) {
      feedback.textContent = '받을 기사는 한 가지 이상 선택해야 합니다.';
      return;
    }
    draft.schedule = {...draft.schedule, sources};
    renderSchedule();
    changed();
  } else if (target.dataset.move !== undefined) {
    moveCategory(target.closest('[data-category-name]').dataset.categoryName, Number(target.dataset.move));
  } else if (target.id === 'category-reset') {
    draft.category_order = [];
    draft.hidden_categories = [];
    renderCategories();
    changed();
  }
});

form.addEventListener('change', event => {
  const target = event.target;
  if (target === time) {
    if (time.value) draft.schedule = {...draft.schedule, time: time.value};
    renderSchedule();
  } else if (target === enabled) {
    draft.schedule = {...draft.schedule, enabled: enabled.checked};
    renderSchedule();
  } else if (target.id === 'schedule-max') draft.schedule = {...draft.schedule, max_items: Number(target.value)};
  else if (target.id === 'display-count') draft.display_count = Number(target.value);
  else if (target.id === 'in-app-notification') draft.in_app_notification = target.checked;
  else if (target.id === 'email-notification') draft.email_notification = target.checked;
  else if (target.dataset.showCategory !== undefined) {
    const name = target.closest('[data-category-name]').dataset.categoryName;
    draft.hidden_categories = target.checked ? draft.hidden_categories.filter(item => item !== name) : [...draft.hidden_categories, name];
    if (!draft.category_order.length) draft.category_order = orderedCategories();
    renderCategories();
    document.querySelector(`[data-category-name="${CSS.escape(name)}"] [data-show-category]`)?.focus();
  } else return;
  changed();
});

function validate() {
  if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(draft.schedule.time)) return '예약 시각을 올바르게 입력해주세요.';
  if (draft.schedule.enabled && !draft.schedule.days.length) return '예약 알림을 사용하려면 요일을 하나 이상 선택해주세요.';
  if (draft.keywords.length > MAX_KEYWORDS) return `선호 검색어는 최대 ${MAX_KEYWORDS}개까지 저장할 수 있습니다.`;
  return '';
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  if (saving) return;
  if (time.value) draft.schedule = {...draft.schedule, time: time.value};
  const problem = validate();
  if (problem) {
    feedback.textContent = problem;
    return;
  }
  saving = true;
  const button = $('#settings-save');
  button.disabled = true;
  button.textContent = '저장 중…';
  try {
    const response = await fetch('/api/settings', {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(draft)});
    const body = await response.json().catch(() => ({}));
    if (response.status === 401) {
      feedback.textContent = '로그인이 만료되었습니다. 메인에서 다시 로그인한 뒤 저장해주세요.';
      return;
    }
    if (!response.ok) {
      feedback.textContent = body.error || '설정을 저장하지 못했습니다. 입력값을 확인해주세요.';
      return;
    }
    saved = body.settings;
    categories = body.available_categories;
    initial.next_run = body.next_run;
    draft = structuredClone(saved);
    renderAll();
    feedback.textContent = '설정을 저장했습니다.' + (body.next_run && saved.schedule.enabled ? ` 다음 예약: ${body.next_run}` : '');
  } catch {
    feedback.textContent = '네트워크 오류로 저장하지 못했습니다. 다시 시도해주세요.';
  } finally {
    saving = false;
    button.disabled = false;
    button.textContent = '설정 저장';
  }
});

form.addEventListener('reset', event => {
  event.preventDefault();
  draft = structuredClone(saved);
  keywordInput.value = '';
  showKeywordError('');
  renderAll();
  feedback.textContent = '마지막으로 저장한 값으로 되돌렸습니다.';
});

$('#run-now').addEventListener('click', async () => {
  const button = $('#run-now');
  const status = $('#run-feedback');
  button.disabled = true;
  status.textContent = '예약 소식을 만드는 중입니다…';
  try {
    const response = await fetch('/api/inbox/run', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'});
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      status.textContent = body.error || '예약 소식을 만들지 못했습니다. 다시 시도해주세요.';
      return;
    }
    status.textContent = `예약 소식함에 ${body.items.length}건을 넣었습니다. 저장된 설정 기준으로 골랐습니다.`;
    const nav = $('#inbox-nav');
    if (nav && saved.in_app_notification) {
      const badge = nav.querySelector('.inbox-badge') || nav.appendChild(document.createElement('small'));
      const count = (Number(badge.dataset.count) || Number((badge.textContent.match(/\d+/) || [0])[0])) + 1;
      badge.className = 'inbox-badge';
      badge.dataset.count = String(count);
      badge.textContent = `새 ${count}`;
    }
  } catch {
    status.textContent = '네트워크 오류로 예약 소식을 만들지 못했습니다.';
  } finally {
    button.disabled = false;
  }
});

document.querySelectorAll('.settings-menu a').forEach(link => link.addEventListener('click', () => {
  document.querySelectorAll('.settings-menu a').forEach(item => {
    item.classList.toggle('active', item === link);
    if (item === link) item.setAttribute('aria-current', 'location');
    else item.removeAttribute('aria-current');
  });
}));
document.querySelectorAll('[data-open-dialog]').forEach(button => button.addEventListener('click', () => {
  document.getElementById(button.dataset.openDialog).showModal();
}));
document.querySelectorAll('[data-close-dialog]').forEach(button => button.addEventListener('click', () => {
  button.closest('dialog').close();
}));
renderAll();

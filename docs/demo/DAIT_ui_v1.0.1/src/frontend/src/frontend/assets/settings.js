// 설정 화면. 예약 수집·선호 검색어·카테고리 순서·노출 설정은 [설정 저장]으로 서버(/api/settings)에 저장합니다.
// macOS Safari 대응:
//  - 저장은 localStorage가 아니라 서버에 합니다. Safari는 7일간 방문하지 않은 사이트의 스크립트 저장소를
//    지우고, 개인정보 보호 창에서는 창을 닫으면 사라지기 때문입니다. (예전 미리보기 값은 처음 한 번만 옮겨 옵니다.)
//  - 한글 입력 중 Enter: Safari는 조합 종료(compositionend) 뒤에 keyCode 229인 keydown을 보내므로
//    isComposing만으로는 걸러지지 않습니다. 229와 조합 상태를 함께 확인해 검색어가 잘리거나 두 번 들어가지 않게 합니다.
//  - structuredClone 대신 JSON 복사, dialog.showModal이 없을 때의 대체 동작을 둡니다(구형 Safari).
(() => {
  const MAX_KEYWORDS = 3;
  const MAX_TIMES = 5;
  const DAY_NAMES = ['월', '화', '수', '목', '금', '토', '일'];
  const $ = selector => document.querySelector(selector);
  const clone = value => JSON.parse(JSON.stringify(value));
  const dataNode = $('#settings-data');
  const initial = dataNode ? JSON.parse(dataNode.textContent) : null;

  const hour = $('#schedule-hour');
  const minute = $('#schedule-minute');
  const enabled = $('#schedule-enabled');
  const addTime = $('#schedule-add');
  const timeChips = $('#schedule-chips');
  const timeCount = $('#schedule-count');
  const timeFeedback = $('#schedule-feedback');
  const badge = $('#schedule-state');
  const feedback = $('#settings-feedback');
  const keywordInput = $('#keyword-input');
  const keywordError = $('#keyword-error');
  const saveButton = $('#settings-save');

  // 공통: 메뉴·안내 창·닉네임 (팀원 v1.0.1 동작 유지)
  document.querySelectorAll('.settings-menu a').forEach(link => link.addEventListener('click', () => {
    document.querySelectorAll('.settings-menu a').forEach(item => {
      item.classList.toggle('active', item === link);
      if (item === link) item.setAttribute('aria-current', 'location');
      else item.removeAttribute('aria-current');
    });
  }));
  document.querySelectorAll('[data-open-dialog]').forEach(button => button.addEventListener('click', () => {
    const dialog = document.getElementById(button.dataset.openDialog);
    if (typeof dialog.showModal === 'function') dialog.showModal();
    else dialog.setAttribute('open', '');
  }));
  document.querySelectorAll('[data-close-dialog]').forEach(button => button.addEventListener('click', () => {
    const dialog = button.closest('dialog');
    if (typeof dialog.close === 'function') dialog.close();
    else dialog.removeAttribute('open');
  }));
  $('#nickname-form')?.addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget, input = $('#nickname-input');
    const status = $('#nickname-feedback'), button = form.querySelector('button');
    button.disabled = true;
    status.textContent = '저장 중…';
    try {
      const response = await fetch('/api/settings/nickname', {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({nickname: input.value})});
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || '닉네임을 저장하지 못했습니다.');
      input.value = result.nickname;
      $('.session-status').textContent = result.nickname ? result.nickname + '님' : '회원님';
      status.textContent = result.message;
    } catch (error) { status.textContent = error.message || '닉네임을 저장하지 못했습니다.'; }
    finally { button.disabled = false; }
  });

  if (!initial) return;
  let saved = initial.settings;
  let categories = initial.available_categories;
  let nextRun = initial.next_run;
  let draft = clone(saved);
  let saving = false;
  let composing = false;

  // 예전 v1.0.1 미리보기(브라우저 저장) 값이 있으면, 서버에 아직 저장한 적 없을 때 한 번만 가져옵니다.
  const owner = $('#schedule').dataset.scheduleOwner;
  const legacyKey = 'dait.schedule.preview.v1:' + encodeURIComponent(owner);
  let migrated = false;
  try {
    const legacy = JSON.parse(localStorage.getItem(legacyKey) || 'null');
    if (!initial.saved && legacy && Array.isArray(legacy.times) && legacy.times.length) {
      const times = legacy.times.filter(value => /^(?:[01]\d|2[0-3]):(?:00|30)$/.test(value));
      if (times.length) {
        draft.schedule.times = [...new Set(times)].sort().slice(0, MAX_TIMES);
        if (typeof legacy.enabled === 'boolean') draft.schedule.enabled = legacy.enabled;
        migrated = true;
      }
    }
  } catch (_) { /* Safari 개인정보 보호 창 등에서 저장소 접근이 막혀도 서버 값으로 계속합니다. */ }

  function setPressed(button, on) {
    button.setAttribute('aria-pressed', String(on));
    button.classList.toggle('active', on);
  }

  function changed() {
    return JSON.stringify(draft) !== JSON.stringify(saved);
  }

  function previewText() {
    const schedule = draft.schedule;
    if (!schedule.enabled) return '예약 수집을 사용하지 않습니다.';
    if (!schedule.times.length) return '예약 시간을 한 개 이상 추가해주세요.';
    if (!schedule.days.length) return '요일을 하나 이상 선택해주세요.';
    const days = schedule.days.length === 7 ? '매일' : '매주 ' + schedule.days.map(day => DAY_NAMES[day]).join('·');
    const tail = JSON.stringify(schedule) !== JSON.stringify(saved.schedule) ? ' · 저장하면 적용됩니다' : nextRun ? ` · 다음 ${nextRun}` : '';
    return `${days} ${schedule.times.join(', ')} KST${tail}`;
  }

  function renderTimes(message = '') {
    const times = draft.schedule.times;
    timeCount.textContent = `${times.length} / ${MAX_TIMES}`;
    timeChips.replaceChildren();
    for (const time of times) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'schedule-chip';
      button.dataset.removeTime = time;
      button.textContent = `${time} ×`;
      button.setAttribute('aria-label', `${time} 예약 시각 삭제`);
      timeChips.append(button);
    }
    addTime.disabled = times.length >= MAX_TIMES;
    timeFeedback.textContent = message || (times.length >= MAX_TIMES ? `예약 시각은 최대 ${MAX_TIMES}개까지 설정할 수 있습니다.` : '');
  }

  function renderSchedule() {
    const schedule = draft.schedule;
    enabled.checked = schedule.enabled;
    $('#schedule-max').value = String(schedule.max_items);
    document.querySelectorAll('[data-day]').forEach(chip => setPressed(chip, schedule.days.includes(Number(chip.dataset.day))));
    document.querySelectorAll('[data-source]').forEach(chip => setPressed(chip, schedule.sources.includes(chip.dataset.source)));
    badge.textContent = schedule.enabled ? '사용' : '사용 안 함';
    badge.classList.toggle('ready', schedule.enabled);
    badge.classList.toggle('pending', !schedule.enabled);
    $('#schedule-preview').textContent = previewText();
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
    keywordInput.placeholder = draft.keywords.length >= MAX_KEYWORDS ? `최대 ${MAX_KEYWORDS}개를 모두 등록했습니다` : '예: 멀티모달, AI 에이전트, HBM';
  }

  function orderedCategories() {
    const rank = new Map(draft.category_order.map((name, index) => [name, index]));
    const position = name => (rank.has(name) ? rank.get(name) : rank.size + categories.indexOf(name));
    return categories.slice().sort((a, b) => position(a) - position(b));
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
      const label = document.createElement('span');
      label.className = 'category-name';
      label.textContent = shown ? name : `${name} (숨김)`;
      row.append(label);
      for (const step of [-1, 1]) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'icon-button';
        button.dataset.move = String(step);
        button.textContent = step < 0 ? '↑' : '↓';
        button.disabled = step < 0 ? index === 0 : index === ordered.length - 1;
        button.setAttribute('aria-label', `${name} ${step < 0 ? '위로' : '아래로'}`);
        row.append(button);
      }
      const toggle = document.createElement('label');
      toggle.className = 'switch-control';
      const input = document.createElement('input');
      input.type = 'checkbox';
      input.className = 'sr-only';
      input.dataset.showCategory = '';
      input.checked = shown;
      input.setAttribute('aria-label', `${name} 표시`);
      const knob = document.createElement('span');
      knob.className = 'switch';
      knob.setAttribute('aria-hidden', 'true');
      toggle.append(input, knob);
      row.append(toggle);
      list.append(row);
    });
  }

  function renderAll() {
    renderTimes();
    renderSchedule();
    renderKeywords();
    renderCategories();
    $('#display-count').value = String(draft.display_count);
    $('#in-app-notification').checked = draft.in_app_notification;
    $('#email-notification').checked = draft.email_notification;
  }

  function touched() {
    feedback.textContent = changed() ? '변경 내용이 있습니다. [설정 저장]을 눌러야 적용됩니다.' : '';
    $('#schedule-preview').textContent = previewText();
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
    draft.keywords = draft.keywords.concat(word);
    keywordInput.value = '';
    renderKeywords();
    touched();
    keywordInput.focus();
  }

  function addScheduleTime() {
    const raw = String(hour.value).trim();
    const hourNumber = Number(raw);
    // Safari의 number 입력은 글자를 그대로 받아 value가 빈 문자열이 될 수 있어 여기서 다시 확인합니다.
    if (raw === '' || !Number.isInteger(hourNumber) || hourNumber < 0 || hourNumber > 23) {
      renderTimes('시는 0부터 23까지 정수로 입력해주세요.');
      hour.focus();
      return;
    }
    const time = `${String(hourNumber).padStart(2, '0')}:${minute.value}`;
    if (draft.schedule.times.includes(time)) return renderTimes('이미 추가한 예약 시각입니다.');
    if (draft.schedule.times.length >= MAX_TIMES) return renderTimes(`예약 시각은 최대 ${MAX_TIMES}개까지 설정할 수 있습니다.`);
    draft.schedule.times = draft.schedule.times.concat(time).sort();
    renderTimes();
    touched();
  }

  function moveCategory(name, step) {
    const order = orderedCategories();
    const from = order.indexOf(name);
    const to = from + step;
    if (from < 0 || to < 0 || to >= order.length) return;
    const swap = order[from];
    order[from] = order[to];
    order[to] = swap;
    draft.category_order = order;
    renderCategories();
    const row = document.querySelector(`[data-category-name="${CSS.escape(name)}"]`);
    (row && (row.querySelector(`[data-move="${step}"]:not(:disabled)`) || row.querySelector('[data-move]:not(:disabled)')))?.focus();
    touched();
  }

  addTime.addEventListener('click', addScheduleTime);
  hour.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.isComposing && event.keyCode !== 229) {
      event.preventDefault();
      addScheduleTime();
    }
  });
  $('#keyword-add').addEventListener('click', addKeyword);
  keywordInput.addEventListener('compositionstart', () => { composing = true; });
  keywordInput.addEventListener('compositionend', () => { composing = false; });
  keywordInput.addEventListener('keydown', event => {
    if (event.key !== 'Enter') return;
    event.preventDefault();
    if (composing || event.isComposing || event.keyCode === 229) return;
    addKeyword();
  });
  keywordInput.addEventListener('input', () => showKeywordError(''));

  document.addEventListener('click', event => {
    const target = event.target.closest('button');
    if (!target || !target.closest('.settings-sections')) return;
    if (target.dataset.removeTime !== undefined) {
      draft.schedule.times = draft.schedule.times.filter(item => item !== target.dataset.removeTime);
      renderTimes('예약 시각을 삭제했습니다.');
      touched();
    } else if (target.dataset.removeKeyword !== undefined) {
      draft.keywords = draft.keywords.filter(word => word !== target.dataset.removeKeyword);
      renderKeywords();
      touched();
    } else if (target.dataset.day !== undefined) {
      const day = Number(target.dataset.day);
      const days = draft.schedule.days.includes(day) ? draft.schedule.days.filter(d => d !== day) : draft.schedule.days.concat(day);
      draft.schedule.days = days.sort((a, b) => a - b);
      renderSchedule();
      touched();
    } else if (target.dataset.source !== undefined) {
      const source = target.dataset.source;
      const sources = draft.schedule.sources.includes(source) ? draft.schedule.sources.filter(s => s !== source) : draft.schedule.sources.concat(source);
      if (!sources.length) {
        feedback.textContent = '받을 기사는 한 가지 이상 선택해야 합니다.';
        return;
      }
      draft.schedule.sources = sources;
      renderSchedule();
      touched();
    } else if (target.dataset.move !== undefined) {
      moveCategory(target.closest('[data-category-name]').dataset.categoryName, Number(target.dataset.move));
    } else if (target.id === 'category-reset') {
      draft.category_order = [];
      draft.hidden_categories = [];
      renderCategories();
      touched();
    }
  });

  document.addEventListener('change', event => {
    const target = event.target;
    if (target === enabled) {
      draft.schedule.enabled = enabled.checked;
      renderSchedule();
    } else if (target.id === 'schedule-max') draft.schedule.max_items = Number(target.value);
    else if (target.id === 'display-count') draft.display_count = Number(target.value);
    else if (target.id === 'in-app-notification') draft.in_app_notification = target.checked;
    else if (target.id === 'email-notification') draft.email_notification = target.checked;
    else if (target.dataset && target.dataset.showCategory !== undefined) {
      const name = target.closest('[data-category-name]').dataset.categoryName;
      draft.hidden_categories = target.checked ? draft.hidden_categories.filter(item => item !== name) : draft.hidden_categories.concat(name);
      if (!draft.category_order.length) draft.category_order = orderedCategories();
      renderCategories();
      document.querySelector(`[data-category-name="${CSS.escape(name)}"] [data-show-category]`)?.focus();
    } else return;
    touched();
  });

  function validate() {
    const schedule = draft.schedule;
    if (schedule.enabled && !schedule.times.length) return '예약 수집을 사용하려면 예약 시간을 한 개 이상 추가해주세요.';
    if (schedule.enabled && !schedule.days.length) return '예약 수집을 사용하려면 요일을 하나 이상 선택해주세요.';
    if (draft.keywords.length > MAX_KEYWORDS) return `선호 검색어는 최대 ${MAX_KEYWORDS}개까지 저장할 수 있습니다.`;
    return '';
  }

  saveButton.addEventListener('click', async () => {
    if (saving) return;
    const problem = validate();
    if (problem) {
      feedback.textContent = problem;
      return;
    }
    saving = true;
    saveButton.disabled = true;
    saveButton.textContent = '저장 중…';
    try {
      const response = await fetch('/api/settings', {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(draft), cache: 'no-store'});
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
      nextRun = body.next_run;
      draft = clone(saved);
      if (migrated) {
        try { localStorage.removeItem(legacyKey); } catch (_) { /* 지우지 못해도 다음부터는 서버 값을 씁니다. */ }
        migrated = false;
      }
      renderAll();
      feedback.textContent = '설정을 저장했습니다.' + (nextRun && saved.schedule.enabled ? ` 다음 예약: ${nextRun}` : '');
    } catch (_) {
      feedback.textContent = '네트워크 오류로 저장하지 못했습니다. 다시 시도해주세요.';
    } finally {
      saving = false;
      saveButton.disabled = false;
      saveButton.textContent = '설정 저장';
    }
  });

  $('#settings-reset').addEventListener('click', () => {
    draft = clone(saved);
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
      const response = await fetch('/api/inbox/run', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}', cache: 'no-store'});
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        status.textContent = body.error || '예약 소식을 만들지 못했습니다. 다시 시도해주세요.';
        return;
      }
      status.textContent = `예약 소식함에 ${body.items.length}건을 넣었습니다. 저장된 설정 기준으로 골랐습니다.`;
      const nav = $('#inbox-nav');
      if (nav && saved.in_app_notification) {
        let counter = nav.querySelector('.inbox-badge');
        if (!counter) {
          counter = document.createElement('small');
          counter.className = 'inbox-badge';
          nav.append(counter);
        }
        const count = (Number(counter.dataset.count) || Number((counter.textContent.match(/\d+/) || [0])[0])) + 1;
        counter.dataset.count = String(count);
        counter.textContent = `새 ${count}`;
      }
    } catch (_) {
      status.textContent = '네트워크 오류로 예약 소식을 만들지 못했습니다.';
    } finally {
      button.disabled = false;
    }
  });

  hour.value = '8';
  renderAll();
  if (migrated) feedback.textContent = '이 브라우저에 남아 있던 예약 시간을 불러왔습니다. [설정 저장]을 누르면 계정에 저장됩니다.';
  if (new URLSearchParams(window.location.search).get('section') === 'interests' || window.location.hash === '#interests') {
    $('#interests').scrollIntoView();
    document.querySelector('.settings-menu a[href="#interests"]')?.click();
  }
})();

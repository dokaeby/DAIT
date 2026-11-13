/* 설정 화면은 /v1 API만 호출하며 DB와 인증 정책은 서버에 둔다. */
(async () => {
  'use strict';
  const $ = id => document.getElementById(id);
  const show = (id, text, ok = true) => { $(id).textContent = text; $(id).classList.toggle('is-error', !ok); };
  let sessionExpired = false;
  function showGuest() {
    $('settings-sidebar').hidden = true;
    $('settings-body').hidden = true;
    $('settings-main').classList.add('guest-view');
    $('auth-required').hidden = false;
  }
  async function request(url, options) {
    if (sessionExpired) throw new Error('로그인이 만료되었습니다. 다시 로그인해 주세요.');
    const res = await DAIT.api(url, options);
    if (res.status === 401) {
      sessionExpired = true;
      showGuest();
      throw new Error('로그인이 만료되었습니다. 다시 로그인해 주세요.');
    }
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(typeof body.message === 'string' ? body.message : '요청을 처리하지 못했습니다. 다시 시도해 주세요.');
    }
    return res.status === 204 ? null : res.json();
  }
  async function action(control, feedback, callback) {
    if (control.dataset.busy) return;
    control.dataset.busy = 'true';
    const controls = control.matches('form') ? [...control.querySelectorAll('input,select,button')] : [control];
    const disabled = controls.map(el => el.disabled);
    controls.forEach(el => { el.disabled = true; });
    try { await callback(); }
    catch (error) { show(feedback, error instanceof TypeError ? '서버에 연결할 수 없습니다. 다시 시도해 주세요.' : error.message, false); }
    finally { controls.forEach((el, i) => { el.disabled = disabled[i]; }); delete control.dataset.busy; }
  }
  function keywords(id) {
    const values = [...new Set($(id).value.split(',').map(value => value.trim()).filter(Boolean))];
    if (values.length > 20 || values.some(value => value.length > 50)) throw new Error('키워드는 최대 20개, 각 50자까지 입력해 주세요.');
    return values;
  }
  const user = await DAIT.currentUser();
  if (!user) { showGuest(); return; }
  $('settings-body').hidden = false;
  $('settings-sidebar').hidden = false;
  $('account-email').textContent = user.email;
  $('account-nickname').textContent = user.nickname || '미설정';
  $('nickname-input').value = user.nickname || '';
  $('nickname-form').addEventListener('submit', event => {
    event.preventDefault();
    const value = $('nickname-input').value.normalize('NFKC').trim();
    action(event.currentTarget, 'nickname-feedback', async () => {
      const result = await request('/v1/me/nickname', { method: 'PATCH', body: JSON.stringify({ nickname: value || null }) });
      $('nickname-input').value = result.nickname || '';
      $('account-nickname').textContent = result.nickname || '미설정';
      show('nickname-feedback', '닉네임을 저장했습니다.');
      await DAIT.renderAuthArea();
    });
  });
  const welcoming = new URLSearchParams(location.search).get('welcome') === '1';
  if (welcoming) { $('welcome-interests').hidden = false; $('interests').prepend($('welcome-interests')); }
  function markSettingsSection(section = location.hash || '#schedule') {
    document.querySelectorAll('.settings-menu a').forEach(link => {
      const active = link.getAttribute('href') === section;
      link.classList.toggle('active', active);
      if (active) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
    document.querySelectorAll('#settings-sidebar .nav-item').forEach(link => {
      const target = section === '#interests' ? '/settings.html#interests' : '/settings.html';
      link.classList.toggle('active', link.getAttribute('href') === target);
    });
  }
  if (location.hash === '#display') history.replaceState(null, '', '#schedule');
  markSettingsSection();
  window.addEventListener('hashchange', () => markSettingsSection());
  let sectionScrollPending = false;
  function updateSettingsSectionFromScroll() {
    sectionScrollPending = false;
    const sections = [...document.querySelectorAll('.settings-menu a')]
      .map(link => document.getElementById(link.hash.slice(1)))
      .filter(Boolean);
    if (!sections.length) return;
    const head = document.querySelector('[data-sticky-controls]');
    const menu = document.querySelector('.settings-menu');
    const marker = Math.max(head.getBoundingClientRect().bottom, window.innerWidth <= 1100 ? menu.getBoundingClientRect().bottom : 0) + 24;
    let current = sections[0];
    for (const section of sections) {
      if (section.getBoundingClientRect().top <= marker) current = section;
    }
    if (window.scrollY > 0 && window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2) {
      current = sections[sections.length - 1];
    }
    markSettingsSection('#' + current.id);
  }
  window.addEventListener('scroll', () => {
    if (!sectionScrollPending) {
      sectionScrollPending = true;
      requestAnimationFrame(updateSettingsSectionFromScroll);
    }
  }, { passive: true });

  function renderSidebar(catalog) {
    const host = $('settings-sidebar-categories'); host.replaceChildren();
    const codes = { ai: 'AI', economy: 'ECONOMY', society: 'POLITICS', en_ai: 'AI', en_economy: 'ECONOMY', en_society: 'POLITICS' };
    const labels = { ai: 'AI•인공지능', economy: '경제·비즈니스', society: '사회·문화' };
    for (const group of catalog.groups) {
      if (!codes[group.group]) continue;
      const english = group.group.startsWith('en_');
      const englishNames = {en_ai: 'AI & Technology', en_economy: 'Economy & Business', en_society: 'Society & Culture'};
      if (group.group === 'en_ai') {
        const label = document.createElement('span'); label.className = 'nav-label'; label.textContent = 'English News'; host.append(label);
      }
      const container = document.createElement('div'); container.className = 'topic-group';
      const row = document.createElement('div'); row.className = 'topic-heading-row';
      const heading = document.createElement('a'); heading.className = 'nav-item topic-heading';
      heading.textContent = english ? englishNames[group.group] : '✦ ' + labels[group.group];
      heading.href = '/?' + new URLSearchParams({ui: '20261112-search', category: codes[group.group], ...(english ? {language: 'en'} : {})});
      const list = document.createElement('ul'); list.className = 'topic-list'; list.hidden = true;
      list.id = 'settings-topics-' + group.group;
      const toggle = document.createElement('button'); toggle.type = 'button'; toggle.className = 'topic-toggle';
      toggle.setAttribute('aria-label', (labels[group.group] || group.group_name) + ' 소주제 펼치기/접기');
      toggle.setAttribute('aria-expanded', 'false'); toggle.setAttribute('aria-controls', list.id);
      toggle.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>';
      toggle.addEventListener('click', () => { list.hidden = !list.hidden; toggle.setAttribute('aria-expanded', String(!list.hidden)); });
      for (const item of group.interests) {
        const li = document.createElement('li'); const link = document.createElement('a');
        link.className = 'topic-button'; link.textContent = item.name;
        link.href = '/?' + new URLSearchParams({ ui: '20261112-search', category: codes[group.group], topic: item.code, ...(group.group.startsWith('en_') ? {language:'en'} : {}) });
        li.append(link); list.append(li);
      }
      row.append(heading, toggle); container.append(row, list); host.append(container);
    }
  }

  const interestInputs = () => [...$('interest-options').querySelectorAll('input[type=checkbox]')];
  let interestLoading = false;
  function interestCount() { $('interest-count').textContent = `${interestInputs().filter(el => el.checked).length}개 선택`; }
  function applyInterests(data) {
    const selected = new Set(data.interests.map(item => item.code));
    interestInputs().forEach(el => { el.checked = selected.has(el.value); });
    interestCount();
  }
  async function loadInterests() {
    if (interestLoading) return;
    interestLoading = true;
    $('interest-fields').disabled = true;
    $('interests-retry').hidden = true;
    show('interests-feedback', '관심사를 불러오고 있습니다…');
    try {
      const [catalog, mine] = await Promise.all([request('/v1/interests/catalog'), request('/v1/me/interests')]);
      renderSidebar(catalog);
      const fragment = document.createDocumentFragment();
      for (const group of catalog.groups) {
        const section = document.createElement('section'); section.className = 'interest-group';
        const title = document.createElement('h3'); title.textContent = group.group_name; section.append(title);
        const pills = document.createElement('div'); pills.className = 'interest-pills';
        for (const item of group.interests) {
          const label = document.createElement('label'); label.className = 'interest-pill';
          const input = document.createElement('input'); input.type = 'checkbox'; input.value = item.code;
          const text = document.createElement('span'); text.className = 'interest-pill-label';
          const icon = document.createElement('span'); icon.className = 'pill-icon'; icon.setAttribute('aria-hidden', 'true');
          text.append(icon, document.createTextNode(item.name)); label.append(input, text); pills.append(label);
        }
        section.append(pills); fragment.append(section);
      }
      $('interest-options').replaceChildren(fragment);
      applyInterests(mine);
      $('interest-fields').disabled = false;
      show('interests-feedback', '선택하거나 해제하면 자동으로 저장됩니다.');
      if (location.hash === '#interests') $('interests').scrollIntoView();
    } catch (error) {
      show('interests-feedback', '관심사를 불러오지 못했습니다. 다시 불러오기를 눌러 주세요.', false);
      $('interests-retry').hidden = false;
    } finally { interestLoading = false; }
  }
  const autosave = window.createInterestAutosave({
    read: () => interestInputs().filter(el => el.checked).map(el => el.value),
    write: interests => request('/v1/me/interests', { method: 'PUT', body: JSON.stringify({ interests }) }),
    status: state => {
      $('interests-save-retry').hidden = state !== 'error';
      show('interests-feedback', state === 'saving' ? '저장 중…' : state === 'saved' ? '저장되었습니다.' : '저장하지 못했습니다. 다시 시도해 주세요.', state !== 'error');
    }
  });
  function interestsChanged() {
    if ($('interest-fields').disabled) return;
    interestCount(); autosave.change();
  }
  $('interest-options').addEventListener('change', interestsChanged);
  for (const [id, checked] of [['interests-all', true], ['interests-clear', false]]) $(id).addEventListener('click', () => {
    interestInputs().forEach(el => { el.checked = checked; }); interestsChanged();
  });
  $('interests-retry').addEventListener('click', loadInterests);
  $('interests-save-retry').addEventListener('click', () => autosave.flush().catch(() => {}));
  $('interests-form').addEventListener('submit', event => event.preventDefault());
  // Finish pending writes before leaving for the main page or a sidebar topic.
  document.addEventListener('click', async event => {
    const link = event.target.closest('a[href]');
    if (!link || event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || link.target || link.hasAttribute('download')) return;
    const target = new URL(link.href, location.href);
    if (target.origin !== location.origin || (target.pathname === location.pathname && target.search === location.search) || !autosave.dirty()) return;
    event.preventDefault();
    try { await autosave.flush(); location.assign(target.href); }
    catch { $('interests-feedback').scrollIntoView({ block: 'center' }); }
  });
  window.addEventListener('beforeunload', event => {
    if (autosave.dirty()) { event.preventDefault(); event.returnValue = ''; }
  });

  function applySettings(data) {
    $('set-default-count').value = String(data.default_count);
    $('set-keywords').value = data.keywords.join(', ');
    $('set-in-app').checked = data.in_app_notice;
    $('set-email').checked = data.email_notice;
  }
  $('settings-form').addEventListener('submit', event => {
    event.preventDefault();
    action(event.currentTarget, 'settings-feedback', async () => {
      const result = await request('/v1/me/settings', { method: 'PATCH', body: JSON.stringify({ default_count: Number($('set-default-count').value), keywords: keywords('set-keywords'), in_app_notice: $('set-in-app').checked, email_notice: $('set-email').checked }) });
      applySettings(result); show('settings-feedback', '저장했습니다.');
    });
  });
  for (let hour = 0; hour < 24; hour++) { const option = document.createElement('option'); option.value = String(hour).padStart(2, '0'); option.textContent = option.value + '시'; $('sched-hour').append(option); }
  const getTime = () => $('sched-hour').value + ':' + $('sched-minute').value;
  let scheduleCount = 0;
  $('withdraw-open').addEventListener('click', () => { $('withdraw-form').reset(); $('withdraw-feedback').textContent = ''; $('withdraw-dialog').showModal(); });
  $('withdraw-cancel').addEventListener('click', () => $('withdraw-dialog').close());
  $('withdraw-dialog').addEventListener('close', () => { $('withdraw-password').value = ''; });
  $('withdraw-form').addEventListener('submit', event => {
    event.preventDefault();
    action(event.currentTarget, 'withdraw-feedback', async () => {
      const res = await fetch('/v1/me', { method: 'DELETE', headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + DAIT.getToken('dait_access_token') }, body: JSON.stringify({ password: $('withdraw-password').value }) });
      if (!res.ok) throw new Error(res.status === 429 ? '시도 횟수가 초과됐습니다. 나중에 다시 시도해 주세요.' : '탈퇴하지 못했습니다. 비밀번호와 로그인 상태를 확인해 주세요.');
      $('withdraw-password').value = ''; DAIT.clearTokens();
      try { localStorage.removeItem('dait_remembered_email'); } catch { /* 저장소를 쓸 수 없어도 탈퇴는 완료된다. */ }
      location.assign('/?ui=20261112-search');
    });
  });
  async function loadSchedules() {
    const data = await request('/v1/me/schedules');
    scheduleCount = data.items.length;
    $('schedule-count').textContent = `${scheduleCount} / 5`;
    const fragment = document.createDocumentFragment();
    if (!data.items.length) { const li = document.createElement('li'); li.textContent = '등록된 예약이 없습니다.'; fragment.append(li); }
    for (const schedule of data.items) {
      const li = document.createElement('li'); li.className = 'schedule-item';
      const text = document.createElement('span'); text.className = 'schedule-meta';
      text.textContent = schedule.local_time;
      const remove = document.createElement('button');
      remove.type = 'button'; remove.className = 'schedule-remove'; remove.textContent = '×';
      remove.setAttribute('aria-label', `${schedule.local_time} 예약 삭제`);
      remove.addEventListener('click', () => action(remove, 'schedule-feedback', async () => {
        await request('/v1/me/schedules/' + encodeURIComponent(schedule.id), { method: 'DELETE' });
        show('schedule-feedback', '예약을 삭제했습니다.');
        await loadSchedules();
      }));
      li.append(text, remove); fragment.append(li);
    }
    const otherTimezones = data.items.some(item => item.timezone !== 'Asia/Seoul');
    $('schedule-timezone-warning').hidden = !otherTimezones;
    $('schedule-list').replaceChildren(fragment);
  }
  $('schedule-form').addEventListener('submit', event => {
    event.preventDefault();
    const form = event.currentTarget;
    action(form, 'schedule-feedback', async () => {
      if (scheduleCount >= 5) throw new Error('예약은 최대 5개까지 추가할 수 있습니다.');
      const payload = { local_time: getTime(), timezone: 'Asia/Seoul', criteria: { categories: ['AI'], source_ids: [], keywords: [] }, enabled: true };
      await request('/v1/me/schedules', { method: 'POST', body: JSON.stringify(payload) });
      form.reset(); show('schedule-feedback', '예약을 추가했습니다.'); await loadSchedules();
    });
  });
  await Promise.all([
    loadInterests(),
    action($('schedule-form'), 'schedule-feedback', loadSchedules),
  ]);
})();

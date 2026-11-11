/* 설정 화면은 /v1 API만 호출하며 DB와 인증 정책은 서버에 둔다. */
(async () => {
  'use strict';
  const $ = id => document.getElementById(id);
  const show = (id, text, ok = true) => { $(id).textContent = text; $(id).classList.toggle('is-error', !ok); };
  let sessionExpired = false;
  function showGuest() {
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
      show('interests-feedback', '선택 후 관심사 저장을 눌러 주세요.');
    } catch (error) {
      show('interests-feedback', '관심사를 불러오지 못했습니다. 다시 불러오기를 눌러 주세요.', false);
      $('interests-retry').hidden = false;
    } finally { interestLoading = false; }
  }
  $('interest-options').addEventListener('change', interestCount);
  for (const [id, checked] of [['interests-all', true], ['interests-clear', false]]) $(id).addEventListener('click', () => { interestInputs().forEach(el => { el.checked = checked; }); interestCount(); });
  $('interests-retry').addEventListener('click', loadInterests);
  $('interests-form').addEventListener('submit', event => {
    event.preventDefault();
    if ($('interest-fields').disabled) return;
    const interests = interestInputs().filter(el => el.checked).map(el => el.value);
    action(event.currentTarget, 'interests-feedback', async () => {
      const result = await request('/v1/me/interests', { method: 'PUT', body: JSON.stringify({ interests }) });
      applyInterests(result); show('interests-feedback', '관심사를 저장했습니다.');
    });
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
  let editing = null;
  let editingCriteria = null;
  let editingEnabled = true;
  function resetSchedule() { editing = null; editingCriteria = null; editingEnabled = true; $('schedule-form').reset(); $('sched-tz').value = 'Asia/Seoul'; $('sched-submit').textContent = '예약 추가'; $('sched-cancel-edit').hidden = true; }
  async function loadSchedules() {
    const data = await request('/v1/me/schedules');
    const fragment = document.createDocumentFragment();
    if (!data.items.length) { const li = document.createElement('li'); li.textContent = '등록된 예약이 없습니다.'; fragment.append(li); }
    for (const schedule of data.items) {
      const li = document.createElement('li'); li.className = 'schedule-item';
      const text = document.createElement('span'); text.className = 'schedule-meta';
      text.textContent = `${schedule.local_time} · ${schedule.timezone} · ${schedule.enabled ? '사용' : '중지'} · 다음 예정 ${schedule.next_run_at ? new Date(schedule.next_run_at).toLocaleString('ko-KR') : '-'}${schedule.criteria.keywords.length ? ' · ' + schedule.criteria.keywords.join(', ') : ''}`;
      const edit = document.createElement('button'); edit.className = 'secondary-button'; edit.type = 'button'; edit.textContent = '수정';
      edit.addEventListener('click', () => {
        if ($('schedule-form').dataset.busy) return;
        editing = schedule.id; editingCriteria = schedule.criteria; editingEnabled = schedule.enabled;
        $('sched-time').value = schedule.local_time; $('sched-tz').value = schedule.timezone; $('sched-keywords').value = schedule.criteria.keywords.join(', ');
        $('sched-submit').textContent = '예약 수정'; $('sched-cancel-edit').hidden = false; show('schedule-feedback', ''); $('sched-time').focus();
      });
      const del = document.createElement('button'); del.type = 'button'; del.className = 'danger-button'; del.textContent = '삭제';
      del.addEventListener('click', () => action(del, 'schedule-feedback', async () => {
        await request('/v1/me/schedules/' + encodeURIComponent(schedule.id), { method: 'DELETE' });
        if (editing === schedule.id) resetSchedule();
        show('schedule-feedback', '삭제했습니다.'); await loadSchedules();
      }));
      li.append(text, edit, del); fragment.append(li);
    }
    $('schedule-list').replaceChildren(fragment);
  }
  $('sched-cancel-edit').addEventListener('click', resetSchedule);
  $('schedule-form').addEventListener('submit', event => {
    event.preventDefault();
    action(event.currentTarget, 'schedule-feedback', async () => {
      const isEdit = editing !== null;
      const payload = { local_time: $('sched-time').value, timezone: $('sched-tz').value.trim(), criteria: { ...(editingCriteria || { categories: ['AI'], source_ids: [] }), keywords: keywords('sched-keywords') }, enabled: editingEnabled };
      await request('/v1/me/schedules' + (isEdit ? '/' + encodeURIComponent(editing) : ''), { method: isEdit ? 'PATCH' : 'POST', body: JSON.stringify(payload) });
      resetSchedule(); show('schedule-feedback', isEdit ? '예약을 수정했습니다.' : '예약을 추가했습니다.'); await loadSchedules();
    });
  });
  await Promise.all([
    loadInterests(),
    action($('settings-form'), 'settings-feedback', async () => { applySettings(await request('/v1/me/settings')); }),
    action($('schedule-form'), 'schedule-feedback', loadSchedules),
  ]);
})();

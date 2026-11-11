(() => {
  const hour = document.querySelector('#schedule-hour');
  const minute = document.querySelector('#schedule-minute');
  const enabled = document.querySelector('#schedule-enabled');
  const add = document.querySelector('#schedule-add');
  const chips = document.querySelector('#schedule-chips');
  const feedback = document.querySelector('#schedule-preview');
  const count = document.querySelector('#schedule-count');
  const badge = document.querySelector('#schedule-state');
  const owner = document.querySelector('#schedule').dataset.scheduleOwner;
  const storageKey = 'dait.schedule.preview.v1:' + encodeURIComponent(owner);
  let times = [];
  let storageError = false;
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) || 'null');
    if (saved && Array.isArray(saved.times)) {
      times = [...new Set(saved.times.filter(value => typeof value === 'string' && /^(?:[01]\d|2[0-3]):(?:00|30)$/.test(value)))].sort().slice(0, 5);
      if (typeof saved.enabled === 'boolean') enabled.checked = saved.enabled;
    }
  } catch (_) { storageError = true; }

  function persist() {
    try {
      localStorage.setItem(storageKey, JSON.stringify({times, enabled: enabled.checked}));
      storageError = false;
    } catch (_) { storageError = true; }
  }

  function render(message = '') {
    count.textContent = `${times.length} / 5`;
    chips.replaceChildren();
    for (const time of times) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'schedule-chip';
      button.textContent = `${time} ×`;
      button.setAttribute('aria-label', `${time} 예약 시각 삭제`);
      button.addEventListener('click', () => { times = times.filter(item => item !== time); persist(); render('예약 시각을 삭제했습니다.'); });
      chips.append(button);
    }
    add.disabled = times.length >= 5;
    badge.textContent = enabled.checked ? '사용 · 미리보기' : '사용 안 함 · 미리보기';
    badge.classList.toggle('ready', enabled.checked);
    badge.classList.toggle('pending', !enabled.checked);
    feedback.textContent = storageError ? '브라우저에 예약 시각을 저장하지 못했습니다. 저장 공간 설정을 확인해주세요.' : message || (times.length >= 5 ? '예약 시각은 최대 5개까지 설정할 수 있습니다.' : enabled.checked && !times.length ? '예약 수집을 사용하려면 시각을 한 개 이상 추가해주세요.' : enabled.checked ? '선택한 시각을 확인해주세요.' : '예약 수집을 사용하지 않는 미리보기입니다. 선택한 시각은 유지됩니다.');
  }
  hour.value = '8';
  add.addEventListener('click', () => {
    const rawHour = hour.value.trim();
    const hourNumber = Number(rawHour);
    if (rawHour === '' || !Number.isInteger(hourNumber) || hourNumber < 0 || hourNumber > 23) {
      render('시는 0부터 23까지 정수로 입력해주세요.');
      hour.focus();
      return;
    }
    const time = `${String(hourNumber).padStart(2, '0')}:${minute.value}`;
    if (times.includes(time)) { render('이미 추가한 예약 시각입니다.'); return; }
    if (times.length >= 5) { render('예약 시각은 최대 5개까지 설정할 수 있습니다.'); return; }
    times.push(time); times.sort(); persist(); render();
  });
  enabled.addEventListener('change', () => { persist(); render(); });
  document.querySelector('#settings-reset')?.addEventListener('click', () => {
    times = []; hour.value = '8'; minute.value = '30'; enabled.checked = true; persist();
    render('예약 수집 미리보기를 초기화했습니다.');
  });
  document.querySelectorAll('.settings-menu a').forEach(link => link.addEventListener('click', () => {
    document.querySelectorAll('.settings-menu a').forEach(item => {
      item.classList.toggle('active', item === link);
      if (item === link) item.setAttribute('aria-current', 'location');
      else item.removeAttribute('aria-current');
    });
  }));
  document.querySelectorAll('[data-open-dialog]').forEach(button => button.addEventListener('click', () => document.getElementById(button.dataset.openDialog).showModal()));
  document.querySelectorAll('[data-close-dialog]').forEach(button => button.addEventListener('click', () => button.closest('dialog').close()));
  document.querySelector('#nickname-form')?.addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget, input = document.querySelector('#nickname-input');
    const feedback = document.querySelector('#nickname-feedback'), button = form.querySelector('button');
    button.disabled = true;
    feedback.textContent = '저장 중…';
    try {
      const response = await fetch('/api/settings/nickname', {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({nickname: input.value})});
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || '닉네임을 저장하지 못했습니다.');
      input.value = result.nickname;
      document.querySelector('.session-status').textContent = result.nickname ? result.nickname + '님' : '회원님';
      feedback.textContent = result.message;
    } catch (error) { feedback.textContent = error.message || '닉네임을 저장하지 못했습니다.'; }
    finally { button.disabled = false; }
  });
  render();
  if (new URLSearchParams(window.location.search).get('section') === 'interests' || window.location.hash === '#interests') {
    document.querySelector('#interests').scrollIntoView();
    const link = document.querySelector('.settings-menu a[href="#interests"]');
    link?.click();
  }
})();

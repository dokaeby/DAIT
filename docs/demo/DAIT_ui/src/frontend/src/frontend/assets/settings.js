const form = document.querySelector('#settings-form');
const keywords = document.querySelector('#interest-keywords');
const preview = document.querySelector('#keyword-preview');
const feedback = document.querySelector('#settings-feedback');
const time = document.querySelector('#collection-time');
const enabled = document.querySelector('#schedule-enabled');

function updateKeywords() {
  const items = [...new Set(keywords.value.split(',').map(item => item.trim()).filter(Boolean))];
  keywords.setCustomValidity(items.length > 3 ? '관심 키워드는 최대 3개까지 입력할 수 있습니다.' : '');
  preview.replaceChildren();
  for (const item of items.slice(0, 3)) {
    const tag = document.createElement('span');
    tag.className = 'input-tag';
    tag.textContent = item;
    preview.append(tag);
  }
  preview.hidden = items.length === 0;
}

function updateSchedule() {
  const badge = document.querySelector('#schedule-state');
  badge.textContent = enabled.checked ? '사용 · 미리보기' : '사용 안 함 · 미리보기';
  badge.classList.toggle('ready', enabled.checked);
  badge.classList.toggle('pending', !enabled.checked);
  document.querySelector('#schedule-preview').textContent = enabled.checked
    ? `예약 예시: 매일 ${time.value || '--:--'} KST · 실제 예약은 등록되지 않았습니다.`
    : '예약 수집을 사용하지 않는 화면 예시입니다.';
}

keywords.addEventListener('input', updateKeywords);
time.addEventListener('input', updateSchedule);
enabled.addEventListener('change', updateSchedule);
form.addEventListener('input', () => { feedback.textContent = ''; });
form.addEventListener('change', () => { feedback.textContent = ''; });
form.addEventListener('submit', event => {
  event.preventDefault();
  feedback.textContent = '현재는 화면 확인 단계입니다. 설정은 저장되지 않았으며 실제 수집·추천·알림에도 적용되지 않습니다.';
});
form.addEventListener('reset', () => {
  // reset 이벤트 이후 브라우저가 초기값을 복원합니다.
  setTimeout(() => {
    updateKeywords();
    updateSchedule();
    feedback.textContent = '입력 내용을 이 화면을 열었을 때의 값으로 되돌렸습니다.';
  }, 0);
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
updateKeywords();
updateSchedule();

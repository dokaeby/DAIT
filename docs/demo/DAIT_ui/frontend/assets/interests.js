const form = document.querySelector('#interests-form');
const choices = [...form.querySelectorAll('input[name="categories"]')];
const feedback = document.querySelector('#interests-feedback');
const saveButton = document.querySelector('#interests-save');
const cancelLink = document.querySelector('#interests-cancel');
let saving = false;

function updateSelection() {
  document.querySelector('#interest-count').textContent = choices.filter(input => input.checked).length + '개 선택';
  form.querySelector('.interest-options').removeAttribute('aria-invalid');
  feedback.textContent = '';
  feedback.classList.remove('is-error');
}
choices.forEach(input => input.addEventListener('change', updateSelection));
document.querySelector('#interests-all').addEventListener('click', () => {
  choices.forEach(input => { input.checked = true; });
  updateSelection();
});
document.querySelector('#interests-clear').addEventListener('click', () => {
  choices.forEach(input => { input.checked = false; });
  updateSelection();
});
cancelLink?.addEventListener('click', event => { if (saving) event.preventDefault(); });
const skipButton = document.querySelector('#interests-skip');
skipButton?.addEventListener('click', async () => {
  if (saving) return;
  saving = true;
  const controls = [...form.querySelectorAll('input, button')];
  controls.forEach(control => { control.disabled = true; });
  form.setAttribute('aria-busy', 'true');
  form.querySelector('.interest-options').removeAttribute('aria-invalid');
  feedback.classList.remove('is-error');
  feedback.textContent = '선택을 기록하고 기본 뉴스로 이동합니다…';
  try {
    const response = await fetch('/api/interests/skip', {method: 'POST', headers: {'Accept': 'application/json'}});
    const data = await response.json();
    if (!response.ok) {
      if (response.status === 401) document.querySelector('#interests-login').hidden = false;
      throw new Error(data.error || '다음에 하기 선택을 저장하지 못했습니다.');
    }
    window.location.assign('/');
  } catch (error) {
    feedback.textContent = error.message || '선택을 기록하지 못했습니다. 다시 시도해주세요.';
    feedback.classList.add('is-error');
  } finally {
    saving = false;
    controls.forEach(control => { control.disabled = false; });
    form.removeAttribute('aria-busy');
  }
});

form.addEventListener('submit', async event => {
  event.preventDefault();
  if (saving) return;
  const selected = choices.filter(input => input.checked).map(input => input.value);
  if (!selected.length) {
    feedback.textContent = '관심 카테고리를 한 개 이상 선택해주세요.';
    feedback.classList.add('is-error');
    form.querySelector('.interest-options').setAttribute('aria-invalid', 'true');
    choices[0]?.focus();
    return;
  }
  saving = true;
  const controls = [...form.querySelectorAll('input, button')];
  controls.forEach(control => { control.disabled = true; });
  cancelLink?.setAttribute('aria-disabled', 'true');
  form.setAttribute('aria-busy', 'true');
  const originalText = saveButton.textContent;
  saveButton.textContent = '저장 중…';
  feedback.classList.remove('is-error');
  feedback.textContent = '관심 카테고리를 저장하고 있습니다…';
  try {
    const response = await fetch('/api/interests', {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({categories: selected})});
    const data = await response.json();
    if (!response.ok) {
      if (response.status === 401) document.querySelector('#interests-login').hidden = false;
      throw new Error(data.error || '관심 카테고리를 저장하지 못했습니다.');
    }
    feedback.textContent = data.message;
    window.location.assign('/');
  } catch (error) {
    feedback.textContent = error.message || '저장 결과를 확인하지 못했습니다. 연결을 확인하고 다시 시도해주세요.';
    feedback.classList.add('is-error');
  } finally {
    saving = false;
    controls.forEach(control => { control.disabled = false; });
    cancelLink?.removeAttribute('aria-disabled');
    form.removeAttribute('aria-busy');
    saveButton.textContent = originalText;
  }
});

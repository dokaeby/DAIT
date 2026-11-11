const button = document.querySelector('#standalone-copy');
button?.addEventListener('click', async () => {
  const status = document.querySelector('#copy-status');
  try {
    await navigator.clipboard.writeText(document.querySelector('#original-url').href);
    status.textContent = '원문 링크를 복사했습니다.';
  } catch {
    status.textContent = '복사하지 못했습니다. 원본 정보의 링크를 직접 복사해 주세요.';
  }
});

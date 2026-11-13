/* A second view of the same search, without resizing the article layout. */
(() => {
  const header = document.querySelector('.app-header');
  const mainForm = document.getElementById('search-form');
  const mainInput = document.getElementById('query');
  if (!header || !mainForm || !mainInput) return;
  const icon = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/></svg>';
  const host = document.createElement('div'); host.className = 'header-search';
  host.innerHTML = '<button class="header-search-open" type="button" aria-label="뉴스 검색 열기" aria-expanded="false" aria-controls="header-search-form">' + icon + '</button>' +
    '<form id="header-search-form" class="header-search-form" role="search" aria-label="상단 뉴스 검색"><label class="sr-only" for="header-query">뉴스 검색</label><input id="header-query" type="search" maxlength="100" placeholder="뉴스 검색" aria-controls="search-results"><button class="header-search-submit" type="submit" aria-label="검색">' + icon + '</button><button class="header-search-clear" type="button" aria-label="검색 초기화">초기화</button><button class="header-search-close" type="button" aria-label="검색창 닫기">닫기</button></form>';
  header.insertBefore(host, header.querySelector('.header-actions'));
  const input = host.querySelector('input'), form = host.querySelector('form');
  const open = host.querySelector('.header-search-open');
  function close() { host.classList.remove('is-open'); open.setAttribute('aria-expanded', 'false'); }
  open.addEventListener('click', () => { host.classList.add('is-open'); open.setAttribute('aria-expanded', 'true'); input.focus(); });
  host.querySelector('.header-search-close').addEventListener('click', () => { close(); open.focus(); });
  form.addEventListener('keydown', event => { if (event.key === 'Escape') { close(); open.focus(); } });
  input.addEventListener('input', () => { mainInput.value = input.value; mainInput.dispatchEvent(new Event('input', { bubbles: true })); });
  mainInput.addEventListener('input', () => { input.value = mainInput.value; });
  form.addEventListener('submit', event => { event.preventDefault(); mainInput.value = input.value; mainForm.requestSubmit(); });
  host.querySelector('.header-search-clear').addEventListener('click', () => { document.querySelector('.clear-search').click(); input.value = mainInput.value; input.focus(); });
  let pending = false;
  function update() {
    pending = false;
    const rect = header.getBoundingClientRect();
    const visible = mainForm.getBoundingClientRect().bottom <= rect.bottom;
    if (!visible && host.contains(document.activeElement)) mainInput.focus({ preventScroll: true });
    host.hidden = !visible;
    header.classList.toggle('has-search', visible);
    if (!visible) close();
    input.value = mainInput.value;
    document.documentElement.style.setProperty('--app-header-height', Math.ceil(rect.height) + 'px');
    document.documentElement.style.setProperty('--section-offset', (Math.ceil(rect.height) + 24) + 'px');
  }
  function queue() { if (!pending) { pending = true; requestAnimationFrame(update); } }
  window.addEventListener('scroll', queue, { passive: true });
  window.addEventListener('resize', queue);
  window.addEventListener('pageshow', queue);
  new ResizeObserver(queue).observe(header);
  // Chips and sidebar navigation can clear the query without an input event.
  window.addEventListener('dait-search-sync', () => { input.value = mainInput.value; });
  update();
})();

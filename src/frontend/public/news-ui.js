/* v1.0.2 presentation connected to the integrated /v1/news contract. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const names = { AI: 'AI•인공지능', ECONOMY: '경제·비즈니스', POLITICS: '사회·문화' };
  const topics = {
    AI: ['모델·연구', 'AI 에이전트', '개발 도구', '오픈소스·로컬 모델', 'AI 인프라'],
    ECONOMY: ['산업 동향', '기업·경영', '스타트업·투자', '금융시장', '일자리'],
    POLITICS: ['정책·제도', '교육', '건강·의료', '환경·기후', '문화·콘텐츠'],
  };
  const labels = { READY: '✓ 요약 준비 완료', INSUFFICIENT: '△ 정보 부족', FAILED: '! 생성 실패', PENDING: '○ 요약 준비 중' };
  const params = new URLSearchParams(location.search);
  let category = Object.hasOwn(names, params.get('category')) ? params.get('category') : '';
  const expandedGroups = new Set();
  let cursor = null;
  let pageCursor = null, pageStack = [], busy = false;
  let shownCategory = '', shownQuery = '', shownHasResults = false;
  const readIds = new Set();
  function refreshReads() {
    document.querySelectorAll('[data-article-id]').forEach(el => {
      const read = readIds.has(el.dataset.articleId);
      el.classList.toggle('is-read', read);
      let badge = el.querySelector('.read-badge');
      if (read && !badge) { badge = document.createElement('span'); badge.className = 'read-badge'; badge.textContent = '읽음'; el.querySelector('.news-meta').append(badge); }
    });
  }
  async function markRead(id) {
    if (guest) {
      readIds.add(id);
      try { localStorage.setItem('dait_guest_reads', JSON.stringify([...readIds].slice(-2000))); } catch {}
      refreshReads(); return;
    }
    try {
      const res = await DAIT.api('/v1/news/' + encodeURIComponent(id) + '/read', { method: 'PUT' });
      if (!res.ok) throw new Error();
      readIds.add(id); refreshReads();
    } catch { $('search-status').textContent = '읽음 기록을 저장하지 못했습니다. 기사를 다시 열면 재시도합니다.'; }
  }
  let listRequest;
  let detailRequest;
  let originalUrl = '';
  let guest = true;
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  function safeUrl(raw) {
    try { const url = new URL(raw); return url.protocol === 'https:' ? url.href : ''; } catch { return ''; }
  }
  function date(raw) {
    const value = new Date(raw);
    return Number.isNaN(value.getTime()) ? '' : value.toLocaleString('ko-KR');
  }
  function summary(lines, status) {
    return lines?.length ? `<ul class="summary-list">${lines.map(line => `<li>${escape(line)}</li>`).join('')}</ul>` : `<p class="empty-summary">${escape(status === 'INSUFFICIENT' ? '요약을 작성하기에 기사 정보가 부족합니다.' : labels[status] || '저장된 요약이 없습니다.')}</p>`;
  }
  async function json(url, signal) {
    const res = await DAIT.api(url, { signal, headers: { Accept: 'application/json' } });
    if (!res.ok) throw new Error(res.status === 404 ? '기사를 찾을 수 없습니다.' : '뉴스를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.');
    return res.json();
  }
  function card(item) {
    const id = escape(item.id);
    const url = safeUrl(item.original_url);
    return `<li class="article news-card" data-article-id="${id}"><div class="rank" aria-label="목록 ${escape(item.rank)}번째">${escape(item.rank)}</div><div class="news-main"><p class="category-tag ai">${escape(names[item.category] || item.category)}</p><h2 class="news-title"><button type="button" data-detail="${id}">${escape(item.title)}</button></h2><div class="news-meta"><span>${escape(item.source_name)}</span><span class="meta-dot"></span><time>${escape(date(item.published_at))}</time></div></div><div class="summary-box"><p class="summary-title">✦ AI 3줄 요약</p>${summary(item.summary_lines, item.processing_status)}</div><div class="card-actions"><span class="status-tag ${item.processing_status === 'READY' ? 'ready' : 'partial'}">${escape(labels[item.processing_status] || '상태 확인 중')}</span><button class="primary-button" type="button" data-detail="${id}">상세 보기</button>${url ? `<a class="secondary-button" href="${escape(url)}" target="_blank" rel="noopener noreferrer">원문 열기 ↗</a>` : ''}</div></li>`;
  }
  function syncSidebar() {
    const query = $('query').value.trim();
    document.querySelectorAll('[data-topic-group]').forEach(button => {
      const active = button.dataset.topicGroup === category;
      button.classList.toggle('active', active);
      button.parentElement.classList.toggle('is-active', active);
    });
    document.querySelectorAll('[data-topic-toggle]').forEach(button => {
      const expanded = expandedGroups.has(button.dataset.topicToggle);
      button.setAttribute('aria-expanded', String(expanded));
      $(button.getAttribute('aria-controls')).hidden = !expanded;
    });
    document.querySelectorAll('[data-topic]').forEach(button => {
      const active = button.dataset.topicCategory === category && button.dataset.topic === query;
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', String(active));
    });
    $('topic-select').value = topics[category]?.includes(query) ? category + ':' + query : '';
  }
  function buildSidebar() {
    for (const [code, values] of Object.entries(topics)) {
      const group = document.createElement('div'); group.className = 'topic-group';
      const button = document.createElement('button'); button.type = 'button'; button.className = 'nav-item topic-heading';
      button.dataset.topicGroup = code; button.textContent = '✦ ' + names[code];
      const row = document.createElement('div'); row.className = 'topic-heading-row';
      const toggle = document.createElement('button'); toggle.type = 'button'; toggle.className = 'topic-toggle';
      toggle.dataset.topicToggle = code;
      toggle.setAttribute('aria-controls', 'topics-' + code);
      toggle.setAttribute('aria-expanded', 'false');
      toggle.setAttribute('aria-label', names[code] + ' 소주제 펼치기/접기');
      toggle.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>';
      row.append(button, toggle);
      const list = document.createElement('ul'); list.id = 'topics-' + code; list.className = 'topic-list';
      list.hidden = true;
      const options = document.createElement('optgroup'); options.label = names[code];
      for (const topic of values) {
        const li = document.createElement('li');
        const child = document.createElement('button'); child.type = 'button'; child.className = 'topic-button';
        child.dataset.topic = topic; child.dataset.topicCategory = code; child.textContent = topic;
        li.append(child); list.append(li);
        const option = document.createElement('option'); option.value = code + ':' + topic; option.textContent = topic; options.append(option);
      }
      group.append(row, list); $('sidebar-categories').append(group); $('topic-select').append(options);
    }
    $('sidebar-categories').addEventListener('click', event => {
      const toggle = event.target.closest('[data-topic-toggle]');
      if (toggle) {
        const code = toggle.dataset.topicToggle;
        if (expandedGroups.has(code)) expandedGroups.delete(code);
        else expandedGroups.add(code);
        syncSidebar();
        return;
      }
      const topic = event.target.closest('[data-topic]');
      if (topic) { category = topic.dataset.topicCategory; $('query').value = topic.dataset.topic; load(); return; }
      const group = event.target.closest('[data-topic-group]');
      if (!group) return;
      category = group.dataset.topicGroup;
      $('query').value = '';
      load();
    });
    $('topic-select').addEventListener('change', () => {
      const value = $('topic-select').value;
      if (value) { const split = value.indexOf(':'); category = value.slice(0, split); $('query').value = value.slice(split + 1); }
      else $('query').value = '';
      load();
    });
  }
  async function load(direction = '', retainSearch = false) {
    if (direction && (guest || busy)) return;
    if (direction) { category = shownCategory; $('query').value = shownQuery; }
    if (guest) { category = ''; $('query').value = ''; }
    syncSidebar();
    listRequest?.abort();
    const request = listRequest = new AbortController();
    const target = direction === 'next' ? cursor : direction === 'prev' ? pageStack.at(-1) : null;
    if (direction === 'next' && !target) return;
    if (direction === 'prev' && !pageStack.length) return;
    busy = true;
    $('search-results').setAttribute('aria-busy', 'true');
    $('load-more').disabled = true; $('load-previous').disabled = true;
    $('search-status').textContent = '뉴스를 불러오고 있습니다…';
    const query = new URLSearchParams({ sort: 'latest', page_size: '10' });
    if (category) query.set('category', category);
    const keyword = retainSearch && shownHasResults && !$('query').value.trim() ? shownQuery : $('query').value.trim();
    if (keyword) query.set('q', keyword);
    if (target) query.set('cursor', target);
    try {
      const data = await json('/v1/news?' + query, request.signal);
      const items = guest ? data.items.slice(0, 10) : data.items;
      let activity;
      if (!guest) {
        const aq = new URLSearchParams({ q: query.get('q') || '' });
        items.forEach(item => aq.append('ids', item.id));
        activity = await json('/v1/news/activity?' + aq, request.signal);
      }
      if (request !== listRequest) return;
      if (direction === 'next') pageStack.push(pageCursor);
      else if (direction === 'prev') pageStack.pop();
      else pageStack = [];
      pageCursor = target;
      shownCategory = query.get('category') || ''; shownQuery = query.get('q') || ''; shownHasResults = items.length > 0;
      history.replaceState(null, '', '/?' + query);
      $('news-list').innerHTML = items.map(card).join('');
      $('result-count').textContent = guest ? '최신 뉴스 ' + items.length + '건' : '전체 기사';
      document.querySelectorAll('[data-category]').forEach(el => {
        const code = el.dataset.category;
        el.classList.toggle('active', code === category);
        el.setAttribute('aria-pressed', String(code === category));
        if (activity) el.textContent = (names[code] || '전체') + '(' + (code ? activity.counts[code] || 0 : activity.total) + ')';
      });
      if (activity) { readIds.clear(); activity.read_ids.forEach(id => readIds.add(id)); }
      refreshReads();
      $('search-status').textContent = data.meta.message || '';
      if (!items.length) $('news-list').innerHTML = '<li class="empty-result"><strong>표시할 뉴스가 없습니다</strong><p>다른 검색어나 카테고리를 선택해 주세요.</p></li>';
      cursor = data.page.has_more ? data.page.next_cursor : null;
      $('pagination').hidden = guest || !items.length;
      $('load-more').hidden = guest; $('load-previous').hidden = guest;
      $('page-number').textContent = (pageStack.length + 1) + ' / ' + Math.max(pageStack.length + 1, Math.ceil((activity ? (shownCategory ? activity.counts[shownCategory] || 0 : activity.total) : data.meta.total_visible) / 10)) + ' 페이지';
      updateScrollControls();
      if (direction) window.scrollTo({ top: 0, behavior: 'instant' });
    } catch (error) {
      if (error.name === 'AbortError') return;
      $('search-status').textContent = error.message;
      const retry = document.createElement('button');
      retry.type = 'button'; retry.className = 'secondary-button'; retry.textContent = '다시 시도';
      retry.addEventListener('click', () => load(direction));
      if ($('news-list').children.length) $('search-status').append(' ', retry);
      if (!$('news-list').children.length) $('news-list').innerHTML = '<li class="empty-result"><strong>뉴스를 불러올 수 없습니다</strong><br><button type="button" class="secondary-button" id="retry-news">다시 시도</button></li>';
    } finally {
      if (request === listRequest) {
        busy = false; $('load-more').disabled = !cursor; $('load-previous').disabled = !pageStack.length;
        $('search-results').setAttribute('aria-busy', 'false');
      }
    }
  }
  async function openDetail(id) {
    detailRequest?.abort();
    const request = detailRequest = new AbortController();
    originalUrl = '';
    $('detail-copy').disabled = true;
    $('detail-original').hidden = true;
    $('detail-original').removeAttribute('href');
    $('detail-title').textContent = '기사 불러오는 중';
    $('detail-meta').textContent = '';
    $('detail-category').textContent = '';
    $('detail-summary').replaceChildren();
    $('detail-text').textContent = '';
    $('detail-translation').hidden = true;
    $('detail-feedback').textContent = '';
    $('detail-copy-status').textContent = '';
    $('detail-sources').hidden = true;
    $('detail-source-name').textContent = '';
    $('detail-source-url').textContent = '';
    $('detail-source-url').removeAttribute('href');
    if (!$('detail').open) $('detail').showModal();
    updateScrollControls();
    try {
      const data = await json('/v1/news/' + encodeURIComponent(id), request.signal);
      if (request !== detailRequest || !$('detail').open) return;
      markRead(id);
      $('detail-title').textContent = data.article.title;
      $('detail-category').textContent = names[data.article.category] || data.article.category;
      $('detail-meta').textContent = `${data.article.source_name} · ${date(data.article.published_at)}`;
      $('detail-summary').innerHTML = summary(data.content.summary_lines, data.content.content_status);
      document.querySelector('#detail-summary ul')?.classList.add('key-points');
      document.querySelectorAll('#detail-summary li').forEach(line => {
        const text = document.createElement('span');
        text.textContent = line.textContent;
        line.replaceChildren(text);
      });
      $('detail-text').textContent = data.content.translated_text || '저장된 번역 본문이 없습니다. 원문에서 확인해 주세요.';
      $('detail-translation').hidden = !(data.article.translation_required ?? (data.article.original_language && !['ko', 'und'].includes(data.article.original_language)));
      $('detail-feedback').textContent = labels[data.content.content_status] || '';
      originalUrl = safeUrl(data.source.original_url);
      if (originalUrl) {
        $('detail-original').href = originalUrl; $('detail-original').hidden = false; $('detail-copy').disabled = false;
        $('detail-source-name').textContent = data.article.source_name;
        $('detail-source-url').href = originalUrl;
        $('detail-source-url').textContent = originalUrl;
        $('detail-sources').hidden = false;
      }
    } catch (error) {
      if (error.name !== 'AbortError') { $('detail-title').textContent = '기사를 불러올 수 없습니다'; $('detail-feedback').textContent = error.message; }
    }
  }
  $('query').value = (params.get('q') || '').slice(0, 100);
  $('query').addEventListener('input', () => {
    if ($('query').value.trim()) return;
    if (shownHasResults) {
      listRequest?.abort(); busy = false;
      $('search-status').textContent = '';
      $('search-results').setAttribute('aria-busy', 'false');
      $('load-more').disabled = !cursor; $('load-previous').disabled = !pageStack.length;
    } else if (shownQuery || busy) { category = ''; $('query').value = ''; load(); }
  });
  $('search-form').addEventListener('submit', event => { event.preventDefault(); load(); });
  $('categories').addEventListener('click', event => { const el = event.target.closest('[data-category]'); if (el) { category = el.dataset.category; load('', true); } });
  $('load-more').addEventListener('click', () => load('next'));
  $('load-previous').addEventListener('click', () => load('prev'));
  $('news-list').addEventListener('click', event => {
    const el = event.target.closest('[data-detail]');
    if (el) openDetail(el.dataset.detail);
    const original = event.target.closest('a[target=_blank]');
    if (original) markRead(original.closest('[data-article-id]').dataset.articleId);
    if (event.target.closest('#retry-news')) load();
  });
  $('detail-close').addEventListener('click', () => $('detail').close());
  $('detail').addEventListener('close', () => { detailRequest?.abort(); originalUrl = ''; updateScrollControls(); });
  $('detail-copy').addEventListener('click', async () => {
    const url = originalUrl;
    if (!url) return;
    try { await navigator.clipboard.writeText(url); if (url === originalUrl) $('detail-copy-status').textContent = '원문 링크를 복사했습니다.'; }
    catch { if (url === originalUrl) $('detail-copy-status').textContent = '복사하지 못했습니다. 원문 링크를 이용해 주세요.'; }
  });
  let scrollAnchor = 0;
  function updateScrollControls() {
    const controls = $('scroll-controls');
    const card = document.querySelector('.news-card');
    controls.hidden = !card || !!document.querySelector('dialog[open]');
    if (!card) return;
    if (window.scrollY < 2 || !scrollAnchor) scrollAnchor = card.getBoundingClientRect().top + window.scrollY;
    const shell = document.querySelector('.app-shell').getBoundingClientRect();
    controls.style.setProperty('--scroll-top', Math.min(Math.max(100, scrollAnchor), innerHeight - 150) + 'px');
    controls.style.setProperty('--scroll-right', Math.max(8, document.documentElement.clientWidth - shell.right - 88) + 'px');
    $('scroll-up').disabled = window.scrollY <= 2;
    $('scroll-down').disabled = window.scrollY + innerHeight >= document.documentElement.scrollHeight - 2;
  }
  $('scroll-up').addEventListener('click', () => window.scrollTo({ top: 0, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' }));
  $('scroll-down').addEventListener('click', () => window.scrollTo({ top: document.documentElement.scrollHeight, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' }));
  window.addEventListener('scroll', updateScrollControls, { passive: true });
  window.addEventListener('resize', () => { scrollAnchor = 0; updateScrollControls(); });
  new MutationObserver(updateScrollControls).observe(document.body, { subtree: true, attributes: true, attributeFilter: ['open'] });
  buildSidebar();
  DAIT.currentUser().then(user => {
    guest = !user;
    if (guest) { try { const ids = JSON.parse(localStorage.getItem('dait_guest_reads') || '[]'); if (Array.isArray(ids)) ids.filter(id => typeof id === 'string').slice(-2000).forEach(id => readIds.add(id)); } catch {} }
    document.querySelectorAll('[data-member-only]').forEach(el => { el.hidden = guest; });
    document.querySelector('.page-title').textContent = user?.nickname ? `${user.nickname}님의 AI 뉴스` : '오늘의 AI 뉴스';
    load();
  });
})();

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
  let globalSearch = params.get('search_scope') === 'all';
  let searchAllArticles = ['all', 'filtered'].includes(params.get('search_scope'));
  let category = Object.hasOwn(names, params.get('category')) ? params.get('category') : '';
  const expandedGroups = new Set();
  let cursor = null;
  let busy = false;
  const PAGE_SIZE = '4';
  let pageStart = null, pageHistory = [], currentPage = 1;
  let language = params.get('language') === 'en' ? 'en' : 'ko', sidebarTopic = params.get('topic') || '';
  const responseCache = new Map();
  let shownCategory = '', shownQuery = '', shownHasResults = false;
  const readIds = new Set();
  let personalizedChips = false;
  let selectedInterest = params.get('interest') || '';
  let savedInterests = [];
  const englishNames = { AI: 'AI & Technology', ECONOMY: 'Economy & Business', POLITICS: 'Society & Culture' };
  const topicCodes = {AI: ['models','agents','devtools','opensource','infra'], ECONOMY: ['industry','business','startups','markets','jobs'], POLITICS: ['policy','education','health','climate','culture']};
  const groupCodes = {AI:'ai', ECONOMY:'economy', POLITICS:'society'};
  function configureInterestChips(user) {
    const host = $('categories');
    host.replaceChildren();
    savedInterests = user?.interests || [];
    personalizedChips = savedInterests.length > 0;
    $('interest-count-note').hidden = !personalizedChips;
    if (!savedInterests.some(item => item.code === selectedInterest)) selectedInterest = '';
    if (selectedInterest) language = selectedInterest.startsWith('en.') ? 'en' : 'ko';
    for (const region of ['ko', 'en']) {
      const row = document.createElement('div'); row.className = 'region-chip-row'; row.dataset.region = region;
      const label = document.createElement('strong'); label.className = 'region-chip-label'; label.textContent = region === 'ko' ? '국내' : '해외';
      const chips = document.createElement('div'); chips.className = 'region-chips';
      const make = (name, code, interest) => {
        const button = document.createElement('button'); button.type = 'button'; button.className = 'chip'; button.dataset.chipLanguage = region; button.dataset.chipLabel = name;
        if (interest) { button.dataset.interestChip = code; button.dataset.interestQuery = name; }
        else button.dataset.category = code;
        button.textContent = name + '(…)'; chips.append(button); return button;
      };
      make(region === 'ko' ? '전체' : 'All', '', false);
      if (personalizedChips) {
        const interests = savedInterests.filter(item => item.code.startsWith('en.') === (region === 'en'));
        interests.forEach((item, index) => { make(item.name, item.code, true).hidden = index >= 5; });
        if (interests.length > 5) {
          const toggle = document.createElement('button'); toggle.type = 'button'; toggle.className = 'chip interest-toggle'; toggle.dataset.interestExpand = region;
          chips.id = 'interest-chips-' + region;
          toggle.setAttribute('aria-controls', chips.id); toggle.setAttribute('aria-label', (region === 'ko' ? '국내' : '해외') + ' 관심사 펼치기');
          toggle.setAttribute('aria-expanded','false'); toggle.textContent = '더 보기 (' + (interests.length - 5) + ')'; row.append(toggle);
        }
        if (!interests.length) {
          const note = document.createElement('span'); note.className = 'region-empty'; note.textContent = '선택한 관심사가 없습니다'; chips.append(note);
        }
      } else {
        for (const code of Object.keys(names)) make((region === 'ko' ? names : englishNames)[code], code, false);
      }
      row.prepend(label, chips); host.append(row);
    }
  }
  function selectionTitle() {
    if (globalSearch) return '국내·해외 · 전체 검색';
    const prefix = language === 'en' ? '해외' : '국내';
    let name = (language === 'en' ? englishNames : names)[category] || '전체';
    const code = selectedInterest || sidebarTopic;
    if (code) {
      const saved = savedInterests.find(item => item.code === code);
      if (saved) name = saved.name;
      else {
        const base = code.replace(/^en\./, '').split('.');
        const cat = Object.keys(groupCodes).find(key => groupCodes[key] === base[0]);
        const index = cat ? topicCodes[cat].indexOf(base[1]) : -1;
        if (index >= 0) {
          const englishButton = document.querySelector('[data-english-topic="' + base.join('.') + '"]');
          name = language === 'en' && englishButton ? englishButton.textContent : topics[cat][index];
        }
      }
    }
    return prefix + ' · ' + name;
  }
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
    const canonical = new URL(url, location.origin);
    canonical.searchParams.sort();
    const cacheKey = canonical.pathname + canonical.search;
    const cached = responseCache.get(cacheKey);
    const ttl = canonical.pathname === '/v1/news/activity' ? 15000 : 60000;
    if (cached && Date.now() - cached.time < ttl) return cached.value;
    const res = await DAIT.api(url, { signal, headers: { Accept: 'application/json' } });
    if (!res.ok) throw new Error(res.status === 404 ? '기사를 찾을 수 없습니다.' : '뉴스를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.');
    const value = await res.json();
    if (url.startsWith('/v1/news?') || url.startsWith('/v1/news/activity?')) {
      if (responseCache.size > 100) responseCache.clear();
      responseCache.set(cacheKey, {time: Date.now(), value});
    }
    return value;
  }
  function card(item) {
    const id = escape(item.id);
    const url = safeUrl(item.original_url);
    return `<li class="article news-card" data-article-id="${id}"><div class="rank" aria-label="목록 ${escape(item.rank)}번째">${escape(item.rank)}</div><div class="news-main"><p class="article-tags"><span class="category-tag ai">${escape(names[item.category] || item.category)}</span><span class="origin-tag">${item.original_language === 'ko' ? '국내' : item.original_language && item.original_language !== 'und' ? '해외' : '구분 미확인'}</span></p><h2 class="news-title"><a href="${escape(url)}" target="_blank" rel="noopener noreferrer">${escape(item.title)}</a></h2><div class="news-meta"><span>${escape(item.source_name)}</span>${item.author_name ? `<span> · ${escape(item.author_name)}</span>` : ''}<span class="meta-dot"></span><time>${escape(date(item.published_at))}</time></div></div><div class="summary-box"><p class="summary-title">✦ AI 3줄 요약</p>${summary(item.summary_lines, item.processing_status)}</div><div class="card-actions">${item.processing_status === 'READY' ? '' : `<span class="status-tag partial">${escape(labels[item.processing_status] || '상태 확인 중')}</span>`}${url ? `<a class="secondary-button" href="${escape(url)}" target="_blank" rel="noopener noreferrer">원문 열기 ↗</a>` : ''}<button type="button" class="secondary-button" data-copy-url="${escape(url)}">링크 복사</button></div></li>`;
  }
  function syncSidebar() {
    const query = $('query').value.trim();
    document.querySelectorAll('[data-topic-group]').forEach(button => {
      const active = language !== 'en' && !selectedInterest.startsWith('en.') && button.dataset.topicGroup === category;
      button.classList.toggle('active', active);
      button.parentElement.classList.toggle('is-active', active);
    });
    document.querySelectorAll('[data-topic-toggle]').forEach(button => {
      const expanded = expandedGroups.has(button.dataset.topicToggle);
      button.setAttribute('aria-expanded', String(expanded));
      $(button.getAttribute('aria-controls')).hidden = !expanded;
    });
    document.querySelectorAll('[data-topic]').forEach(button => {
      const code = groupCodes[button.dataset.topicCategory] + '.' + topicCodes[button.dataset.topicCategory][topics[button.dataset.topicCategory].indexOf(button.dataset.topic)];
      const active = language === 'ko' && (sidebarTopic || selectedInterest) === code;
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', String(active));
    });
    const englishTopic = selectedInterest.startsWith('en.') ? selectedInterest.slice(3) : sidebarTopic;
    const englishCategory = selectedInterest.startsWith('en.') ? ({ai:'AI', economy:'ECONOMY', society:'POLITICS'}[englishTopic.split('.')[0]]) : category;
    const englishSelected = language === 'en' || selectedInterest.startsWith('en.');
    document.querySelectorAll('[data-english-group]').forEach(button => {
      const active = englishSelected && button.dataset.englishGroup === englishCategory;
      button.classList.toggle('active', active);
      button.parentElement.classList.toggle('is-active', active);
      button.setAttribute('aria-pressed', String(active));
    });
    document.querySelectorAll('[data-english-topic]').forEach(button => {
      const active = englishSelected && button.dataset.englishTopic === englishTopic;
      button.classList.toggle('active', active); button.setAttribute('aria-pressed', String(active));
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
      if (topic) { globalSearch = false; searchAllArticles = false; language = 'ko'; selectedInterest = ''; category = topic.dataset.topicCategory; sidebarTopic = groupCodes[category] + '.' + topicCodes[category][topics[category].indexOf(topic.dataset.topic)]; $('query').value = ''; load(); return; }
      const group = event.target.closest('[data-topic-group]');
      if (!group) return;
      globalSearch = false; searchAllArticles = false; language = 'ko'; sidebarTopic = ''; selectedInterest = '';
      category = group.dataset.topicGroup;
      $('query').value = '';
      load();
    });
    $('topic-select').addEventListener('change', () => {
      const value = $('topic-select').value;
      language = 'ko'; selectedInterest = ''; sidebarTopic = '';
      if (value) { const split = value.indexOf(':'); category = value.slice(0, split); const name = value.slice(split + 1); sidebarTopic = groupCodes[category] + '.' + topicCodes[category][topics[category].indexOf(name)]; $('query').value = ''; }
      else $('query').value = '';
      load();
    });
  }
  function updateChips(activities) {
      document.querySelectorAll('[data-chip-language]').forEach(el => {
        const region = el.dataset.chipLanguage, activity = activities[region];
        const interest = el.dataset.interestChip;
        const code = el.dataset.category || '';
        const selectedTopic = selectedInterest || (sidebarTopic ? (language === 'en' ? 'en.' + sidebarTopic.replace(/^en\./,'') : sidebarTopic) : '');
        const active = !globalSearch && language === region && (interest ? interest === selectedTopic : !selectedTopic && code === category);
        el.classList.toggle('active', active); el.setAttribute('aria-pressed', String(active));
        if (activity) el.textContent = el.dataset.chipLabel + '(' + (interest ? activity.interest_counts?.[interest] || 0 : code ? activity.counts[code] || 0 : activity.total) + ')';
      });

  }
  async function load(direction = '', retainSearch = false) {
    if (direction && (guest || busy)) return;
    const target = direction === 'next' ? cursor : direction === 'prev' ? pageHistory.at(-1) : null;
    if (direction === 'next' && !target || direction === 'prev' && !pageHistory.length) return;
    if (direction) { category = shownCategory; $('query').value = shownQuery; }
    window.dispatchEvent(new Event('dait-search-sync'));
    if (guest) category = '';
    syncSidebar();
    updateChips({});
    listRequest?.abort();
    const request = listRequest = new AbortController();
    busy = true;
    $('search-results').setAttribute('aria-busy', 'true');
    $('load-more').disabled = true; $('load-previous').disabled = true;
    const query = new URLSearchParams({sort: 'latest', page_size: guest ? '10' : PAGE_SIZE});
    if (category) query.set('category', category);
    if (searchAllArticles) query.set('search_scope', globalSearch ? 'all' : 'filtered');
    if (!globalSearch && language) query.set('language', language);
    if (searchAllArticles && selectedInterest) query.set('topic', selectedInterest);
    if (sidebarTopic) query.set('topic', sidebarTopic);
    if (personalizedChips && !guest && !sidebarTopic && !searchAllArticles) {
      query.set('personalized', 'true');
      if (selectedInterest) query.set('interest', selectedInterest);
    }
    const keyword = retainSearch && shownHasResults && !$('query').value.trim() ? shownQuery : $('query').value.trim();
    if (keyword) query.set('q', keyword);
    if (target) query.set('cursor', target);
    $('search-status').textContent = '뉴스를 불러오고 있습니다…';
    const countsPromise = guest ? Promise.resolve({}) : Promise.all(['ko','en'].map(async region => {
      const aq = new URLSearchParams({q: keyword, language: region});
      if (personalizedChips && !searchAllArticles) aq.set('personalized', 'true');
      return [region, await json('/v1/news/activity?' + aq, request.signal)];
    })).then(entries => Object.fromEntries(entries));
    countsPromise.then(activities => {
      if (request === listRequest) updateChips(activities);
    }).catch(error => {
      if (request === listRequest && error.name !== 'AbortError') $('search-status').textContent = '기사 수를 갱신하지 못했습니다.';
    });
    try {
      let data = await json('/v1/news?' + query, request.signal);
      if (request !== listRequest) return;
      let items = data.items;
      $('news-list').innerHTML = items.map(card).join('');
      refreshReads();
      if (!guest && data.page.has_more) {
        $('news-list').innerHTML = items.map(card).join('');
        const next = new URLSearchParams(query);
        next.set('cursor', data.page.next_cursor);
        const second = await json('/v1/news?' + next, request.signal);
        if (request !== listRequest) return;
        items = [...items, ...second.items];
        data = {...data, page: second.page};
      }
      if (request !== listRequest) return;
      if (direction === 'next') { pageHistory.push(pageStart); currentPage++; }
      else if (direction === 'prev') { pageHistory.pop(); currentPage--; }
      else { pageHistory = []; currentPage = 1; }
      pageStart = target;
      shownCategory = category; shownQuery = keyword; shownHasResults = items.length > 0;
      history.replaceState(null, '', '/?' + query);
      $('news-list').innerHTML = items.map(card).join('');
      $('result-count').textContent = guest ? '최신 뉴스 ' + items.length + '건' : selectionTitle() + ' · ' + data.meta.total_visible + '건';


      $('search-status').textContent = data.meta.message || '';
      if (!items.length) $('news-list').innerHTML = '<li class="empty-result"><strong>' + escape(guest ? '표시할 뉴스가 없습니다' : selectionTitle() + '에 해당하는 기사가 없습니다') + '</strong></li>';
      cursor = data.page.has_more ? data.page.next_cursor : null;
      $('pagination').hidden = guest || !items.length;
      $('load-more').hidden = guest; $('load-previous').hidden = guest;
      $('page-number').textContent = currentPage + ' / ' + Math.max(1, Math.ceil(data.meta.total_visible / 8)) + ' 페이지';
      if (direction) window.scrollTo({top: 0, behavior: 'instant'});
      refreshReads();
      if (!guest && items.length) {
        const reads = new URLSearchParams();
        items.forEach(item => reads.append('ids', item.id));
        json('/v1/news/read-state?' + reads, request.signal).then(ids => {
          if (request !== listRequest) return;
          ids.forEach(id => readIds.add(id)); refreshReads();
        }).catch(() => {});
      }
      updateScrollControls();
    } catch (error) {
      if (error.name !== 'AbortError') $('search-status').textContent = error.message;
    } finally {
      if (request === listRequest) {
        busy = false; $('load-more').disabled = !cursor;
        $('load-previous').disabled = !pageHistory.length;
        $('search-results').setAttribute('aria-busy', 'false');
      }
    }
  }
  $('query').value = (params.get('q') || '').slice(0, 100);
  $('query').addEventListener('input', () => {
    if ($('query').value.trim()) return;
    if (shownHasResults) {
      listRequest?.abort(); busy = false;
      document.querySelectorAll('#news-list .news-skeleton').forEach(el => el.remove());
      $('search-status').textContent = '';
      $('search-results').setAttribute('aria-busy', 'false');
      $('load-more').disabled = !cursor;
    } else if (shownQuery || busy) { globalSearch = false; searchAllArticles = false; language = 'ko'; selectedInterest = ''; sidebarTopic = ''; category = ''; $('query').value = ''; load(); }
  });
  $('search-form').addEventListener('submit', event => {
    event.preventDefault();
    globalSearch = !!$('query').value.trim();
    searchAllArticles = globalSearch;
    language = globalSearch ? '' : 'ko';
    category = ''; selectedInterest = ''; sidebarTopic = '';
    load();
  });
  document.querySelector('.clear-search').addEventListener('click', event => {
    event.preventDefault();
    $('query').value = '';
    category = '';
    globalSearch = false; searchAllArticles = false; selectedInterest = ''; language = 'ko'; sidebarTopic = '';
    load();
  });
  $('categories').addEventListener('click', event => {
    const toggle = event.target.closest('[data-interest-expand]');
    if (toggle) {
      const expanded = toggle.getAttribute('aria-expanded') !== 'true';
      toggle.setAttribute('aria-expanded', String(expanded));
      const buttons = [...toggle.closest('.region-chip-row').querySelectorAll('[data-interest-chip]')];
      buttons.forEach((el,index) => { el.hidden = index >= 5 && !expanded; });
      toggle.textContent = expanded ? '접기' : '더 보기 (' + (buttons.length - 5) + ')';
      toggle.setAttribute('aria-label', (toggle.dataset.interestExpand === 'ko' ? '국내' : '해외') + ' 관심사 ' + (expanded ? '접기' : '펼치기'));
      return;
    }
    const el = event.target.closest('[data-chip-language]');
    if (!el) return;
    globalSearch = false; language = el.dataset.chipLanguage; sidebarTopic = '';
    selectedInterest = el.dataset.interestChip || '';
    category = el.dataset.category || '';
    load('', true);
  });
  $('load-more').addEventListener('click', () => load('next'));
  $('load-previous').addEventListener('click', () => load('prev'));
  $('news-list').addEventListener('click', event => {
    const el = event.target.closest('[data-detail]');
    if (el) return;
    const copy = event.target.closest('[data-copy-url]');
    if (copy) {
      const url = safeUrl(copy.dataset.copyUrl);
      if (!url) return;
      navigator.clipboard.writeText(url).then(() => {
        copy.textContent = '복사 완료';
        setTimeout(() => { copy.textContent = '링크 복사'; }, 1500);
      }).catch(() => { $('search-status').textContent = '링크를 복사하지 못했습니다.'; });
    }
    const original = event.target.closest('a[target=_blank]');
    if (original) markRead(original.closest('[data-article-id]').dataset.articleId);
    if (event.target.closest('#retry-news')) load();
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

  function buildEnglishSidebar() {
    const groups = [
      ['AI', 'AI & Technology', 'ai', [['models','Models & Research'],['agents','AI Agents'],['devtools','Developer Tools'],['opensource','Open Source & Local Models'],['infra','AI Infrastructure']]],
      ['ECONOMY', 'Economy & Business', 'economy', [['industry','Industry Trends'],['business','Corporate & Management'],['startups','Startups & Ventures'],['markets','Finance & Markets'],['jobs','Jobs & Employment']]],
      ['POLITICS', 'Society & Culture', 'society', [['policy','Policy & Administration'],['education','Education'],['health','Health & Medicine'],['climate','Environment & Climate'],['culture','Culture & Content']]]
    ];
    const host = $('sidebar-categories');
    const label = document.createElement('span'); label.className = 'nav-label'; label.textContent = 'English News'; host.append(label);
    for (const [categoryCode, name, prefix, values] of groups) {
      const group = document.createElement('div'); group.className = 'topic-group';
      const row = document.createElement('div'); row.className = 'topic-heading-row';
      const heading = document.createElement('button'); heading.type = 'button'; heading.className = 'nav-item topic-heading'; heading.textContent = name; heading.dataset.englishGroup = categoryCode;
      const toggle = document.createElement('button'); toggle.type = 'button'; toggle.className = 'topic-toggle'; toggle.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>'; toggle.setAttribute('aria-label', name + ' topics');
      const list = document.createElement('ul'); list.className = 'topic-list'; list.hidden = true; list.id = 'english-' + prefix;
      toggle.setAttribute('aria-controls', list.id); toggle.setAttribute('aria-expanded','false');
      toggle.addEventListener('click', () => { list.hidden = !list.hidden; toggle.setAttribute('aria-expanded', String(!list.hidden)); });
      const select = topic => { globalSearch = false; searchAllArticles = false; language = 'en'; sidebarTopic = topic; selectedInterest = ''; category = categoryCode; $('query').value = ''; load(); };
      heading.addEventListener('click', () => select(''));
      row.append(heading, toggle);
      for (const [id, text] of values) {
        const li = document.createElement('li'); const button = document.createElement('button'); button.type = 'button'; button.className = 'topic-button'; button.textContent = text; button.dataset.englishTopic = prefix + '.' + id;
        button.addEventListener('click', () => select(prefix + '.' + id)); li.append(button); list.append(li);
      }
      group.append(row, list); host.append(group);
    }
  }

  buildSidebar();
  buildEnglishSidebar();
  function applySession(user) {
    responseCache.clear(); readIds.clear();
    guest = !user;
    configureInterestChips(user);
    if (guest) { try { const ids = JSON.parse(localStorage.getItem('dait_guest_reads') || '[]'); if (Array.isArray(ids)) ids.filter(id => typeof id === 'string').slice(-2000).forEach(id => readIds.add(id)); } catch {} }
    $('search-form').removeAttribute('data-member-only');
    $('search-form').hidden = false;
    document.querySelectorAll('[data-member-only]').forEach(el => { el.hidden = guest; });
    document.querySelector('.page-title').textContent = user?.nickname ? `${user.nickname}님의 AI 뉴스` : '오늘의 AI 뉴스';
    load();
  }
  DAIT.currentUser().then(applySession);
  window.addEventListener('pageshow', event => {
    if (!event.persisted) return;
    DAIT.currentUser().then(user => {
      if (!user) { category = ''; $('query').value = ''; }
      applySession(user);
      DAIT.renderAuthArea();
    });
  });
})();

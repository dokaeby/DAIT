(() => {
  const cards = [...document.querySelectorAll('.news-card')];
  if (cards.length) {
    const input = document.querySelector('.search-input');
    const message = document.querySelector('#state-message');
    const count = document.querySelector('.result-meta strong');
    const list = document.querySelector('.news-list');
    const initial = cards.map((card, i) => {
      const title = card.querySelector('.news-title').textContent.trim();
      const summary = [...card.querySelectorAll('.summary-list li')].map(el => el.textContent.trim());
      const source = card.querySelector('.news-meta span').textContent.trim();
      const time = card.querySelector('time').textContent.trim();
      const data = {title, summary, source, time, id: String(i + 1)};
      card.tabIndex = 0;
      card.setAttribute('role', 'link');
      card.setAttribute('aria-label', `${title} 상세 보기`);
      const link = card.querySelector('a[href="detail.html"]');
      link.href = `detail.html?article=${i + 1}`;
      const open = () => { sessionStorage.setItem('dait-article', JSON.stringify(data)); location.href = link.href; };
      card.addEventListener('click', e => { if (!e.target.closest('button, a, select')) open(); });
      card.addEventListener('keydown', e => { if (e.target === card && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); open(); } });
      link.addEventListener('click', () => sessionStorage.setItem('dait-article', JSON.stringify(data)));
      return {card, data, index:i};
    });
    function search() {
      const term = input.value.trim().toLocaleLowerCase();
      let visible = 0;
      for (const {card, data} of initial) {
        card.hidden = !!term && !`${data.title} ${data.summary.join(' ')}`.toLocaleLowerCase().includes(term);
        if (!card.hidden) visible++;
      }
      count.textContent = `검증 완료 뉴스 ${visible}건`;
      message.hidden = visible > 0;
      message.textContent = visible ? '' : '검색 결과가 없습니다. 검색어를 바꾸거나 초기화해 주세요.';
    }
    document.querySelector('#search-button').addEventListener('click', search);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); search(); } });
    input.addEventListener('search', () => { if (!input.value) search(); });
    document.querySelector('#reset-button').addEventListener('click', () => { input.value = ''; search(); input.focus(); });
    document.querySelectorAll('.chip').forEach(chip => chip.addEventListener('click', () => {
      document.querySelectorAll('.chip').forEach(c => { c.classList.remove('active'); c.setAttribute('aria-pressed','false'); });
      chip.classList.add('active'); chip.setAttribute('aria-pressed','true'); search();
    }));
    document.querySelector('.select-like').addEventListener('change', e => {
      const sorted = [...initial].sort((a,b) => e.target.value === '최신순' ? b.data.time.localeCompare(a.data.time) : a.index-b.index);
      sorted.forEach(({card}) => list.append(card));
    });
    document.querySelectorAll('.chip').forEach(c => c.setAttribute('aria-pressed', String(c.classList.contains('active'))));
  }
  const title = document.querySelector('.article-title');
  if (title) {
    const sourcePanel = document.querySelector('.source-panel');
    document.querySelector('.content-stack').prepend(sourcePanel);
    const articleId = new URLSearchParams(location.search).get('article');
    let data; try { data = JSON.parse(sessionStorage.getItem('dait-article')); } catch (_) {}
    if (articleId && data && data.id === articleId) {
      title.textContent = data.title;
      document.querySelector('.article-hero .news-meta + h1 + .news-meta strong').textContent = data.source;
      document.querySelector('.article-hero .news-meta span:last-child').textContent = data.time;
      document.querySelector('.source-panel .source-value').textContent = data.source;
      document.querySelectorAll('.source-panel .source-value')[1].textContent = data.time + ' KST';
      document.querySelectorAll('.key-points li').forEach((li,i) => li.textContent = data.summary[i]);
      if (articleId !== '1') {
        const translation = [...document.querySelectorAll('.panel')].find(p => p.querySelector('.panel-title')?.textContent === '한국어 번역');
        translation.querySelector('.panel-caption').textContent = '내용 부족';
        translation.querySelectorAll('.translation-copy').forEach((el,i) => { if (i === 0) el.textContent = '이 예시 기사에는 번역 내용이 제공되지 않습니다.'; else el.remove(); });
        document.querySelectorAll('.related-item').forEach(a => a.removeAttribute('href'));
      }
    }
  }
})();

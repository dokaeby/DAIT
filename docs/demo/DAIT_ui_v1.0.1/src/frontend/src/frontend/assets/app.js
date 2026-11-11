
    const dialog = document.querySelector('#detail');
    const field = id => document.getElementById('detail-' + id);
    const searchForm = document.querySelector('form.search');
    const searchInput = document.querySelector('#query');
    const searchStatus = document.querySelector('#search-status');
    const searchError = document.querySelector('#search-error');
    let appliedQuery = searchInput.value.trim();
    let category = new URL(location.href).searchParams.get('category') || '';
    const sortControl = document.querySelector('#sort');
    function searchUrl() {
      const url = new URL(searchForm.action);
      if (category) url.searchParams.set('category', category);
      url.searchParams.set('sort', sortControl.value);
      return url;
    }
    const loginQuery = document.querySelector('form[action="/login"] input[name="q"]');
    const loginDialog = document.querySelector('#login-dialog');
    const loginForm = document.querySelector('.login-form');
    const loginError = document.querySelector('#login-error');
    const signupForm = document.querySelector('#signup-form');
    const signupFeedback = document.querySelector('#signup-feedback');
    const signupLink = document.querySelector('#show-signup');
    const signupUser = document.querySelector('#signup-user');
    const signupNickname = document.querySelector('#signup-nickname');
    const signupNicknameError = document.querySelector('#signup-nickname-error');
    const signupUserError = document.querySelector('#signup-user-error');
    const signupPassword = document.querySelector('#signup-password');
    const signupPasswordError = document.querySelector('#signup-password-error');
    const signupPasswordConfirm = document.querySelector('#signup-password-confirm');
    const signupPasswordConfirmError = document.querySelector('#signup-password-confirm-error');
    let confirmMismatchChecked = false;
    let authViewVersion = 0;
    function resetSignupValidation() {
      confirmMismatchChecked = false;
      for (const input of [signupUser, signupNickname, signupPassword, signupPasswordConfirm]) {
        input.setCustomValidity('');
        input.removeAttribute('aria-invalid');
      }
      for (const error of [signupUserError, signupNicknameError, signupPasswordError, signupPasswordConfirmError]) error.hidden = true;
      signupPasswordError.textContent = '비밀번호는 최소 5자 이상 입력해주세요';
      signupPasswordConfirmError.textContent = '';
    }
    function showSignupFieldError(name, message) {
      const fields = {nickname: [signupNickname, signupNicknameError], user: [signupUser, signupUserError], password: [signupPassword, signupPasswordError], password_confirm: [signupPasswordConfirm, signupPasswordConfirmError]};
      if (!fields[name]) return;
      const [input, error] = fields[name];
      input.setCustomValidity(message);
      input.setAttribute('aria-invalid', 'true');
      error.textContent = message;
      error.hidden = false;
    }
    signupNickname.addEventListener('input', () => {
      signupNickname.setCustomValidity('');
      signupNickname.removeAttribute('aria-invalid');
      signupNicknameError.hidden = true;
    });
    signupUser.addEventListener('input', () => {
      signupUser.setCustomValidity('');
      signupUser.removeAttribute('aria-invalid');
      signupUserError.hidden = true;
      signupFeedback.textContent = '';
      signupFeedback.classList.remove('is-success');
    });
    function validateSignupConfirmation(checkMatch = confirmMismatchChecked) {
      let message = '';
      if (signupPasswordConfirm.value && Array.from(signupPasswordConfirm.value).length < 5) {
        message = '비밀번호는 최소 5자 이상 입력해주세요';
      } else if (signupPasswordConfirm.value && checkMatch && signupPasswordConfirm.value !== signupPassword.value) {
        message = '비밀번호가 일치 하지 않습니다. 다시 입력해주세요';
      }
      signupPasswordConfirm.setCustomValidity(message);
      signupPasswordConfirm.setAttribute('aria-invalid', String(Boolean(message)));
      signupPasswordConfirmError.textContent = message;
      signupPasswordConfirmError.hidden = !message;
      signupFeedback.textContent = '';
      signupFeedback.classList.remove('is-success');
      return !message;
    }
    function validateSignupPassword() {
      const invalid = Boolean(signupPassword.value) && Array.from(signupPassword.value).length < 5;
      signupPassword.setCustomValidity(invalid ? '비밀번호는 최소 5자 이상 입력해주세요' : '');
      signupPassword.setAttribute('aria-invalid', String(invalid));
      signupPasswordError.hidden = !invalid;
      signupPasswordError.textContent = '비밀번호는 최소 5자 이상 입력해주세요';
      signupFeedback.textContent = '';
      signupFeedback.classList.remove('is-success');
      if (confirmMismatchChecked || signupPasswordConfirm.value) validateSignupConfirmation();
      return !invalid;
    }
    signupPassword.addEventListener('input', validateSignupPassword);
    signupPassword.addEventListener('blur', validateSignupPassword);
    signupPassword.addEventListener('invalid', validateSignupPassword);
    signupPasswordConfirm.addEventListener('input', () => validateSignupConfirmation());
    signupPasswordConfirm.addEventListener('blur', () => validateSignupConfirmation());
    signupPasswordConfirm.addEventListener('invalid', () => validateSignupConfirmation());
    function showAuthView(signup) {
      authViewVersion++;
      const fromUser = document.querySelector(signup ? '#login-user' : '#signup-user');
      const toUser = document.querySelector(signup ? '#signup-user' : '#login-user');
      if (fromUser.value) toUser.value = fromUser.value;
      loginForm.hidden = signup;
      signupForm.hidden = !signup;
      document.querySelector('#login-title').textContent = signup ? '회원가입' : '로그인';
      document.querySelector('#login-close').setAttribute('aria-label', signup ? '회원가입 창 닫기' : '로그인 창 닫기');
      loginError.textContent = '';
      loginError.classList.remove('is-success');
      signupFeedback.textContent = '';
      signupFeedback.classList.remove('is-success');
      for (const input of loginDialog.querySelectorAll('input[type="password"]')) input.value = '';
      resetSignupValidation();
      if (loginDialog.open) toUser.focus();
    }
    signupLink.addEventListener('click', () => showAuthView(true));
    document.querySelector('#show-login').addEventListener('click', () => showAuthView(false));
    signupForm.addEventListener('submit', async event => {
      event.preventDefault();
      confirmMismatchChecked = true;
      const passwordValid = validateSignupPassword();
      const confirmationValid = validateSignupConfirmation(true);
      if (!passwordValid || !confirmationValid) {
        (passwordValid ? signupPasswordConfirm : signupPassword).focus();
        return;
      }
      const version = authViewVersion;
      const body = new URLSearchParams(new FormData(signupForm));
      const controls = [...signupForm.querySelectorAll('input, button')];
      for (const control of controls) control.disabled = true;
      signupForm.setAttribute('aria-busy', 'true');
      signupFeedback.textContent = '회원가입 정보를 저장하고 있습니다…';
      try {
        const response = await fetch('/signup', {method: 'POST', headers: {'Accept': 'application/json'}, body});
        const data = await response.json();
        if (version !== authViewVersion || !loginDialog.open || signupForm.hidden) return;
        if (!response.ok) {
          for (const [name, message] of Object.entries(data.field_errors || {})) showSignupFieldError(name, message);
          signupFeedback.textContent = data.error || '회원가입 정보를 저장하지 못했습니다.';
          return;
        }
        signupUser.value = data.user.username;
        showAuthView(false);
        loginError.classList.add('is-success');
        loginError.textContent = '회원가입이 완료되었습니다. 로그인해주세요.';
      } catch {
        if (version === authViewVersion && loginDialog.open && !signupForm.hidden) {
          signupFeedback.textContent = '처리 결과를 확인하지 못했습니다. 연결을 확인해주세요. 다시 시도할 때 중복 아이디 안내가 나오면 이미 저장되었을 수 있습니다.';
        }
      } finally {
        for (const control of controls) control.disabled = false;
        signupForm.removeAttribute('aria-busy');
      }
    });
    function openAuth(signup) {
      loginError.textContent = '';
      loginForm.reset();
      signupForm.reset();
      showAuthView(signup);
      loginQuery.value = appliedQuery;
      loginDialog.showModal();
      document.querySelector(signup ? '#signup-nickname' : '#login-user').focus();
    }
    document.querySelector('#login-open')?.addEventListener('click', () => openAuth(false));
    document.querySelector('#signup-open')?.addEventListener('click', () => openAuth(true));
    document.querySelector('#login-close').addEventListener('click', () => loginDialog.close());
    loginDialog.addEventListener('close', () => {
      authViewVersion++;
      for (const input of loginDialog.querySelectorAll('input[type="password"]')) input.value = '';
    });
    loginForm.addEventListener('submit', async event => {
      event.preventDefault();
      const button = loginForm.querySelector('button[type="submit"]');
      button.disabled = true;
      signupLink.disabled = true;
      loginError.textContent = '';
      loginError.classList.remove('is-success');
      try {
        const response = await fetch('/login', {method:'POST', headers:{'Accept':'application/json'}, body:new URLSearchParams(new FormData(loginForm))});
        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.error || '로그인하지 못했습니다.');
        }
        window.location.assign(response.url);
      } catch (error) { loginError.textContent = error.message || '로그인하지 못했습니다.'; }
      finally { button.disabled = false; signupLink.disabled = false; }
    });
    let searchController;
    let searchNumber = 0;
    let semanticTimer;
    let semanticBusy = false;
    let semanticWanted = false;
    let currentSearchJob = null;

    function queueSemantic() {
      clearTimeout(semanticTimer);
      semanticWanted = Array.from(appliedQuery).length >= 2;
      if (semanticWanted) semanticTimer = setTimeout(runSemantic, 500);
    }
    async function runSemantic() {
      if (semanticBusy || !semanticWanted) return;
      semanticBusy = true;
      semanticWanted = false;
      const current = searchNumber;
      const query = searchInput.value.trim();
      try {
        if (current === searchNumber) searchStatus.textContent = '키워드 결과를 표시합니다. 의미 검색을 준비하고 있습니다…';
        const response = await fetch('/api/search-lab/jobs', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action:'integrated', query, category})});
        const started = await response.json();
        if (!response.ok) throw new Error(started.error || '검색을 시작하지 못했습니다.');
        let job;
        do {
          await new Promise(resolve => setTimeout(resolve, 800));
          const poll = await fetch('/api/search-lab/jobs/' + started.job_id, {cache:'no-store'});
          job = await poll.json();
          if (!poll.ok) throw new Error(job.error || '검색 진행 상태를 확인하지 못했습니다.');
          if (current === searchNumber && job.status === 'running') searchStatus.textContent = job.message;
        } while (job.status === 'running');
        if (current !== searchNumber) return;
        if (job.status !== 'completed') throw new Error(job.message);
        const url = searchUrl();
        url.searchParams.set('q', query);
        url.searchParams.set('search_job', started.job_id);
        const result = await fetch(url, {cache:'no-store'});
        if (!result.ok) throw new Error('검색 결과를 불러오지 못했습니다.');
        const next = new DOMParser().parseFromString(await result.text(), 'text/html');
        if (current !== searchNumber) return;
        const results = next.querySelector('#search-results');
        if (!results) throw new Error('검색 결과가 없습니다.');
        searchController?.abort();
        currentSearchJob = started.job_id;
        document.querySelector('#search-results').replaceWith(document.importNode(results, true));
        searchStatus.textContent = sortControl.value === 'latest' ? '검색 관련도 상위 결과를 최신순으로 표시합니다.' : '키워드와 의미 유사도를 결합한 결과입니다.';
      } catch (error) {
        if (current === searchNumber) searchStatus.textContent = '의미 검색을 완료하지 못했습니다. 키워드 결과를 표시합니다: ' + error.message;
      } finally {
        semanticBusy = false;
        if (semanticWanted) void runSemantic();
      }
    }
    const batchButton = document.querySelector('#summary-batch');
    const batchStatus = document.querySelector('#summary-batch-status');
    let batchPolling = false;
    let lastProcessed = null;
    let lastSummaryRevision = null;
    async function refreshSavedSummaries() {
      if (searchInput.value.trim() && Array.from(searchInput.value.trim()).length < 2) return;
      const current = searchNumber;
      const jobId = currentSearchJob;
      const url = searchUrl();
      if (appliedQuery) url.searchParams.set('q', appliedQuery);
      if (jobId) url.searchParams.set('search_job', jobId);
      const response = await fetch(url, {cache: 'no-store'});
      if (!response.ok) throw new Error('저장 요약 조회 실패');
      const next = new DOMParser().parseFromString(await response.text(), 'text/html');
      const results = next.querySelector('#search-results');
      if (results && current === searchNumber && jobId === currentSearchJob) {
        document.querySelector('#search-results').replaceWith(document.importNode(results, true));
      }
    }
    async function watchBatch() {
      if (batchPolling) return;
      batchPolling = true;
      try {
        while (true) {
          const response = await fetch('/api/summary/batch-status', {cache:'no-store'});
          if (!response.ok) throw new Error('진행 상태 조회 실패');
          const job = await response.json();
          batchStatus.textContent = job.message;
          if (lastProcessed !== (job.processed || 0) || lastSummaryRevision !== job.revision) {
            await refreshSavedSummaries();
            lastProcessed = job.processed || 0;
            lastSummaryRevision = job.revision;
          }
          batchButton.hidden = true;
          // 완료 후에도 수집 결과를 확인합니다. 이 조회는 AI 생성을 요청하지 않습니다.
          await new Promise(resolve => setTimeout(resolve, 5000));
        }
      } catch (error) {
        batchStatus.textContent = '요약 준비 상태를 확인하지 못했습니다: ' + error.message;
        batchButton.hidden = true;
      } finally {
        batchPolling = false;
        setTimeout(() => { void watchBatch(); }, 10000);
      }
    }
    batchButton.addEventListener('click', async () => {
      batchButton.disabled = true;
      batchStatus.textContent = '요약 준비를 요청하고 있습니다…';
      try {
        const response = await fetch('/api/summary/batch', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'});
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || '요청 실패');
        lastProcessed = 0;
        batchButton.hidden = true;
        await watchBatch();
      } catch (error) {
        batchStatus.textContent = '요약 준비 상태를 확인하지 못했습니다: ' + error.message;
      } finally { batchButton.disabled = false; }
    });
    void watchBatch();

    function cancelSearch() {
      currentSearchJob = null;
      searchController?.abort();
      searchNumber++;
    }

    async function refreshSearch(current) {
      const controller = new AbortController();
      searchController = controller;
      const url = searchUrl();
      if (appliedQuery) url.searchParams.set('q', appliedQuery);
      document.querySelector('#search-results').setAttribute('aria-busy', 'true');
      searchStatus.textContent = '검색 중입니다…';
      try {
        const response = await fetch(url, {cache: 'no-store', signal: controller.signal});
        if (!response.ok) throw new Error('검색 실패');
        const html = await response.text();
        if (current !== searchNumber) return;
        const next = new DOMParser().parseFromString(html, 'text/html');
        const results = next.querySelector('#search-results');
        if (!results) throw new Error('검색 결과 없음');
        document.querySelector('#search-results').replaceWith(document.importNode(results, true));
        loginQuery.value = next.querySelector('form[action="/login"] input[name="q"]').value;
        history.replaceState(null, '', url.pathname + url.search);
        searchStatus.textContent = appliedQuery ? '검색 결과를 갱신했습니다.' : '기본 목록으로 돌아왔습니다.';
      } catch (error) {
        if (error.name !== 'AbortError' && current === searchNumber) {
          searchStatus.textContent = '검색을 갱신하지 못했습니다. 이전 결과를 표시합니다. 검색어를 수정해 다시 시도해 주세요.';
        }
      } finally {
        if (current === searchNumber) document.querySelector('#search-results').removeAttribute('aria-busy');
      }
    }

    function searchOnChange() {
      cancelSearch();
      clearTimeout(semanticTimer);
      semanticWanted = false;
      loginQuery.value = appliedQuery;
      void refreshSearch(searchNumber);
      queueSemantic();
    }
    searchInput.addEventListener('input', () => {
      cancelSearch();
      clearTimeout(semanticTimer);
      semanticWanted = false;
      searchError.hidden = true;
      searchInput.removeAttribute('aria-invalid');
      document.querySelector('#search-results').removeAttribute('aria-busy');
      searchStatus.textContent = '';
    });
    sortControl.addEventListener('change', searchOnChange);
    const expandInterests = document.querySelector('[data-interest-expand]');
    expandInterests?.addEventListener('click', () => {
      const expanded = expandInterests.getAttribute('aria-expanded') === 'true';
      const interestChips = [...document.querySelectorAll('[data-category]')].filter(chip => chip.dataset.category);
      const visible = interestChips.slice(0, 5);
      const active = interestChips.find(chip => chip.dataset.category === category);
      if (active && !visible.includes(active)) visible[4] = active;
      interestChips.forEach(chip => { chip.hidden = expanded && !visible.includes(chip); });
      expandInterests.setAttribute('aria-expanded', String(!expanded));
      expandInterests.textContent = expanded ? `나머지 ${expandInterests.dataset.count}개 펼치기` : '접기';
    });
    document.querySelectorAll('[data-category]').forEach(chip => chip.addEventListener('click', event => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      category = chip.dataset.category;
      document.querySelectorAll('[data-category]').forEach(item => item.classList.toggle('active', item.dataset.category === category));
      searchOnChange();
    }));
    searchForm.addEventListener('submit', event => {
      event.preventDefault();
      const query = searchInput.value.trim();
      if (Array.from(query).length < 2) {
        searchError.textContent = '최소 2자 이상 입력해주세요.';
        searchError.hidden = false;
        searchInput.setAttribute('aria-invalid', 'true');
        return;
      }
      searchError.hidden = true;
      searchInput.removeAttribute('aria-invalid');
      appliedQuery = query;
      sortControl.value = 'rank';
      searchOnChange();
    });
    // KAN-10: 선호 검색어 칩을 누르면 그 단어로 바로 검색합니다. 같은 칩을 다시 누르면 검색을 지웁니다.
    document.querySelectorAll('[data-keyword]').forEach(chip => chip.addEventListener('click', () => {
      const word = chip.dataset.keyword;
      const clearing = appliedQuery === word;
      // v1.0.1 검색은 입력창이 아니라 appliedQuery로 조회하므로 함께 바꿔야 실제로 검색됩니다.
      searchInput.value = clearing ? '' : word;
      appliedQuery = clearing ? '' : word;
      searchError.hidden = true;
      searchInput.removeAttribute('aria-invalid');
      sortControl.value = clearing ? 'latest' : 'rank';
      document.querySelectorAll('[data-keyword]').forEach(item => item.classList.toggle('active', !clearing && item === chip));
      searchOnChange();
    }));
    document.querySelector('#clear-search').addEventListener('click', event => {
      event.preventDefault();
      searchInput.value = '';
      appliedQuery = '';
      searchError.hidden = true;
      searchInput.removeAttribute('aria-invalid');
      sortControl.value = 'latest';
      searchOnChange();
      searchInput.focus();
    });
    if (Array.from(appliedQuery).length >= 2) queueSemantic();

    let requestNumber = 0;
    let articleUrl = '';
    const generateButton = field('ai-generate');
    function showSummary(summary) {
      field('ai-lines').replaceChildren();
      for (const line of summary.lines) {
        const item = document.createElement('li');
        item.textContent = line;
        field('ai-lines').append(item);
      }
      field('ai-message').textContent = summary.message;
      generateButton.hidden = !summary.can_retry;
      generateButton.textContent = '요약 다시 시도';
      // 팝업에서 확인한 최신 저장 결과를 같은 기사의 메인 카드에도 반영합니다.
      const id = decodeURIComponent(new URL(articleUrl).pathname.slice('/article/'.length));
      const card = Array.from(document.querySelectorAll('[data-article-id]'))
        .find(item => item.dataset.articleId === id);
      if (!card) return;
      const box = card.querySelector('.summary-box');
      box.querySelector('.summary-list, .empty-summary')?.remove();
      const content = document.createElement(summary.lines.length ? 'ul' : 'p');
      content.className = summary.lines.length ? 'summary-list' : 'empty-summary';
      if (summary.lines.length) {
        for (const line of summary.lines) {
          const item = document.createElement('li');
          item.textContent = line;
          content.append(item);
        }
      } else content.textContent = summary.message;
      box.append(content);
      const badge = card.querySelector('.status-tag');
      badge.className = 'status-tag ' + summary.status_tone;
      badge.textContent = summary.status_label;
    }
    let summaryTimer;
    const terminalSummaryStates = new Set(['generated', 'insufficient', 'failed']);
    async function watchSavedSummary(url, current) {
      clearTimeout(summaryTimer);
      if (!dialog.open || current !== requestNumber) return;
      let again = true;
      try {
        const response = await fetch(url + '?format=json', {cache: 'no-store'});
        if (!response.ok) throw new Error('저장 요약 조회 실패');
        const article = await response.json();
        if (!dialog.open || current !== requestNumber) return;
        showSummary(article.ai_summary);
        again = !terminalSummaryStates.has(article.ai_summary.status);
      } catch {
        if (!dialog.open || current !== requestNumber) return;
        field('ai-message').textContent = '요약 상태를 확인하지 못했습니다. 잠시 후 다시 확인합니다.';
      }
      if (again && dialog.open && current === requestNumber) {
        summaryTimer = setTimeout(() => { void watchSavedSummary(url, current); }, 3000);
      }
    }
    generateButton.addEventListener('click', async () => {
      const current = requestNumber;
      const url = articleUrl;
      clearTimeout(summaryTimer);
      generateButton.disabled = true;
      field('ai-message').textContent = '요약을 다시 요청하고 있습니다…';
      try {
        const response = await fetch('/api/summary/jobs', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({article_path:new URL(url).pathname})});
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || '요청 실패');
        if (dialog.open && current === requestNumber) await watchSavedSummary(url, current);
      } catch (error) {
        if (dialog.open && current === requestNumber) field('ai-message').textContent = error.message;
      } finally {
        if (dialog.open && current === requestNumber) generateButton.disabled = false;
      }
    });
    document.addEventListener('click', async event => {
      const link = event.target.closest('#search-results [data-detail]');
      if (!link) return;
      if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      const current = ++requestNumber;
      clearTimeout(summaryTimer);
      articleUrl = link.href;
      generateButton.hidden = true;
      generateButton.disabled = false;
      field('copy').disabled = true;
      field('copy-status').textContent = '';
      field('original').removeAttribute('href');
      field('title').textContent = '기사 불러오는 중';
      for (const name of ['category', 'meta', 'text', 'note', 'foreign']) field(name).textContent = '';
      field('original').hidden = true;
      field('sources').hidden = true;
      field('original-title').textContent = '';
      field('original-title').hidden = true;
      field('description-heading').textContent = '기사 설명';
      field('ai-lines').replaceChildren();
      field('ai-message').textContent = '저장된 요약을 확인하고 있습니다.';
      dialog.showModal();
      try {
        const response = await fetch(link.href + '?format=json', {cache: 'no-store'});
        if (!response.ok) throw new Error('기사 조회 실패');
        const article = await response.json();
        if (!dialog.open || current !== requestNumber) return;
        field('title').textContent = article.title;
        field('category').textContent = article.categories || '기타';
        field('meta').textContent = article.source + ' · ' + article.published_at;
        field('original-title').textContent = article.is_foreign ? '원문 제목: ' + article.original_title : '';
        field('original-title').hidden = !article.is_foreign;
        field('description-heading').textContent = article.is_foreign ? '원문 RSS 설명' : '기사 설명';
        showSummary(article.ai_summary);
        if (!terminalSummaryStates.has(article.ai_summary.status)) {
          summaryTimer = setTimeout(() => { void watchSavedSummary(link.href, current); }, 3000);
        }
        field('text').textContent = article.description || '제공된 기사 설명이 없습니다.';
        field('note').textContent = '언론사 RSS에서 제공한 설명입니다. 기사 전문이나 AI 3줄 요약이 아닙니다.';
        field('foreign').textContent = article.foreign_notice;
        if (article.original_url) {
          field('copy').disabled = false;
          field('source-name').textContent = article.source;
          field('source-url').textContent = article.original_url;
          field('source-url').href = article.original_url;
          field('sources').hidden = false;
          field('original').href = article.original_url;
          field('original').hidden = false;
        } else {
          field('note').textContent += ' 사용할 수 있는 원문 링크가 없습니다.';
        }
      } catch (error) {
        if (dialog.open && current === requestNumber) {
          field('title').textContent = '기사를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.';
          field('ai-message').textContent = '';
        }
      }
    });
    document.querySelector('.card-close').addEventListener('click', () => dialog.close());
    dialog.addEventListener('close', () => { requestNumber++; clearTimeout(summaryTimer); });
    field('copy').addEventListener('click', async () => {
      const current = requestNumber;
      try {
        await navigator.clipboard.writeText(field('original').href);
        if (current === requestNumber) field('copy-status').textContent = '원문 링크를 복사했습니다.';
      } catch {
        if (current === requestNumber) field('copy-status').textContent = '복사하지 못했습니다. 원본 정보의 링크를 직접 복사해 주세요.';
      }
    });
    

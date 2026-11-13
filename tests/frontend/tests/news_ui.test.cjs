/* Run with Node and Playwright installed; uses isolated browser/API fixtures only. */
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium, firefox } = require('playwright');
const targetBrowser = process.env.DAIT_TEST_BROWSER || 'chrome';
const launchBrowser = () => targetBrowser === 'firefox' ? firefox.launch({ headless: true }) : chromium.launch({ executablePath: targetBrowser === 'edge' ? 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe' : 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
const root = path.resolve(__dirname, '../../../src/frontend/public');

test('local UI: cards, safe content, popup, paging, search, error and mobile layout', async () => {
  const browser = await launchBrowser();
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    await page.addInitScript(() => localStorage.setItem('dait_access_token', 'fixture-token'));
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const requests = [];
    let liveTotal = 100;
    const savedReads = new Set();
    const item = { id: 'n1', rank: 1, title: '<img src=x onerror=alert(1)> AI 소식', original_language: 'en', source_name: '테스트 뉴스', published_at: '2026-11-11T09:00:00Z', category: 'AI', summary_lines: ['첫 번째 요약', '두 번째 요약', '세 번째 요약'], processing_status: 'READY', original_url: 'https://example.com/news' };
    await page.route('http://dait.test/**', async route => {
      const url = new URL(route.request().url());
      if (url.pathname === '/v1/me/session') return route.fulfill({ json: { authenticated: true, user: { email: 'fixture@example.com' } } });
      if (url.pathname === '/v1/news/activity') return route.fulfill({ json: { total: liveTotal, counts: { AI: 50, ECONOMY: 30, POLITICS: liveTotal - 80 }, read_ids: [...savedReads] } });
      if (url.pathname.endsWith('/read')) { savedReads.add(url.pathname.split('/').at(-2)); return route.fulfill({ status: 204 }); }
      if (url.pathname === '/v1/news') {
        requests.push(url);
        if (url.searchParams.get('q') === 'error') return route.fulfill({ status: 500, json: {} });
        const items = url.searchParams.get('q') === 'empty' ? [] : [{ ...item, id: url.searchParams.has('cursor') ? 'n2' : 'n1' }];
        return route.fulfill({ json: { items, page: { has_more: items.length > 0 && !url.searchParams.has('cursor'), next_cursor: 'next' }, meta: { total_visible: items.length ? 2 : 0, message: null } } });
      }
      if (url.pathname.startsWith('/v1/news/')) return route.fulfill({ json: { article: item, content: { summary_lines: item.summary_lines, translated_text: '번역 본문입니다.', content_status: 'READY' }, source: { original_url: item.original_url } } });
      let filename = url.pathname === '/' ? 'index.html' : url.pathname.replace(/^\/mockup\//, '').replace(/^\//, '');
      const file = path.join(root, filename);
      if (!fs.existsSync(file)) return route.fulfill({ status: 404, body: '' });
      return route.fulfill({ body: fs.readFileSync(file), contentType: filename.endsWith('.css') ? 'text/css' : filename.endsWith('.js') ? 'text/javascript' : 'text/html; charset=utf-8' });
    });
    await page.goto('http://dait.test/');
    await page.locator('.news-card').waitFor();
    assert.equal(await page.locator('.page-title').textContent(), '오늘의 AI 뉴스');
    assert.equal(await page.locator('[data-category=""]').getAttribute('aria-pressed'), 'true');
    assert.equal(requests[0].searchParams.has('category'), false);
    assert.equal(await page.locator('.news-card').count(), 1);
    assert.equal(await page.locator('#result-count').textContent(), '전체 기사');
    assert.equal(await page.locator('[data-category=""]').textContent(), '전체(100)');
    assert.equal(await page.locator('.news-title img').count(), 0, 'API titles must remain plain text');
    assert.match(await page.locator('.news-title').textContent(), /<img/);
    await page.getByRole('button', { name: '상세 보기', exact: true }).click();
    await page.getByText('번역 본문입니다.', { exact: true }).waitFor();
    assert.equal(await page.locator('#detail').evaluate(el => el.open), true);
    await page.locator('.news-card.is-read').first().waitFor();
    assert.equal(await page.locator('#detail-original').getAttribute('href'), item.original_url);
    assert.equal(await page.locator('#detail-page').count(), 0);
    assert.equal(await page.locator('#detail-source-url').getAttribute('href'), item.original_url);
    assert.equal(await page.locator('#detail .key-points li').count(), 3);
    if (process.env.DAIT_UI_SHOTS) await page.screenshot({ path: path.join(process.env.DAIT_UI_SHOTS, 'dait-popup-desktop.png') });
    await page.evaluate(() => Object.defineProperty(navigator, 'clipboard', {
      configurable: true, value: { writeText: async value => { window.copiedUrl = value; } },
    }));
    await page.locator('#detail-copy').click();
    await page.getByText('원문 링크를 복사했습니다.', { exact: true }).waitFor();
    assert.equal(await page.evaluate(() => window.copiedUrl), item.original_url);
    await page.mouse.click(1, 1);
    assert.equal(await page.locator('#detail').evaluate(el => el.open), true);
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#detail').evaluate(el => el.open), false);
    item.original_language = 'ko';
    await page.getByRole('button', { name: '상세 보기', exact: true }).click();
    await page.waitForFunction(() => document.querySelector('#detail-source-url').hasAttribute('href'));
    assert.equal(await page.locator('#detail-translation').isVisible(), false);
    assert.equal(await page.locator('#detail .key-points li').count(), 3);
    await page.keyboard.press('Escape');
    item.original_language = 'en';
    await page.getByRole('button', { name: '다음 10건' }).click();
    await page.waitForFunction(() => document.querySelector('[data-article-id=n2]') !== null);
    assert.equal(await page.locator('.news-card').count(), 1);
    assert.equal(await page.evaluate(() => window.scrollY), 0);
    await page.getByRole('button', { name: '이전 10건' }).click();
    await page.waitForFunction(() => document.querySelector('[data-article-id=n1]') !== null);
    assert.equal(await page.locator('#load-previous').isDisabled(), true);
    liveTotal = 101;
    await page.reload();
    await page.locator('.news-card.is-read').waitFor();
    assert.equal(await page.locator('[data-category=""]').textContent(), '전체(101)');
    await page.locator('[data-category="ECONOMY"]').click();
    await page.waitForFunction(() => document.querySelector('#search-results').getAttribute('aria-busy') === 'false');
    assert.equal(requests.at(-1).searchParams.get('category'), 'ECONOMY');
    await page.locator('#query').fill('empty');
    await page.getByRole('button', { name: '검색', exact: true }).click();
    await page.getByText('표시할 뉴스가 없습니다', { exact: true }).waitFor();
    await page.locator('#query').fill('');
    await page.locator('.news-card').waitFor();
    assert.equal(requests.at(-1).searchParams.has('q'), false);
    await page.locator('#query').fill('error');
    await page.getByRole('button', { name: '검색', exact: true }).click();
    await page.getByRole('button', { name: '다시 시도' }).waitFor();
    await page.locator('#query').fill('');
    await page.locator('.news-card').waitFor();
    await page.locator('#query').fill('AI');
    await page.locator('[data-category=""]').click();
    await page.waitForFunction(() => document.querySelector('#search-results').getAttribute('aria-busy') === 'false');
    assert.equal(requests.at(-1).searchParams.has('category'), false);
    assert.equal(requests.at(-1).searchParams.has('q'), false);
    assert.equal(await page.locator('#query').inputValue(), '');
    await page.locator('[data-category=ECONOMY]').click();
    await page.waitForFunction(() => document.querySelector('#search-results').getAttribute('aria-busy') === 'false');
    assert.equal(requests.at(-1).searchParams.has('q'), false);
    assert.equal(requests.at(-1).searchParams.get('category'), 'ECONOMY');
    await page.locator('[data-category=""]').click();
    await page.waitForFunction(() => document.querySelector('#search-results').getAttribute('aria-busy') === 'false');
    assert.match(await page.locator('#page-number').textContent(), /1 \/ 11/);
    await page.setViewportSize({ width: 1920, height: 1000 });
    await page.waitForFunction(() => {
      const shell = document.querySelector('.app-shell').getBoundingClientRect();
      return document.querySelector('#scroll-controls').getBoundingClientRect().left >= shell.right + 40;
    });
    const gap = await page.evaluate(() => document.querySelector('#scroll-controls').getBoundingClientRect().left - document.querySelector('.app-shell').getBoundingClientRect().right);
    assert.ok(gap >= 40, 'outside gutter gap: ' + gap);
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `overflow at ${width}px`);
      if (process.env.DAIT_UI_SHOTS) await page.screenshot({ path: path.join(process.env.DAIT_UI_SHOTS, `dait-step2-${width}.png`), fullPage: true });
      await page.emulateMedia({ reducedMotion: 'reduce' });
      const down = page.locator('#scroll-down');
      if (await down.isEnabled()) {
        await down.click();
        await page.waitForFunction(() => document.querySelector('#scroll-down').disabled);
        await page.locator('#scroll-up').click();
        await page.waitForFunction(() => window.scrollY <= 2);
      }
      await page.getByRole('button', { name: '상세 보기', exact: true }).click();
      assert.equal(await page.locator('#scroll-controls').isVisible(), false);
      await page.getByText('번역 본문입니다.', { exact: true }).waitFor();
      assert.equal(await page.locator('#detail').evaluate(el => el.scrollWidth <= el.clientWidth), true, `popup overflow at ${width}px`);
      if (process.env.DAIT_UI_SHOTS) await page.screenshot({ path: path.join(process.env.DAIT_UI_SHOTS, `dait-popup-${width}.png`) });
      await page.keyboard.press('Escape');
    }
    assert.deepEqual(errors, []);
  } finally { await browser.close(); }
});

test('auth dialogs: compact checkboxes, footer links, persistent backdrop and remembered email', async () => {
  const browser = await launchBrowser();
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    let loginFails = false;
    await page.route('http://dait.test/**', async route => {
      const url = new URL(route.request().url());
      if (url.pathname === '/v1/auth/login') {
        const body = route.request().postDataJSON();
        assert.deepEqual(Object.keys(body).sort(), ['email', 'password']);
        return route.fulfill({ status: loginFails ? 401 : 200, json: loginFails ? { message: '로그인 실패' } : { tokens: {} } });
      }
      if (url.pathname === '/v1/news/activity') return route.fulfill({ json: { total: 100, counts: { AI: 50, ECONOMY: 30, POLITICS: 20 }, read_ids: [] } });
      if (url.pathname.endsWith('/read')) return route.fulfill({ status: 204 });
      if (url.pathname === '/v1/news') return route.fulfill({ json: { items: [], page: { has_more: false }, meta: { total_visible: 0 } } });
      const name = url.pathname === '/' ? 'index.html' : url.pathname.replace(/^\/mockup\//, '').replace(/^\//, '');
      const file = path.join(root, name);
      if (!fs.existsSync(file)) return route.fulfill({ status: 404 });
      return route.fulfill({ body: fs.readFileSync(file), contentType: name.endsWith('.css') ? 'text/css' : name.endsWith('.js') ? 'text/javascript' : 'text/html; charset=utf-8' });
    });
    await page.goto('http://dait.test/');
    await page.locator('#signup-open').click();
    async function checkLayout(checkbox) {
      const size = await page.locator(checkbox).boundingBox();
      const label = await page.locator(`${checkbox} + span`).boundingBox();
      assert.ok(size.width >= 13 && size.width <= 18 && size.height <= 18);
      assert.ok(label.x > size.x && label.x - (size.x + size.width) <= 10);
      const submit = await page.locator('#auth-form [type=submit]').boundingBox();
      const navigation = await page.locator('.auth-navigation').boundingBox();
      assert.ok(navigation.y >= submit.y + submit.height);
    }
    assert.equal(await page.locator('#auth-terms').count(), 0);
    await page.mouse.click(5, 5);
    assert.equal(await page.locator('#auth-dialog').evaluate(el => el.open), true);
    await page.locator('#auth-switch').click();
    await checkLayout('#auth-remember');
    assert.equal(await page.getByLabel('이메일 저장', { exact: true }).count(), 1);
    await page.locator('#auth-email').fill('remember@example.com');
    await page.locator('#auth-password').fill('test-password');
    await page.locator('#auth-remember').check();
    await Promise.all([page.waitForNavigation(), page.locator('#auth-form [type=submit]').click()]);
    assert.equal(await page.evaluate(() => localStorage.getItem('dait_remembered_email')), 'remember@example.com');
    assert.equal(await page.evaluate(() => Object.values(localStorage).some(value => value.includes('test-password'))), false);
    await page.locator('#login-open').click();
    assert.equal(await page.locator('#auth-email').inputValue(), 'remember@example.com');
    assert.equal(await page.locator('#auth-password').inputValue(), '');
    assert.equal(await page.locator('#auth-remember').isChecked(), true);
    await page.locator('#auth-remember').uncheck();
    assert.equal(await page.evaluate(() => localStorage.getItem('dait_remembered_email')), null);
    await page.locator('#auth-close').click();
    await page.locator('#login-open').click();
    assert.equal(await page.locator('#auth-email').inputValue(), '');
    loginFails = true;
    await page.locator('#auth-email').fill('failed@example.com');
    await page.locator('#auth-password').fill('test-password');
    await page.locator('#auth-remember').check();
    await page.locator('#auth-form [type=submit]').click();
    await page.getByText('로그인 실패', { exact: true }).waitFor();
    assert.equal(await page.evaluate(() => localStorage.getItem('dait_remembered_email')), null);
    for (const width of [1280, 390]) {
      await page.setViewportSize({ width, height: 900 });
      await checkLayout('#auth-remember');
      if (process.env.DAIT_UI_SHOTS) await page.screenshot({ path: path.join(process.env.DAIT_UI_SHOTS, `dait-auth-${width}.png`) });
      await page.locator('#auth-switch').click();
      assert.equal(await page.locator('#auth-terms').count(), 0);
      if (process.env.DAIT_UI_SHOTS) await page.screenshot({ path: path.join(process.env.DAIT_UI_SHOTS, `dait-signup-${width}.png`) });
      await page.locator('#auth-switch').click();
    }
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#auth-dialog').evaluate(el => el.open), false);
    assert.deepEqual(errors, []);
  } finally { await browser.close(); }
});

test('settings: account interests, save/reload, failures, safe schedules and guest protection', async () => {
  const browser = await launchBrowser();
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    await page.addInitScript(() => { if (!sessionStorage.getItem('seeded')) { localStorage.setItem('dait_access_token', 'test-token'); sessionStorage.setItem('seeded', '1'); } });
    let withdrawals = 0;
    let selected = ['ai.models'];
    let failCatalog = false, failSave = false, catalogCalls = 0, interestSaves = 0;
    const item = { code: 'ai.models', name: '모델·연구', group: 'ai' };
    let settings = { default_count: 10, keywords: ['AI'], in_app_notice: true, email_notice: false };
    let schedules = [{ id: 's1', local_time: '09:00', timezone: 'Asia/Seoul', enabled: false, criteria: { categories: ['ECONOMY'], source_ids: ['source-1'], keywords: ['<img src=x onerror=alert(1)>'] }, next_run_at: null }];
    let updatedSchedule;
    await page.route('http://dait.test/**', async route => {
      const req = route.request(), url = new URL(req.url()), method = req.method();
      if (url.pathname === '/v1/me/session') return route.fulfill({ json: { authenticated: true, user: { email: 'test@example.com' } } });
      if (url.pathname === '/v1/me' && method === 'DELETE') { withdrawals++; return route.fulfill({ status: 401, json: {} }); }
      if (url.pathname === '/v1/interests/catalog') { catalogCalls++; return route.fulfill({ status: failCatalog ? 503 : 200, json: { groups: [{ group: 'ai', group_name: 'AI', interests: [item, { code: 'ai.agents', name: 'AI 에이전트', group: 'ai' }] }] } }); }
      if (url.pathname.startsWith('/v1/me/')) assert.equal(req.headers().authorization, 'Bearer test-token');
      if (url.pathname === '/v1/me/interests') {
        if (method === 'PUT') {
          interestSaves++;
          await new Promise(resolve => setTimeout(resolve, 100));
          if (failSave) return route.fulfill({ status: 422, json: { message: '저장 오류' } });
          selected = req.postDataJSON().interests;
        }
        return route.fulfill({ json: { interests: selected.map(code => ({ ...item, code })) } });
      }
      if (url.pathname === '/v1/me/settings') { if (method === 'PATCH') settings = { ...settings, ...req.postDataJSON() }; return route.fulfill({ json: settings }); }
      if (url.pathname === '/v1/me/schedules' && method === 'GET') return route.fulfill({ json: { items: schedules } });
      if (url.pathname === '/v1/me/schedules/s1' && method === 'DELETE') { schedules = []; return route.fulfill({ status: 204 }); }
      if (url.pathname === '/v1/me/schedules' && method === 'POST') { updatedSchedule = req.postDataJSON(); schedules.push({ id: 'new', ...updatedSchedule, next_run_at: null }); return route.fulfill({ status: 201, json: schedules.at(-1) }); }
      const name = url.pathname.replace(/^\/mockup\//, '').replace(/^\//, '') || 'index.html';
      const file = path.join(root, name);
      if (!fs.existsSync(file)) return route.fulfill({ status: 404 });
      return route.fulfill({ body: fs.readFileSync(file), contentType: name.endsWith('.css') ? 'text/css' : name.endsWith('.js') ? 'text/javascript' : 'text/html; charset=utf-8' });
    });
    await page.goto('http://dait.test/settings.html');
    await page.locator('#interest-fields:not([disabled])').waitFor();
    assert.equal(await page.locator('#sched-minute option').count(), 2);
    assert.equal(await page.locator('#sched-keywords').count(), 0);
    assert.equal(await page.locator('.settings-gear').count(), 0);
    await page.locator('#withdraw-open').click();
    await page.locator('#withdraw-cancel').click();
    assert.equal(withdrawals, 0);
    await page.locator('#withdraw-open').click();
    await page.locator('#withdraw-password').fill('incorrect-fixture');
    await page.locator('#withdraw-form [type=submit]').click();
    await page.getByText('탈퇴하지 못했습니다. 비밀번호와 로그인 상태를 확인해 주세요.', { exact: true }).waitFor();
    assert.equal(withdrawals, 1);
    await page.locator('#withdraw-cancel').click();
    assert.equal(await page.locator('#interest-count').textContent(), '1개 선택');
    assert.equal(await page.locator('.schedule-meta img').count(), 0);
    assert.match(await page.locator('.schedule-meta').textContent(), /09:00/);
    await page.locator('#interests-clear').click();
    await page.locator('#interests-form [type=submit]').click();
    await page.getByText('관심사를 저장했습니다.', { exact: true }).waitFor();
    assert.deepEqual(selected, []);
    await page.reload(); await page.locator('#interest-fields:not([disabled])').waitFor();
    assert.equal(await page.locator('#interest-count').textContent(), '0개 선택');
    await page.locator('#interests-all').click();
    failSave = true;
    await page.locator('#interests-form [type=submit]').click();
    await page.getByText('저장 오류', { exact: true }).waitFor();
    assert.deepEqual(selected, []);
    assert.equal(await page.locator('#interest-count').textContent(), '2개 선택');
    failSave = false;
    const before = interestSaves;
    await page.locator('#interests-form').evaluate(form => { form.requestSubmit(); form.requestSubmit(); });
    await page.getByText('관심사를 저장했습니다.', { exact: true }).waitFor();
    assert.equal(interestSaves, before + 1);
    await page.locator('#set-keywords').fill('로봇, 로봇, AI');
    await page.locator('#settings-form [type=submit]').click();
    await page.getByText('저장했습니다.', { exact: true }).waitFor();
    assert.deepEqual(settings.keywords, ['로봇', 'AI']);
    assert.equal(await page.locator('.schedule-item').textContent(), '09:00×');
    assert.equal(await page.locator('#schedule-count').textContent(), '1 / 5');
    await page.getByRole('button', { name: '09:00 예약 삭제' }).click();
    await page.getByText('예약을 삭제했습니다.', { exact: true }).waitFor();
    assert.equal(await page.locator('#schedule-count').textContent(), '0 / 5');
    await page.locator('#sched-hour').selectOption('10');
    await page.locator('#sched-minute').selectOption('30');
    await page.locator('#sched-submit').click();
    await page.getByText('예약을 추가했습니다.', { exact: true }).waitFor();
    assert.equal(updatedSchedule.local_time, '10:30');
    assert.equal(updatedSchedule.timezone, 'Asia/Seoul');
    assert.equal(await page.locator('.schedule-item').textContent(), '10:30×');
    failCatalog = true;
    await page.reload(); await page.locator('#interests-retry').waitFor();
    assert.equal(await page.locator('#interest-fields').evaluate(el => el.disabled), true);
    failCatalog = false; await page.locator('#interests-retry').click();
    await page.locator('#interest-fields:not([disabled])').waitFor();
    await page.setViewportSize({ width: 390, height: 900 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    if (process.env.DAIT_UI_SHOTS) await page.screenshot({ path: path.join(process.env.DAIT_UI_SHOTS, 'dait-settings-390.png'), fullPage: true });
    const previousCalls = catalogCalls;
    await page.evaluate(() => localStorage.removeItem('dait_access_token'));
    await page.reload(); await page.locator('#auth-required').waitFor();
    assert.equal(catalogCalls, previousCalls, 'guests must not load account settings');
    for (const width of [1280, 390]) {
      await page.setViewportSize({ width, height: 900 });
      const main = await page.locator('#settings-main').boundingBox();
      const notice = await page.locator('#auth-required').boundingBox();
      assert.ok(Math.abs((main.y + main.height / 2) - (notice.y + notice.height / 2)) < 2);
      assert.ok(Math.abs((main.x + main.width / 2) - (notice.x + notice.width / 2)) < 2);
      assert.equal(await page.getByRole('link', { name: '메인으로 돌아가기' }).getAttribute('href'), '/?ui=20261112-search');
      if (process.env.DAIT_UI_SHOTS) await page.screenshot({ path: path.join(process.env.DAIT_UI_SHOTS, `dait-guest-notice-${width}.png`) });
    }
    await page.getByRole('link', { name: '메인으로 돌아가기' }).click();
    assert.equal(new URL(page.url()).pathname, '/');
    assert.equal(new URL(page.url()).searchParams.get('q') || '', '');
    assert.deepEqual(errors, []);
  } finally { await browser.close(); }
});

test('sidebar topics and optional nickname signup with login handoff', async () => {
  const browser = await launchBrowser();
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    await page.addInitScript(() => { if (!sessionStorage.getItem('seeded')) { localStorage.setItem('dait_access_token', 'sidebar-token'); sessionStorage.setItem('seeded', '1'); } });
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    const searches = [], signups = [];
    let nicknameAvailable = true;
    await page.route('http://dait.test/**', async route => {
      const req = route.request(), url = new URL(req.url());
      if (url.pathname === '/v1/news/activity') return route.fulfill({ json: { total: 100, counts: { AI: 50, ECONOMY: 30, POLITICS: 20 }, read_ids: [] } });
      if (url.pathname.endsWith('/read')) return route.fulfill({ status: 204 });
      if (url.pathname === '/v1/news') { searches.push(url); return route.fulfill({ json: { items: [], page: { has_more: false }, meta: { total_visible: 0 } } }); }
      if (url.pathname === '/v1/auth/nickname-availability') return route.fulfill({ json: { nickname: url.searchParams.get('nickname'), available: nicknameAvailable } });
      if (url.pathname === '/v1/auth/signup') { signups.push(req.postDataJSON()); return route.fulfill({ status: 201, json: { user: { email: 'join@example.com' }, tokens: { access_token: 'unused-signup-token', refresh_token: 'unused-refresh' } } }); }
      if (url.pathname === '/v1/me/session') return route.fulfill({ json: { authenticated: true, user: { email: 'join@example.com', nickname: '<b>닉네임</b>' } } });
      const name = url.pathname === '/' ? 'index.html' : url.pathname.replace(/^\/mockup\//, '').replace(/^\//, '');
      const file = path.join(root, name);
      if (!fs.existsSync(file)) return route.fulfill({ status: 404 });
      return route.fulfill({ body: fs.readFileSync(file), contentType: name.endsWith('.css') ? 'text/css' : name.endsWith('.js') ? 'text/javascript' : 'text/html; charset=utf-8' });
    });
    await page.goto('http://dait.test/');
    await page.locator('[data-topic-group=AI]').waitFor();
    await page.waitForFunction(() => document.querySelector('.page-title').textContent.includes('님의 AI 뉴스'));
    assert.equal(await page.locator('.page-title b').count(), 0);
    assert.equal(await page.locator('[data-topic-toggle][aria-expanded=false]').count(), 3);
    assert.equal(await page.locator('.topic-list:visible').count(), 0);
    assert.equal(await page.locator('[data-topic]').count(), 15);
    assert.match(await page.locator('[data-topic-group=AI]').textContent(), /AI•인공지능/);
    assert.equal(await page.locator('[data-category=AI]').textContent(), 'AI•인공지능(50)');
    for (const code of ['AI', 'ECONOMY', 'POLITICS']) {
      const title = await page.locator(`[data-topic-group=${code}]`).boundingBox();
      const arrow = await page.locator(`[data-topic-toggle=${code}]`).boundingBox();
      const icon = await page.locator(`[data-topic-toggle=${code}] svg`).boundingBox();
      assert.ok(arrow.x >= title.x + title.width);
      assert.ok(Math.abs((title.y + title.height / 2) - (arrow.y + arrow.height / 2)) < 2);
      assert.ok(Math.abs((icon.x + icon.width / 2) - (arrow.x + arrow.width / 2)) < 1);
      assert.ok(Math.abs((icon.y + icon.height / 2) - (arrow.y + arrow.height / 2)) < 1);
    }
    const initialRequests = searches.length;
    const initialUrl = page.url();
    await page.locator('[data-topic-toggle=ECONOMY]').click();
    assert.equal(searches.length, initialRequests);
    assert.equal(page.url(), initialUrl);
    assert.equal(await page.locator('[data-category=""]').getAttribute('aria-pressed'), 'true');
    await page.locator('[data-topic-group=ECONOMY]').click();
    await page.waitForFunction(() => document.querySelector('#search-results').getAttribute('aria-busy') === 'false');
    assert.equal(searches.at(-1).searchParams.get('category'), 'ECONOMY');
    await page.getByRole('button', { name: '산업 동향', exact: true }).click();
    await page.waitForFunction(() => document.querySelector('#search-results').getAttribute('aria-busy') === 'false');
    assert.equal(searches.at(-1).searchParams.get('topic'), 'economy.industry');
    assert.equal(searches.at(-1).searchParams.has('q'), false);
    assert.equal(await page.locator('[data-topic="산업 동향"]').getAttribute('aria-pressed'), 'true');
    const countBeforeCollapse = searches.length;
    const urlBeforeCollapse = page.url();
    await page.locator('[data-topic-toggle=ECONOMY]').click();
    assert.equal(await page.locator('#topics-ECONOMY').isVisible(), false);
    assert.equal(await page.locator('[data-topic-toggle=ECONOMY]').getAttribute('aria-expanded'), 'false');
    assert.equal(await page.locator('#query').inputValue(), '산업 동향');
    assert.equal(searches.length, countBeforeCollapse, 'collapse must not change the query');
    assert.equal(page.url(), urlBeforeCollapse);
    await page.locator('[data-topic-toggle=ECONOMY]').focus();
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('#topics-ECONOMY').isVisible(), true);
    await page.reload();
    await page.locator('[data-topic="산업 동향"].active').waitFor({ state: 'attached' });
    assert.equal(await page.locator('.topic-list:visible').count(), 0);
    assert.equal(await page.locator('[data-topic-toggle][aria-expanded=false]').count(), 3);
    await page.setViewportSize({ width: 390, height: 900 });
    await page.locator('#topic-select').selectOption('POLITICS:교육');
    await page.waitForFunction(() => document.querySelector('#search-results').getAttribute('aria-busy') === 'false');
    assert.equal(searches.at(-1).searchParams.get('category'), 'POLITICS');
    assert.equal(searches.at(-1).searchParams.get('topic'), 'society.education');
    assert.equal(searches.at(-1).searchParams.has('q'), false);
    await page.evaluate(() => localStorage.removeItem('dait_access_token'));
    await page.reload();
    await page.locator('#signup-open').click();
    await page.locator('#auth-email').fill('join@example.com');
    await page.locator('#auth-password').fill('Strong-test-password!');
    await page.locator('#auth-password-confirm').fill('Strong-test-password!');
    await page.locator('#auth-nickname').fill('한');
    await page.locator('#nickname-check').click();
    await page.getByText('닉네임은 2~30자로 입력해 주세요.', { exact: true }).waitFor();
    assert.equal(await page.locator('#auth-form [type=submit]').isDisabled(), true);
    await page.locator('#auth-nickname').fill('하늘');
    nicknameAvailable = false;
    await page.locator('#nickname-check').click();
    await page.getByText('이미 사용 중인 닉네임입니다.', { exact: true }).waitFor();
    assert.equal(await page.locator('#auth-form [type=submit]').isDisabled(), true);
    nicknameAvailable = true;
    await page.locator('#nickname-check').click();
    await page.getByText('사용 가능한 닉네임입니다.', { exact: true }).waitFor();
    await page.locator('#auth-nickname').fill('다른이름');
    assert.equal(await page.locator('#auth-form [type=submit]').isDisabled(), true, 'changing nickname invalidates the check');
    await page.locator('#nickname-check').click();
    await page.getByText('사용 가능한 닉네임입니다.', { exact: true }).waitFor();
    await page.locator('#auth-form [type=submit]').click();
    await page.getByRole('heading', { name: '로그인', exact: true }).waitFor();
    assert.equal(signups[0].nickname, '다른이름');
    assert.equal(await page.locator('#auth-email').inputValue(), 'join@example.com');
    assert.equal(await page.locator('#auth-password').inputValue(), '');
    assert.equal(await page.evaluate(() => localStorage.getItem('dait_access_token')), null);
    assert.equal(await page.locator('#auth-dialog').evaluate(el => el.open), true);
    await page.locator('#auth-switch').click();
    await page.locator('#auth-email').fill('blank@example.com');
    await page.locator('#auth-password').fill('Strong-test-password!');
    await page.locator('#auth-password-confirm').fill('Strong-test-password!');
    await page.locator('#auth-form [type=submit]').click();
    await page.getByRole('heading', { name: '로그인', exact: true }).waitFor();
    assert.equal(signups[1].nickname, null);
    assert.equal(await page.locator('#auth-email').inputValue(), 'blank@example.com');
    await page.locator('#auth-close').click();
    await page.evaluate(() => localStorage.setItem('dait_access_token', 'login-token'));
    await page.reload();
    await page.getByText('<b>닉네임</b>님', { exact: true }).waitFor({ state: 'attached' });
    assert.equal(await page.locator('#auth-area b').count(), 0);
    assert.equal(await page.locator('.page-title').textContent(), '<b>닉네임</b>님의 AI 뉴스');
    await page.evaluate(() => localStorage.removeItem('dait_access_token'));
    await page.reload();
    await page.locator('#login-open').waitFor();
    assert.equal(await page.locator('.page-title').textContent(), '오늘의 AI 뉴스');
    assert.equal(await page.locator('#categories').isVisible(), false);
    assert.deepEqual(errors, []);
  } finally { await browser.close(); }
});

test('guest list is latest ten only and has no sort selector', async () => {
  const browser = await launchBrowser();
  try {
    const page = await browser.newPage();
    let requested;
    await page.route('http://dait.test/**', async route => {
      const url = new URL(route.request().url());
      if (url.pathname === '/v1/news/activity') return route.fulfill({ json: { total: 100, counts: { AI: 50, ECONOMY: 30, POLITICS: 20 }, read_ids: [] } });
      if (url.pathname.endsWith('/read')) return route.fulfill({ status: 204 });
      if (url.pathname === '/v1/news') {
        requested = url;
        return route.fulfill({ json: { items: Array.from({ length: 23 }, (_, index) => ({ id: 'n' + index, rank: index + 1, title: '기사 ' + index, source_name: '출처', category: 'AI', published_at: '2026-11-11T09:00:00Z', summary_lines: ['요약'], processing_status: 'READY', original_url: 'https://example.com/' + index })), page: { has_more: true, next_cursor: 'next' }, meta: { total_visible: 23 } } });
      }
      const name = url.pathname === '/' ? 'index.html' : url.pathname.replace(/^\/mockup\//, '').replace(/^\//, '');
      const file = path.join(root, name);
      if (!fs.existsSync(file)) return route.fulfill({ status: 404 });
      return route.fulfill({ body: fs.readFileSync(file), contentType: name.endsWith('.css') ? 'text/css' : name.endsWith('.js') ? 'text/javascript' : 'text/html; charset=utf-8' });
    });
    await page.goto('http://dait.test/?sort=rank&category=AI&q=searched');
    await page.getByText('최신 뉴스 10건', { exact: true }).waitFor();
    assert.equal(await page.locator('.news-card').count(), 10);
    assert.equal(await page.locator('#sort').count(), 0);
    assert.equal(await page.locator('#load-more').isVisible(), false);
    assert.equal(requested.searchParams.get('sort'), 'latest');
    assert.equal(requested.searchParams.has('category'), false);
    assert.equal(requested.searchParams.get('q'), 'searched');
    for (const width of [1280, 390]) {
      await page.setViewportSize({ width, height: 900 });
      for (const selector of ['#sidebar-categories', '#categories', '#topic-select', '.mobile-tab[href="/?category=AI"]']) {
        assert.equal(await page.locator(selector).isVisible(), false, selector);
      }
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    }
    await page.locator('#load-more').evaluate(el => el.click());
    assert.equal(await page.locator('.news-card').count(), 10);
  } finally { await browser.close(); }
});

test('initial news preview appears while full page is pending', async () => {
  const browser = await launchBrowser();
  try {
    const page = await browser.newPage();
    let releaseFull;
    const fullGate = new Promise(resolve => { releaseFull = resolve; });
    const items = Array.from({ length: 10 }, (_, i) => ({ id: 'preview' + i, rank: i + 1, title: 'News ' + i, source_name: 'Source', category: 'AI', published_at: '2026-11-11T09:00:00Z', summary_lines: [], processing_status: 'READY', original_url: 'https://example.com/' + i }));
    await page.route('http://dait.test/**', async route => {
      const url = new URL(route.request().url());
      if (url.pathname === '/v1/news') {
        if (url.searchParams.get('page_size') === '10') await fullGate;
        const result = url.searchParams.get('page_size') === '4' ? items.slice(0, 4) : items;
        return route.fulfill({ json: { items: result, page: { has_more: false }, meta: { total_visible: result.length } } });
      }
      const name = url.pathname === '/' ? 'index.html' : url.pathname.replace(/^\/mockup\//, '').replace(/^\//, '');
      const file = path.join(root, name);
      if (!fs.existsSync(file)) return route.fulfill({ status: 404 });
      return route.fulfill({ body: fs.readFileSync(file), contentType: name.endsWith('.css') ? 'text/css' : name.endsWith('.js') ? 'text/javascript' : 'text/html; charset=utf-8' });
    });
    await page.goto('http://dait.test/');
    await page.locator('.news-card').first().waitFor();
    assert.equal(await page.locator('.news-card').count(), 4);
    assert.equal(await page.locator('.news-skeleton').count(), 6);
    releaseFull();
    await page.waitForFunction(() => document.querySelectorAll('.news-card').length === 10);
    assert.equal(await page.locator('.news-skeleton').count(), 0);
  } finally { await browser.close(); }
});

test('guest search stays visible after reset and logout from settings', async () => {
  const browser = await launchBrowser();
  try {
    const page = await browser.newPage();
    let guestQuery = '';
    await page.route('http://dait.test/**', async route => {
      const url = new URL(route.request().url());
      if (url.pathname === '/v1/me/session') return route.fulfill({ json: { authenticated: true, user: { email: 'test@example.com' } } });
      if (url.pathname === '/v1/auth/logout') return route.fulfill({ status: 204 });
      if (url.pathname === '/v1/news') {
        guestQuery = url.searchParams.get('q') || '';
        return route.fulfill({ json: { items: [], page: { has_more: false }, meta: { total_visible: 0 } } });
      }
      if (url.pathname.startsWith('/v1/')) return route.fulfill({ status: 200, json: url.pathname.endsWith('/catalog') ? { groups: [] } : url.pathname.endsWith('/interests') ? { interests: [] } : url.pathname.endsWith('/schedules') ? { items: [] } : { default_count: 10, keywords: [] } });
      const name = url.pathname === '/' ? 'index.html' : url.pathname.replace(/^\/mockup\//, '').replace(/^\//, '');
      const file = path.join(root, name);
      if (!fs.existsSync(file)) return route.fulfill({ status: 404 });
      return route.fulfill({ body: fs.readFileSync(file), contentType: name.endsWith('.css') ? 'text/css' : name.endsWith('.js') ? 'text/javascript' : 'text/html; charset=utf-8' });
    });
    await page.goto('http://dait.test/');
    await page.locator('#login-open').waitFor();
    assert.equal(await page.locator('#search-form').isVisible(), true);
    await page.locator('#query').fill('AI');
    await page.locator('#search-form').evaluate(form => form.requestSubmit());
    await page.waitForFunction(() => document.querySelector('#search-results').getAttribute('aria-busy') === 'false');
    assert.equal(guestQuery, 'AI');
    await page.locator('.clear-search').click();
    await page.waitForFunction(() => document.querySelector('#search-results').getAttribute('aria-busy') === 'false');
    assert.equal(await page.locator('#search-form').isVisible(), true);
    assert.equal(await page.locator('#query').inputValue(), '');
    assert.equal(guestQuery, '');
    for (const returnPath of ['back', 'link']) {
      await page.evaluate(() => localStorage.setItem('dait_access_token', 'test-token'));
      await page.reload();
      await page.locator('#logout-btn').waitFor();
      await page.locator('.sidebar a[href="/settings.html"]').click();
      await page.locator('#logout-btn').click();
      await page.locator('#auth-required').waitFor();
      if (returnPath === 'back') await page.goBack();
      else await page.locator('#auth-required a').click();
      await page.locator('#login-open').waitFor();
      assert.equal(await page.locator('#search-form').isVisible(), true, returnPath);
      assert.equal(await page.evaluate(() => localStorage.getItem('dait_access_token')), null);
    }
    await page.evaluate(() => {
      const form = document.querySelector('#search-form');
      form.setAttribute('data-member-only', ''); form.hidden = true;
      window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true }));
    });
    await page.locator('#search-form:visible').waitFor();
    assert.equal(await page.locator('#search-form').getAttribute('data-member-only'), null);
  } finally { await browser.close(); }
});

test('first login invitation is optional and saved interests become expandable chips', async () => {
  const browser = await launchBrowser();
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    const choices = [
      { code: 'ai.models', name: '모델·연구', group: 'ai' }, { code: 'ai.agents', name: 'AI 에이전트', group: 'ai' },
      { code: 'ai.devtools', name: '개발 도구', group: 'ai' }, { code: 'ai.opensource', name: '오픈소스·로컬 모델', group: 'ai' },
      { code: 'ai.infra', name: 'AI 인프라', group: 'ai' }, { code: 'economy.industry', name: '산업 동향', group: 'economy' },
      { code: 'economy.business', name: '기업·경영', group: 'economy' }
    ];
    let selected = [], first = true, lastQuery;
    await page.route('http://dait.test/**', async route => {
      const req = route.request(), url = new URL(req.url());
      if (url.pathname === '/v1/auth/login') { const welcome = first; first = false; return route.fulfill({ json: { tokens: { access_token: 'new-account' }, onboarding_required: welcome } }); }
      if (url.pathname === '/v1/me/session') return route.fulfill({ json: { authenticated: true, user: { email: 'new@example.com', nickname: '하늘' }, interests: selected } });
      if (url.pathname === '/v1/interests/catalog') return route.fulfill({ json: { groups: ['ai', 'economy'].map(group => ({ group, group_name: group, interests: choices.filter(item => item.group === group) })) } });
      if (url.pathname === '/v1/me/interests') { if (req.method() === 'PUT') selected = choices.filter(item => req.postDataJSON().interests.includes(item.code)); return route.fulfill({ json: { interests: selected } }); }
      if (url.pathname === '/v1/me/settings') return route.fulfill({ json: { default_count: 10, keywords: [], in_app_notice: true, email_notice: false } });
      if (url.pathname === '/v1/me/schedules') return route.fulfill({ json: { items: [] } });
      if (url.pathname === '/v1/news/activity') return route.fulfill({ json: { total: 0, counts: { AI: 0, ECONOMY: 0, POLITICS: 0 }, read_ids: [] } });
      if (url.pathname === '/v1/news') { lastQuery = url; return route.fulfill({ json: { items: [], page: { has_more: false }, meta: { total_visible: 0 } } }); }
      const name = url.pathname === '/' ? 'index.html' : url.pathname.replace(/^\/mockup\//, '').replace(/^\//, '');
      const file = path.join(root, name);
      if (!fs.existsSync(file)) return route.fulfill({ status: 404 });
      return route.fulfill({ body: fs.readFileSync(file), contentType: name.endsWith('.css') ? 'text/css' : name.endsWith('.js') ? 'text/javascript' : 'text/html; charset=utf-8' });
    });
    await page.goto('http://dait.test/');
    await page.locator('#login-open').click();
    await page.locator('#auth-email').fill('new@example.com');
    await page.locator('#auth-password').fill('fixture-password');
    await page.locator('#auth-form [type=submit]').click();
    await page.waitForURL('**/settings.html?welcome=1#interests');
    await page.locator('#interest-fields:not([disabled])').waitFor();
    assert.equal(await page.locator('#welcome-interests').isVisible(), true);
    await page.locator('#welcome-interests a').click();
    await page.locator('[data-category=AI]').waitFor();
    assert.equal(await page.locator('[data-interest-chip]').count(), 0);
    await page.locator('.sidebar a[href="/settings.html#interests"]').click();
    await page.locator('#interest-fields:not([disabled])').waitFor();
    await page.locator('#interests-all').click();
    await page.locator('#interests-form [type=submit]').click();
    await page.getByText('관심사를 저장했습니다.', { exact: true }).waitFor();
    await page.locator('a.brand').click();
    await page.locator('[data-interest-chip]').first().waitFor();
    assert.equal(await page.locator('[data-interest-chip]:visible').count(), 5);
    await page.locator('[data-interest-expand]').click();
    assert.equal(await page.locator('[data-interest-chip]:visible').count(), 7);
    await page.locator('[data-interest-chip="economy.industry"]').click();
    await page.waitForFunction(() => document.querySelector('#search-results').getAttribute('aria-busy') === 'false');
    assert.equal(lastQuery.searchParams.get('personalized'), 'true');
    assert.equal(lastQuery.searchParams.get('interest'), 'economy.industry');
    assert.equal(lastQuery.searchParams.has('q'), false);
    await page.locator('[data-category=""]').click();
    await page.waitForFunction(() => document.querySelector('#search-results').getAttribute('aria-busy') === 'false');
    assert.equal(lastQuery.searchParams.has('q'), false);
    assert.equal(lastQuery.searchParams.has('interest'), false);
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.goto('http://dait.test/settings.html');
      await page.locator('#interest-fields:not([disabled])').waitFor();
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      if (process.env.DAIT_UI_SHOTS) await page.screenshot({ path: path.join(process.env.DAIT_UI_SHOTS, 'settings-workspace-' + width + '.png'), fullPage: true });
    }
    assert.deepEqual(errors, []);
  } finally { await browser.close(); }
});

test('withdrawal succeeds only after password confirmation', async () => {
  const browser = await launchBrowser();
  try {
    const page = await browser.newPage();
    await page.addInitScript(() => { if (!sessionStorage.getItem('fixture-once')) { localStorage.setItem('dait_access_token','fixture'); localStorage.setItem('dait_remembered_email','test@example.com'); sessionStorage.setItem('fixture-once','1'); } });
    let calls = 0;
    await page.route('http://dait.test/**', async route => {
      const req = route.request(), url = new URL(req.url());
      if (url.pathname === '/v1/me/session') return route.fulfill({ json: { authenticated:true,user:{email:'test@example.com'} } });
      if (url.pathname === '/v1/me' && req.method() === 'DELETE') { calls++; assert.equal(req.postDataJSON().password,'fixture-password'); return route.fulfill({ json: { result:'done' } }); }
      if (url.pathname === '/v1/interests/catalog') return route.fulfill({ json: { groups:[] } });
      if (url.pathname === '/v1/me/interests') return route.fulfill({ json: { interests:[] } });
      if (url.pathname === '/v1/me/settings') return route.fulfill({ json: { default_count:10,keywords:[],in_app_notice:true,email_notice:false } });
      if (url.pathname === '/v1/me/schedules') return route.fulfill({ json: { items:[] } });
      if (url.pathname === '/v1/news') return route.fulfill({ json: { items:[],page:{has_more:false},meta:{total_visible:0} } });
      const name = url.pathname === '/' ? 'index.html' : url.pathname.replace(/^\/mockup\//,'').replace(/^\//,'');
      const file=path.join(root,name); if(!fs.existsSync(file)) return route.fulfill({status:404});
      return route.fulfill({body:fs.readFileSync(file),contentType:name.endsWith('.css')?'text/css':name.endsWith('.js')?'text/javascript':'text/html; charset=utf-8'});
    });
    await page.goto('http://dait.test/settings.html');
    await page.locator('#withdraw-open').click();
    await page.locator('#withdraw-cancel').click();
    assert.equal(calls,0);
    await page.locator('#withdraw-open').click();
    await page.locator('#withdraw-password').fill('fixture-password');
    await page.locator('#withdraw-form [type=submit]').click();
    await page.waitForURL('**/?ui=20261112-search*');
    await page.locator('#login-open').waitFor();
    assert.equal(calls,1);
    assert.equal(await page.evaluate(()=>localStorage.getItem('dait_access_token')),null);
    assert.equal(await page.evaluate(()=>localStorage.getItem('dait_remembered_email')),null);
  } finally { await browser.close(); }
});

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
    assert.equal(requests.at(-1).searchParams.get('q'), 'AI');
    assert.equal(await page.locator('#query').inputValue(), 'AI');
    await page.locator('#query').fill('');
    await page.waitForFunction(() => document.querySelector('#search-results').getAttribute('aria-busy') === 'false');
    assert.equal(requests.at(-1).searchParams.get('q'), 'AI');
    assert.equal(await page.locator('#query').inputValue(), '');
    await page.locator('[data-category=ECONOMY]').click();
    await page.waitForFunction(() => document.querySelector('#search-results').getAttribute('aria-busy') === 'false');
    assert.equal(requests.at(-1).searchParams.get('q'), 'AI');
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
    await checkLayout('#auth-terms');
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
      await checkLayout('#auth-terms');
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
    let selected = ['ai.models'];
    let failCatalog = false, failSave = false, catalogCalls = 0, interestSaves = 0;
    const item = { code: 'ai.models', name: '모델·연구', group: 'ai' };
    let settings = { default_count: 10, keywords: ['AI'], in_app_notice: true, email_notice: false };
    let schedules = [{ id: 's1', local_time: '09:00', timezone: 'Asia/Seoul', enabled: false, criteria: { categories: ['ECONOMY'], source_ids: ['source-1'], keywords: ['<img src=x onerror=alert(1)>'] }, next_run_at: null }];
    let updatedSchedule;
    await page.route('http://dait.test/**', async route => {
      const req = route.request(), url = new URL(req.url()), method = req.method();
      if (url.pathname === '/v1/me/session') return route.fulfill({ json: { authenticated: true, user: { email: 'test@example.com' } } });
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
      if (url.pathname === '/v1/me/schedules/s1' && method === 'PATCH') { updatedSchedule = req.postDataJSON(); schedules[0] = { ...schedules[0], ...updatedSchedule }; return route.fulfill({ json: schedules[0] }); }
      const name = url.pathname.replace(/^\/mockup\//, '').replace(/^\//, '') || 'index.html';
      const file = path.join(root, name);
      if (!fs.existsSync(file)) return route.fulfill({ status: 404 });
      return route.fulfill({ body: fs.readFileSync(file), contentType: name.endsWith('.css') ? 'text/css' : name.endsWith('.js') ? 'text/javascript' : 'text/html; charset=utf-8' });
    });
    await page.goto('http://dait.test/settings.html');
    await page.locator('#interest-fields:not([disabled])').waitFor();
    assert.equal(await page.locator('#interest-count').textContent(), '1개 선택');
    assert.equal(await page.locator('.schedule-meta img').count(), 0);
    assert.match(await page.locator('.schedule-meta').textContent(), /<img/);
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
    await page.locator('.schedule-item').getByRole('button', { name: '수정', exact: true }).click();
    await page.locator('#sched-time').fill('10:30');
    await page.locator('#sched-submit').click();
    await page.getByText('예약을 수정했습니다.', { exact: true }).waitFor();
    assert.equal(updatedSchedule.enabled, false);
    assert.deepEqual(updatedSchedule.criteria.categories, ['ECONOMY']);
    assert.deepEqual(updatedSchedule.criteria.source_ids, ['source-1']);
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
      assert.equal(await page.getByRole('link', { name: '메인으로 돌아가기' }).getAttribute('href'), '/');
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
    assert.equal(searches.at(-1).searchParams.get('q'), '산업 동향');
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
    assert.equal(searches.at(-1).searchParams.get('q'), '교육');
    await page.evaluate(() => localStorage.removeItem('dait_access_token'));
    await page.reload();
    await page.locator('#signup-open').click();
    await page.locator('#auth-email').fill('join@example.com');
    await page.locator('#auth-password').fill('Strong-test-password!');
    await page.locator('#auth-password-confirm').fill('Strong-test-password!');
    await page.locator('#auth-terms').check();
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
    await page.locator('#auth-terms').check();
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
    await page.goto('http://dait.test/?sort=rank&category=AI&q=ignored');
    await page.getByText('최신 뉴스 10건', { exact: true }).waitFor();
    assert.equal(await page.locator('.news-card').count(), 10);
    assert.equal(await page.locator('#sort').count(), 0);
    assert.equal(await page.locator('#load-more').isVisible(), false);
    assert.equal(requested.searchParams.get('sort'), 'latest');
    assert.equal(requested.searchParams.has('category'), false);
    assert.equal(requested.searchParams.has('q'), false);
    for (const width of [1280, 390]) {
      await page.setViewportSize({ width, height: 900 });
      for (const selector of ['#sidebar-categories', '#search-form', '#categories', '#topic-select', '.mobile-tab[href="/?category=AI"]']) {
        assert.equal(await page.locator(selector).isVisible(), false, selector);
      }
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    }
    await page.locator('#load-more').evaluate(el => el.click());
    assert.equal(await page.locator('.news-card').count(), 10);
  } finally { await browser.close(); }
});

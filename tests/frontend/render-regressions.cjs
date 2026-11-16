// Run from the repository root: node tests/frontend/render-regressions.cjs
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const app = fs.readFileSync('src/frontend/public/app.js', 'utf8');
const news = fs.readFileSync('src/frontend/public/news-ui.js', 'utf8');
const settings = fs.readFileSync('src/frontend/public/settings-ui.js', 'utf8');
const memory = () => {
  const values = new Map();
  return {getItem: k => values.get(k) || null, setItem: (k, v) => values.set(k, v), removeItem: k => values.delete(k)};
};

async function sessionTests() {
  const localStorage = memory(), sessionStorage = memory();
  let calls = 0;
  const context = () => {
    const ctx = {window: {}, localStorage, sessionStorage, document: {createElement: () => ({}), head: {appendChild() {}}},
      fetch: async () => { calls++; return {ok: true, status: 200, json: async () => ({authenticated: true, user: {id: 'a'}, interests: []})}; }};
    vm.createContext(ctx);
    vm.runInContext(app.slice(0, app.indexOf('  function escapeHtml')) +
      'window.test = {currentUser, setTokens, clearTokens, api, waitForGoogle: p => {googleReturnPromise = p;}};})();', ctx);
    return ctx.window.test;
  };
  const a = context();
  let finish;
  a.waitForGoogle(new Promise(resolve => {finish = resolve;}));
  const waiting = a.currentUser();
  await Promise.resolve();
  assert.equal(calls, 0, 'Google exchange must finish before guest/member initialization');
  a.setTokens({access_token: 'account-a'}); finish();
  assert.equal((await waiting).id, 'a');
  assert.equal((await context().currentUser()).id, 'a');
  assert.equal(calls, 1, 'Navigation reuses the recently verified session');
  a.clearTokens();
  assert.equal(await context().currentUser(), null);
  assert.equal(sessionStorage.getItem('dait_session_ui_v1'), null);
}

async function feedTests() {
  let finish, calls = 0;
  const ctx = {URL, location: {origin: 'https://test'}, responseCache: new Map(), pendingResponses: new Map(),
    feedScope: 'a', FEED_TTL: 900000, FEED_RETENTION: 86400000, persistFeedCache() {},
    DAIT: {api: async (_url, options) => {
      calls++; assert.equal(options.signal, undefined, 'Chip switching must not abort a shared fetch');
      await new Promise(resolve => {finish = resolve;});
      return {ok: true, json: async () => ({items: [{id: 'one'}]})};
    }}};
  vm.createContext(ctx);
  vm.runInContext(news.slice(news.indexOf('  async function json('), news.indexOf('  function card(')) + 'globalThis.read = json;', ctx);
  const first = ctx.read('/v1/news?interest=ai.agents', {aborted: true});
  const second = ctx.read('/v1/news?interest=ai.agents', {});
  assert.equal(calls, 1, 'Repeated chip requests share one in-flight response');
  finish(); await Promise.all([first, second]);
  await ctx.read('/v1/news?interest=ai.agents', {});
  assert.equal(calls, 1, 'A completed response is immediately reusable');
  const pending = ctx.read('/v1/news?interest=ai.models', {});
  ctx.feedScope = 'b'; ctx.responseCache.clear(); finish(); await pending;
  assert.equal(ctx.responseCache.size, 0, 'An old account response must not populate the new account cache');
}

function passwordTests() {
  const make = () => ({dataset: {}, events: {}, attrs: {}, children: [],
    setAttribute(k, v) {this.attrs[k] = v;}, addEventListener(k, fn) {this.events[k] = fn;},
    append(...children) {this.children.push(...children);}, before(wrapper) {this.wrapper = wrapper;}, focus() {}});
  const input = Object.assign(make(), {id: 'withdraw-password', type: 'password'});
  const ctx = {document: {createElement: make}};
  vm.createContext(ctx);
  vm.runInContext(app.slice(app.indexOf('  function attachCapsLockHints('), app.indexOf('  function openAuthDialog(')) + 'globalThis.attach = attachCapsLockHints;', ctx);
  const form = {querySelectorAll: () => [input]};
  ctx.attach(form); ctx.attach(form);
  assert.equal(input.wrapper.children.length, 3, 'Enhancement is idempotent');
  const [, hint, toggle] = input.wrapper.children;
  input.events.keydown({type: 'keydown', key: 'A', getModifierState: () => true});
  assert.equal(hint.hidden, false, 'Caps Lock warns after typing');
  input.events.keyup({type: 'keyup', key: 'CapsLock', getModifierState: () => false});
  assert.equal(hint.hidden, true);
  toggle.events.click(); assert.equal(input.type, 'text'); assert.equal(toggle.attrs['aria-pressed'], 'true');
  toggle.events.click(); assert.equal(input.type, 'password');
}

function settingsTests() {
  let selected;
  const sections = ['schedule', 'interests', 'nickname-settings', 'account'].map((id, i) => ({id, getBoundingClientRect: () => ({top: i * 100})}));
  const ctx = {sectionScrollPending: true, clickedSection: '#nickname-settings',
    markSettingsSection: value => {selected = value;},
    window: {innerWidth: 1500, innerHeight: 800, scrollY: 1000},
    document: {documentElement: {scrollHeight: 1800}, getElementById: id => sections.find(s => s.id === id),
      querySelectorAll: () => sections.map(s => ({hash: '#' + s.id})),
      querySelector: () => ({getBoundingClientRect: () => ({bottom: 100})})}};
  vm.createContext(ctx);
  const start = settings.indexOf('  function updateSettingsSectionFromScroll()');
  vm.runInContext(settings.slice(start, settings.indexOf("  window.addEventListener('scroll'", start)) + 'updateSettingsSectionFromScroll();', ctx);
  assert.equal(selected, '#nickname-settings', 'Bottom-of-page detection must preserve the clicked nickname section');
  ctx.clickedSection = ''; vm.runInContext('updateSettingsSectionFromScroll();', ctx);
  assert.equal(selected, '#account', 'Manual scrolling resumes normal section tracking');
}

async function prefetchTests() {
  const calls = [];
  let active = 0, peak = 0;
  const chips = Array.from({length: 10}, (_, i) => ({hidden: false, closest: () => null,
    dataset: {interestChip: (i < 5 ? '' : 'en.') + 'ai.' + i, chipLanguage: i < 5 ? 'ko' : 'en'}}));
  const ctx = {URLSearchParams, guest: false, globalSearch: false, personalizedChips: true, feedScope: 'a',
    document: {hidden: false, querySelectorAll: () => chips},
    json: async url => {
      calls.push(url); active++; peak = Math.max(peak, active);
      await new Promise(setImmediate); active--;
      return {page: {has_more: !new URL(url, 'https://test').searchParams.has('cursor'), next_cursor: 'next'}};
    }};
  vm.createContext(ctx);
  vm.runInContext(news.slice(news.indexOf('  let prefetchTimer;'), news.indexOf('  async function load(')) + 'globalThis.warm = prefetchInterests;', ctx);
  ctx.warm(new URLSearchParams('page_size=4&category=AI&topic=ai.old&cursor=old'), {signal: {aborted: true}});
  for (let i = 0; i < 30; i++) await new Promise(setImmediate);
  assert.equal(calls.length, 20, 'Warm both four-article halves for all visible regional chips');
  assert.equal(peak, 2, 'Background warmup limits concurrent requests');
  for (const url of calls) {
    const q = new URL(url, 'https://test').searchParams;
    assert.equal(q.has('category'), false); assert.equal(q.has('topic'), false);
    assert.notEqual(q.get('cursor'), 'old');
    assert.equal(q.get('language'), q.get('interest').startsWith('en.') ? 'en' : 'ko');
  }
}

function sidebarTests() {
  const make = code => ({dataset: {topicGroup: code, englishGroup: code}, active: false,
    classList: {toggle() {}}, parentElement: {classList: {toggle() {}}},
    setAttribute(_key, value) {this.active = value === 'true';}});
  const ko = ['AI', 'ECONOMY', 'POLITICS'].map(make), en = ['AI', 'ECONOMY', 'POLITICS'].map(make);
  // Domestic headings use their visual active class instead of aria-pressed.
  ko.forEach(button => {button.classList.toggle = (_key, value) => {button.active = value;};});
  const ctx = {language: 'ko', selectedInterest: 'economy.finance', sidebarTopic: '', category: '', topics: {},
    $: () => ({value: ''}), document: {querySelectorAll: selector => selector === '[data-topic-group]' ? ko : selector === '[data-english-group]' ? en : []}};
  vm.createContext(ctx);
  vm.runInContext(news.slice(news.indexOf('  function syncSidebar()'), news.indexOf('  function buildSidebar()')) + 'globalThis.sync = syncSidebar;', ctx);
  ctx.sync(); assert(ko[1].active); assert(!ko[0].active);
  ctx.language = 'en'; ctx.selectedInterest = 'en.ai.agents'; ctx.sync();
  assert(en[0].active); assert(ko.every(button => !button.active));
}

(async () => {
  await sessionTests(); await feedTests(); await prefetchTests();
  passwordTests(); settingsTests(); sidebarTests();
  console.log('PASS: Google initialization ordering, navigation session cache, shared chip requests, account isolation, bounded regional prefetch, password controls, settings section tracking, regional sidebar selection');
})().catch(error => {console.error(error); process.exitCode = 1;});

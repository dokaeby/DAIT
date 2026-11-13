// Run: node tests/frontend/page-jump.cjs
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const source = fs.readFileSync('src/frontend/public/news-ui.js', 'utf8');
const nodes = new Map(), requests = [];
const node = id => {
  if (!nodes.has(id)) nodes.set(id, {value: '', textContent: '', disabled: false, attrs: {},
    setAttribute(k, v) {this.attrs[k] = v;}, addEventListener(k, fn) {this[k] = fn;}, focus() {}, select() {}, replaceChildren() {}});
  return nodes.get(id);
};
const ctx = {URLSearchParams, AbortController, Event, clearTimeout, setTimeout,
  btoa: text => Buffer.from(text).toString('base64'),
  DISPLAY_PAGE_SIZE: 8, PAGE_SIZE: '4', currentPage: 1, totalPages: 13, pageStart: null,
  cursor: null, busy: false, guest: false, listRequest: null, prefetchTimer: null,
  category: 'AI', shownCategory: 'AI', shownQuery: 'chip', shownHasResults: true,
  language: 'en', selectedInterest: 'en.ai.agents', sidebarTopic: '', personalizedChips: true,
  globalSearch: false, searchAllArticles: false, readIds: new Set(), $: node,
  window: {dispatchEvent() {}, scrollTo() {}}, history: {replaceState() {}},
  syncSidebar() {}, updateChips() {}, refreshReads() {}, prefetchInterests() {}, updateScrollControls() {},
  selectionTitle: () => 'AI Agents', card: item => item.id, escape: text => text,
  json: async url => {
    const parsed = new URL(url, 'https://test');
    if (parsed.pathname !== '/v1/news') return [];
    requests.push(parsed.searchParams);
    const offset = parsed.searchParams.has('cursor') ? JSON.parse(Buffer.from(parsed.searchParams.get('cursor'), 'base64url')).o : 0;
    const count = Math.min(4, 97 - offset);
    return {items: Array.from({length: Math.max(0, count)}, (_, i) => ({id: String(offset + i)})),
      meta: {total_visible: 97}, page: {has_more: offset + count < 97,
        next_cursor: Buffer.from(JSON.stringify({o: offset + count})).toString('base64url')}};
  }};
vm.createContext(ctx);
vm.runInContext(source.slice(source.indexOf('  function pageCursor('), source.indexOf('  let language =')) +
  source.slice(source.indexOf('  async function load('), source.indexOf("  $('query').value = (params")) +
  source.slice(source.indexOf("  $('page-jump-form').addEventListener"), source.indexOf("  $('news-list').addEventListener")), ctx);

(async () => {
  assert.equal(ctx.pageCursor(1), null);
  await ctx.load('jump', false, false, 10);
  assert.equal(ctx.currentPage, 10);
  assert.equal(ctx.totalPages, 13);
  assert.equal(JSON.parse(Buffer.from(requests[0].get('cursor'), 'base64url')).o, 72);
  assert.equal(JSON.parse(Buffer.from(requests[1].get('cursor'), 'base64url')).o, 76);
  for (const query of requests) {
    assert.equal(query.get('language'), 'en'); assert.equal(query.get('category'), 'AI');
    assert.equal(query.get('interest'), 'en.ai.agents'); assert.equal(query.get('q'), 'chip');
  }
  await ctx.load('prev'); assert.equal(ctx.currentPage, 9);
  await ctx.load('next'); assert.equal(ctx.currentPage, 10);
  await ctx.load('jump', false, false, 13);
  assert.equal(ctx.cursor, null, 'The final partial page has no next page');
  assert.equal(node('load-more').disabled, true);
  await ctx.load('jump', false, false, 1);
  assert.equal(node('load-previous').disabled, true);
  for (const value of ['', '0', '-1', '14', '2.5', 'abc', '1e1']) {
    const before = requests.length;
    node('page-jump-input').value = value;
    node('page-jump-form').submit({preventDefault() {}});
    assert.equal(requests.length, before);
    assert.equal(node('page-jump-input').attrs['aria-invalid'], 'true');
  }
  await ctx.load();
  assert.equal(ctx.currentPage, 1, 'Changing a filter resets to page one');
  console.log('PASS: direct offset navigation, search/region/topic preservation, previous/next after jump, final partial page, invalid input, filter reset');
})().catch(error => {console.error(error); process.exitCode = 1;});

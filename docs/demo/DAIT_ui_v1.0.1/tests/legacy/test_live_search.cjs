// 실제 페이지 스크립트의 입력 이벤트와 응답 순서를 브라우저 없이 점검합니다.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

class Element {
  constructor(value = '') { this.value = value; this.events = {}; this.attributes = {}; }
  addEventListener(name, handler) { this.events[name] = handler; }
  emit(name, event = {}) { return this.events[name]?.({preventDefault() {}, ...event}); }
  setAttribute(name, value) { this.attributes[name] = value; }
  removeAttribute(name) { delete this.attributes[name]; }
  replaceWith(next) { elements.set('#search-results', next); }
  focus() {}
}
const elements = new Map();
for (const key of ['#detail', 'form.search', '#query', '#search-status',
  'form[action="/login"] input[name="q"]', '#search-results', '#clear-search', '.card-close']) {
  elements.set(key, new Element());
}
elements.get('form.search').action = 'http://127.0.0.1:8000/';
const requests = [];
let address = '/';
const document = {
  querySelector: key => elements.get(key),
  addEventListener() {},
  importNode: node => node,
};
const context = {
  document, URL, AbortController,
  history: {replaceState: (_, __, url) => { address = url; }},
  // Abort를 무시하는 응답도 늦게 도착하도록 해 최신 응답 검사까지 확인합니다.
  fetch: (url, options) => new Promise(resolve => requests.push({url: new URL(url), options, resolve})),
  DOMParser: class {
    parseFromString(text) {
      const query = JSON.parse(text).query;
      const next = new Element();
      next.query = query;
      return {querySelector: selector => selector === '#search-results' ? next : {value: query}};
    }
  },
};
const source = fs.readFileSync(path.join(__dirname, 'app.py'), 'utf8');
const script = source.match(/<script>([\s\S]*?)<\/script>/)[1].replaceAll('{{', '{').replaceAll('}}', '}');
vm.runInNewContext(script, context);
async function respond(index, query) {
  requests[index].resolve({ok: true, text: async () => JSON.stringify({query})});
  await new Promise(resolve => setImmediate(resolve));
}

(async () => {
  const input = elements.get('#query');
  input.value = '반도체'; input.emit('input');
  assert.equal(requests.length, 1, 'Input alone must immediately request search.');
  input.value = '반도'; input.emit('input');
  assert.equal(requests.length, 2, 'Deletion must immediately request search.');
  assert.equal(requests[0].options.signal.aborted, true);
  await respond(1, '반도');
  await respond(0, '반도체');
  assert.equal(elements.get('#search-results').query, '반도');

  input.value = '반'; input.emit('input'); await respond(2, '반');
  assert.equal(elements.get('#search-results').query, '반');
  input.value = ''; input.emit('input'); await respond(3, '');
  assert.equal(requests[3].url.search, '');
  assert.equal(elements.get('#search-results').query, '');
  assert.equal(address, '/');

  input.value = '반'; input.emit('input', {isComposing: true});
  assert.equal(requests.length, 5, 'Korean composition input must also request search.');
  await respond(4, '반');
  elements.get('form.search').emit('submit');
  assert.equal(requests.length, 6, 'Search button or Enter must also refresh current input.');
  await respond(5, '반');
  elements.get('#clear-search').emit('click'); await respond(6, '');
  assert.equal(input.value, '');
  assert.equal(elements.get('form[action="/login"] input[name="q"]').value, '');
  console.log('Live search: deletion, clear, stale response and Korean composition checks passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });

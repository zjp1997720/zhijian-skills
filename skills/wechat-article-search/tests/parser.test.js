const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const {
  extractRedirectUrlFromHtml,
  parseArticlesFromSearchHtml,
  parseCliArgs,
} = require('../scripts/search_wechat.js');

test('parses committed Sogou fixture without network access', () => {
  const fixture = fs.readFileSync(path.join(__dirname, 'fixtures/search-results.html'), 'utf8');
  const articles = parseArticlesFromSearchHtml(fixture, 10);
  assert.equal(articles.length, 1);
  assert.equal(articles[0].title, 'Codex 模型路由实战');
  assert.equal(articles[0].source, '智见 AI');
  assert.equal(articles[0].url, 'https://weixin.sogou.com/link?url=demo');
});

test('extracts both meta and assembled JavaScript redirect URLs', () => {
  assert.equal(
    extractRedirectUrlFromHtml('<meta http-equiv="refresh" content="0; url=https://mp.weixin.qq.com/s/a">'),
    'https://mp.weixin.qq.com/s/a',
  );
  assert.equal(
    extractRedirectUrlFromHtml("var url='';url += 'https://mp.weixin.';url += 'qq.com/s/b';window.location.replace(url)"),
    'https://mp.weixin.qq.com/s/b',
  );
});

test('parses CLI options deterministically', () => {
  assert.deepEqual(parseCliArgs(['Codex', '--num', '3', '--output', 'out.json', '--resolve-url']), {
    query: 'Codex',
    num: 3,
    output: 'out.json',
    resolveRealUrl: true,
  });
});

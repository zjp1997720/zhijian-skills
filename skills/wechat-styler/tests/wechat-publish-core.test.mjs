import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildInjectScript,
  buildProbeScript,
  extractArticleDocument,
} from '../scripts/wechat-publish-core.mjs';

test('extracts the shared article root when generated HTML exposes the contract', () => {
  const html = '<html><head><title>示例</title><meta name="description" content="摘要"></head><body><section data-wechat-root="article"><section><img src="https://img.test/a.png" alt="A"></section></section><aside>忽略</aside></body></html>';
  const result = extractArticleDocument(html);

  assert.equal(result.title, '示例');
  assert.equal(result.summary, '摘要');
  assert.equal(result.imageUrls.length, 1);
  assert.match(result.content, /^<section data-wechat-root="article">/);
  assert.doesNotMatch(result.content, /忽略/);
});

test('falls back to the first balanced article section for legacy output', () => {
  const html = '<body><section style="background-color:#fff"><section><p>正文</p></section></section><p>尾部</p></body>';
  const result = extractArticleDocument(html);

  assert.match(result.content, /正文/);
  assert.doesNotMatch(result.content, /尾部/);
});

test('builds raw UTF-8 HTML injection without parsing the HTML as JSON', () => {
  const script = buildInjectScript('<section><p>中文</p></section>');

  assert.match(script, /new TextDecoder\("utf-8"\)\.decode\(bytes\)/);
  assert.doesNotMatch(script, /JSON\.parse\(new TextDecoder/);
});

test('probes the body editor without selecting the title ProseMirror', () => {
  const script = buildProbeScript();

  assert.match(script, /title-editor__input/);
  assert.match(script, /rich_media_content/);
  assert.match(script, /bodyEditor/);
});

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildMetadataVerification,
  buildInjectScript,
  buildProbeScript,
  buildVerifyScript,
  extractArticleDocument,
  hardenCodeBlockLineBreaks,
} from '../scripts/wechat-publish-core.mjs';

test('extracts the shared article root when generated HTML exposes the contract', () => {
  const html = '<html><head><title>示例</title><meta name="description" content="摘要"></head><body><section data-wechat-root="article"><section><img src="https://img.test/a.png" alt="A"></section></section><aside>忽略</aside></body></html>';
  const result = extractArticleDocument(html);

  assert.equal(result.title, '示例');
  assert.equal(result.summary, '摘要');
  assert.equal(result.imageUrls.length, 1);
  assert.deepEqual(result.nonHttpImageUrls, []);
  assert.match(result.content, /^<section data-wechat-root="article">/);
  assert.doesNotMatch(result.content, /忽略/);
});

test('identifies local-preview image paths before WeChat injection', () => {
  const html = '<section data-wechat-root="article"><img src="图片和附件/封面.png"><img src="https://img.test/body.png"></section>';
  const result = extractArticleDocument(html);

  assert.deepEqual(result.nonHttpImageUrls, ['图片和附件/封面.png']);
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

test('hardens legacy code-block newlines before injection and records the break contract', () => {
  const legacy = '<section data-wechat-root="article"><pre><code>第一行\n第二行\n\n第四行</code></pre></section>';
  const hardened = hardenCodeBlockLineBreaks(legacy);
  const result = extractArticleDocument(legacy);

  assert.match(hardened, /<pre><code>第一行<br>第二行<br><br>第四行<\/code><\/pre>/);
  assert.match(result.content, /第一行<br>第二行<br><br>第四行/);
  assert.equal(result.codeBlockCount, 1);
  assert.equal(result.codeBlockBreakCount, 3);
});

test('probes the body editor without selecting the title ProseMirror', () => {
  const script = buildProbeScript();

  assert.match(script, /title-editor__input/);
  assert.match(script, /rich_media_content/);
  assert.match(script, /bodyEditor/);
});

test('treats qlogo and qpic hosts as settled WeChat images', () => {
  const script = buildVerifyScript();

  assert.match(script, /mmbiz\.qpic\.cn/);
  assert.match(script, /mmbiz\.qlogo\.cn/);
  assert.match(script, /wx\.qlogo\.cn/);
  assert.match(script, /trustedImageHosts/);
});

test('verifies fenced-code hard breaks after WeChat persistence', () => {
  const script = buildVerifyScript();

  assert.match(script, /bodyEditor\.querySelectorAll\("pre"\)/);
  assert.match(script, /codeBlockBreakCount/);
  assert.match(script, /querySelectorAll\("br"\)/);
});

test('verifies Xiaolan as native SVG paths instead of removable image references', () => {
  const html = '<section data-wechat-root="article"><svg><g data-xiaolan-render="native-svg-pixels"><path d="M0 0h1v1z"/></g></svg></section>';
  const result = extractArticleDocument(html);
  const script = buildVerifyScript();

  assert.equal(result.svgImageCount, 0);
  assert.equal(result.xiaolanNativeFrameCount, 1);
  assert.match(script, /svg image/);
  assert.match(script, /data-xiaolan-render="native-svg-pixels"/);
  assert.match(script, /svg path/);
});

test('summary verification distinguishes match, mismatch, missing readback and not requested', () => {
  assert.deepEqual(buildMetadataVerification({ summary: '摘要' }, { summary: '摘要' }),
    { summaryChecked: true, expectedSummary: '摘要', summaryMatches: true });
  assert.equal(buildMetadataVerification({ summary: '另一个摘要' }, { summary: '摘要' }).summaryMatches, false);
  assert.equal(buildMetadataVerification(null, { summary: '摘要' }).summaryMatches, false);
  assert.equal(buildMetadataVerification({ summary: '' }, { summary: '' }).summaryMatches, true);
  assert.equal(buildMetadataVerification({ summary: '旧摘要' }, { summary: '' }).summaryMatches, false);
  assert.deepEqual(buildMetadataVerification({ summary: '保留原摘要' }, {}),
    { summaryChecked: false, expectedSummary: null, summaryMatches: null });
});

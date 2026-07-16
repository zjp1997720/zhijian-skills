import assert from 'node:assert/strict';
import test from 'node:test';

import {
  findRemoteImageUrls,
  replaceImageUrls,
  shouldOptimizeImage,
} from '../scripts/wechat-image-pipeline.mjs';

test('detects an oversized remote image when it exceeds the byte limit', () => {
  assert.equal(shouldOptimizeImage(15 * 1024 * 1024, 2 * 1024 * 1024), true);
  assert.equal(shouldOptimizeImage(600 * 1024, 2 * 1024 * 1024), false);
});

test('collects only external content images that still need WeChat transfer', () => {
  const html = '<img src="https://img.test/a.png"><img src="https://mmbiz.qpic.cn/b.png"><img src="data:image/png;base64,abc">';

  assert.deepEqual(findRemoteImageUrls(html), ['https://img.test/a.png']);
});

test('replaces every occurrence of an optimized image URL', () => {
  const html = '<img src="https://img.test/a.png"><a href="https://img.test/a.png">A</a>';
  const mapping = new Map([['https://img.test/a.png', 'https://cdn.test/a.jpg']]);

  assert.equal(replaceImageUrls(html, mapping), '<img src="https://cdn.test/a.jpg"><a href="https://cdn.test/a.jpg">A</a>');
});

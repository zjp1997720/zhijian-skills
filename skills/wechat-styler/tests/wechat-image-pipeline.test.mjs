import assert from 'node:assert/strict';
import test from 'node:test';

import {
  assertDistinctUploadedUrls,
  findRemoteImageUrls,
  gifOptimizationProfiles,
  isGifImageUrl,
  optimizedFilenameForUrl,
  optimizedGifFilenameForUrl,
  optimizeLocalGif,
  optimizeContentImages,
  replaceImageUrls,
  shouldOptimizeImage,
} from '../scripts/wechat-image-pipeline.mjs';
import { isWeChatHostedImageUrl } from '../scripts/wechat-image-hosts.mjs';

test('detects an oversized remote image when it exceeds the byte limit', () => {
  assert.equal(shouldOptimizeImage(15 * 1024 * 1024, 2 * 1024 * 1024), true);
  assert.equal(shouldOptimizeImage(600 * 1024, 2 * 1024 * 1024), false);
});

test('collects only external content images that still need WeChat transfer', () => {
  const html = [
    '<img src="https://img.test/a.png">',
    '<img src="https://mmbiz.qpic.cn/b.png">',
    '<img src="https://mmbiz.qlogo.cn/c.png">',
    '<img src="https://wx.qlogo.cn/d.png">',
    '<img src="data:image/png;base64,abc">',
  ].join('');

  assert.deepEqual(findRemoteImageUrls(html), ['https://img.test/a.png']);
});

test('uses an exact WeChat image-host allowlist', () => {
  assert.equal(isWeChatHostedImageUrl('https://mmbiz.qlogo.cn/a.png'), true);
  assert.equal(isWeChatHostedImageUrl('https://mmbiz.qpic.cn/a.png'), true);
  assert.equal(isWeChatHostedImageUrl('https://evil-mmbiz.qpic.cn/a.png'), false);
  assert.equal(isWeChatHostedImageUrl('not a URL'), false);
});

test('replaces every occurrence of an optimized image URL', () => {
  const html = '<img src="https://img.test/a.png"><a href="https://img.test/a.png">A</a>';
  const mapping = new Map([['https://img.test/a.png', 'https://cdn.test/a.jpg']]);

  assert.equal(replaceImageUrls(html, mapping), '<img src="https://cdn.test/a.jpg"><a href="https://cdn.test/a.jpg">A</a>');
});

test('uses a stable unique upload filename for each source URL', () => {
  const first = optimizedFilenameForUrl('https://img.test/a.png');
  const second = optimizedFilenameForUrl('https://img.test/b.png');

  assert.match(first, /^wechat-[a-f0-9]{16}\.jpg$/);
  assert.equal(first, optimizedFilenameForUrl('https://img.test/a.png'));
  assert.notEqual(first, second);
});

test('recognizes GIF URLs and keeps a stable GIF upload filename', () => {
  assert.equal(isGifImageUrl('https://img.test/a.GIF?version=2'), true);
  assert.equal(isGifImageUrl('https://img.test/a.png'), false);
  assert.equal(isGifImageUrl('not a URL'), false);
  assert.match(optimizedGifFilenameForUrl('https://img.test/a.gif'), /^wechat-[a-f0-9]{16}\.gif$/);
});

test('rejects different source images that PicGo collapses to one URL', () => {
  assert.throws(
    () => assertDistinctUploadedUrls(new Map([
      ['https://img.test/a.png', 'https://cdn.test/source-wechat.jpg'],
      ['https://img.test/b.png', 'https://cdn.test/source-wechat.jpg'],
    ])),
    /same URL for different source images/,
  );
});

test('stops optimization before duplicate upload URLs can overwrite article images', async () => {
  const content = '<img src="https://img.test/a.png"><img src="https://img.test/b.png">';

  await assert.rejects(
    optimizeContentImages(content, {
      forceUrls: ['https://img.test/a.png', 'https://img.test/b.png'],
      optimizeRemote: async () => 'https://cdn.test/source-wechat.jpg',
    }),
    /retry with --no-optimize-images/,
  );
});

test('routes animated GIF URLs through optimization without changing them to JPEG', async () => {
  const content = [
    '<img src="https://img.test/a.gif">',
    '<img src="https://img.test/b.GIF">',
    '<img src="https://img.test/large.png">',
  ].join('');
  const optimizedUrls = [];

  const result = await optimizeContentImages(content, {
    forceUrls: [
      'https://img.test/a.gif',
      'https://img.test/b.GIF',
      'https://img.test/large.png',
    ],
    optimizeRemote: async (url) => {
      optimizedUrls.push(url);
      const extension = isGifImageUrl(url) ? '.gif' : '.jpg';
      return `https://cdn.test/${encodeURIComponent(url)}${extension}`;
    },
  });

  assert.deepEqual(optimizedUrls, [
    'https://img.test/a.gif',
    'https://img.test/b.GIF',
    'https://img.test/large.png',
  ]);
  assert.equal(result.mapping.size, 3);
  assert.match(result.content, /src="https:\/\/cdn\.test\/https%3A%2F%2Fimg\.test%2Fa\.gif\.gif"/);
  assert.match(result.content, /src="https:\/\/cdn\.test\/https%3A%2F%2Fimg\.test%2Fb\.GIF\.gif"/);
  assert.match(result.content, /src="https:\/\/cdn\.test\/https%3A%2F%2Fimg\.test%2Flarge\.png\.jpg"/);
});

test('reduces animated GIFs through bounded ffmpeg profiles until they fit', () => {
  const calls = [];
  const sizes = [3 * 1024 * 1024, 1500 * 1024];
  const target = optimizeLocalGif('/tmp/source.gif', {
    maxWidth: 1920,
    maxBytes: 2 * 1024 * 1024,
    workDir: '/tmp',
    targetFilename: 'wechat-test.gif',
    runCommand: (command, args) => calls.push({ command, args }),
    getFileSize: () => sizes.shift(),
  });

  assert.equal(target, '/tmp/wechat-test.gif');
  assert.equal(calls.length, 2);
  assert.equal(calls[0].command, 'ffmpeg');
  assert.match(calls[0].args.join(' '), /palettegen=max_colors=128/);
  assert.match(calls[0].args.join(' '), /paletteuse=/);
  assert.match(calls[0].args.join(' '), /-loop 0/);
  assert.match(calls[1].args.join(' '), /palettegen=max_colors=96/);
});

test('keeps GIF optimization profiles within the configured width', () => {
  assert.deepEqual(
    gifOptimizationProfiles(700).map(({ width }) => width),
    [700, 700, 700, 640, 480],
  );
});

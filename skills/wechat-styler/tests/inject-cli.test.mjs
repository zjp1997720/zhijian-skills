import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const skillRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

test('requires an explicit OpenCLI profile instead of using an author machine default', () => {
  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wechat-inject-profile-'));
  const htmlPath = path.join(workDir, 'article.html');
  fs.writeFileSync(htmlPath, '<html><body><section data-wechat-root="article"><p>正文</p></section></body></html>');

  const env = { ...process.env };
  delete env.OPENCLI_PROFILE;
  const result = spawnSync(process.execPath, [
    path.join(skillRoot, 'scripts/inject-to-wechat.mjs'),
    htmlPath,
    '--reuse-current',
    '--verify-only',
  ], { encoding: 'utf8', env });

  assert.equal(result.status, 1);
  assert.match(result.stderr, /--profile or OPENCLI_PROFILE is required/);
  fs.rmSync(workDir, { recursive: true, force: true });
});

test('verifies an existing editor through the CLI without writing', () => {
  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wechat-inject-cli-'));
  const binDir = path.join(workDir, 'bin');
  const htmlPath = path.join(workDir, 'article.html');
  const reportPath = path.join(workDir, 'report.json');
  fs.mkdirSync(binDir);
  fs.writeFileSync(htmlPath, '<html><body><section data-wechat-root="article"><p>正文</p></section></body></html>');
  const fakeOpencli = `#!/bin/sh
case "$*" in
  *"JSON.stringify({url: window.location.href})"*) printf '%s\\n' '{"url":"https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2"}' ;;
  *" state") printf 'URL: https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit\\n' ;;
  *"hasTitleEditor"*) printf '%s\\n' '{"readyState":"complete","hasTitleEditor":true,"hasBodyEditor":true,"editorCount":2,"bodyHeight":500}' ;;
  *) printf '%s\\n' '{"ok":true,"title":"测试标题","visibleTitle":"测试标题","summary":"","svgCount":0,"animateCount":0,"imageCount":0,"failedUrls":[],"pendingImages":[],"textLength":2,"firstText":"正文","lastText":"正文","titleOccurrencesInBody":0,"saved":true,"url":"https://mp.weixin.qq.com/cgi-bin/appmsg?token=secret"}' ;;
esac
`;
  const executable = path.join(binDir, 'opencli');
  fs.writeFileSync(executable, fakeOpencli, { mode: 0o755 });

  const result = spawnSync(process.execPath, [
    path.join(skillRoot, 'scripts/inject-to-wechat.mjs'),
    htmlPath,
    '--reuse-current',
    '--verify-only',
    '--profile',
    'test',
    '--title',
    '测试标题',
    '--report',
    reportPath,
  ], {
    encoding: 'utf8',
    env: { ...process.env, PATH: `${binDir}:${process.env.PATH}` },
  });

  assert.equal(result.status, 0, result.stderr || result.stdout);
  const report = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
  assert.equal(report.mode, 'verify-only');
  assert.equal(report.live.url.includes('secret'), false);
  fs.rmSync(workDir, { recursive: true, force: true });
});

test('replaces an existing cover from a local file and confirms a saved draft without a history field', () => {
  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wechat-inject-save-'));
  const binDir = path.join(workDir, 'bin');
  const htmlPath = path.join(workDir, 'article.html');
  const coverPath = path.join(workDir, 'cover.jpg');
  const coverFlag = path.join(workDir, 'cover-selected');
  const reportPath = path.join(workDir, 'report.json');
  fs.mkdirSync(binDir);
  fs.writeFileSync(htmlPath, '<html><body><section data-wechat-root="article"><p>正文</p><img src="https://mmbiz.qpic.cn/a.jpg"></section></body></html>');
  fs.writeFileSync(coverPath, Buffer.from([0xff, 0xd8, 0xff, 0xd9]));
  const fakeOpencli = `#!/bin/sh
case "$*" in
  *"JSON.stringify({url: window.location.href})"*) printf '%s\\n' '{"url":"https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2"}' ;;
  *" state") printf 'URL: https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit\\n' ;;
  *"hasTitleEditor"*) printf '%s\\n' '{"readyState":"complete","hasTitleEditor":true,"hasBodyEditor":true,"editorCount":2,"bodyHeight":500}' ;;
  *"bodyEditor.innerHTML"*) printf '%s\\n' '{"ok":true,"svgCount":0,"animateCount":0,"imageCount":1,"textLength":2}' ;;
  *"setValue"*) printf '%s\\n' '{"title":"测试标题","visibleTitle":"测试标题","summary":"测试摘要","author":""}' ;;
  *"pendingImages"*) printf '%s\\n' '{"ok":true,"title":"测试标题","visibleTitle":"测试标题","summary":"测试摘要","svgCount":0,"animateCount":0,"imageCount":1,"failedUrls":[],"pendingImages":[],"textLength":2,"firstText":"正文","lastText":"正文","titleOccurrencesInBody":0,"saved":true,"url":"https://mp.weixin.qq.com/cgi-bin/appmsg?appmsgid=42&token=secret"}' ;;
  *"cover area not found"*) if [ -f '${coverFlag}' ]; then printf '%s\\n' '{"ok":true,"hasImage":true,"sources":["https://mmbiz.qpic.cn/cover-new.jpg"]}'; else printf '%s\\n' '{"ok":true,"hasImage":true,"sources":["https://mmbiz.qpic.cn/cover-old.jpg"]}'; fi ;;
  *"cover trigger not found"*) printf '%s\\n' '{"ok":true,"hasBodyImage":false}' ;;
  *"new DataTransfer"*) printf '%s\\n' '{"ok":true,"filename":"cover.jpg","bytes":4}' ;;
  *"weui-desktop-img-picker__img-title"*) touch '${coverFlag}'; printf '%s\\n' '{"ok":true,"filename":"cover.jpg"}' ;;
  *"save button not found"*) printf '%s\\n' '{"ok":true}' ;;
  *"#history_pop tr"*) printf '%s\\n' '{"url":"https://mp.weixin.qq.com/cgi-bin/appmsg?appmsgid=42&token=secret","saved":true,"appmsgid":"42"}' ;;
  *) printf '%s\\n' '{"ok":true}' ;;
esac
`;
  const executable = path.join(binDir, 'opencli');
  fs.writeFileSync(executable, fakeOpencli, { mode: 0o755 });

  const result = spawnSync(process.execPath, [
    path.join(skillRoot, 'scripts/inject-to-wechat.mjs'),
    htmlPath,
    '--reuse-current',
    '--profile',
    'test',
    '--title',
    '测试标题',
    '--summary',
    '测试摘要',
    '--cover-file',
    coverPath,
    '--save-draft',
    '--report',
    reportPath,
  ], {
    encoding: 'utf8',
    env: { ...process.env, PATH: `${binDir}:${process.env.PATH}` },
  });

  assert.equal(result.status, 0, result.stderr || result.stdout);
  const report = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
  assert.equal(report.mode, 'saved-draft');
  assert.equal(report.verification.summaryMatches, true);
  assert.equal(report.verification.expectedSummary, '测试摘要');
  assert.equal(report.expected.images, 1);
  assert.equal(report.cover.strategy, 'uploaded-file');
  assert.deepEqual(report.save.history, []);
  assert.equal(report.save.confirmed, true);
  assert.equal(report.save.url.includes('secret'), false);
  fs.rmSync(workDir, { recursive: true, force: true });
});

test('writes an actionable failure report when cover selection cannot continue', () => {
  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wechat-inject-failure-'));
  const binDir = path.join(workDir, 'bin');
  const htmlPath = path.join(workDir, 'article.html');
  const reportPath = path.join(workDir, 'report.json');
  fs.mkdirSync(binDir);
  fs.writeFileSync(htmlPath, '<html><body><section data-wechat-root="article"><p>正文</p></section></body></html>');
  const fakeOpencli = `#!/bin/sh
case "$*" in
  *"JSON.stringify({url: window.location.href})"*) printf '%s\\n' '{"url":"https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2"}' ;;
  *" state") printf 'URL: https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit\\n' ;;
  *"hasTitleEditor"*) printf '%s\\n' '{"readyState":"complete","hasTitleEditor":true,"hasBodyEditor":true,"editorCount":2,"bodyHeight":500}' ;;
  *"bodyEditor.innerHTML"*) printf '%s\\n' '{"ok":true,"svgCount":0,"animateCount":0,"imageCount":0,"textLength":2}' ;;
  *"setValue"*) printf '%s\\n' '{"title":"测试标题","visibleTitle":"测试标题","summary":"","author":""}' ;;
  *"pendingImages"*) printf '%s\\n' '{"ok":true,"title":"测试标题","visibleTitle":"测试标题","summary":"","svgCount":0,"animateCount":0,"imageCount":0,"failedUrls":[],"pendingImages":[],"textLength":2,"firstText":"正文","lastText":"正文","titleOccurrencesInBody":0,"url":"https://mp.weixin.qq.com/cgi-bin/appmsg?token=secret"}' ;;
  *"cover area not found"*) printf '%s\\n' '{"ok":true,"hasImage":false,"sources":[]}' ;;
  *"cover trigger not found"*) printf '%s\\n' '{"ok":true,"hasBodyImage":false}' ;;
  *) printf '%s\\n' '{"ok":true}' ;;
esac
`;
  const executable = path.join(binDir, 'opencli');
  fs.writeFileSync(executable, fakeOpencli, { mode: 0o755 });

  const result = spawnSync(process.execPath, [
    path.join(skillRoot, 'scripts/inject-to-wechat.mjs'),
    htmlPath,
    '--reuse-current',
    '--profile',
    'test',
    '--title',
    '测试标题',
    '--sync-cover-from-body',
    '--report',
    reportPath,
  ], {
    encoding: 'utf8',
    env: { ...process.env, PATH: `${binDir}:${process.env.PATH}` },
  });

  assert.equal(result.status, 1);
  const report = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
  assert.equal(report.mode, 'failed');
  assert.equal(report.phase, 'cover');
  assert.match(report.error.details, /--cover-file/);
  assert.match(report.recovery.join(' '), /--cover-file/);
  assert.equal(report.live.url.includes('secret'), false);
  fs.rmSync(workDir, { recursive: true, force: true });
});

for (const [label, expected, actual, matches, exitCode] of [
  ['matched', '目标摘要', '目标摘要', true, 0],
  ['mismatched', '目标摘要', '旧摘要', false, 1],
  ['omitted', undefined, '保留摘要', null, 0],
  ['cleared', '', '', true, 0],
]) {
  test(`verify-only reports summary ${label} without writing the editor`, () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'wechat-summary-'));
    try {
      const bin = path.join(dir, 'bin'); fs.mkdirSync(bin);
      const html = path.join(dir, 'article.html');
      const reportPath = path.join(dir, 'report.json');
      fs.writeFileSync(html, '<section data-wechat-root="article"><p>正文</p></section>');
      const live = JSON.stringify({ ok: true, summary: actual, failedUrls: [], pendingImages: [] });
      fs.writeFileSync(path.join(bin, 'opencli'), `#!/bin/sh
case "$*" in
  *"JSON.stringify({url: window.location.href})"*) printf '%s\n' '{"url":"https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2"}' ;;
  *"hasTitleEditor"*) printf '%s\n' '{"readyState":"complete","hasTitleEditor":true,"hasBodyEditor":true,"editorCount":2,"bodyHeight":500}' ;;
  *"pendingImages"*) printf '%s\n' '${live}' ;;
  *) echo 'unexpected operation' >&2; exit 9 ;;
esac
`, { mode: 0o755 });
      const args = [path.join(skillRoot, 'scripts/inject-to-wechat.mjs'), html, '--profile', 'test', '--reuse-current', '--verify-only', '--editor-timeout', '1000', '--report', reportPath];
      if (expected !== undefined) args.push('--summary', expected);
      const result = spawnSync(process.execPath, args, { encoding: 'utf8', env: { ...process.env, PATH: `${bin}:${process.env.PATH}` } });
      assert.equal(result.status, exitCode, result.stderr || result.stdout);
      const report = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
      assert.equal(report.mode, 'verify-only');
      assert.equal(report.verification.summaryMatches, matches);
      assert.equal(report.verification.summaryChecked, expected !== undefined);
    } finally { fs.rmSync(dir, { recursive: true, force: true }); }
  });
}

import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const skillRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

test('verifies an existing editor through the CLI without writing', () => {
  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wechat-inject-cli-'));
  const binDir = path.join(workDir, 'bin');
  const htmlPath = path.join(workDir, 'article.html');
  const reportPath = path.join(workDir, 'report.json');
  fs.mkdirSync(binDir);
  fs.writeFileSync(htmlPath, '<html><body><section data-wechat-root="article"><p>正文</p></section></body></html>');
  const fakeOpencli = `#!/bin/sh
case "$*" in
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

test('injects metadata, synchronizes the first body image, and confirms a saved draft', () => {
  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wechat-inject-save-'));
  const binDir = path.join(workDir, 'bin');
  const htmlPath = path.join(workDir, 'article.html');
  const reportPath = path.join(workDir, 'report.json');
  fs.mkdirSync(binDir);
  fs.writeFileSync(htmlPath, '<html><body><section data-wechat-root="article"><p>正文</p><img src="https://mmbiz.qpic.cn/a.jpg"></section></body></html>');
  const fakeOpencli = `#!/bin/sh
case "$*" in
  *" state") printf 'URL: https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit\\n' ;;
  *"hasTitleEditor"*) printf '%s\\n' '{"readyState":"complete","hasTitleEditor":true,"hasBodyEditor":true,"editorCount":2,"bodyHeight":500}' ;;
  *"bodyEditor.innerHTML"*) printf '%s\\n' '{"ok":true,"svgCount":0,"animateCount":0,"imageCount":1,"textLength":2}' ;;
  *"setValue"*) printf '%s\\n' '{"title":"测试标题","visibleTitle":"测试标题","summary":"测试摘要","author":""}' ;;
  *"pendingImages"*) printf '%s\\n' '{"ok":true,"title":"测试标题","visibleTitle":"测试标题","summary":"测试摘要","svgCount":0,"animateCount":0,"imageCount":1,"failedUrls":[],"pendingImages":[],"textLength":2,"firstText":"正文","lastText":"正文","titleOccurrencesInBody":0,"saved":true,"url":"https://mp.weixin.qq.com/cgi-bin/appmsg?appmsgid=42&token=secret"}' ;;
  *"body has no cover image"*) printf '%s\\n' '{"ok":true}' ;;
  *"body cover candidate not found"*) printf '%s\\n' '{"ok":true}' ;;
  *"styledImage"*) printf '%s\\n' '{"ok":true}' ;;
  *"save button not found"*) printf '%s\\n' '{"ok":true}' ;;
  *"#history_pop tr"*) printf '%s\\n' '{"url":"https://mp.weixin.qq.com/cgi-bin/appmsg?appmsgid=42&token=secret","saved":true,"history":["saved"]}' ;;
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
    '--sync-cover-from-body',
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
  assert.equal(report.expected.images, 1);
  assert.equal(report.save.url.includes('secret'), false);
  fs.rmSync(workDir, { recursive: true, force: true });
});

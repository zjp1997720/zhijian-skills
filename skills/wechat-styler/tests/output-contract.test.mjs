import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const skillRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

test('renders the shared content root and metadata for downstream publishers', () => {
  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wechat-output-contract-'));
  const input = path.join(workDir, 'article.md');
  const output = path.join(workDir, 'article.html');
  fs.writeFileSync(input, '---\ntitle: 合同测试\nsummary: 摘要测试\n---\n\n# 正文标题\n\n正文。\n');

  const result = spawnSync(process.execPath, [
    path.join(skillRoot, 'scripts/convert.mjs'), input, '--output', output,
  ], { encoding: 'utf8' });

  assert.equal(result.status, 0, result.stderr || result.stdout);
  const html = fs.readFileSync(output, 'utf8');
  assert.match(html, /data-wechat-root="article"/);
  assert.match(html, /<meta name="description" content="摘要测试">/);
  fs.rmSync(workDir, { recursive: true, force: true });
});

test('renders fenced code with explicit hard breaks that survive WeChat sanitization', () => {
  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wechat-code-breaks-'));
  const input = path.join(workDir, 'article.md');
  const output = path.join(workDir, 'article.html');
  fs.writeFileSync(input, [
    '```text',
    '第一行',
    '第二行',
    '',
    '第四行',
    '```',
    '',
  ].join('\n'));

  const result = spawnSync(process.execPath, [
    path.join(skillRoot, 'scripts/convert.mjs'), input,
    '--theme', 'zhijian',
    '--output', output,
  ], { encoding: 'utf8' });

  assert.equal(result.status, 0, result.stderr || result.stdout);
  const html = fs.readFileSync(output, 'utf8');
  assert.match(html, /<pre\b[^>]*><code\b[^>]*>第一行<br>第二行<br><br>第四行<\/code><\/pre>/);
  fs.rmSync(workDir, { recursive: true, force: true });
});

test('passes the generated path to the opener without shell interpretation', () => {
  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wechat-output-safety-'));
  const input = path.join(workDir, 'article.md');
  const output = path.join(workDir, 'article.html"; touch INJECTED; #');
  fs.writeFileSync(input, '# 正文\n');

  const result = spawnSync(process.execPath, [
    path.join(skillRoot, 'scripts/convert.mjs'), input, '--output', output,
  ], { cwd: workDir, encoding: 'utf8' });

  assert.equal(result.status, 0, result.stderr || result.stdout);
  assert.equal(fs.existsSync(path.join(workDir, 'INJECTED')), false);
  assert.equal(fs.existsSync(output), true);
  fs.rmSync(workDir, { recursive: true, force: true });
});

test('zhijian theme keeps action and trust semantics visually distinct', () => {
  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wechat-zhijian-theme-'));
  const input = path.join(workDir, 'article.md');
  const output = path.join(workDir, 'article.html');
  fs.writeFileSync(input, [
    '## 章节标题',
    '',
    '### 结构标题',
    '',
    '正文包含 **普通加粗** 和 [资料链接](https://example.com)。',
    '',
    '- 列表正文',
    '',
    '> 一段用于交代上下文或证据的普通引用。',
    '',
    '![图注测试](https://example.com/image.png)',
    '',
  ].join('\n'));

  const result = spawnSync(process.execPath, [
    path.join(skillRoot, 'scripts/convert.mjs'), input,
    '--theme', 'zhijian',
    '--output', output,
  ], { encoding: 'utf8' });

  assert.equal(result.status, 0, result.stderr || result.stdout);
  const html = fs.readFileSync(output, 'utf8');
  assert.match(html, /font-size:15px;font-weight:450[^>]+line-height:1\.68/);
  assert.match(html, /<h2[^>]+font-family:'TsangerJinKai02'[^>]+font-size:22px;font-weight:500[^>]+border-left:4px solid #B85235/);
  assert.match(html, /<h3[^>]+font-family:'TsangerJinKai02'[^>]+font-size:18px;font-weight:600[^>]+color:#1B365D/);
  assert.match(html, /<ul[^>]+font-size:15px;font-weight:450/);
  assert.match(html, /<strong style="color:#A04A2E;font-weight:600/);
  assert.match(html, /<a href="https:\/\/example\.com"[^>]+color:#1B365D/);
  assert.match(html, /<section data-wechat-block="quote" style="background-color:#EEF2F7;padding:13px 16px 14px[^>]+border-radius:4px;">/);
  assert.match(html, /<p[^>]*><span style="display:inline-block[^>]+font-size:21px[^>]+color:#1B365D[^>]*>“<\/span>/);
  assert.doesNotMatch(html, /display:block[^>]+>“<\/span>/);
  assert.doesNotMatch(html, /background-color:#EEF2F7;border-left:/);
  assert.match(html, /<section style="text-align:center;margin:0;background-color:#F5F4ED;">\s*<img[^>]+alt="图注测试"/);
  assert.match(html, /<p style="font-family:'Source Han Sans CN'[^\"]*font-size:13px[^\"]*line-height:1\.4;text-align:center;margin:0 12px 22px/);
  assert.doesNotMatch(html, /text-align:center;margin:0 0 8px;background-color:#F5F4ED/);
  fs.rmSync(workDir, { recursive: true, force: true });
});

for (const script of ['convert', 'content-density-audit', 'mobile-visual-qa']) {
  for (const flag of ['--help', '-h']) {
    test(`${script} ${flag} documents options without reading files or launching Chrome`, () => {
      const result = spawnSync(process.execPath, [path.join(skillRoot, `scripts/${script}.mjs`), '/missing/input.md', flag],
        { encoding: 'utf8', env: { ...process.env, CHROME_CHANNEL: 'must-not-launch' } });
      assert.equal(result.status, 0, result.stderr || result.stdout);
      assert.match(result.stdout, /Usage:/);
      assert.match(result.stdout, /--/);
      assert.equal(result.stderr, '');
    });
  }
}

test('generated HTML is Git whitespace clean while preserving meaningful code spaces', () => {
  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wechat-whitespace-'));
  try {
    const input = path.join(workDir, 'article.md');
    const output = path.join(workDir, 'article.html');
    const source = '# 标题\n\n正文。\n\n```text\n  indented  \nnext\n```\n';
    fs.writeFileSync(input, source);
    const result = spawnSync(process.execPath, [path.join(skillRoot, 'scripts/convert.mjs'), input, '--output', output], { encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr || result.stdout);
    const html = fs.readFileSync(output, 'utf8');
    assert.doesNotMatch(html, /[ \t]+$/m);
    assert.match(html, /  indented  <br>next/);
    assert.equal(fs.readFileSync(input, 'utf8'), source);
    const check = spawnSync('git', ['-c', 'core.whitespace=blank-at-eol,blank-at-eof', 'diff', '--no-index', '--check', '/dev/null', output], { encoding: 'utf8' });
    assert.ok([0, 1].includes(check.status), check.stdout || check.stderr);
    assert.equal(check.stdout + check.stderr, '');
  } finally { fs.rmSync(workDir, { recursive: true, force: true }); }
});

test('density help also works through a Skill symlink', () => {
  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wechat-help-link-'));
  try {
    const link = path.join(workDir, 'skill');
    fs.symlinkSync(skillRoot, link, 'dir');
    const result = spawnSync(process.execPath, [path.join(link, 'scripts/content-density-audit.mjs'), '--help'], { encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /Usage:/);
  } finally { fs.rmSync(workDir, { recursive: true, force: true }); }
});

test('local image conversion warns about hosting while preserving preview and source', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'wechat-local-images-'));
  try {
    const input = path.join(dir, 'article.md');
    const output = path.join(dir, 'article.html');
    const source = '![本地图](图片和附件/local.png)\n\n![远程图](https://example.com/a.png)\n';
    fs.writeFileSync(input, source);
    const result = spawnSync(process.execPath, [path.join(skillRoot, 'scripts/convert.mjs'), input, '--output', output], { encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr || result.stdout);
    assert.match(result.stderr, /1.*非 HTTP/);
    assert.match(result.stderr, /opencli-injection/);
    assert.match(fs.readFileSync(output, 'utf8'), /src="图片和附件\/local.png"/);
    assert.equal(fs.readFileSync(input, 'utf8'), source);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

function convertWith(markdown, extraArgs) {
  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wechat-cover-h1-'));
  const input = path.join(workDir, 'article.md');
  const output = path.join(workDir, 'article.html');
  fs.writeFileSync(input, markdown);
  const result = spawnSync(process.execPath, [
    path.join(skillRoot, 'scripts/convert.mjs'), input, '--output', output, ...extraArgs,
  ], { encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr || result.stdout);
  const html = fs.readFileSync(output, 'utf8');
  fs.rmSync(workDir, { recursive: true, force: true });
  return html;
}

const h1Article = '\n# 学校 AI 推不动的根本原因\n\n第一段正文。\n\n## 小节\n\n# 中段一级标题\n\n后文。\n';
const countH1 = (html) => (html.match(/<h1\b/g) || []).length;

test('opening animation replaces the leading H1 instead of repeating it', () => {
  const html = convertWith(h1Article, ['--cover', '--cover-template', 'scroll-painting', '--brand-cta', 'none']);
  assert.equal(countH1(html), 1, 'only the mid-article H1 stays');
  assert.doesNotMatch(html, /<h1[^>]*>(?:<[^>]+>)*学校 AI 推不动的根本原因/);
  assert.match(html, /中段一级标题/);
  assert.match(html, /<svg[\s\S]*学校 AI 推不动的/, 'cover title falls back to the leading H1');
});

test('explicit cover title still removes the leading H1; --keep-h1 opts out', () => {
  const removed = convertWith(h1Article, ['--cover', '--cover-title', '短标题', '--brand-cta', 'none']);
  assert.equal(countH1(removed), 1);
  const kept = convertWith(h1Article, ['--cover', '--keep-h1', '--brand-cta', 'none']);
  assert.equal(countH1(kept), 2);
});

test('without an opening animation the leading H1 is unchanged', () => {
  const html = convertWith(h1Article, ['--brand-cta', 'none']);
  assert.equal(countH1(html), 2);
});

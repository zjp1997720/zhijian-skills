import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { validateHtml } from '../scripts/validate.mjs';

const skillRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

function convert(md) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'wechat-callout-'));
  const input = path.join(dir, 'a.md');
  const output = path.join(dir, 'a.html');
  fs.writeFileSync(input, md);
  const r = spawnSync(process.execPath, [
    path.join(skillRoot, 'scripts/convert.mjs'), input, '--output', output, '--components', '--no-open',
  ], { encoding: 'utf8' });
  assert.equal(r.status, 0, r.stderr || r.stdout);
  return fs.readFileSync(output, 'utf8');
}

test('NOTE/WARNING blocks render inline bold, code and highlight without leaking **', () => {
  const html = convert('# T\n\n正文。\n\n> [!NOTE] 前文**加粗一**后文 `x<y` ==标记==\n\n> [!WARNING] 请**务必**备份\n');
  assert.doesNotMatch(html.replace(/<[^>]*>/g, ''), /\*\*/);
  assert.match(html, /提示<\/span>前文<strong style="[^"]*"><span[^>]*>加粗一<\/span><\/strong>后文/);
  assert.match(html, /注意<\/span>请<strong style="[^"]*"><span[^>]*>务必<\/span><\/strong>备份/);
  assert.match(html, /<code [^>]*><span[^>]*>x&lt;y<\/span><\/code>/);
  assert.match(html, /border-bottom:1px solid/);
  assert.equal(validateHtml(html).errors.length, 0);
});

test('validate flags leaked ** in visible text but not inside code blocks', () => {
  const r = validateHtml('<p style="x">前文**漏出**后文</p>');
  assert.ok(r.errors.some((e) => /\*\*/.test(e.message)), JSON.stringify(r));
  const inCode = '<p style="x">用法 <code>a **b** c</code></p>\n<pre><code>**x**</code></pre>';
  assert.equal(validateHtml(inCode).errors.length, 0);
});

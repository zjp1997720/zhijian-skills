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

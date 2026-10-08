#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const SHORT_LIMIT = 40;
const ULTRASHORT_LIMIT = 20;
const LONG_LIMIT = 100;
const VERY_LONG_LIMIT = 140;

function normalizeText(text) {
  return text
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, ' ')
    .trim();
}

function cleanMarkdownInline(text) {
  return normalizeText(text
    .replace(/!\[[^\]]*\]\([^)]*\)/g, '')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/<[^>]+>/g, '')
    .replace(/[`*_~=]/g, ''));
}

export function extractMarkdownParagraphs(source) {
  let lines = source.split(/\r?\n/);
  if (lines[0]?.trim() === '---') {
    const end = lines.slice(1).findIndex(line => line.trim() === '---');
    if (end >= 0) lines = lines.slice(end + 2);
  }

  const paragraphs = [];
  let buffer = [];
  let inCode = false;
  let inComponent = false;

  const flush = () => {
    if (!buffer.length) return;
    const raw = buffer.join(' ').trim();
    buffer = [];
    if (!raw || /^(#{1,6}\s|!\[|>\s?|[-*+]\s|\d+[.)]\s|\||---$|<)/.test(raw)) return;
    const cleaned = cleanMarkdownInline(raw);
    if (cleaned) paragraphs.push(cleaned);
  };

  for (const line of lines) {
    const stripped = line.trim();
    if (stripped.startsWith('```')) {
      flush();
      inCode = !inCode;
      continue;
    }
    if (inCode) continue;
    if (stripped.startsWith(':::')) {
      flush();
      inComponent = !inComponent;
      continue;
    }
    if (inComponent) continue;
    if (!stripped) {
      flush();
      continue;
    }
    buffer.push(stripped);
  }
  flush();
  return paragraphs;
}

export function extractHtmlParagraphs(source) {
  return [...source.matchAll(/<p style="([^"]+)">([\s\S]*?)<\/p>/g)]
    .filter(match => match[1].includes('font-weight:400')
      && match[1].includes('color:#141413')
      && match[1].includes('text-align:justify'))
    .map(match => normalizeText(match[2].replace(/<[^>]+>/g, '')))
    .filter(Boolean);
}

function visibleLength(text) {
  return [...text.replace(/\s+/g, '')].length;
}

function maxRun(lengths, predicate) {
  let best = 0;
  let current = 0;
  for (const length of lengths) {
    if (predicate(length)) {
      current += 1;
      best = Math.max(best, current);
    } else {
      current = 0;
    }
  }
  return best;
}

export function analyzeParagraphDensity(paragraphs, source = '') {
  const lengths = paragraphs.map(visibleLength);
  const count = lengths.length;
  if (!count) {
    return { source, status: 'fail', paragraphCount: 0, issues: ['没有识别到正文自然段'], warnings: [] };
  }

  const sorted = [...lengths].sort((a, b) => a - b);
  const median = count % 2
    ? sorted[(count - 1) / 2]
    : (sorted[count / 2 - 1] + sorted[count / 2]) / 2;
  const p90 = sorted[Math.min(count - 1, Math.floor((count - 1) * 0.9))];
  const shortCount = lengths.filter(length => length <= SHORT_LIMIT).length;
  const longCount = lengths.filter(length => length >= LONG_LIMIT).length;
  const veryLongCount = lengths.filter(length => length >= VERY_LONG_LIMIT).length;
  const shortRatio = shortCount / count;
  const longRatio = longCount / count;
  const veryLongRatio = veryLongCount / count;
  const longRun = maxRun(lengths, length => length >= LONG_LIMIT);
  const ultrashortRun = maxRun(lengths, length => length <= ULTRASHORT_LIMIT);
  const issues = [];
  const warnings = [];

  if (count >= 8) {
    if (median > 90) issues.push(`正文段落中位数 ${median} 字，高于 90 字`);
    if (longRatio >= 0.35) issues.push(`百字长段占比 ${(longRatio * 100).toFixed(1)}%，高于 35%`);
    if (veryLongRatio >= 0.20) issues.push(`140 字以上长段占比 ${(veryLongRatio * 100).toFixed(1)}%，高于 20%`);
    if (longRun >= 3) issues.push(`连续百字长段达到 ${longRun} 个`);
    if (shortRatio < 0.15 && median > 70) issues.push(`40 字以内短段仅占 ${(shortRatio * 100).toFixed(1)}%，缺少节奏变化`);
    if (ultrashortRun >= 8) {
      warnings.push(`连续 20 字以内短段达到 ${ultrashortRun} 个；请人工检查是否为残句、口号或无信息碎切，数量本身不构成失败`);
    }
  }
  if (Math.max(...lengths) > 180) warnings.push(`最长段落 ${Math.max(...lengths)} 字`);
  if (p90 > 130) warnings.push(`P90 段落长度 ${p90} 字`);

  return {
    source,
    status: issues.length ? 'fail' : 'pass',
    paragraphCount: count,
    characterCount: lengths.reduce((sum, length) => sum + length, 0),
    mean: Number((lengths.reduce((sum, length) => sum + length, 0) / count).toFixed(1)),
    median,
    p90,
    max: Math.max(...lengths),
    shortLe40: shortCount,
    shortRatio: Number(shortRatio.toFixed(4)),
    longGe100: longCount,
    longRatio: Number(longRatio.toFixed(4)),
    veryLongGe140: veryLongCount,
    veryLongRatio: Number(veryLongRatio.toFixed(4)),
    maxConsecutiveGe100: longRun,
    maxConsecutiveLe20: ultrashortRun,
    issues,
    warnings,
  };
}

export function analyzeContentDensity(source, sourceName = '', kind = 'markdown') {
  const paragraphs = kind === 'html'
    ? extractHtmlParagraphs(source)
    : extractMarkdownParagraphs(source);
  return analyzeParagraphDensity(paragraphs, sourceName);
}

export function formatDensityReport(report) {
  const head = `${report.status === 'pass' ? '✓' : '⚠'} 段落密度 ${report.status.toUpperCase()}: `
    + `正文 ${report.paragraphCount} 段，中位数 ${report.median ?? 0} 字，`
    + `P90 ${report.p90 ?? 0} 字，连续百字长段 ${report.maxConsecutiveGe100 ?? 0} 个`;
  const details = [
    ...report.issues.map(issue => `  ERROR: ${issue}`),
    ...report.warnings.map(warning => `  WARN: ${warning}`),
  ];
  if (report.status === 'fail') {
    details.push('  ACTION: 回到 Markdown，按语义切换点拆分或合并段落；不要用缩小字号代替内容层修复。');
  }
  return [head, ...details].join('\n');
}

function main() {
  const args = process.argv.slice(2);
  if (args.includes('--help') || args.includes('-h')) {
    console.log(`Usage: node scripts/content-density-audit.mjs <article.md|html> [options]
  --strict                   Exit 1 when density audit fails
  --json                     Print the report as JSON
  -h, --help                 Show help without reading input`);
    process.exit(0);
  }

  const strict = args.includes('--strict');
  const json = args.includes('--json');
  const input = args.find(arg => !arg.startsWith('--'));
  if (!input) {
    console.error('Usage: node scripts/content-density-audit.mjs <article.md|html> [--strict] [--json]');
    process.exit(1);
  }
  const inputPath = path.resolve(input);
  const source = fs.readFileSync(inputPath, 'utf8');
  const kind = /\.html?$/i.test(inputPath) ? 'html' : 'markdown';
  const report = analyzeContentDensity(source, inputPath, kind);
  console.log(json ? JSON.stringify(report, null, 2) : formatDensityReport(report));
  if (strict && report.status === 'fail') process.exit(1);
}

const isMain = process.argv[1] && fs.realpathSync(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) main();

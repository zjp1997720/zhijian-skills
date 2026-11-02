// :::figure 围栏 → 内联 SVG（组件模式）或引用块（默认模式）。convert.mjs 只调用这里。
import fs from 'node:fs';
import path from 'node:path';

import yaml from 'js-yaml';

import { resolveBrowserLaunch } from '../qa-browser.mjs';
import { SpecError, W, stripAnimation } from './core.mjs';
import { buildFigure } from './figure.mjs';
import { loadFont, resolveFigureFont } from './fonts.mjs';
import { PAGE, checkRendered, checkStructure, checkTheme } from './gates.mjs';
import { themeTokens } from './theme.mjs';

const MAX_FIGURES = 5;

/** details 每行一条，都带图 ID 和原因。 */
export class FigureError extends Error {
  constructor(details) {
    super(details.join('\n'));
    this.name = 'FigureError';
    this.details = details;
  }
}

/** 按行找围栏，跳过代码块里的示例。 */
function findBlocks(markdown) {
  const lines = markdown.split('\n');
  const blocks = [];
  let code = null;
  for (let i = 0; i < lines.length; i += 1) {
    const fence = lines[i].match(/^ {0,3}(`{3,}|~{3,})/);
    if (code) {
      if (fence && fence[1][0] === code[0] && fence[1].length >= code.length && lines[i].trim() === fence[1]) code = null;
    } else if (fence) {
      code = fence[1];
    } else if (/^:::figure\s*$/.test(lines[i])) {
      let end = i + 1;
      while (end < lines.length && !/^:::\s*$/.test(lines[end])) end += 1;
      if (end === lines.length) throw new FigureError([`图解 fig-${String(blocks.length + 1).padStart(2, '0')}：第 ${i + 1} 行的 :::figure 没有闭合的 :::`]);
      blocks.push({ start: i, end, body: lines.slice(i + 1, end).join('\n') });
      i = end;
    }
  }
  return { lines, blocks };
}

function replaceBlocks({ lines, blocks }, render) {
  const out = [];
  let at = 0;
  blocks.forEach((block, index) => {
    out.push(...lines.slice(at, block.start), render(block, index));
    at = block.end + 1;
  });
  out.push(...lines.slice(at));
  return out.join('\n');
}

function parseBlock(block, index) {
  const fallbackId = block.body.match(/^id:\s*["']?([\w-]+)/m)?.[1] || `fig-${String(index + 1).padStart(2, '0')}`;
  let spec;
  try {
    spec = yaml.load(block.body);
  } catch (error) {
    throw new FigureError([`图解 ${fallbackId}：YAML 解析失败：${error.reason || error.message}`]);
  }
  if (!spec || typeof spec !== 'object' || Array.isArray(spec)) throw new FigureError([`图解 ${fallbackId}：围栏内容必须是 YAML 字段`]);
  const id = spec.id === undefined ? fallbackId : String(spec.id);
  if (!/^[\w-]+$/.test(id)) throw new FigureError([`图解 ${id}：id 只能用字母、数字、下划线和连字符`]);
  return { id, spec };
}

/** 去掉围栏，给段落密度审计用：图解不是正文段落。 */
export function stripFigureFences(markdown) {
  return replaceBlocks(findBlocks(markdown), () => '');
}

/** 默认模式：标题加结论句的引用，不暴露标记。 */
export function applyFigureFallback(markdown) {
  const found = findBlocks(markdown);
  const parsed = found.blocks.map(parseBlock);
  return replaceBlocks(found, (_, index) => {
    const { id, spec } = parsed[index];
    if (!spec.title || !spec.conclusion) throw new FigureError([`图解 ${id}：每张图都要有 title（结论式标题）和 conclusion（结论句）`]);
    return `\n> **${spec.title}**\n>\n> ${spec.conclusion}\n`;
  });
}

/** 组件模式：生成 SVG 并跑不需要浏览器的硬检查，任何一张不过都整体报错。 */
export function prepareFigures(markdown, theme, { font: fontFlag = null, env = process.env } = {}) {
  const found = findBlocks(markdown);
  if (!found.blocks.length) return { markdown, figures: [], font: null };
  const parsed = found.blocks.map(parseBlock);
  const errors = [];
  if (parsed.length > MAX_FIGURES) errors.push(`图解 ${parsed[MAX_FIGURES].id}：一篇不超过 ${MAX_FIGURES} 张，这篇有 ${parsed.length} 张`);
  const seen = new Set();
  for (const { id } of parsed) {
    if (seen.has(id)) errors.push(`图解 ${id}：id 重复`);
    seen.add(id);
  }
  const tokens = themeTokens(theme);
  const font = resolveFigureFont({ flag: fontFlag, env });
  const loaded = font.path ? loadFont(font.path) : null;
  const figures = [];
  for (const { id, spec } of parsed) {
    try {
      const fig = buildFigure(spec, tokens, { font: loaded });
      const issues = [...checkStructure(fig.svg), ...checkTheme(tokens)];
      if (issues.length) errors.push(`图解 ${id}：${issues.join('；')}`);
      figures.push({ id, fig });
    } catch (error) {
      if (!(error instanceof SpecError)) throw error;
      errors.push(`图解 ${id}：${error.message}`);
    }
  }
  if (errors.length) throw new FigureError(errors);
  const svgById = new Map(figures.map(({ id, fig }) => [id, fig.svg]));
  const html = replaceBlocks(found, (_, index) => `\n<section style="margin:20px 0;line-height:0;">${svgById.get(parsed[index].id)}</section>\n`);
  return { markdown: html, figures, font };
}

async function launch() {
  const { chromium } = await import('playwright-core');
  const { source, ...options } = resolveBrowserLaunch();
  return { browser: await chromium.launch(options), source };
}

async function writeContactSheet(browser, rows, file) {
  const page = await browser.newPage({ viewport: { width: 4 * W + 18, height: 900 } });
  const imgs = rows.flatMap((picks) => picks.map((png) => `<img width="${W}" src="data:image/png;base64,${png.toString('base64')}">`));
  await page.setContent(`<!doctype html><body style="margin:0;background:#969696;display:grid;grid-template-columns:repeat(4,${W}px);gap:6px">${imgs.join('')}</body>`);
  await page.waitForTimeout(100);
  await page.screenshot({ path: file, fullPage: true });
  await page.close();
}

/**
 * 在浏览器里跑渲染检查，可选输出 PNG、联系图和报告。
 * 没有浏览器时：要 PNG 就报错；只是转换就照常出稿，并在报告里写明没查。
 */
export async function verifyFigures(prepared, { pngDir = null } = {}) {
  const { figures, font } = prepared;
  const notes = font?.note ? [font.note] : [];
  const exposed = [...new Set(figures.flatMap(({ fig }) => fig.notes))];
  if (exposed.length) notes.push(`风险：这些拉丁文留在 <text> 里，iOS 微信正式阅读器可能漏画（svg-animation-design.md 踩坑 14）：${exposed.join('、')}`);
  const report = {
    status: 'pass',
    font: font?.path ? path.basename(font.path) : null,
    font_source: font?.source || null,
    rendered: 'pass',
    notes,
    figures: figures.map(({ id, fig }) => ({ id, type: fig.type, mode: fig.mode, theme: fig.theme, title: fig.title, conclusion: fig.conclusion, dur: fig.dur, kb: Math.round(Buffer.byteLength(fig.svg) / 102.4) / 10, issues: [] })),
  };
  let launched;
  try {
    launched = await launch();
  } catch (error) {
    const reason = String(error.message).split('\n')[0];
    if (pngDir) throw new FigureError([`图解 ${figures.map((f) => f.id).join('、')}：--figure-png 需要浏览器：${reason}。可用 CHROME_EXECUTABLE 指定`]);
    report.rendered = 'skipped';
    report.notes.push(`渲染检查未执行（没有可用浏览器：${reason}）`);
    return report;
  }
  const { browser } = launched;
  const errors = [];
  try {
    const page = await browser.newPage({ viewport: { width: W, height: 900 } });
    const hi = pngDir ? await browser.newPage({ viewport: { width: W, height: 900 }, deviceScaleFactor: 3 }) : null;
    if (pngDir) fs.mkdirSync(pngDir, { recursive: true });
    const rows = [];
    for (let i = 0; i < figures.length; i += 1) {
      const { id, fig } = figures[i];
      const { issues, metrics, picks } = await checkRendered(page, fig);
      Object.assign(report.figures[i], metrics, { issues });
      if (issues.length) errors.push(`图解 ${id}：${issues.join('；')}`);
      if (pngDir) {
        fs.writeFileSync(path.join(pngDir, `${id}.svg`), fig.svg);
        await hi.setContent(PAGE(stripAnimation(fig.svg)));
        await hi.waitForTimeout(100);
        await hi.locator('svg').screenshot({ path: path.join(pngDir, `${id}.png`) });
        rows.push(picks);
      }
    }
    if (pngDir) await writeContactSheet(browser, rows, path.join(pngDir, 'contact.png'));
  } finally {
    await browser.close();
  }
  report.status = errors.length ? 'fail' : 'pass';
  report.rendered = errors.length ? 'fail' : 'pass';
  if (pngDir) fs.writeFileSync(path.join(pngDir, 'report.json'), `${JSON.stringify(report, null, 2)}\n`);
  if (errors.length) throw new FigureError(errors);
  return report;
}

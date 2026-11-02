// 硬检查：结构白名单在 Node 里查，几何和动画在 Chromium 里实测。
import { W, round, stripAnimation } from './core.mjs';
import { contrast } from './figure.mjs';
import { decodePng, diffRatio } from './png.mjs';

const ALLOWED_TAGS = new Set(['svg', 'g', 'rect', 'line', 'circle', 'path', 'text', 'tspan', 'animate', 'animateTransform']);
const ALLOWED_ANIM_ATTRS = new Set(['opacity', 'transform']);
const MIN_FONT = 12;
const MIN_HOLD = 2;
const MAX_KB = 30;
export const PAGE = (svg) => `<!doctype html><html><body style="margin:0;background:#fff;font-family:'PingFang SC',sans-serif">${svg}</body></html>`;

const measureTexts = () => {
  const out = [];
  for (const t of document.querySelectorAll('text, path[data-glyph]')) {
    const b = t.getBoundingClientRect();
    let op = 1;
    for (let e = t; e && e.tagName !== 'svg'; e = e.parentElement) op *= parseFloat(getComputedStyle(e).opacity);
    out.push({ s: t.getAttribute('data-glyph') || t.textContent, l: b.left, r: b.right, t: b.top, b: b.bottom, op, box: t.getAttribute('data-box') });
  }
  return out;
};

// 文字压线：在文字框内撒点，问每条线和曲线的描边有没有碰到。字形路径（有填充）按文字框参与重叠检查。
const measureCollisions = () => {
  const svg = document.querySelector('svg');
  const pt = svg.createSVGPoint();
  const hits = [];
  const boxes = [];
  const lines = [...svg.querySelectorAll('line, path[fill="none"]')];
  const visible = (el) => {
    for (let e = el; e && e.tagName !== 'svg'; e = e.parentElement) if (parseFloat(getComputedStyle(e).opacity) < 0.01) return false;
    return true;
  };
  for (const t of svg.querySelectorAll('text, path[data-glyph]')) {
    if (!visible(t)) continue;
    const b = t.getBoundingClientRect();
    for (const l of lines) {
      if (!visible(l)) continue;
      const m = l.getScreenCTM().inverse();
      let hit = false;
      for (let i = 0; i <= 12 && !hit; i += 1) {
        for (let j = 1; j < 4 && !hit; j += 1) {
          pt.x = b.left + ((b.right - b.left) * i) / 12;
          pt.y = b.top + ((b.bottom - b.top) * j) / 4;
          hit = l.isPointInStroke(pt.matrixTransform(m));
        }
      }
      if (hit) {
        hits.push(t.getAttribute('data-glyph') || t.textContent);
        break;
      }
    }
  }
  for (const p of svg.querySelectorAll('path:not([fill="none"]):not([data-glyph])')) {
    if (!visible(p)) continue;
    const b = p.getBoundingClientRect();
    boxes.push({ s: '[标题或数字]', l: b.left, r: b.right, t: b.top, b: b.bottom, op: 1, box: null });
    for (const r of svg.querySelectorAll('rect[stroke]')) {
      if (!visible(r)) continue;
      const q = r.getBoundingClientRect();
      const inside = b.left >= q.left && b.right <= q.right && b.top >= q.top && b.bottom <= q.bottom;
      if (!inside && Math.min(b.right, q.right) - Math.max(b.left, q.left) > 0 && Math.min(b.bottom, q.bottom) - Math.max(b.top, q.top) > 0) {
        hits.push('[标题或数字压住节点框]');
      }
    }
  }
  return { hits, boxes };
};

const seek = (t) => {
  const s = document.querySelector('svg');
  s.pauseAnimations();
  s.setCurrentTime(t);
};

/** 公众号只保留已验证的标签和动画属性。 */
export function checkStructure(svg) {
  const issues = [];
  const tags = new Set();
  const open = [];
  let hasId = false;
  let wellFormed = true;
  for (const m of svg.matchAll(/<(\/?)([A-Za-z][\w:-]*)((?:[^>"']|"[^"]*"|'[^']*')*?)(\/?)>/g)) {
    const [, closing, name, attrs, selfClosing] = m;
    tags.add(name);
    if (/\sid\s*=/.test(attrs)) hasId = true;
    if (closing) wellFormed = open.pop() === name && wellFormed;
    else if (!selfClosing) open.push(name);
  }
  if (!wellFormed || open.length) issues.push('malformed-svg');
  for (const tag of [...tags].sort()) if (!ALLOWED_TAGS.has(tag)) issues.push(`tag-not-allowed:${tag}`);
  for (const [, attr] of svg.matchAll(/attributeName="([^"]+)"/g)) if (!ALLOWED_ANIM_ATTRS.has(attr)) issues.push(`anim-attr-not-allowed:${attr}`);
  if (hasId) issues.push('id-attribute');
  for (const [, size] of svg.matchAll(/font-size="([\d.]+)"/g)) if (Number(size) < MIN_FONT) issues.push(`font-too-small:${size}`);
  const kb = Buffer.byteLength(svg) / 1024;
  if (kb > MAX_KB) issues.push(`too-large:${kb.toFixed(1)}KB>${MAX_KB}KB`);
  return issues;
}

export function checkTheme(theme) {
  const pairs = [['text', 'bg'], ['muted', 'bg'], ['faint', 'bg'], ['text', 'node'], ['keyText', 'keyFill'], ['text', 'sunken']];
  return pairs.filter(([a, b]) => contrast(theme[a], theme[b]) < 4.5).map(([a, b]) => `contrast:${a}/${b}=${contrast(theme[a], theme[b]).toFixed(2)}`);
}

const shot = async (page) => page.locator('svg').screenshot();

/** 返回 {issues, metrics, picks}；picks 是三个动画中途帧加静态图的 PNG。 */
export async function checkRendered(page, fig) {
  const issues = [];
  const { dur } = fig;
  await page.setContent(PAGE(stripAnimation(fig.qa)));
  await page.waitForTimeout(120);
  const texts = (await page.evaluate(measureTexts)).filter((t) => t.op > 0.01);
  const staticPng = await shot(page);
  const staticImg = decodePng(staticPng);
  const collide = await page.evaluate(measureCollisions);
  issues.push(...collide.hits.map((s) => `text-on-line:${s}`));
  texts.push(...collide.boxes);
  for (const t of texts) {
    if (t.l < 6 || t.r > W - 6) issues.push(`text-off-canvas:${t.s}`);
    if (t.box) {
      const [x, y, w, h] = t.box.split(',').map(Number);
      if (t.l < x + 1 || t.r > x + w - 1 || t.t < y || t.b > y + h) issues.push(`text-out-of-box:${t.s}`);
    }
  }
  texts.forEach((a, i) => {
    for (const b of texts.slice(i + 1)) {
      if (Math.min(a.r, b.r) - Math.max(a.l, b.l) > 1 && Math.min(a.b, b.b) - Math.max(a.t, b.t) > 2) issues.push(`text-overlap:${a.s}|${b.s}`);
    }
  });
  await page.setContent(PAGE(fig.svg));
  await page.waitForTimeout(80);
  const step = 0.2;
  const ratios = [];
  const frames = [];
  for (let i = 0; i < Math.trunc(dur / step); i += 1) {
    await page.evaluate(seek, round(i * step, 2));
    await page.waitForTimeout(15);
    const png = await shot(page);
    ratios.push(diffRatio(decodePng(png), staticImg));
    frames.push(png);
  }
  const maxChange = Math.max(...ratios);
  if (maxChange < 0.001) issues.push('not-animated');
  const settled = ratios.map((r) => r < 0.002);
  let best = 0;
  let run = 0;
  for (const s of [...settled, ...settled]) {
    run = s ? run + 1 : 0;
    best = Math.max(best, Math.min(run, settled.length));
  }
  const hold = round(best * step, 2);
  if (fig.mode === 'build') {
    if (hold < MIN_HOLD) issues.push(`hold-too-short:${hold}s<${MIN_HOLD}s`);
  } else if (maxChange > 0.08) {
    issues.push(`tour-content-moves:${maxChange.toFixed(3)}`);
  }
  const picks = [0.14, 0.3, 0.5].map((p) => frames[Math.trunc(frames.length * p)]);
  picks.push(staticPng);
  return { issues, metrics: { dur, hold, max_change: round(maxChange, 3), kb: round(Buffer.byteLength(fig.svg) / 1024, 1) }, picks };
}

/**
 * generate-cover-animation.mjs
 * 从主题色 + 标题参数生成公众号开场 SVG 动画
 *
 * 5 个模板:
 *   ink-wash       墨韵开篇(默认 · 方法论/品牌)
 *   typewriter     打字机流(技术/教程 · 逐字打字+光标跟随)
 *   scroll-painting 画卷展开(案例/故事)
 *   spotlight      聚焦聚光灯(观点/判断)
 *   minimal-sketch 极简白描(随笔/思考)
 *
 * 用法:
 *   node generate-cover-animation.mjs --theme zhijian --template typewriter \
 *     --title "初识 WorkBuddy" --subtitle "..." --tags "最全面,低门槛" --output cover.svg
 *
 * 被 convert.mjs 内部调用:
 *   import { generateCoverAnimation } from './generate-cover-animation.mjs';
 *   const svg = generateCoverAnimation(theme, { template, title, subtitle, tags });
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// ─── 主题加载 ───────────────────────────────────────────
function loadTheme(themeName) {
  const themePath = path.join(__dirname, '..', 'themes', `${themeName}.yaml`);
  if (!fs.existsSync(themePath)) {
    throw new Error(`主题文件不存在: ${themePath}`);
  }
  const yaml = fs.readFileSync(themePath, 'utf8');
  return parseYaml(yaml);
}

function parseYaml(text) {
  const result = {};
  for (const line of text.split('\n')) {
    const m = line.match(/^(\w+):\s*(.*)$/);
    if (m && !m[2].startsWith('{')) {
      let val = m[2].trim();
      if (val.startsWith('"') && val.endsWith('"')) val = val.slice(1, -1);
      if (val.startsWith("'") && val.endsWith("'")) val = val.slice(1, -1);
      if (val && !isNaN(val)) val = Number(val);
      result[m[1]] = val;
    }
  }
  return result;
}

// ─── 参数解析 ───────────────────────────────────────────
function parseArgs() {
  const args = process.argv.slice(2);
  const opts = {
    theme: 'zhijian',
    template: 'ink-wash',
    title: '',
    subtitle: '',
    tags: '',
    output: null,
    accentColor: null,
    bgColor: null,
  };
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    const next = args[i + 1];
    switch (arg) {
      case '--theme': opts.theme = next; i++; break;
      case '--template': opts.template = next; i++; break;
      case '--title': opts.title = next; i++; break;
      case '--subtitle': opts.subtitle = next; i++; break;
      case '--tags': opts.tags = next; i++; break;
      case '--output': case '-o': opts.output = next; i++; break;
      case '--accent-color': opts.accentColor = next; i++; break;
      case '--bg-color': opts.bgColor = next; i++; break;
      case '--help': case '-h':
        console.log(`用法: node generate-cover-animation.mjs --theme zhijian --template typewriter --title "标题" --subtitle "副标题" --tags "标签1,标签2" --output cover.svg\n\n模板: ink-wash | typewriter | scroll-painting | spotlight | minimal-sketch`);
        process.exit(0);
    }
  }
  return opts;
}

// ─── 字宽计算(等宽字体,区分大小写) ──────────────────
function getCharWidth(ch, fontSize) {
  if (/[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]/.test(ch)) return fontSize * 1.0;
  if (/[A-Z]/.test(ch)) return fontSize * 0.72; // 大写更宽
  return fontSize * 0.6;
}

// 英文字母额外间距
function getCharGap(ch) {
  if (/[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]/.test(ch)) return 0;
  return 1.5;
}

// ─── 逐字打字 + 光标跟随(核心函数) ────────────────────
function buildTypewriter(text, cx, y, fontSize, fill, font, startDelay, interval, accentColor) {
  const chars = [...text];
  const widths = chars.map(ch => getCharWidth(ch, fontSize));
  const gaps = chars.map(ch => getCharGap(ch));
  const totalW = widths.reduce((a, b) => a + b, 0) + gaps.reduce((a, b) => a + b, 0) - gaps[gaps.length - 1];
  const sx = cx - totalW / 2;
  const xs = [];
  let acc = sx;
  for (let i = 0; i < chars.length; i++) {
    xs.push(acc);
    acc += widths[i] + gaps[i];
  }

  const charDur = interval * 0.8;
  let svg = '';
  for (let i = 0; i < chars.length; i++) {
    const delay = startDelay + i * interval;
    svg += `<text x="${xs[i].toFixed(1)}" y="${y}" text-anchor="start" font-size="${fontSize}" font-weight="500" fill="${fill}" font-family="${font}" opacity="0">`;
    svg += `<tspan leaf="">${chars[i]}</tspan>`;
    svg += `<animate attributeName="opacity" values="0;1" dur="${charDur}s" begin="${delay.toFixed(2)}s" fill="freeze"/></text>`;
  }

  // 光标跟随
  const totalDur = chars.length * interval;
  const cursorW = Math.max(2, fontSize * 0.06);
  const cursorH = fontSize * 0.8;
  const cursorY = y - fontSize * 0.7;
  const endDelay = startDelay + totalDur;

  const xVals = [(sx - cursorW - 2).toFixed(1)];
  const keyTimes = ['0'];
  for (let i = 0; i < chars.length; i++) {
    xVals.push((xs[i] + widths[i] + gaps[i] + 1).toFixed(1));
    keyTimes.push(((i + 1) / chars.length).toFixed(4));
  }

  svg += `<rect x="${sx.toFixed(1)}" y="${cursorY.toFixed(1)}" width="${cursorW}" height="${cursorH.toFixed(1)}" fill="${accentColor}" opacity="0">`;
  svg += `<animate attributeName="x" values="${xVals.join(';')}" keyTimes="${keyTimes.join(';')}" dur="${totalDur}s" begin="${startDelay}s" fill="freeze"/>`;
  svg += `<animate attributeName="opacity" values="0;1" dur="0.05s" begin="${startDelay}s" fill="freeze"/>`;
  svg += `<animate attributeName="opacity" values="1;0;1;0;1;0;0" dur="${(endDelay - startDelay + 1.2)}s" begin="${startDelay}s" fill="freeze"/>`;
  svg += `</rect>`;

  return { svg, sx, totalW, endDelay, lastCursorX: parseFloat(xVals[xVals.length - 1]) };
}

// ─── 模板 1: 墨韵开篇 ──────────────────────────────────
function templateInkWash(C, opts) {
  const tagList = opts.tags ? opts.tags.split(',').map(t => t.trim()).filter(Boolean) : [];
  const W = 640, H = 400, cx = W / 2;

  let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMin meet" style="display:block;width:100%;max-width:${W}px;margin:0 auto;">`;
  svg += `<rect x="0" y="0" width="${W}" height="${H}" fill="${C.bg}"/>`;

  // 墨点晕染
  svg += `<circle cx="${cx}" cy="180" r="0" fill="${C.accent}" opacity="0.08"><animate attributeName="r" values="0;120;180" dur="0.8s" begin="0.2s" fill="freeze" calcMode="spline" keyTimes="0;0.6;1" keySplines="0.25 0.1 0.25 1;0.4 0 0.6 1"/><animate attributeName="opacity" values="0.08;0.04;0" dur="0.8s" begin="0.2s" fill="freeze"/></circle>`;

  // 顶部标签
  if (C.topLabel) {
    svg += `<text x="${cx}" y="60" text-anchor="middle" font-size="13" font-weight="600" fill="${C.accent}" letter-spacing="4" font-family="${C.uiFont}" opacity="0"><tspan leaf="">${C.topLabel}</tspan><animate attributeName="opacity" values="0;1" dur="0.5s" begin="0.8s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.25 0.1 0.25 1"/></text>`;
  }

  // 主标题
  if (opts.title) {
    svg += `<g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.7s" begin="1.2s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.25 0.1 0.25 1"/><animateTransform attributeName="transform" type="translate" values="0 30;0 0" dur="0.7s" begin="1.2s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.25 0.1 0.25 1"/><text x="${cx}" y="170" text-anchor="middle" font-size="48" font-weight="500" fill="${C.text}" font-family="${C.headingFont}"><tspan leaf="">${opts.title}</tspan></text></g>`;
  }

  // 分隔线(rect + animate width,微信保留)
  svg += `<rect x="${cx - 50}" y="198" width="0" height="3" rx="1.5" fill="${C.accent}" opacity="0"><animate attributeName="width" values="0;100" dur="0.5s" begin="1.9s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.22 1 0.36 1"/><animate attributeName="opacity" values="0;1" dur="0.05s" begin="1.9s" fill="freeze"/></rect>`;

  // 副标题
  if (opts.subtitle) {
    svg += `<text x="${cx}" y="245" text-anchor="middle" font-size="18" fill="${C.tertiary}" font-family="${C.serifFont}" opacity="0"><tspan leaf="">${opts.subtitle}</tspan><animate attributeName="opacity" values="0;1" dur="0.6s" begin="2.4s" fill="freeze"/></text>`;
  }

  // 特性标签
  if (tagList.length > 0) {
    const tagW = 80, tagH = 28, tagGap = 20;
    const totalTagW = tagList.length * tagW + (tagList.length - 1) * tagGap;
    const startTagX = cx - totalTagW / 2;
    const tagColors = [C.accent, C.secondary, C.tertiary];
    tagList.forEach((tag, i) => {
      const x = startTagX + i * (tagW + tagGap);
      const color = tagColors[i % tagColors.length];
      const delay = 3.0 + i * 0.3;
      svg += `<g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.4s" begin="${delay}s" fill="freeze"/><rect x="${x}" y="290" width="${tagW}" height="${tagH}" rx="14" fill="none" stroke="${color}" stroke-width="1.2"/><text x="${x + tagW / 2}" y="308" text-anchor="middle" font-size="12" fill="${color}" font-family="${C.uiFont}"><tspan leaf="">${tag}</tspan></text></g>`;
    });
  }

  // 底部提示 + 箭头
  svg += `<g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.5s" begin="4.0s" fill="freeze"/><circle cx="${cx - 15}" cy="360" r="3" fill="${C.accent}"/><circle cx="${cx}" cy="360" r="3" fill="${C.light}"/><circle cx="${cx + 15}" cy="360" r="3" fill="${C.light}"/><text x="${cx}" y="388" text-anchor="middle" font-size="11" fill="${C.hint}" font-family="${C.uiFont}" letter-spacing="2"><tspan leaf="">向下滑动开始阅读</tspan></text></g>`;
  svg += `<g opacity="0"><animate attributeName="opacity" values="0;0.6" dur="0.4s" begin="4.3s" fill="freeze"/><g transform="translate(${cx},340)"><text x="0" y="0" text-anchor="middle" font-size="16" fill="${C.hint}" font-family="sans-serif"><tspan leaf="">↓</tspan><animateTransform attributeName="transform" type="translate" values="${cx} 340;${cx} 348;${cx} 340" dur="1.5s" begin="4.5s" repeatCount="indefinite" calcMode="spline" keyTimes="0;0.5;1" keySplines="0.4 0 0.6 1;0.4 0 0.6 1"/></text></g></g>`;
  svg += `</svg>`;
  return svg;
}

// ─── 模板 2: 打字机流 ──────────────────────────────────
function templateTypewriter(C, opts) {
  const W = 640, H = 280, cx = W / 2;

  // 品牌标签去掉（zhijian 主题左上角已有智见AI，重复）
  // 主标题紧贴顶部，压缩纵向空档
  const titleStart = 0.3;
  const title = buildTypewriter(opts.title || '', cx, 65, 48, C.text, C.monoFont, titleStart, 0.13, C.accent);
  const lineDelay = title.endDelay + 0.3;
  const subStart = lineDelay + 0.8 + 0.2;
  const subtitle = buildTypewriter(opts.subtitle || '', cx, 140, 26, C.tertiary, C.serifFont, subStart, 0.08, C.accent);
  const hintStart = subtitle.endDelay + 0.3;
  const hint = buildTypewriter('> 向下滑动继续阅读', cx, 210, 18, C.accent, C.monoFont, hintStart, 0.07, C.accent);
  const hintCursorBlink = hint.lastCursorX + 2;
  const arrowDelay = hint.endDelay + 0.5;

  let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMin meet" style="display:block;width:100%;max-width:${W}px;margin:0 auto;">`;
  svg += `<rect x="0" y="0" width="${W}" height="${H}" fill="${C.bg}"/>`;
  svg += title.svg;
  // 横线:rect + animate width(dur 0.8s) — y 跟随标题底部（标题 y=65，font-size=48）
  svg += `<rect x="${title.sx.toFixed(1)}" y="85" width="0" height="2.5" rx="1.25" fill="${C.accent}" opacity="0"><animate attributeName="width" values="0;${title.totalW.toFixed(1)}" dur="0.8s" begin="${lineDelay.toFixed(2)}s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.22 1 0.36 1"/><animate attributeName="opacity" values="0;1" dur="0.05s" begin="${lineDelay.toFixed(2)}s" fill="freeze"/></rect>`;
  svg += subtitle.svg;
  svg += hint.svg;
  // 提示光标:亮0.6s 灭0.6s — y 跟随提示文字底部（提示 y=210，font-size=16）
  svg += `<rect x="${hintCursorBlink.toFixed(1)}" y="196" width="2" height="18" fill="${C.accent}" opacity="0"><animate attributeName="opacity" values="0;1" dur="0.05s" begin="${hint.endDelay.toFixed(2)}s" fill="freeze"/><animate attributeName="opacity" values="1;1;0;0" dur="1.2s" begin="${(hint.endDelay + 0.1).toFixed(2)}s" repeatCount="indefinite"/></rect>`;
  // 箭头 — y=240（提示文字下方）
  svg += `<g opacity="0"><animate attributeName="opacity" values="0;0.5" dur="0.4s" begin="${arrowDelay.toFixed(2)}s" fill="freeze"/><g transform="translate(${cx},245)"><text x="0" y="0" text-anchor="middle" font-size="18" fill="${C.hint}" font-family="sans-serif"><tspan leaf="">↓</tspan><animateTransform attributeName="transform" type="translate" values="${cx} 245;${cx} 253;${cx} 245" dur="1.5s" begin="${(arrowDelay + 0.2).toFixed(2)}s" repeatCount="indefinite" calcMode="spline" keyTimes="0;0.5;1" keySplines="0.4 0 0.6 1;0.4 0 0.6 1"/></text></g></g>`;
  svg += `</svg>`;
  return svg;
}

// ─── 模板 3: 画卷展开 ──────────────────────────────────
function templateScrollPainting(C, opts) {
  const W = 640, H = 380, cx = W / 2;

  let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMin meet" style="display:block;width:100%;max-width:${W}px;margin:0 auto;">`;
  svg += `<rect x="0" y="0" width="${W}" height="${H}" fill="${C.bg}"/>`;

  // 上方横线:从左到右
  svg += `<rect x="60" y="119" width="0" height="1.5" rx="0.75" fill="${C.tertiary}"><animate attributeName="width" values="0;520" dur="0.6s" begin="0.2s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.25 0.1 0.25 1"/></rect>`;

  // 主标题上浮
  if (opts.title) {
    svg += `<g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.6s" begin="0.8s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.25 0.1 0.25 1"/><animateTransform attributeName="transform" type="translate" values="0 25;0 0" dur="0.6s" begin="0.8s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.25 0.1 0.25 1"/><text x="${cx}" y="170" text-anchor="middle" font-size="40" font-weight="500" fill="${C.text}" font-family="${C.headingFont}"><tspan leaf="">${opts.title}</tspan></text></g>`;
  }

  // 下方横线:从右到左
  svg += `<rect x="60" y="199" width="0" height="1.5" rx="0.75" fill="${C.tertiary}"><animate attributeName="width" values="0;520" dur="0.5s" begin="1.3s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.25 0.1 0.25 1"/><animate attributeName="x" values="580;60" dur="0.5s" begin="1.3s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.25 0.1 0.25 1"/></rect>`;

  // 副标题
  if (opts.subtitle) {
    svg += `<text x="${cx}" y="245" text-anchor="middle" font-size="17" fill="${C.tertiary}" font-family="${C.serifFont}" opacity="0"><tspan leaf="">${opts.subtitle}</tspan><animate attributeName="opacity" values="0;1" dur="0.6s" begin="1.8s" fill="freeze"/></text>`;
  }

  // 日期标记
  const dateStr = opts.date || new Date().toISOString().slice(0, 7).replace('-', '.');
  svg += `<g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.4s" begin="2.3s" fill="freeze"/><text x="60" y="310" font-size="11" fill="${C.hint}" font-family="${C.uiFont}" letter-spacing="1"><tspan leaf="">${dateStr}</tspan></text><rect x="60" y="316" width="100" height="1" fill="${C.light}"/></g>`;

  // 作者标记
  const author = opts.author || (C.topLabel || '').replace(/[·].*/, '').trim();
  if (author) {
    svg += `<g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.4s" begin="2.5s" fill="freeze"/><text x="580" y="310" text-anchor="end" font-size="11" fill="${C.hint}" font-family="${C.uiFont}" letter-spacing="1"><tspan leaf="">${author} 出品</tspan></text><rect x="480" y="316" width="100" height="1" fill="${C.light}"/></g>`;
  }

  // 向下滑动
  svg += `<g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.5s" begin="3.0s" fill="freeze"/><text x="${cx}" y="350" text-anchor="middle" font-size="11" fill="${C.hint}" font-family="${C.uiFont}" letter-spacing="2"><tspan leaf="">向下滑动查看全文</tspan></text><g transform="translate(${cx},360)"><text x="0" y="0" text-anchor="middle" font-size="14" fill="${C.hint}" font-family="sans-serif"><tspan leaf="">↓</tspan><animateTransform attributeName="transform" type="translate" values="${cx} 360;${cx} 368;${cx} 360" dur="1.5s" begin="3.3s" repeatCount="indefinite" calcMode="spline" keyTimes="0;0.5;1" keySplines="0.4 0 0.6 1;0.4 0 0.6 1"/></text></g></g>`;
  svg += `</svg>`;
  return svg;
}

// ─── 模板 4: 聚焦聚光灯 ────────────────────────────────
function templateSpotlight(C, opts) {
  const W = 640, H = 400, cx = W / 2;
  const tagList = opts.tags ? opts.tags.split(',').map(t => t.trim()).filter(Boolean) : [];

  let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMin meet" style="display:block;width:100%;max-width:${W}px;margin:0 auto;">`;
  svg += `<rect x="0" y="0" width="${W}" height="${H}" fill="${C.bg}"/>`;

  // 聚光灯渐变
  svg += `<defs><radialGradient id="spotlight-${Date.now()}"><stop offset="0%" stop-color="${C.accent}" stop-opacity="0.12"/><stop offset="60%" stop-color="${C.accent}" stop-opacity="0.04"/><stop offset="100%" stop-color="${C.accent}" stop-opacity="0"/></radialGradient></defs>`;
  svg += `<circle cx="${cx}" cy="170" r="0" fill="url(#spotlight-${Date.now()})"><animate attributeName="r" values="0;200" dur="0.8s" begin="0.3s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.25 0.1 0.25 1"/></circle>`;

  // 品牌标签
  if (C.topLabel) {
    svg += `<text x="${cx}" y="60" text-anchor="middle" font-size="13" font-weight="600" fill="${C.accent}" letter-spacing="4" font-family="${C.uiFont}" opacity="0"><tspan leaf="">${C.topLabel} · 深度评测</tspan><animate attributeName="opacity" values="0;1" dur="0.5s" begin="0.8s" fill="freeze"/></text>`;
  }

  // 主标题:缩放放大
  if (opts.title) {
    svg += `<g transform="translate(${cx},170) scale(0.3)" opacity="0"><animateTransform attributeName="transform" type="scale" additive="sum" values="0.3;1.1;1" dur="1.2s" begin="1.2s" fill="freeze" calcMode="spline" keyTimes="0;0.7;1" keySplines="0.25 0.1 0.25 1;0.4 0 0.6 1"/><animate attributeName="opacity" values="0;1" dur="0.4s" begin="1.2s" fill="freeze"/><text x="0" y="0" text-anchor="middle" font-size="44" font-weight="500" fill="${C.text}" font-family="${C.headingFont}"><tspan leaf="">${opts.title}</tspan></text></g>`;
  }

  // 粗短线
  svg += `<rect x="${cx - 50}" y="208" width="0" height="4" rx="2" fill="${C.accent}" opacity="0"><animate attributeName="width" values="0;100" dur="0.3s" begin="2.5s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.22 1 0.36 1"/><animate attributeName="opacity" values="0;1" dur="0.05s" begin="2.5s" fill="freeze"/></rect>`;

  // 副标题
  if (opts.subtitle) {
    svg += `<text x="${cx}" y="255" text-anchor="middle" font-size="18" fill="${C.tertiary}" font-family="${C.serifFont}" opacity="0"><tspan leaf="">${opts.subtitle}</tspan><animate attributeName="opacity" values="0;1" dur="0.5s" begin="2.8s" fill="freeze"/></text>`;
  }

  // 判断标签
  if (tagList.length >= 2) {
    svg += `<g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.4s" begin="3.2s" fill="freeze"/><rect x="${cx - 110}" y="300" width="100" height="30" rx="4" fill="${C.accent}"/><text x="${cx - 60}" y="319" text-anchor="middle" font-size="12" font-weight="600" fill="#fff" font-family="${C.uiFont}"><tspan leaf="">${tagList[0]}</tspan></text></g>`;
    svg += `<g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.4s" begin="3.5s" fill="freeze"/><rect x="${cx + 10}" y="300" width="100" height="30" rx="4" fill="none" stroke="${C.secondary}" stroke-width="1.5"/><text x="${cx + 60}" y="319" text-anchor="middle" font-size="12" font-weight="600" fill="${C.secondary}" font-family="${C.uiFont}"><tspan leaf="">${tagList[1]}</tspan></text></g>`;
  }

  // 向下滑动
  svg += `<g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.5s" begin="4.0s" fill="freeze"/><text x="${cx}" y="370" text-anchor="middle" font-size="11" fill="${C.hint}" font-family="${C.uiFont}" letter-spacing="2"><tspan leaf="">向下滑动查看深度分析</tspan></text><g transform="translate(${cx},380)"><text x="0" y="0" text-anchor="middle" font-size="14" fill="${C.hint}" font-family="sans-serif"><tspan leaf="">↓</tspan><animateTransform attributeName="transform" type="translate" values="${cx} 380;${cx} 388;${cx} 380" dur="1.5s" begin="4.3s" repeatCount="indefinite" calcMode="spline" keyTimes="0;0.5;1" keySplines="0.4 0 0.6 1;0.4 0 0.6 1"/></text></g></g>`;
  svg += `</svg>`;
  return svg;
}

// ─── 模板 5: 极简白描 ──────────────────────────────────
function templateMinimalSketch(C, opts) {
  const W = 640, H = 480, cx = W / 2;

  let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMin meet" style="display:block;width:100%;max-width:${W}px;margin:0 auto;">`;
  svg += `<rect x="0" y="0" width="${W}" height="${H}" fill="${C.bg}"/>`;

  // 主标题:直接淡入,延迟0.5s
  if (opts.title) {
    svg += `<text x="${cx}" y="220" text-anchor="middle" font-size="36" font-weight="400" fill="${C.text}" font-family="${C.headingFont}" opacity="0"><tspan leaf="">${opts.title}</tspan><animate attributeName="opacity" values="0;1" dur="1s" begin="0.5s" fill="freeze"/></text>`;
  }

  // 细线
  svg += `<rect x="${cx - 40}" y="249" width="0" height="1" rx="0.5" fill="${C.tertiary}" opacity="0.6"><animate attributeName="width" values="0;80" dur="0.8s" begin="1.5s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.22 1 0.36 1"/></rect>`;

  // 副标题
  if (opts.subtitle) {
    svg += `<text x="${cx}" y="290" text-anchor="middle" font-size="16" fill="${C.tertiary}" font-family="${C.serifFont}" opacity="0"><tspan leaf="">${opts.subtitle}</tspan><animate attributeName="opacity" values="0;1" dur="0.8s" begin="2.2s" fill="freeze"/></text>`;
  }

  // 呼吸圆点
  svg += `<circle cx="${cx}" cy="400" r="5" fill="${C.accent}" opacity="0"><animate attributeName="opacity" values="0;0.3;0.8;0.3;0" dur="2s" begin="2.8s" repeatCount="indefinite"/><animate attributeName="r" values="5;7;5" dur="2s" begin="2.8s" repeatCount="indefinite" calcMode="spline" keyTimes="0;0.5;1" keySplines="0.4 0 0.6 1;0.4 0 0.6 1"/></circle>`;
  svg += `</svg>`;
  return svg;
}

// ─── 主入口:从主题生成开场动画 ────────────────────────
const TEMPLATES = {
  'ink-wash': templateInkWash,
  'typewriter': templateTypewriter,
  'scroll-painting': templateScrollPainting,
  'spotlight': templateSpotlight,
  'minimal-sketch': templateMinimalSketch,
};

export function generateCoverAnimation(theme, options = {}) {
  const {
    template = 'ink-wash',
    title = '',
    subtitle = '',
    tags = '',
    date = '',
    author = '',
  } = options;

  // 从主题取色(带兜底)
  const C = {
    bg: theme.background_color || '#F5F4ED',
    accent: theme.accent_color || '#B85235',
    secondary: theme.accent_secondary || theme.trust_blue || '#1B365D',
    text: theme.text_color || '#141413',
    tertiary: theme.tertiary_color || theme.secondary_color || '#6B6A64',
    light: '#D8D5C8',
    hint: '#9CA3AF',
    headingFont: theme.heading_font || "'TsangerJinKai02','Source Han Serif SC','Songti SC',Georgia,serif",
    serifFont: theme.font_family_cn || "'Source Han Serif SC','Songti SC',serif",
    uiFont: theme.ui_font || "'Source Han Sans SC','PingFang SC',sans-serif",
    monoFont: theme.code_font || "'JetBrains Mono','SF Mono',Consolas,Monaco,monospace",
    topLabel: theme.top_label || '',
  };

  const fn = TEMPLATES[template] || TEMPLATES['ink-wash'];
  return fn(C, { title, subtitle, tags, date, author });
}

// ─── CLI 入口 ──────────────────────────────────────────
function main() {
  const opts = parseArgs();

  if (!opts.title) {
    console.error('错误: 必须提供 --title 参数');
    process.exit(1);
  }

  let theme = {};
  try {
    theme = loadTheme(opts.theme);
  } catch (e) {
    console.warn(`警告: ${e.message},使用默认颜色`);
  }

  if (opts.accentColor) theme.accent_color = opts.accentColor;
  if (opts.bgColor) theme.background_color = opts.bgColor;

  const svg = generateCoverAnimation(theme, {
    template: opts.template,
    title: opts.title,
    subtitle: opts.subtitle,
    tags: opts.tags,
  });

  if (opts.output) {
    fs.writeFileSync(opts.output, svg);
    console.log(`✓ 开场动画已生成: ${opts.output} (${svg.length} 字符, 模板: ${opts.template})`);
  } else {
    process.stdout.write(svg);
  }
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) main();

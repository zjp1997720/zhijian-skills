// 画布、文字和时间轴。基态永远等于终态，动画只负责“先收起、再按序回来”或“高亮巡游”。
import { glyphPath } from './fonts.mjs';

export const W = 360;
export const M = 20;
export const INNER = W - 2 * M;
export const EASE = '0.42 0 0.58 1';
export const OUT = '0.16 1 0.3 1';
export const LIN = '0 0 1 1';
export const RESET_FROM = 0.4;
export const RESET_TO = 0.7;
export const BUILD_FROM = 0.8;
export const HOLD_TAIL = 2.2;
const FONT_STACK = '"Noto Sans SC","PingFang SC","Microsoft YaHei",sans-serif';
const NO_LINE_START = '，。、；：！？）';
const LINE_END_PUNCT = '，。、；：！？';

/** 规格写得放不下或不合规，消息直接告诉写规格的人怎么改。 */
export class SpecError extends Error {
  constructor(message) {
    super(message);
    this.name = 'SpecError';
  }
}

/** 定点格式化；精确落在舍入中点时取偶数，和字形路径、时间轴的一位小数约定一致。 */
export function fixed(value, digits = 1) {
  const abs = Math.abs(value);
  const exact = abs.toFixed(100).split('.');
  const tail = exact[1].slice(digits);
  let text = abs.toFixed(digits);
  if (/^50*$/.test(tail)) {
    const lastDigit = Number((exact[0] + exact[1].slice(0, digits)).at(-1));
    if (lastDigit % 2 === 0) text = digits ? `${exact[0]}.${exact[1].slice(0, digits)}` : exact[0];
  }
  return (value < 0 || Object.is(value, -0) ? '-' : '') + text;
}

export function round(value, digits = 0) {
  return Number(fixed(value, digits));
}

const trimZeros = (text) => (text.includes('.') ? text.replace(/0+$/, '').replace(/\.$/, '') : text);

export function num(value) {
  return trimZeros(fixed(value, 1));
}

export function escapeText(value) {
  return String(value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

/** 布局用的估算宽度；真实宽度由 gates 在浏览器里复核。 */
export function estWidth(text, size) {
  let total = 0;
  for (const char of String(text)) {
    if (char.codePointAt(0) > 0x2E7F) total += 1;
    else if (" .,:;!|'".includes(char)) total += 0.32;
    else if (/\p{Lu}/u.test(char)) total += 0.68;
    else if (/\p{Nd}/u.test(char)) total += 0.6;
    else total += 0.56;
  }
  return total * size;
}

/** 按估算宽度折行，标点不落到行首。 */
export function wrap(text, size, maxWidth) {
  const lines = [];
  let cur = '';
  for (const token of text.match(/[A-Za-z0-9_.+\-/~@]+|\s|./gu) || []) {
    if (cur && estWidth(cur + token, size) > maxWidth && !NO_LINE_START.includes(token)) {
      lines.push(cur.trimEnd());
      cur = token.trimStart();
    } else {
      cur += token;
    }
  }
  if (cur.trim()) lines.push(cur.trimEnd());
  return lines;
}

/** 折两行时选最匀称的断点，优先断在标点后，避免“么长”“美元”这种孤行。 */
export function balance(text, size, maxWidth, lines = 2) {
  if (estWidth(text, size) <= maxWidth) return [text];
  const greedy = wrap(text, size, maxWidth);
  if (greedy.length !== 2 || lines !== 2) return greedy;
  const tokens = text.match(/[A-Za-z0-9_.+\-/~@%]+|\s|./gu) || [];
  let best = greedy;
  let bestScore = Infinity;
  for (let i = 1; i < tokens.length; i += 1) {
    const a = tokens.slice(0, i).join('').trimEnd();
    const b = tokens.slice(i).join('').trimStart();
    if (!a || !b || NO_LINE_START.includes([...b][0]) || estWidth(a, size) > maxWidth || estWidth(b, size) > maxWidth) continue;
    const score = Math.abs(estWidth(a, size) - estWidth(b, size)) - (LINE_END_PUNCT.includes([...a].at(-1)) ? size * 6 : 0);
    if (score < bestScore) {
      best = [a, b];
      bestScore = score;
    }
  }
  return best;
}

/** frames: [[秒, 值, 进入该帧的缓动]]。 */
function anim(attr, frames, dur, type = null) {
  const keyTimes = frames.map(([t]) => (t === 0 ? '0' : trimZeros(fixed(t / dur, 4)))).join(';');
  const values = frames.map(([, v]) => v).join(';');
  const splines = frames.slice(1).map(([, , s]) => s).join(';');
  const [tag, typeAttr] = type ? ['animateTransform', ` type="${type}"`] : ['animate', ''];
  return `<${tag} attributeName="${attr}"${typeAttr} values="${values}" keyTimes="${keyTimes}" calcMode="spline" `
    + `keySplines="${splines}" dur="${num(round(dur, 2))}s" begin="0s" repeatCount="indefinite"/>`;
}

export class Fig {
  constructor(spec, theme, { font = null, holdTail = HOLD_TAIL } = {}) {
    this.spec = spec;
    this.t = theme;
    this.font = font;
    this.holdTail = holdTail;
    this.parts = [];
    this.end = BUILD_FROM;
    this.mode = 'build';
    this.fixedDur = null;
  }

  // —— 绘制 ——
  add(part) {
    this.parts.push(part);
  }

  text(s, x, y, size, fill, { weight = null, anchor = 'start', box = null, aux = false } = {}) {
    if (size < 12) throw new SpecError(`字号 ${size} 小于手机下限 12：${s}`);
    let attrs = weight ? ` font-weight="${weight}"` : '';
    if (anchor !== 'start') attrs += ` text-anchor="${anchor}"`;
    if (box) attrs += ` data-box="${box.map(num).join(',')}"`;
    if (aux) attrs += ' data-aux="1"';
    return `<text x="${num(x)}" y="${num(y)}" font-size="${size}"${attrs} fill="${fill}">${escapeText(s)}</text>`;
  }

  rect(x, y, w, h, fill = 'none', stroke = null, sw = 1, rx = 8) {
    const st = stroke ? ` stroke="${stroke}" stroke-width="${sw}"` : '';
    return `<rect x="${num(x)}" y="${num(y)}" width="${num(w)}" height="${num(h)}" rx="${rx}" fill="${fill}"${st}/>`;
  }

  line(x1, y1, x2, y2, stroke = null, sw = 1) {
    return `<line x1="${num(x1)}" y1="${num(y1)}" x2="${num(x2)}" y2="${num(y2)}" `
      + `stroke="${stroke || this.t.rule}" stroke-width="${sw}" stroke-linecap="round"/>`;
  }

  display(s, x, baseline, size, fill, anchor = 'middle') {
    return `<path d="${glyphPath(this.font, s, size, x, baseline, anchor).d}" fill="${fill}"/>`;
  }

  displayWidth(s, size) {
    return glyphPath(this.font, s, size, 0, 0).width;
  }

  // —— 时间轴：enter 系列的基态都是终态 ——
  claim(at, d) {
    this.end = Math.max(this.end, at + d);
  }

  /** 先收起再回来。how: fade 淡入 / rise 上浮 / grow 从 origin 沿 x 轴生长（markup 用局部坐标）。 */
  enter(markup, at, d = 0.4, how = 'fade', origin = [0, 0]) {
    this.claim(at, d);
    this.add((dur) => {
      const op = [[0, 1, LIN], [RESET_FROM, 1, LIN], [RESET_TO, 0, EASE], [at, 0, LIN]];
      if (how === 'grow') {
        op.push([at + 0.02, 1, LIN], [dur, 1, LIN]);
        const sc = [[0, '1 1', LIN], [RESET_TO, '1 1', LIN], [at, '0.02 1', LIN], [at + d, '1 1', OUT], [dur, '1 1', LIN]];
        return `<g>${anim('opacity', op, dur)}<g transform="translate(${num(origin[0])} ${num(origin[1])})">`
          + `<g>${anim('transform', sc, dur, 'scale')}${markup}</g></g></g>`;
      }
      op.push([at + d, 1, OUT], [dur, 1, LIN]);
      if (how === 'rise') {
        const tr = [[0, '0 0', LIN], [RESET_TO, '0 0', LIN], [at, '0 10', LIN], [at + d, '0 0', OUT], [dur, '0 0', LIN]];
        return `<g>${anim('opacity', op, dur)}<g>${anim('transform', tr, dur, 'translate')}${markup}</g></g>`;
      }
      return `<g>${anim('opacity', op, dur)}${markup}</g>`;
    });
  }

  /** 基态隐藏的辅助高亮（不承载语义）：windows=[[开始, 结束], ...]。 */
  glow(markup, windows) {
    this.claim(windows.at(-1)[1], 0);
    this.add((dur) => {
      const fr = [[0, 0, LIN]];
      for (const [a, b] of windows) fr.push([a, 0, LIN], [a + 0.15, 1, EASE], [b, 1, LIN], [Math.min(b + 0.15, dur), 0, EASE]);
      if (fr.at(-1)[0] < dur) fr.push([dur, 0, LIN]);
      return `<g opacity="0">${anim('opacity', fr, dur)}${markup}</g>`;
    });
  }

  /** 显式写透明度曲线的元素（数字切换用）；frames 首尾必须等于基态 1。 */
  swap(markup, frames) {
    this.claim(frames.at(-1)[0], 0);
    this.add((dur) => `<g>${anim('opacity', [...frames, [dur, 1, LIN]], dur)}${markup}</g>`);
  }

  /** 沿折线走的小圆点，基态隐藏。 */
  tracer(points, at, d, r = 5) {
    this.claim(at, d);
    this.add((dur) => {
      const n = points.length - 1;
      const pair = ([x, y]) => `${num(x)} ${num(y)}`;
      const tr = [[0, pair(points[0]), LIN]];
      if (at > 0) tr.push([at, pair(points[0]), LIN]);
      points.slice(1).forEach((p, i) => tr.push([at + (d * (i + 1)) / n, pair(p), LIN]));
      if (tr.at(-1)[0] < dur) tr.push([dur, pair(points.at(-1)), LIN]);
      const op = [[0, 0, LIN], [at, 0, LIN], [at + 0.1, 1, EASE], [at + d, 1, LIN], [Math.min(at + d + 0.12, dur), 0, EASE]];
      if (op.at(-1)[0] < dur) op.push([dur, 0, LIN]);
      return `<g opacity="0">${anim('opacity', op, dur)}${anim('transform', tr, dur, 'translate')}`
        + `<circle cx="0" cy="0" r="${r}" fill="${this.t.dot}"/></g>`;
    });
  }

  // —— 组装 ——
  duration() {
    return this.fixedDur || round(this.end + this.holdTail, 2);
  }

  /** 返回 {svg 发布版, qa 质检版, dur}。质检版多 data-* 标记。 */
  render(height) {
    const dur = this.duration();
    const body = this.parts.map((p) => (typeof p === 'function' ? p(dur) : p)).join('');
    const h = round(height);
    const qa = `<svg viewBox="0 0 ${W} ${h}" width="${W}" height="${h}" xmlns="http://www.w3.org/2000/svg" `
      + `style='display:block;width:100%;max-width:100%;height:auto;font-family:${FONT_STACK};'>`
      + `<rect x="0" y="0" width="${W}" height="${h}" fill="${this.t.bg}"/>${body}</svg>`;
    return { svg: qa.replace(/ data-(?:box|aux)="[^"]*"/g, ''), qa, dur };
  }
}

export function stripAnimation(svg) {
  return svg.replace(/<animate(?:Transform)?\b[^>]*\/>/g, '');
}

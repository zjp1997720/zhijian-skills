// 规格 → SVG：固定骨架（眉题、结论标题、图解、结论句）+ 一种结构。
import { Fig, INNER, M, SpecError, W, balance, fixed } from './core.mjs';
import { BUILDERS } from './primitives.mjs';

const TITLE_SIZE = 24;

export function contrast(a, b) {
  const lum = (hex) => {
    const [r, g, bl] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
      .map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
    return 0.2126 * r + 0.7152 * g + 0.0722 * bl;
  };
  const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

export function buildFigure(spec, theme, { font = null, holdTail } = {}) {
  const { type, title, conclusion } = spec;
  if (!Object.hasOwn(BUILDERS, type ?? '')) throw new SpecError(`type 只能是 ${Object.keys(BUILDERS).sort().join('、')}，收到 ${type}`);
  if (!title || !conclusion) throw new SpecError('每张图都要有 title（结论式标题）和 conclusion（结论句）');
  const f = new Fig(spec, theme, { font, holdTail });
  if (spec.kicker) f.add(f.text(spec.kicker, W / 2, 28, 12, theme.faint, { anchor: 'middle' }));
  const titleWidth = f.displayWidth(title, TITLE_SIZE);
  if (titleWidth > INNER) throw new SpecError(`标题「${title}」宽 ${fixed(titleWidth, 0)}px，超过 ${INNER}px；控制在 13 个汉字内`);
  f.add(f.display(title, W / 2, 60, TITLE_SIZE, theme.text));
  f.add(f.line(M, 76, W - M, 76));
  const bottom = BUILDERS[type](f, spec, 76);
  let y = bottom + 14;
  f.add(f.line(M, y, W - M, y));
  const lines = balance(conclusion, 15, INNER);
  if (lines.length > 2) throw new SpecError(`结论句超过两行：${conclusion}`);
  y += 26;
  for (const ln of lines) {
    f.add(f.text(ln, W / 2, y, 15, theme.text, { weight: 600, anchor: 'middle' }));
    y += 23;
  }
  const { svg, qa, dur } = f.render(y - 23 + 20);
  return { svg, qa, dur, mode: f.mode, theme: theme.name, title, conclusion, type };
}

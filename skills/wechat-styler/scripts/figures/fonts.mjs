// 字体解析放在这里，只有文章真的用到图解时才加载 opentype.js。
import fs from 'node:fs';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const fixedRound = (value) => Number(value.toFixed(1));
const short = (value) => {
  const text = value.toFixed(1);
  return text.endsWith('.0') ? text.slice(0, -2) : text;
};

export function loadFont(fontPath) {
  const opentype = require('opentype.js');
  const buffer = fs.readFileSync(fontPath);
  return opentype.parse(buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength));
}

export function missingChars(font, text) {
  return [...text].filter((char) => font.charToGlyphIndex(char) === 0);
}

/** 字形转路径，相对坐标 + 一位小数比绝对坐标短约三分之一。返回 {d, width}。 */
export function glyphPath(font, text, size, x, baseline, anchor = 'middle') {
  const k = size / font.unitsPerEm;
  const glyphs = [...text].map((char) => font.charToGlyph(char));
  const width = glyphs.reduce((sum, glyph) => sum + glyph.advanceWidth, 0) * k;
  let cursor = anchor === 'middle' ? x - width / 2 : x;
  const out = [];
  for (const glyph of glyphs) {
    const pt = (px, py) => [fixedRound(cursor + px * k), fixedRound(baseline - py * k)];
    let [cx, cy] = [0, 0];
    let raw = null;
    const rel = ([ax, ay]) => `${short(fixedRound(ax - cx))} ${short(fixedRound(ay - cy))}`;
    for (const c of glyph.path.commands) {
      if (c.type === 'Z') {
        out.push('z');
        continue;
      }
      // opentype.js 会在每段曲线后补一条零长直线，字形路径里不需要。
      if (c.type === 'L' && raw && raw[0] === c.x && raw[1] === c.y) continue;
      raw = [c.x, c.y];
      const p = pt(c.x, c.y);
      if (c.type === 'M') out.push(`M${short(p[0])} ${short(p[1])}`);
      else if (c.type === 'L') out.push(`l${rel(p)}`);
      else if (c.type === 'Q') out.push(`q${rel(pt(c.x1, c.y1))} ${rel(p)}`);
      else if (c.type === 'C') out.push(`c${rel(pt(c.x1, c.y1))} ${rel(pt(c.x2, c.y2))} ${rel(p)}`);
      [cx, cy] = p;
    }
    cursor += glyph.advanceWidth * k;
  }
  return { d: out.join(''), width };
}

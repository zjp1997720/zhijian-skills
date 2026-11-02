// 图解测试共用：造一个临时字体，让测试不依赖本机是否装了某个字体；浏览器拿不到时跳过渲染检查。
import { createRequire } from 'node:module';

import { resolveBrowserLaunch } from '../scripts/qa-browser.mjs';

const require = createRequire(import.meta.url);

/** 每个字符画成一个方块，CJK 占满一个字宽，其余占 0.6。 */
export function makeTestFont(text) {
  const opentype = require('opentype.js');
  const box = (advance) => {
    const path = new opentype.Path();
    path.moveTo(60, -80);
    path.lineTo(advance - 60, -80);
    path.lineTo(advance - 60, 760);
    path.lineTo(60, 760);
    path.close();
    return path;
  };
  const glyphs = [new opentype.Glyph({ name: '.notdef', unicode: 0, advanceWidth: 600, path: new opentype.Path() })];
  [...new Set(text)].forEach((char, i) => {
    const advance = char.codePointAt(0) > 0x2E7F ? 1000 : 600;
    glyphs.push(new opentype.Glyph({ name: `g${i}`, unicode: char.codePointAt(0), advanceWidth: advance, path: char === ' ' ? new opentype.Path() : box(advance) }));
  });
  const font = new opentype.Font({ familyName: 'FigureTest', styleName: 'Regular', unitsPerEm: 1000, ascender: 800, descender: -200, glyphs });
  return opentype.parse(font.toArrayBuffer());
}

/** 返回可用的 Chromium；CI 没有浏览器时返回 {browser: null, reason}。 */
export async function launchBrowser() {
  try {
    const { chromium } = await import('playwright-core');
    const { source, ...launch } = resolveBrowserLaunch();
    return { browser: await chromium.launch(launch), source };
  } catch (error) {
    return { browser: null, reason: `没有可用浏览器，渲染检查跳过：${error.message.split('\n')[0]}` };
  }
}

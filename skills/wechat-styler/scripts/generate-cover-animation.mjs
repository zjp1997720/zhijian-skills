/**
 * generate-cover-animation.mjs
 * 从主题色 + 标题参数生成公众号开场 SVG 动画
 *
 * 6 个模板:
 *   ink-wash       墨韵开篇(默认 · 方法论/品牌)
 *   typewriter     打字机流(技术/教程 · 静态文字+光标动画)
 *   xiaolan-terminal 小蓝终端(品牌技术内容 · 小蓝接线+双色打字)
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
import zlib from 'zlib';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const inlineAssetCache = new Map();

function paethPredictor(a, b, c) {
  const p = a + b - c;
  const pa = Math.abs(p - a);
  const pb = Math.abs(p - b);
  const pc = Math.abs(p - c);
  if (pa <= pb && pa <= pc) return a;
  return pb <= pc ? b : c;
}

function decodeRgbaPng(assetPath) {
  const input = fs.readFileSync(assetPath);
  const signature = input.subarray(0, 8).toString('hex');
  if (signature !== '89504e470d0a1a0a') throw new Error(`小蓝像素资产不是 PNG: ${assetPath}`);

  let width = 0;
  let height = 0;
  let bitDepth = 0;
  let colorType = 0;
  let interlace = 0;
  const compressed = [];
  for (let offset = 8; offset < input.length;) {
    const length = input.readUInt32BE(offset);
    const type = input.subarray(offset + 4, offset + 8).toString('ascii');
    const data = input.subarray(offset + 8, offset + 8 + length);
    if (type === 'IHDR') {
      width = data.readUInt32BE(0);
      height = data.readUInt32BE(4);
      bitDepth = data[8];
      colorType = data[9];
      interlace = data[12];
    } else if (type === 'IDAT') {
      compressed.push(data);
    } else if (type === 'IEND') {
      break;
    }
    offset += length + 12;
  }

  if (!width || !height || bitDepth !== 8 || colorType !== 6 || interlace !== 0) {
    throw new Error(`小蓝像素资产必须是 8-bit RGBA 非交错 PNG: ${assetPath}`);
  }

  const bytesPerPixel = 4;
  const stride = width * bytesPerPixel;
  const raw = zlib.inflateSync(Buffer.concat(compressed));
  const pixels = new Uint8Array(width * height * bytesPerPixel);
  let sourceOffset = 0;
  for (let y = 0; y < height; y += 1) {
    const filter = raw[sourceOffset];
    sourceOffset += 1;
    const rowOffset = y * stride;
    const priorOffset = (y - 1) * stride;
    for (let x = 0; x < stride; x += 1) {
      const value = raw[sourceOffset + x];
      const left = x >= bytesPerPixel ? pixels[rowOffset + x - bytesPerPixel] : 0;
      const up = y > 0 ? pixels[priorOffset + x] : 0;
      const upperLeft = y > 0 && x >= bytesPerPixel ? pixels[priorOffset + x - bytesPerPixel] : 0;
      let decoded = value;
      if (filter === 1) decoded += left;
      else if (filter === 2) decoded += up;
      else if (filter === 3) decoded += Math.floor((left + up) / 2);
      else if (filter === 4) decoded += paethPredictor(left, up, upperLeft);
      else if (filter !== 0) throw new Error(`小蓝像素资产包含不支持的 PNG filter ${filter}: ${assetPath}`);
      pixels[rowOffset + x] = decoded & 0xff;
    }
    sourceOffset += stride;
  }
  return { width, height, pixels };
}

function parseHexColor(value) {
  const normalized = String(value || '#F5F4ED').replace('#', '');
  const hex = normalized.length === 3
    ? normalized.split('').map(char => char + char).join('')
    : normalized.padEnd(6, '0').slice(0, 6);
  return [0, 2, 4].map(index => Number.parseInt(hex.slice(index, index + 2), 16));
}

function preparePixelSamples(decoded, backgroundColor, targetWidth = 192) {
  const width = Math.min(decoded.width, targetWidth);
  const height = Math.max(1, Math.round(decoded.height * width / decoded.width));
  const background = parseHexColor(backgroundColor);
  const samples = new Array(width * height);

  for (let y = 0; y < height; y += 1) {
    const y0 = Math.floor(y * decoded.height / height);
    const y1 = Math.max(y0 + 1, Math.floor((y + 1) * decoded.height / height));
    for (let x = 0; x < width; x += 1) {
      const x0 = Math.floor(x * decoded.width / width);
      const x1 = Math.max(x0 + 1, Math.floor((x + 1) * decoded.width / width));
      let alphaTotal = 0;
      let redTotal = 0;
      let greenTotal = 0;
      let blueTotal = 0;
      let count = 0;
      for (let sourceY = y0; sourceY < y1; sourceY += 1) {
        for (let sourceX = x0; sourceX < x1; sourceX += 1) {
          const offset = (sourceY * decoded.width + sourceX) * 4;
          const alpha = decoded.pixels[offset + 3] / 255;
          alphaTotal += alpha;
          redTotal += decoded.pixels[offset] * alpha;
          greenTotal += decoded.pixels[offset + 1] * alpha;
          blueTotal += decoded.pixels[offset + 2] * alpha;
          count += 1;
        }
      }
      const alpha = alphaTotal / count;
      if (alpha <= 0.06) {
        samples[y * width + x] = null;
        continue;
      }
      const sourceAlpha = alphaTotal || 1;
      const red = redTotal / sourceAlpha * alpha + background[0] * (1 - alpha);
      const green = greenTotal / sourceAlpha * alpha + background[1] * (1 - alpha);
      const blue = blueTotal / sourceAlpha * alpha + background[2] * (1 - alpha);
      if (Math.hypot(red - background[0], green - background[1], blue - background[2]) < 7) {
        samples[y * width + x] = null;
        continue;
      }
      samples[y * width + x] = [red, green, blue];
    }
  }
  return { width, height, samples };
}

function buildWeightedPalette(samples, limit = 32) {
  const histogram = new Map();
  for (const color of samples) {
    if (!color) continue;
    const reduced = color.map(channel => Math.max(0, Math.min(255, Math.round(channel / 8) * 8)));
    const key = reduced.join(',');
    histogram.set(key, (histogram.get(key) || 0) + 1);
  }
  const entries = [...histogram.entries()].map(([key, count]) => ({
    color: key.split(',').map(Number),
    count,
  }));
  if (entries.length <= limit) return entries.map(entry => entry.color);

  const palette = [entries.reduce((best, entry) => entry.count > best.count ? entry : best).color.slice()];
  while (palette.length < limit) {
    let candidate = entries[0];
    let bestScore = -1;
    for (const entry of entries) {
      const nearest = Math.min(...palette.map(color => (
        (entry.color[0] - color[0]) ** 2
        + (entry.color[1] - color[1]) ** 2
        + (entry.color[2] - color[2]) ** 2
      )));
      const score = nearest * Math.log2(entry.count + 2);
      if (score > bestScore) {
        candidate = entry;
        bestScore = score;
      }
    }
    palette.push(candidate.color.slice());
  }

  for (let iteration = 0; iteration < 7; iteration += 1) {
    const sums = palette.map(() => [0, 0, 0, 0]);
    for (const entry of entries) {
      const index = nearestPaletteIndex(entry.color, palette);
      sums[index][0] += entry.color[0] * entry.count;
      sums[index][1] += entry.color[1] * entry.count;
      sums[index][2] += entry.color[2] * entry.count;
      sums[index][3] += entry.count;
    }
    for (let index = 0; index < palette.length; index += 1) {
      if (!sums[index][3]) continue;
      palette[index] = sums[index].slice(0, 3).map(channel => Math.round(channel / sums[index][3]));
    }
  }
  return palette;
}

function nearestPaletteIndex(color, palette) {
  let nearestIndex = 0;
  let nearestDistance = Number.POSITIVE_INFINITY;
  for (let index = 0; index < palette.length; index += 1) {
    const candidate = palette[index];
    const distance = (color[0] - candidate[0]) ** 2
      + (color[1] - candidate[1]) ** 2
      + (color[2] - candidate[2]) ** 2;
    if (distance < nearestDistance) {
      nearestIndex = index;
      nearestDistance = distance;
    }
  }
  return nearestIndex;
}

function loadNativeSvgPixelAsset(filename, backgroundColor, role) {
  const cacheKey = `${filename}:${backgroundColor}:${role}`;
  if (inlineAssetCache.has(cacheKey)) return inlineAssetCache.get(cacheKey);
  const assetPath = path.join(__dirname, '..', 'assets', filename);
  if (!fs.existsSync(assetPath)) {
    throw new Error(`小蓝像素资产不存在: ${assetPath}`);
  }
  const decoded = decodeRgbaPng(assetPath);
  const { width, height, samples } = preparePixelSamples(decoded, backgroundColor);
  const palette = buildWeightedPalette(samples);
  const runsByPalette = palette.map(() => []);

  for (let y = 0; y < height; y += 1) {
    let x = 0;
    while (x < width) {
      const sample = samples[y * width + x];
      if (!sample) {
        x += 1;
        continue;
      }
      const paletteIndex = nearestPaletteIndex(sample, palette);
      let runEnd = x + 1;
      while (runEnd < width) {
        const next = samples[y * width + runEnd];
        if (!next || nearestPaletteIndex(next, palette) !== paletteIndex) break;
        runEnd += 1;
      }
      const runWidth = runEnd - x;
      runsByPalette[paletteIndex].push(`M${x} ${y}h${runWidth}v1h-${runWidth}z`);
      x = runEnd;
    }
  }

  const paths = runsByPalette.map((runs, index) => {
    if (!runs.length) return '';
    const color = `#${palette[index].map(channel => Math.max(0, Math.min(255, channel)).toString(16).padStart(2, '0')).join('')}`;
    return `<path fill="${color}" d="${runs.join('')}"/>`;
  }).join('');
  const scaleX = 168 / width;
  const scaleY = 177 / height;
  const fragment = `<g data-xiaolan-asset="${role}" data-xiaolan-render="native-svg-pixels" data-source-size="${decoded.width}x${decoded.height}" data-pixel-size="${width}x${height}" transform="translate(20 18) scale(${scaleX.toFixed(6)} ${scaleY.toFixed(6)})" shape-rendering="crispEdges">${paths}</g>`;
  inlineAssetCache.set(cacheKey, fragment);
  return fragment;
}

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
    topLabel: null,
    author: null,
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
      case '--top-label': opts.topLabel = next ?? ''; i++; break;
      case '--author': opts.author = next ?? ''; i++; break;
      case '--help': case '-h':
        console.log(`用法: node generate-cover-animation.mjs --theme zhijian --template typewriter --title "标题" --subtitle "副标题" --tags "标签1,标签2" --output cover.svg\n\n  --top-label <文本|none>  品牌标签(默认主题 top_label);none 隐藏\n  --author <文本|none>     画卷署名,原样使用不加「出品」(默认「<top_label> 出品」);none 隐藏\n\n模板: ink-wash | typewriter | xiaolan-terminal | scroll-painting | spotlight | minimal-sketch`);
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

function measureTypewriterWidth(text, fontSize) {
  const chars = [...text];
  if (chars.length === 0) return 0;

  const width = chars.reduce((total, ch) => total + getCharWidth(ch, fontSize), 0);
  const gaps = chars.slice(0, -1).reduce((total, ch) => total + getCharGap(ch), 0);
  return width + gaps;
}

function fitTypewriterFontSize(text, preferredFontSize, maxWidth) {
  const preferredWidth = measureTypewriterWidth(text, preferredFontSize);
  if (!text || preferredWidth <= maxWidth) {
    return preferredFontSize;
  }

  let fontSize = Math.floor((preferredFontSize * maxWidth / preferredWidth) * 10) / 10;
  while (fontSize > 1 && measureTypewriterWidth(text, fontSize) > maxWidth) {
    fontSize = Math.round((fontSize - 0.1) * 10) / 10;
  }
  return Math.max(1, fontSize);
}

function normalizeTypewriterFont(font) {
  const safeFont = String(font || '').trim();
  if (/^['"]?SF Mono['"]?\s*,/.test(safeFont)) {
    return safeFont.replace(/^['"]?SF Mono['"]?\s*,\s*/, '');
  }
  return safeFont || "Menlo,Consolas,'Courier New',monospace";
}

// 5×7 bitmap alphabet for the pixel-terminal template. Unsupported scripts
// fall back to the normal static-baseline typewriter rather than becoming
// missing-glyph boxes.
const PIXEL_GLYPHS = {
  ' ': ['00000','00000','00000','00000','00000','00000','00000'],
  'A': ['01110','10001','10001','11111','10001','10001','10001'],
  'B': ['11110','10001','10001','11110','10001','10001','11110'],
  'C': ['01111','10000','10000','10000','10000','10000','01111'],
  'D': ['11110','10001','10001','10001','10001','10001','11110'],
  'E': ['11111','10000','10000','11110','10000','10000','11111'],
  'F': ['11111','10000','10000','11110','10000','10000','10000'],
  'G': ['01111','10000','10000','10111','10001','10001','01111'],
  'H': ['10001','10001','10001','11111','10001','10001','10001'],
  'I': ['11111','00100','00100','00100','00100','00100','11111'],
  'J': ['00111','00010','00010','00010','00010','10010','01100'],
  'K': ['10001','10010','10100','11000','10100','10010','10001'],
  'L': ['10000','10000','10000','10000','10000','10000','11111'],
  'M': ['10001','11011','10101','10101','10001','10001','10001'],
  'N': ['10001','11001','10101','10011','10001','10001','10001'],
  'O': ['01110','10001','10001','10001','10001','10001','01110'],
  'P': ['11110','10001','10001','11110','10000','10000','10000'],
  'Q': ['01110','10001','10001','10001','10101','10010','01101'],
  'R': ['11110','10001','10001','11110','10100','10010','10001'],
  'S': ['01111','10000','10000','01110','00001','00001','11110'],
  'T': ['11111','00100','00100','00100','00100','00100','00100'],
  'U': ['10001','10001','10001','10001','10001','10001','01110'],
  'V': ['10001','10001','10001','10001','10001','01010','00100'],
  'W': ['10001','10001','10001','10101','10101','10101','01010'],
  'X': ['10001','10001','01010','00100','01010','10001','10001'],
  'Y': ['10001','10001','01010','00100','00100','00100','00100'],
  'Z': ['11111','00001','00010','00100','01000','10000','11111'],
  'a': ['00000','00000','01110','00001','01111','10001','01111'],
  'b': ['10000','10000','10110','11001','10001','10001','11110'],
  'c': ['00000','00000','01111','10000','10000','10000','01111'],
  'd': ['00001','00001','01101','10011','10001','10001','01111'],
  'e': ['00000','00000','01110','10001','11111','10000','01111'],
  'f': ['00110','01001','01000','11100','01000','01000','01000'],
  'g': ['00000','01111','10001','10001','01111','00001','01110'],
  'h': ['10000','10000','10110','11001','10001','10001','10001'],
  'i': ['00100','00000','01100','00100','00100','00100','01110'],
  'j': ['00010','00000','00110','00010','00010','10010','01100'],
  'k': ['10000','10000','10010','10100','11000','10100','10010'],
  'l': ['01100','00100','00100','00100','00100','00100','01110'],
  'm': ['00000','00000','11010','10101','10101','10101','10101'],
  'n': ['00000','00000','10110','11001','10001','10001','10001'],
  'o': ['00000','00000','01110','10001','10001','10001','01110'],
  'p': ['00000','00000','11110','10001','11110','10000','10000'],
  'q': ['00000','00000','01111','10001','01111','00001','00001'],
  'r': ['00000','00000','10110','11001','10000','10000','10000'],
  's': ['00000','00000','01111','10000','01110','00001','11110'],
  't': ['01000','01000','11100','01000','01000','01001','00110'],
  'u': ['00000','00000','10001','10001','10001','10011','01101'],
  'v': ['00000','00000','10001','10001','10001','01010','00100'],
  'w': ['00000','00000','10001','10001','10101','10101','01010'],
  'x': ['00000','00000','10001','01010','00100','01010','10001'],
  'y': ['00000','00000','10001','10001','01111','00001','01110'],
  'z': ['00000','00000','11111','00010','00100','01000','11111'],
  '0': ['01110','10001','10011','10101','11001','10001','01110'],
  '1': ['00100','01100','00100','00100','00100','00100','01110'],
  '2': ['01110','10001','00001','00010','00100','01000','11111'],
  '3': ['11110','00001','00001','01110','00001','00001','11110'],
  '4': ['00010','00110','01010','10010','11111','00010','00010'],
  '5': ['11111','10000','10000','11110','00001','00001','11110'],
  '6': ['01110','10000','10000','11110','10001','10001','01110'],
  '7': ['11111','00001','00010','00100','01000','01000','01000'],
  '8': ['01110','10001','10001','01110','10001','10001','01110'],
  '9': ['01110','10001','10001','01111','00001','00001','01110'],
  ':': ['00000','00100','00100','00000','00100','00100','00000'],
  '.': ['00000','00000','00000','00000','00000','00110','00110'],
  ',': ['00000','00000','00000','00000','00110','00100','01000'],
  '-': ['00000','00000','00000','11111','00000','00000','00000'],
  '_': ['00000','00000','00000','00000','00000','00000','11111'],
  '/': ['00001','00010','00100','01000','10000','00000','00000'],
  '>': ['10000','01000','00100','00010','00100','01000','10000'],
  '<': ['00001','00010','00100','01000','00100','00010','00001'],
  '!': ['00100','00100','00100','00100','00100','00000','00100'],
  '?': ['01110','10001','00001','00010','00100','00000','00100'],
  '+': ['00000','00100','00100','11111','00100','00100','00000'],
  '#': ['01010','01010','11111','01010','11111','01010','01010'],
};

function escapeSvgAttribute(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('"', '&quot;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}

function canRenderPixelText(text) {
  return Boolean(text) && [...text].every(ch => PIXEL_GLYPHS[ch]);
}

function measurePixelText(text, cellSize) {
  const chars = [...text];
  if (chars.length === 0) return 0;
  return chars.length * cellSize * 6 - cellSize;
}

function fitPixelCellSize(text, preferredCellSize, maxWidth) {
  const preferredWidth = measurePixelText(text, preferredCellSize);
  if (!text || preferredWidth <= maxWidth) return preferredCellSize;
  return Math.max(1, Math.floor((preferredCellSize * maxWidth / preferredWidth) * 10) / 10);
}

function renderPixelGlyphs(text, x, topY, cellSize, fill, role) {
  const pixelSize = Math.max(1, Math.floor(cellSize * 0.72 * 10) / 10);
  const step = cellSize * 6;
  let cells = '';

  [...text].forEach((ch, charIndex) => {
    const glyph = PIXEL_GLYPHS[ch];
    let glyphCells = '';
    glyph.forEach((row, rowIndex) => {
      [...row].forEach((bit, colIndex) => {
        if (bit !== '1') return;
        const cellX = x + charIndex * step + colIndex * cellSize;
        const cellY = topY + rowIndex * cellSize;
        glyphCells += `<rect data-pixel-cell="" x="${cellX.toFixed(1)}" y="${cellY.toFixed(1)}" width="${pixelSize.toFixed(1)}" height="${pixelSize.toFixed(1)}" fill="${fill}"/>`;
      });
    });
    cells += `<g data-pixel-glyph="${escapeSvgAttribute(ch)}">${glyphCells}</g>`;
  });

  return `<g data-pixel-text="${role}" data-semantic-text="${escapeSvgAttribute(text)}" aria-label="${escapeSvgAttribute(text)}" shape-rendering="crispEdges">${cells}</g>`;
}

function buildPixelTypewriter(text, x, y, cellSize, fill, startDelay, interval, accentColor, backgroundColor, role) {
  const chars = [...text];
  if (chars.length === 0) {
    return { svg: '', sx: x, totalW: 0, endDelay: startDelay, lastCursorX: x, cursorY: y, cursorW: 0, cursorH: 0 };
  }
  const totalW = measurePixelText(text, cellSize);
  const textTop = y - cellSize * 7;
  const totalDur = chars.length * interval;
  const endDelay = startDelay + totalDur;
  const coverX = x - cellSize * 0.25;
  const coverEndX = x + totalW + cellSize * 0.25;
  const revealXVals = [coverX.toFixed(1)];
  const revealWidthVals = [(coverEndX - coverX).toFixed(1)];
  const revealKeyTimes = ['0'];

  for (let i = 0; i < chars.length; i++) {
    const nextX = Math.min(coverEndX, x + (i + 1) * cellSize * 6);
    revealXVals.push(nextX.toFixed(1));
    revealWidthVals.push(Math.max(0, coverEndX - nextX).toFixed(1));
    revealKeyTimes.push(((startDelay + (i + 1) * interval) / endDelay).toFixed(4));
  }

  let svg = renderPixelGlyphs(text, x, textTop, cellSize, fill, role);
  svg += `<rect data-typewriter-reveal="${role}" x="${coverX.toFixed(1)}" y="${(textTop - 1).toFixed(1)}" width="${(coverEndX - coverX).toFixed(1)}" height="${(cellSize * 7 + 2).toFixed(1)}" fill="${backgroundColor}" opacity="0">`;
  svg += `<animate attributeName="opacity" values="1;1;0" keyTimes="0;0.9999;1" dur="${endDelay.toFixed(2)}s" begin="0s" fill="remove" calcMode="discrete"/>`;
  svg += `<animate attributeName="x" values="${revealXVals.join(';')}" keyTimes="${revealKeyTimes.join(';')}" dur="${endDelay.toFixed(2)}s" begin="0s" fill="remove" calcMode="discrete"/>`;
  svg += `<animate attributeName="width" values="${revealWidthVals.join(';')}" keyTimes="${revealKeyTimes.join(';')}" dur="${endDelay.toFixed(2)}s" begin="0s" fill="remove" calcMode="discrete"/>`;
  svg += `</rect>`;

  const cursorW = Math.max(2, cellSize * 0.75);
  const cursorH = cellSize * 7;
  const cursorY = textTop;
  const cursorPositions = [x - cursorW - cellSize * 0.5];
  for (let i = 0; i < chars.length; i++) cursorPositions.push(x + (i + 1) * cellSize * 6);
  const cursorTimes = cursorPositions.map((_, i) => (i / chars.length).toFixed(4));
  svg += `<rect data-typewriter-cursor="${role}" x="${x.toFixed(1)}" y="${cursorY.toFixed(1)}" width="${cursorW.toFixed(1)}" height="${cursorH.toFixed(1)}" fill="${accentColor}" opacity="0">`;
  svg += `<animate attributeName="x" values="${cursorPositions.map(v => v.toFixed(1)).join(';')}" keyTimes="${cursorTimes.join(';')}" dur="${totalDur.toFixed(2)}s" begin="${startDelay.toFixed(2)}s" fill="freeze" calcMode="discrete"/>`;
  svg += `<animate attributeName="opacity" values="1;0;1" keyTimes="0;0.5;1" dur="0.6s" begin="${startDelay.toFixed(2)}s" end="${(endDelay + 0.25).toFixed(2)}s" repeatCount="indefinite" fill="remove" calcMode="discrete"/>`;
  svg += `</rect>`;

  return {
    svg,
    sx: x,
    totalW,
    endDelay,
    lastCursorX: x + totalW,
    cursorY,
    cursorW,
    cursorH,
  };
}

function buildPixelTerminalLoop(titleText, subtitleText, x, y, cellSize, titleFill, subtitleFill, cursorFill, backgroundColor, inlineGap) {
  const titleW = measurePixelText(titleText, cellSize);
  const subtitleX = x + titleW + (subtitleText ? inlineGap : 0);
  const subtitleW = measurePixelText(subtitleText, cellSize);
  const totalW = titleW + (subtitleText ? inlineGap + subtitleW : 0);
  const step = cellSize * 6;
  const textTop = y - cellSize * 7;
  const coverX = x - cellSize * 0.25;
  const coverEndX = x + totalW + cellSize * 0.25;
  const cycleDur = 4;
  const typingStart = 0.55;
  const typingEnd = 2.65;
  const eraseStart = 3.7;
  const cursorShow = 0.32;

  const segments = [
    { text: titleText, x, width: titleW, fill: titleFill, role: 'title' },
    { text: subtitleText, x: subtitleX, width: subtitleW, fill: subtitleFill, role: 'subtitle' },
  ].filter(segment => segment.text);

  const charStarts = [];
  const charEnds = [];
  segments.forEach(segment => {
    [...segment.text].forEach((_, index) => {
      charStarts.push(segment.x + index * step);
      charEnds.push(Math.min(coverEndX, segment.x + (index + 1) * step));
    });
  });

  let svg = `<g data-terminal-loop="${cycleDur.toFixed(2)}s" data-terminal-phase-order="blank-type-hold-erase">`;
  segments.forEach(segment => {
    svg += renderPixelGlyphs(segment.text, segment.x, textTop, cellSize, segment.fill, segment.role);
  });

  const xValues = [coverX, coverX];
  const widthValues = [coverEndX - coverX, coverEndX - coverX];
  const keyTimes = [0, typingStart / cycleDur];
  const charCount = Math.max(1, charEnds.length);

  charEnds.forEach((edge, index) => {
    const t = typingStart + ((index + 1) / charCount) * (typingEnd - typingStart);
    xValues.push(edge);
    widthValues.push(Math.max(0, coverEndX - edge));
    keyTimes.push(t / cycleDur);
  });

  xValues.push(coverEndX);
  widthValues.push(0);
  keyTimes.push(eraseStart / cycleDur);

  [...charStarts].reverse().forEach((edge, index) => {
    const t = eraseStart + ((index + 1) / charCount) * (cycleDur - eraseStart);
    xValues.push(index === charStarts.length - 1 ? coverX : edge);
    widthValues.push(index === charStarts.length - 1
      ? coverEndX - coverX
      : Math.max(0, coverEndX - edge));
    keyTimes.push(t / cycleDur);
  });

  svg += `<rect data-typewriter-reveal="terminal-loop" x="${coverX.toFixed(1)}" y="${(textTop - 1).toFixed(1)}" width="${(coverEndX - coverX).toFixed(1)}" height="${(cellSize * 7 + 2).toFixed(1)}" fill="${backgroundColor}" opacity="0">`;
  svg += `<animate attributeName="opacity" values="1;1" dur="${cycleDur.toFixed(2)}s" begin="0s" repeatCount="indefinite" calcMode="discrete"/>`;
  svg += `<animate attributeName="x" values="${xValues.map(value => value.toFixed(1)).join(';')}" keyTimes="${keyTimes.map(value => value.toFixed(4)).join(';')}" dur="${cycleDur.toFixed(2)}s" begin="0s" repeatCount="indefinite" calcMode="discrete"/>`;
  svg += `<animate attributeName="width" values="${widthValues.map(value => value.toFixed(1)).join(';')}" keyTimes="${keyTimes.map(value => value.toFixed(4)).join(';')}" dur="${cycleDur.toFixed(2)}s" begin="0s" repeatCount="indefinite" calcMode="discrete"/>`;
  svg += `</rect>`;

  const cursorW = Math.max(2, cellSize * 0.75);
  const cursorH = cellSize * 7;
  const cursorPositions = [x - cursorW - cellSize * 0.5, x - cursorW - cellSize * 0.5, ...charEnds, coverEndX, x - cursorW - cellSize * 0.5];
  const cursorTimes = [
    0,
    typingStart / cycleDur,
    ...charEnds.map((_, index) => (typingStart + ((index + 1) / charCount) * (typingEnd - typingStart)) / cycleDur),
    eraseStart / cycleDur,
    1,
  ];
  svg += `<g data-typewriter-cursor="terminal-loop" opacity="0">`;
  svg += `<animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;${(cursorShow / cycleDur).toFixed(4)};${(eraseStart / cycleDur).toFixed(4)};${((eraseStart + 0.01) / cycleDur).toFixed(4)};1" dur="${cycleDur.toFixed(2)}s" begin="0s" repeatCount="indefinite" calcMode="discrete"/>`;
  svg += `<rect x="${(x - cursorW - cellSize * 0.5).toFixed(1)}" y="${textTop.toFixed(1)}" width="${cursorW.toFixed(1)}" height="${cursorH.toFixed(1)}" fill="${cursorFill}">`;
  svg += `<animate attributeName="x" values="${cursorPositions.map(value => value.toFixed(1)).join(';')}" keyTimes="${cursorTimes.map(value => value.toFixed(4)).join(';')}" dur="${cycleDur.toFixed(2)}s" begin="0s" repeatCount="indefinite" calcMode="discrete"/>`;
  svg += `<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.48;0.5;1" dur="0.64s" begin="0s" repeatCount="indefinite" calcMode="discrete"/>`;
  svg += `</rect></g></g>`;

  return {
    svg,
    titleW,
    subtitleX,
    subtitleW,
    totalW,
    endDelay: cycleDur,
  };
}

function isMixedPixelCharacter(ch) {
  // Keep spaces with the neighbouring font-backed run in mixed copy so their
  // advance matches normal prose. All visible supported Latin glyphs remain
  // native geometry and never depend on the reader's SVG font renderer.
  return ch !== ' ' && Boolean(PIXEL_GLYPHS[ch]);
}

function buildMixedTerminalText(text, x, y, maxWidth, preferredFontSize, preferredCellSize, fill, font, startDelay, interval, accentColor, backgroundColor, role) {
  const chars = [...text];
  if (chars.length === 0) {
    return { svg: '', sx: x, totalW: 0, endDelay: startDelay, lastCursorX: x, cursorY: y, cursorW: 0, cursorH: 0 };
  }

  const measure = (fontSize, cellSize) => {
    const advances = chars.map(ch => isMixedPixelCharacter(ch)
      ? cellSize * 6
      : getCharWidth(ch, fontSize) + getCharGap(ch));
    const trailing = isMixedPixelCharacter(chars.at(-1)) ? cellSize : getCharGap(chars.at(-1));
    return Math.max(0, advances.reduce((sum, width) => sum + width, 0) - trailing);
  };

  const preferredWidth = measure(preferredFontSize, preferredCellSize);
  const scale = preferredWidth > maxWidth ? maxWidth / preferredWidth : 1;
  const fontSize = Math.max(1, Math.floor(preferredFontSize * scale * 10) / 10);
  const cellSize = Math.max(1, Math.floor(preferredCellSize * scale * 10) / 10);
  const widths = chars.map(ch => isMixedPixelCharacter(ch)
    ? cellSize * 5
    : getCharWidth(ch, fontSize));
  const advances = chars.map((ch, index) => widths[index] + (isMixedPixelCharacter(ch) ? cellSize : getCharGap(ch)));
  const totalW = measure(fontSize, cellSize);
  const positions = [];
  let cursorX = x;
  chars.forEach((_, index) => {
    positions.push(cursorX);
    cursorX += advances[index];
  });

  const runs = [];
  chars.forEach((ch, index) => {
    const kind = isMixedPixelCharacter(ch) ? 'pixel' : 'text';
    const previous = runs.at(-1);
    if (!previous || previous.kind !== kind) {
      runs.push({ kind, start: index, text: ch });
    } else {
      previous.text += ch;
    }
  });

  const textTop = y - cellSize * 7;
  let svg = `<g data-mixed-terminal-text="${role}" data-semantic-text="${escapeSvgAttribute(text)}" aria-label="${escapeSvgAttribute(text)}">`;
  runs.forEach((run, runIndex) => {
    const runX = positions[run.start];
    if (run.kind === 'pixel') {
      svg += renderPixelGlyphs(run.text, runX, textTop, cellSize, fill, `${role}-latin-${runIndex}`);
      return;
    }
    svg += `<text data-font-text="${role}-${runIndex}" x="${runX.toFixed(1)}" y="${y}" text-anchor="start" font-size="${fontSize}" font-weight="500" fill="${fill}" font-family="${font}"><tspan leaf="">${escapeSvgAttribute(run.text)}</tspan></text>`;
  });
  svg += `</g>`;

  // Preserve the static complete line as the baseline. The cover exists only
  // while SMIL is running, so stripped or unsupported animation still exposes
  // all semantic text and all native Latin geometry.
  const totalDur = chars.length * interval;
  const endDelay = startDelay + totalDur;
  const cursorW = Math.max(2, Math.min(cellSize * 0.75, fontSize * 0.12));
  const cursorH = Math.max(cellSize * 7, fontSize * 0.8);
  const cursorY = Math.min(textTop, y - fontSize * 0.7);
  const coverX = x - 2;
  const coverEndX = x + totalW + 2;
  const coverY = Math.min(textTop - 1, y - fontSize);
  const coverH = Math.max(cellSize * 7 + 2, fontSize * 1.25);
  const revealXVals = [coverX.toFixed(1)];
  const revealWidthVals = [(coverEndX - coverX).toFixed(1)];
  const revealKeyTimes = ['0'];
  const charEnds = positions.map((position, index) => Math.min(coverEndX, position + advances[index]));

  charEnds.forEach((edge, index) => {
    revealXVals.push(edge.toFixed(1));
    revealWidthVals.push(Math.max(0, coverEndX - edge).toFixed(1));
    revealKeyTimes.push(((startDelay + (index + 1) * interval) / endDelay).toFixed(4));
  });

  svg += `<rect data-typewriter-reveal="${role}" x="${coverX.toFixed(1)}" y="${coverY.toFixed(1)}" width="${(coverEndX - coverX).toFixed(1)}" height="${coverH.toFixed(1)}" fill="${backgroundColor}" opacity="0">`;
  svg += `<animate attributeName="opacity" values="1;1;0" keyTimes="0;0.9999;1" dur="${endDelay.toFixed(2)}s" begin="0s" fill="remove" calcMode="discrete"/>`;
  svg += `<animate attributeName="x" values="${revealXVals.join(';')}" keyTimes="${revealKeyTimes.join(';')}" dur="${endDelay.toFixed(2)}s" begin="0s" fill="remove" calcMode="discrete"/>`;
  svg += `<animate attributeName="width" values="${revealWidthVals.join(';')}" keyTimes="${revealKeyTimes.join(';')}" dur="${endDelay.toFixed(2)}s" begin="0s" fill="remove" calcMode="discrete"/>`;
  svg += `</rect>`;

  const cursorPositions = [x - cursorW - 2, ...charEnds];
  const cursorTimes = cursorPositions.map((_, index) => (index / chars.length).toFixed(4));
  svg += `<rect data-typewriter-cursor="${role}" x="${x.toFixed(1)}" y="${cursorY.toFixed(1)}" width="${cursorW.toFixed(1)}" height="${cursorH.toFixed(1)}" fill="${accentColor}" opacity="0">`;
  svg += `<animate attributeName="x" values="${cursorPositions.map(value => value.toFixed(1)).join(';')}" keyTimes="${cursorTimes.join(';')}" dur="${totalDur.toFixed(2)}s" begin="${startDelay.toFixed(2)}s" fill="freeze" calcMode="discrete"/>`;
  svg += `<animate attributeName="opacity" values="1;0;1" keyTimes="0;0.5;1" dur="0.6s" begin="${startDelay.toFixed(2)}s" end="${(endDelay + 0.25).toFixed(2)}s" repeatCount="indefinite" fill="remove" calcMode="discrete"/>`;
  svg += `</rect>`;

  return {
    svg,
    sx: x,
    totalW,
    endDelay,
    lastCursorX: x + totalW,
    cursorY,
    cursorW,
    cursorH,
  };
}

function buildTerminalText(text, x, y, maxWidth, preferredFontSize, preferredCellSize, fill, font, startDelay, interval, accentColor, backgroundColor, role) {
  if (canRenderPixelText(text)) {
    const cellSize = fitPixelCellSize(text, preferredCellSize, maxWidth);
    return buildPixelTypewriter(
      text, x, y, cellSize, fill, startDelay, interval,
      accentColor, backgroundColor, role,
    );
  }

  if ([...text].some(isMixedPixelCharacter)) {
    return buildMixedTerminalText(
      text, x, y, maxWidth, preferredFontSize, preferredCellSize, fill, font,
      startDelay, interval, accentColor, backgroundColor, role,
    );
  }

  const fontSize = fitTypewriterFontSize(text, preferredFontSize, maxWidth);
  return buildTypewriter(
    text, x, y, fontSize, fill, font, startDelay, interval,
    accentColor, backgroundColor, role, 'start',
  );
}

// Semantic text stays as one statically visible line. A background-coloured
// cover temporarily hides its unrevealed suffix only while SMIL is running.
// If WeChat strips or misses any animation state, the cover falls back to
// opacity=0 and the complete line remains readable.
function buildTypewriter(text, cx, y, fontSize, fill, font, startDelay, interval, accentColor, backgroundColor, role, align = 'center') {
  const chars = [...text];
  if (chars.length === 0) {
    return { svg: '', sx: cx, totalW: 0, endDelay: startDelay, lastCursorX: cx, cursorY: y, cursorW: 0, cursorH: 0 };
  }
  const widths = chars.map(ch => getCharWidth(ch, fontSize));
  const gaps = chars.map(ch => getCharGap(ch));
  const totalW = measureTypewriterWidth(text, fontSize);
  const sx = align === 'start' ? cx : cx - totalW / 2;
  const xs = [];
  let acc = sx;
  for (let i = 0; i < chars.length; i++) {
    xs.push(acc);
    acc += widths[i] + gaps[i];
  }

  // Keep one visible semantic text container. Character tspans share the
  // reveal layer's measured positions, so a step uncovers a complete glyph.
  let svg = `<text x="${sx.toFixed(1)}" y="${y}" text-anchor="start" font-size="${fontSize}" font-weight="500" fill="${fill}" font-family="${font}">`;
  for (let i = 0; i < chars.length; i++) {
    let escapedChar = chars[i];
    if (chars[i] === '<') escapedChar = '&lt;';
    else if (chars[i] === '&') escapedChar = '&amp;';
    svg += `<tspan leaf="" x="${xs[i].toFixed(1)}" y="${y}">${escapedChar}</tspan>`;
  }
  svg += `</text>`;

  // 逐字揭示层：基态透明，动画运行时覆盖未输入的后缀。
  // x/width 使用离散步进，避免退化成连续擦除效果。
  const totalDur = chars.length * interval;
  const cursorW = Math.max(2, fontSize * 0.06);
  const cursorH = fontSize * 0.8;
  const cursorY = y - fontSize * 0.7;
  const endDelay = startDelay + totalDur;
  const coverX = sx - 2;
  const coverEndX = sx + totalW + 2;
  const coverY = y - fontSize;
  const coverH = fontSize * 1.25;
  const revealXVals = [coverX.toFixed(1)];
  const revealWidthVals = [(coverEndX - coverX).toFixed(1)];
  const revealKeyTimes = ['0'];

  for (let i = 0; i < chars.length; i++) {
    const nextX = Math.min(coverEndX, xs[i] + widths[i] + gaps[i] + 1);
    revealXVals.push(nextX.toFixed(1));
    revealWidthVals.push(Math.max(0, coverEndX - nextX).toFixed(1));
    revealKeyTimes.push(((startDelay + (i + 1) * interval) / endDelay).toFixed(4));
  }

  svg += `<rect data-typewriter-reveal="${role}" x="${coverX.toFixed(1)}" y="${coverY.toFixed(1)}" width="${(coverEndX - coverX).toFixed(1)}" height="${coverH.toFixed(1)}" fill="${backgroundColor}" opacity="0">`;
  svg += `<animate attributeName="opacity" values="1;1;0" keyTimes="0;0.9999;1" dur="${endDelay.toFixed(2)}s" begin="0s" fill="remove" calcMode="discrete"/>`;
  svg += `<animate attributeName="x" values="${revealXVals.join(';')}" keyTimes="${revealKeyTimes.join(';')}" dur="${endDelay.toFixed(2)}s" begin="0s" fill="remove" calcMode="discrete"/>`;
  svg += `<animate attributeName="width" values="${revealWidthVals.join(';')}" keyTimes="${revealKeyTimes.join(';')}" dur="${endDelay.toFixed(2)}s" begin="0s" fill="remove" calcMode="discrete"/>`;
  svg += `</rect>`;

  // 光标按同一字符节奏跟随，动画失效时只保留装饰性基态。

  const xVals = [(sx - cursorW - 2).toFixed(1)];
  const keyTimes = ['0'];
  for (let i = 0; i < chars.length; i++) {
    xVals.push((xs[i] + widths[i] + gaps[i] + 1).toFixed(1));
    keyTimes.push(((i + 1) / chars.length).toFixed(4));
  }

  // The cursor is decorative. Its transparent baseline keeps later-line
  // cursors hidden until their own typing sequence starts.
  svg += `<rect data-typewriter-cursor="${role}" x="${sx.toFixed(1)}" y="${cursorY.toFixed(1)}" width="${cursorW}" height="${cursorH.toFixed(1)}" fill="${accentColor}" opacity="0">`;
  svg += `<animate attributeName="x" values="${xVals.join(';')}" keyTimes="${keyTimes.join(';')}" dur="${totalDur}s" begin="${startDelay}s" fill="freeze" calcMode="discrete"/>`;
  svg += `<animate attributeName="opacity" values="1;0;1" keyTimes="0;0.5;1" dur="0.6s" begin="${startDelay}s" end="${(endDelay + 0.25).toFixed(2)}s" repeatCount="indefinite" fill="remove" calcMode="discrete"/>`;
  svg += `</rect>`;

  return {
    svg,
    sx,
    totalW,
    endDelay,
    lastCursorX: parseFloat(xVals[xVals.length - 1]),
    cursorY,
    cursorW,
    cursorH,
  };
}

// ─── 手机优先排版 ───────────────────────────────────────
// 公众号几乎都在手机上读：390px 屏宽时正文列约 358px。viewBox 宽度取 360，
// 让 1 个 viewBox 单位约等于手机上的 1 CSS px，字号即所见；桌面端仍以
// width:100% + max-width:480px 等比放大（标题约 37px，不压过正文 H1 太多）。
const COVER_W = 360;
const COVER_MAX_W = 480;
const COVER_MARGIN = 24;
const COVER_CONTENT_W = COVER_W - COVER_MARGIN * 2;

function n1(value) {
  return Number(value.toFixed(1));
}

function coverSvgOpen(W, H, bg, extraAttrs = '') {
  return `<svg${extraAttrs} xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 ${W} ${n1(H)}" preserveAspectRatio="xMidYMin meet" style="display:block;width:100%;max-width:${COVER_MAX_W}px;margin:0 auto;"><rect x="0" y="0" width="${W}" height="${n1(H)}" fill="${bg}"/>`;
}

function isCjkChar(ch) {
  return /[⺀-鿿豈-﫿　-〿＀-￯“”‘’—…]/.test(ch);
}

// 比例字体的保守估宽：中文 1em，拉丁字母和数字按常见中文字体里的西文字宽估计。
function measureCoverText(text, fontSize, letterSpacing = 0) {
  const chars = [...String(text)];
  let width = 0;
  for (const ch of chars) {
    let factor = 0.6;
    if (isCjkChar(ch)) factor = 1;
    else if (ch === ' ') factor = 0.33;
    else if (/[A-Z]/.test(ch)) factor = 0.7;
    else if (/[0-9]/.test(ch)) factor = 0.58;
    else if (/[a-z]/.test(ch)) factor = 0.56;
    width += factor * fontSize;
  }
  return width + letterSpacing * chars.length;
}

const NO_LINE_START = /[，。、：；！？）」』”’》,.;:!?)\]]/;
const NO_LINE_END = /[（「『“‘《(\[]/;
const PUNCT_BREAK_AFTER = /[，。、：；！？,;:!?的]/;
const WORD_CHAR = /[A-Za-z0-9.%+\-_'&]/;

function twoLineCandidates(text) {
  const chars = [...text];
  const seen = new Set();
  const out = [];
  for (let i = 1; i < chars.length; i += 1) {
    const prev = chars[i - 1];
    const next = chars[i];
    if (WORD_CHAR.test(prev) && WORD_CHAR.test(next)) continue; // 不拆英文单词和数字
    if (NO_LINE_START.test(next) || NO_LINE_END.test(prev)) continue;
    const first = chars.slice(0, i).join('').trimEnd();
    const second = chars.slice(i).join('').trimStart();
    // 不留单字孤行
    if ([...first.replace(/\s/g, '')].length < 2 || [...second.replace(/\s/g, '')].length < 2) continue;
    const key = `${first}\n${second}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const tier = PUNCT_BREAK_AFTER.test(prev) ? 0 : (prev === ' ' || next === ' ') ? 1 : 2;
    out.push({ lines: [first, second], tier });
  }
  return out;
}

function bestTwoLineSplit(text, fontSize, maxWidth, measure, maxTier = 2) {
  const total = measure(text, fontSize);
  const candidates = twoLineCandidates(text)
    .filter(candidate => candidate.tier <= maxTier)
    .map(candidate => ({ ...candidate, widest: Math.max(...candidate.lines.map(line => measure(line, fontSize))) }))
    .filter(candidate => candidate.widest <= maxWidth);
  if (!candidates.length) return null;
  // 优先在标点 /「的」后断行，其次空格，最后才在汉字之间按宽度均衡断行。
  for (const tier of [0, 1]) {
    const pool = candidates.filter(candidate => candidate.tier === tier && candidate.widest <= total * 0.72);
    if (pool.length) return pool.reduce((best, candidate) => candidate.widest < best.widest ? candidate : best).lines;
  }
  return candidates.reduce((best, candidate) => candidate.widest < best.widest ? candidate : best).lines;
}

// 标题优先换成两行而不是缩字；副标题先缩到下限再换行。最多两行。
function layoutLines(text, { fontSize, minFontSize, maxWidth, measure = measureCoverText, prefer = 'wrap' }) {
  const value = String(text || '').trim();
  if (!value) return { lines: [], fontSize, text: '' };
  const fits = size => measure(value, size) <= maxWidth;
  if (fits(fontSize)) return { lines: [value], fontSize, text: value };
  if (prefer === 'shrink') {
    for (let size = fontSize - 0.5; size >= minFontSize; size -= 0.5) {
      if (fits(size)) return { lines: [value], fontSize: size, text: value };
    }
  }
  // 断点质量优先于字号:先在字号区间内找标点 /「的」断点,其次空格,最后才在汉字之间断。
  // 否则较长的后半句在首选字号放不下时,会退成「…培训方，先 / 看他…」这种把词拆开的断行。
  for (const maxTier of [0, 1, 2]) {
    for (let size = fontSize; size >= minFontSize; size -= 0.5) {
      const lines = bestTwoLineSplit(value, size, maxWidth, measure, maxTier);
      if (lines) return { lines, fontSize: size, text: value };
    }
  }
  const lines = bestTwoLineSplit(value, minFontSize, Number.POSITIVE_INFINITY, measure) || [value];
  const widest = Math.max(...lines.map(line => measure(line, minFontSize)));
  return { lines, fontSize: Math.max(1, Math.floor(minFontSize * maxWidth / widest * 10) / 10), text: value };
}

// 一个语义 <text>，每行一个 <tspan leaf="">；多行时在元素上保留完整语义。
function coverText(layout, { x, y, lineHeight = 0, fill, font, anchor = 'middle', weight = '', letterSpacing = 0 }) {
  const { lines, fontSize } = layout;
  if (!lines.length) return '';
  const full = layout.text || lines.join('');
  const semantic = lines.length > 1
    ? ` data-semantic-text="${escapeSvgAttribute(full)}" aria-label="${escapeSvgAttribute(full)}"`
    : '';
  const attrs = `x="${n1(x)}" y="${n1(y)}" text-anchor="${anchor}" font-size="${n1(fontSize)}"${weight ? ` font-weight="${weight}"` : ''} fill="${fill}" font-family="${font}"${letterSpacing ? ` letter-spacing="${letterSpacing}"` : ''}${semantic}`;
  if (lines.length === 1) return `<text ${attrs}><tspan leaf="">${escapeSvgAttribute(lines[0])}</tspan></text>`;
  const spans = lines
    .map((line, index) => `<tspan leaf="" x="${n1(x)}" y="${n1(y + index * lineHeight)}">${escapeSvgAttribute(line)}</tspan>`)
    .join('');
  return `<text ${attrs}>${spans}</text>`;
}

// 文字块高度：首行基线 = top + 0.86em，末行下沿 = 末行基线 + 0.24em。
function textBlockMetrics(layout, top, lineHeight) {
  if (!layout.lines.length) return { baseline: top, bottom: top };
  const baseline = top + layout.fontSize * 0.86;
  const bottom = baseline + (layout.lines.length - 1) * lineHeight + layout.fontSize * 0.24;
  return { baseline, bottom };
}

// 向下箭头：外层 <g> 定位，内部只做相对位移，避免动画期间坐标被叠加两次。
function scrollArrow(cx, baseline, fontSize, fill, begin) {
  return `<g transform="translate(${n1(cx)},${n1(baseline)})"><text x="0" y="0" text-anchor="middle" font-size="${fontSize}" fill="${fill}" font-family="sans-serif"><tspan leaf="">↓</tspan><animateTransform attributeName="transform" type="translate" values="0 0;0 6;0 0" dur="1.5s" begin="${begin}" repeatCount="indefinite" calcMode="spline" keyTimes="0;0.5;1" keySplines="0.4 0 0.6 1;0.4 0 0.6 1"/></text></g>`;
}

function openCover(C, W, H, extraAttrs = '') {
  return coverSvgOpen(W, H, C.bg, extraAttrs);
}

// ─── 模板 1: 墨韵开篇 ──────────────────────────────────
function templateInkWash(C, opts) {
  const tagList = opts.tags ? opts.tags.split(',').map(t => t.trim()).filter(Boolean) : [];
  const W = COVER_W, cx = W / 2;
  let body = '';
  let cursor = 24;

  // 顶部标签
  let label = '';
  if (C.topLabel) {
    const labelBase = cursor + 11;
    label = `<text x="${cx}" y="${n1(labelBase)}" text-anchor="middle" font-size="12" font-weight="600" fill="${C.accent}" letter-spacing="3" font-family="${C.uiFont}"><tspan leaf="">${C.topLabel}</tspan></text>`;
    cursor = labelBase + 20;
  }

  // 主标题
  const title = layoutLines(opts.title, { fontSize: 28, minFontSize: 24, maxWidth: COVER_CONTENT_W });
  const titleLH = title.fontSize * 1.32;
  const titleBox = textBlockMetrics(title, cursor, titleLH);
  const titleSvg = coverText(title, { x: cx, y: titleBox.baseline, lineHeight: titleLH, weight: '500', fill: C.text, font: C.headingFont });
  const inkCy = (cursor + titleBox.bottom) / 2;

  // 墨点晕染
  body += `<circle cx="${cx}" cy="${n1(inkCy)}" r="0" fill="${C.accent}" opacity="0.08"><animate attributeName="r" values="0;70;100" dur="0.8s" begin="0.2s" fill="freeze" calcMode="spline" keyTimes="0;0.6;1" keySplines="0.25 0.1 0.25 1;0.4 0 0.6 1"/><animate attributeName="opacity" values="0.08;0.04;0" dur="0.8s" begin="0.2s" fill="freeze"/></circle>`;
  body += label + titleSvg;

  // 分隔线(rect + animate width,微信保留)
  const dividerY = titleBox.bottom + 12;
  body += `<rect x="${cx - 32}" y="${n1(dividerY)}" width="0" height="3" rx="1.5" fill="${C.accent}" opacity="0"><animate attributeName="width" values="0;64" dur="0.5s" begin="1.9s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.22 1 0.36 1"/><animate attributeName="opacity" values="0;1" dur="0.05s" begin="1.9s" fill="freeze"/></rect>`;
  cursor = dividerY + 3 + 14;

  // 副标题
  const subtitle = layoutLines(opts.subtitle, { fontSize: 15, minFontSize: 14, maxWidth: COVER_CONTENT_W, prefer: 'shrink' });
  const subtitleLH = subtitle.fontSize * 1.5;
  const subtitleBox = textBlockMetrics(subtitle, cursor, subtitleLH);
  body += coverText(subtitle, { x: cx, y: subtitleBox.baseline, lineHeight: subtitleLH, fill: C.tertiary, font: C.serifFont });
  cursor = subtitle.lines.length ? subtitleBox.bottom : cursor - 14;

  // 特性标签
  if (tagList.length > 0) {
    const tagH = 26, tagGap = 10, tagFont = 12;
    const widths = tagList.map(tag => Math.max(64, measureCoverText(tag, tagFont) + 24));
    const totalTagW = widths.reduce((sum, width) => sum + width, 0) + (tagList.length - 1) * tagGap;
    const tagY = cursor + 18;
    const tagColors = [C.accent, C.secondary, C.tertiary];
    let x = cx - totalTagW / 2;
    tagList.forEach((tag, i) => {
      const color = tagColors[i % tagColors.length];
      body += `<g><rect x="${n1(x)}" y="${n1(tagY)}" width="${n1(widths[i])}" height="${tagH}" rx="13" fill="none" stroke="${color}" stroke-width="1.2"/><text x="${n1(x + widths[i] / 2)}" y="${n1(tagY + 17.5)}" text-anchor="middle" font-size="${tagFont}" fill="${color}" font-family="${C.uiFont}"><tspan leaf="">${escapeSvgAttribute(tag)}</tspan></text></g>`;
      x += widths[i] + tagGap;
    });
    cursor = tagY + tagH;
  }

  // 底部提示 + 箭头
  const arrowBase = cursor + 32;
  const dotsY = arrowBase + 12;
  const hintBase = dotsY + 20;
  body += `<g><circle cx="${cx - 12}" cy="${n1(dotsY)}" r="2.5" fill="${C.accent}"/><circle cx="${cx}" cy="${n1(dotsY)}" r="2.5" fill="${C.light}"/><circle cx="${cx + 12}" cy="${n1(dotsY)}" r="2.5" fill="${C.light}"/><text x="${cx}" y="${n1(hintBase)}" text-anchor="middle" font-size="12" fill="${C.hint}" font-family="${C.uiFont}" letter-spacing="2"><tspan leaf="">向下滑动开始阅读</tspan></text></g>`;
  body += scrollArrow(cx, arrowBase, 14, C.hint, '4.5s');
  const H = hintBase + 18;

  return `${openCover(C, W, H)}${body}</svg>`;
}

// ─── 模板 2: 打字机流 ──────────────────────────────────
function buildTypewriterLines(layout, cx, firstBaseline, lineHeight, fontSize, fill, font, startDelay, interval, accentColor, backgroundColor, role) {
  const { lines } = layout;
  let delay = startDelay;
  let svg = '';
  const built = lines.map((line, index) => {
    const lineRole = index === 0 ? role : `${role}-${index + 1}`;
    const result = buildTypewriter(line, cx, n1(firstBaseline + index * lineHeight), fontSize, fill, font, delay, interval, accentColor, backgroundColor, lineRole);
    delay = result.endDelay + 0.05;
    svg += result.svg;
    return result;
  });
  if (built.length > 1) {
    const full = layout.text;
    svg = `<g data-typewriter-lines="${role}" data-semantic-text="${escapeSvgAttribute(full)}" aria-label="${escapeSvgAttribute(full)}">${svg}</g>`;
  }
  const last = built.at(-1);
  const widest = built.reduce((best, item) => item.totalW > best.totalW ? item : best, built[0] || { sx: cx, totalW: 0 });
  return {
    svg,
    endDelay: last ? last.endDelay : startDelay,
    sx: widest.sx,
    totalW: widest.totalW,
    last,
  };
}

function templateTypewriter(C, opts) {
  const W = COVER_W, cx = W / 2;

  // 品牌标签去掉（zhijian 主题左上角已有智见AI，重复）
  const titleStart = 0.3;
  const title = layoutLines(opts.title, { fontSize: 28, minFontSize: 22, maxWidth: COVER_CONTENT_W, measure: measureTypewriterWidth });
  const titleLH = title.fontSize * 1.3;
  const titleBox = textBlockMetrics(title, 18, titleLH);
  const titleLines = buildTypewriterLines(title, cx, titleBox.baseline, titleLH, title.fontSize, C.text, C.monoFont, titleStart, 0.13, C.accent, C.bg, 'title');
  const lineDelay = titleLines.endDelay + 0.3;
  const underlineY = (title.lines.length ? titleBox.bottom : 18) + 8;

  const subStart = lineDelay + 0.8 + 0.2;
  // 逐字定位依赖稳定字宽。副标题混排中英文时使用等宽字体栈，
  // 避免比例衬线字体里的 M/W 等宽字符侵入后一个字母。
  const subtitle = layoutLines(opts.subtitle, { fontSize: 16, minFontSize: 14, maxWidth: COVER_CONTENT_W, measure: measureTypewriterWidth, prefer: 'shrink' });
  const subtitleLH = subtitle.fontSize * 1.5;
  const subtitleBox = textBlockMetrics(subtitle, underlineY + 2.5 + 16, subtitleLH);
  const subtitleLines = buildTypewriterLines(subtitle, cx, subtitleBox.baseline, subtitleLH, subtitle.fontSize, C.tertiary, C.monoFont, subStart, 0.08, C.accent, C.bg, 'subtitle');
  let cursor = subtitle.lines.length ? subtitleBox.bottom : underlineY + 2.5;

  const tagText = opts.tags
    ? opts.tags.split(',').map(tag => tag.trim()).filter(Boolean).join(' · ')
    : '';
  const tagFontSize = fitTypewriterFontSize(tagText, 13, COVER_CONTENT_W);
  const tagBase = cursor + 14 + tagFontSize * 0.86;
  if (tagText) cursor = tagBase + tagFontSize * 0.24;
  const subtitleEnd = subtitle.lines.length ? subtitleLines.endDelay : subStart;
  const tagDelay = subtitleEnd + 0.25;
  const hintStart = (tagText ? tagDelay + 0.55 : subtitleEnd) + 0.3;
  const hintFontSize = 14;
  const hintY = n1(cursor + 22 + hintFontSize * 0.86);
  const hint = buildTypewriter('> 向下滑动继续阅读', cx, hintY, hintFontSize, C.accent, C.monoFont, hintStart, 0.07, C.accent, C.bg, 'hint');
  const hintCursorBlink = hint.lastCursorX + 2;
  const arrowDelay = hint.endDelay + 0.5;
  const arrowBase = hintY + 26;
  const H = arrowBase + 14;

  let svg = openCover(C, W, H);
  svg += titleLines.svg;
  // 横线:rect + animate width(dur 0.8s)，宽度跟随最宽的标题行
  svg += `<rect x="${titleLines.sx.toFixed(1)}" y="${n1(underlineY)}" width="0" height="2.5" rx="1.25" fill="${C.accent}" opacity="0"><animate attributeName="width" values="0;${titleLines.totalW.toFixed(1)}" dur="0.8s" begin="${lineDelay.toFixed(2)}s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.22 1 0.36 1"/><animate attributeName="opacity" values="0;1" dur="0.05s" begin="${lineDelay.toFixed(2)}s" fill="freeze"/></rect>`;
  svg += subtitleLines.svg;
  if (tagText) {
    svg += `<text x="${cx}" y="${n1(tagBase)}" text-anchor="middle" font-size="${tagFontSize}" font-weight="600" fill="${C.secondary}" font-family="${C.uiFont}" letter-spacing="1"><tspan leaf="">${escapeSvgAttribute(tagText)}</tspan></text>`;
  }
  svg += hint.svg;
  // 提示光标:亮0.6s 灭0.6s — y 跟随提示文字底部
  const hintCursorY = hintY - hintFontSize * 0.7;
  svg += `<rect x="${hintCursorBlink.toFixed(1)}" y="${hintCursorY.toFixed(1)}" width="2" height="${hintFontSize}" fill="${C.accent}" opacity="0"><animate attributeName="opacity" values="0;1" dur="0.05s" begin="${hint.endDelay.toFixed(2)}s" fill="freeze"/><animate attributeName="opacity" values="1;1;0;0" dur="1.2s" begin="${(hint.endDelay + 0.1).toFixed(2)}s" repeatCount="indefinite"/></rect>`;
  // 箭头（提示文字下方）
  svg += scrollArrow(cx, arrowBase, 16, C.hint, `${(arrowDelay + 0.2).toFixed(2)}s`);
  svg += `</svg>`;
  return svg;
}

function buildXiaolanTerminalSprite(C) {
  const openFrame = loadNativeSvgPixelAsset('xiaolan-terminal-pixel-open.png', C.bg, 'eyes-open');
  const closedFrame = loadNativeSvgPixelAsset('xiaolan-terminal-pixel-closed.png', C.bg, 'eyes-closed');
  const waveMidFrame = loadNativeSvgPixelAsset('xiaolan-terminal-wave-mid.png', C.bg, 'wave-mid');
  const waveHighFrame = loadNativeSvgPixelAsset('xiaolan-terminal-wave-high.png', C.bg, 'wave-high');
  const waveKeyTimes = '0;0.0583;0.0917;0.1333;0.1750;0.2167;0.2583;1';
  return `<g data-ip="zhijian-xiaolan" data-ip-source="canonical-pet-v2" data-ip-render="high-density-pixel" data-ip-source-sha256="bea0a78d1d435feb9b6465be41db5144bf529c459da698228a2c9ce1d17ed931">
    <g data-xiaolan-motion="idle-avatar">
      <animateTransform attributeName="transform" type="translate" values="0 0;1 -1;2 0;1 2;0 3;-1 2;0 0" keyTimes="0;0.16;0.32;0.5;0.68;0.84;1" dur="3s" begin="0s" repeatCount="indefinite" calcMode="discrete"/>
      <g data-xiaolan-motion="wave-greeting" data-wave-loop="6s" data-wave-sequence="idle-mid-high-mid-high-mid-idle">
        <g data-xiaolan-pose="idle">
          <animate attributeName="opacity" values="1;0;0;0;0;0;1;1" keyTimes="${waveKeyTimes}" dur="6s" begin="0s" repeatCount="indefinite" calcMode="discrete"/>
          ${openFrame}
          <g data-xiaolan-frame="eyes-closed" opacity="0">
            <animate attributeName="opacity" values="0;0;1;0;0" keyTimes="0;0.34;0.37;0.4;1" dur="3s" begin="0s" repeatCount="indefinite" calcMode="discrete"/>
            ${closedFrame}
          </g>
        </g>
        <g data-xiaolan-frame="wave-mid" opacity="0">
          <animate attributeName="opacity" values="0;1;0;1;0;1;0;0" keyTimes="${waveKeyTimes}" dur="6s" begin="0s" repeatCount="indefinite" calcMode="discrete"/>
          ${waveMidFrame}
        </g>
        <g data-xiaolan-frame="wave-high" opacity="0">
          <animate attributeName="opacity" values="0;0;1;0;1;0;0;0" keyTimes="${waveKeyTimes}" dur="6s" begin="0s" repeatCount="indefinite" calcMode="discrete"/>
          ${waveHighFrame}
        </g>
      </g>
      <g data-xiaolan-part="terminal-prompt" transform="translate(87 56)" fill="${C.text}" shape-rendering="crispEdges" aria-label="terminal prompt">
        <rect x="0" y="0" width="2" height="2"/>
        <rect x="2" y="2" width="2" height="2"/>
        <rect x="4" y="4" width="2" height="2"/>
        <rect x="2" y="6" width="2" height="2"/>
        <rect x="0" y="8" width="2" height="2"/>
        <rect x="8" y="8" width="8" height="2"/>
      </g>
    </g>
  </g>`;
}

// 终端文字估宽：纯像素行按 5×7 栅格，中英混排按像素段 + 等宽字体段。
function measureTerminalText(text, fontSize, cellRatio) {
  const cellSize = fontSize * cellRatio;
  if (canRenderPixelText(text)) return measurePixelText(text, cellSize);
  const chars = [...text];
  if (!chars.length) return 0;
  const advances = chars.map(ch => isMixedPixelCharacter(ch)
    ? cellSize * 6
    : getCharWidth(ch, fontSize) + getCharGap(ch));
  const trailing = isMixedPixelCharacter(chars.at(-1)) ? cellSize : getCharGap(chars.at(-1));
  return Math.max(0, advances.reduce((sum, width) => sum + width, 0) - trailing);
}

function buildTerminalLines(layout, x, firstBaseline, lineHeight, maxWidth, fontSize, cellRatio, fill, font, startDelay, interval, accentColor, backgroundColor, role) {
  const { lines } = layout;
  let delay = startDelay;
  let svg = '';
  const built = lines.map((line, index) => {
    const lineRole = index === 0 ? role : `${role}-${index + 1}`;
    const result = buildTerminalText(
      line, x, n1(firstBaseline + index * lineHeight), maxWidth, fontSize, fontSize * cellRatio,
      fill, font, delay, interval, accentColor, backgroundColor, lineRole,
    );
    delay = result.endDelay + 0.05;
    svg += result.svg;
    return result;
  });
  if (built.length > 1) {
    const full = layout.text;
    svg = `<g data-terminal-lines="${role}" data-semantic-text="${escapeSvgAttribute(full)}" aria-label="${escapeSvgAttribute(full)}">${svg}</g>`;
  }
  return { svg, built, last: built.at(-1), endDelay: built.length ? built.at(-1).endDelay : startDelay };
}

// ─── 模板 3: 小蓝终端 ──────────────────────────────────
function templateXiaolanTerminal(C, opts) {
  const W = COVER_W;
  // 左侧角色 + 右侧终端：角色缩到约 84×89，给右侧文字留出约 240 宽的终端栏。
  const spriteScale = 0.5;
  const spriteW = 168 * spriteScale;
  const spriteH = 177 * spriteScale;
  const spriteX = 12;
  const textX = spriteX + spriteW + 12;
  const maxTextWidth = W - textX - 12;
  const pad = 16;
  const titleText = (opts.title || '').trim();
  const subtitleText = (opts.subtitle || '').trim();
  const tagText = opts.tags
    ? opts.tags.split(',').map(tag => tag.trim()).filter(Boolean).join(' / ')
    : '';
  const TITLE_CELL_RATIO = 4.7 / 34;
  const SUBTITLE_CELL_RATIO = 3.8 / 23;
  const maxInlineCell = 3.6;
  const inlineGap = subtitleText ? 12 : 0;
  const bothPixel = canRenderPixelText(titleText)
    && (!subtitleText || canRenderPixelText(subtitleText));
  const combinedPixelLength = [...titleText, ...subtitleText].length;
  const fittedInlineCell = combinedPixelLength > 0
    ? Math.min(maxInlineCell, (maxTextWidth - inlineGap + maxInlineCell) / (combinedPixelLength * 6))
    : maxInlineCell;
  // 纯像素短句同一行循环打字；像素格低于 2.2 时改为分行，避免手机上看不清。
  const loopMode = Boolean(titleText) && bothPixel && fittedInlineCell >= 2.2;

  const tagIsPixel = Boolean(tagText) && canRenderPixelText(tagText);
  const tagCell = tagIsPixel ? fitPixelCellSize(tagText, 2.2, maxTextWidth) : 0;
  const tagSize = tagText && !tagIsPixel ? fitTypewriterFontSize(tagText, 13, maxTextWidth) : 0;
  const tagRowH = tagText ? (tagIsPixel ? tagCell * 7 : tagSize * 1.1) : 0;
  const tagGap = tagText ? 12 : 0;


  let blockH = 0;
  let layoutText;
  let finalLine = null;

  if (loopMode) {
    const rowH = fittedInlineCell * 7;
    blockH = rowH + tagGap + tagRowH;
    layoutText = top => {
      const loop = buildPixelTerminalLoop(
        titleText, subtitleText, textX, top + rowH, fittedInlineCell,
        C.text, C.accent, C.light, C.bg, inlineGap,
      );
      return { svg: loop.svg, tagTop: top + rowH + tagGap };
    };
  } else {
    const measureTitle = (text, size) => measureTerminalText(text, size, TITLE_CELL_RATIO);
    const measureSubtitle = (text, size) => measureTerminalText(text, size, SUBTITLE_CELL_RATIO);
    const title = layoutLines(titleText, { fontSize: 26, minFontSize: 20, maxWidth: maxTextWidth, measure: measureTitle });
    const subtitle = layoutLines(subtitleText, { fontSize: 16, minFontSize: 14, maxWidth: maxTextWidth, measure: measureSubtitle, prefer: 'shrink' });
    const titleLH = title.fontSize * 1.3;
    const subtitleLH = subtitle.fontSize * 1.45;
    const titleH = title.lines.length ? title.fontSize + (title.lines.length - 1) * titleLH : 0;
    const subtitleH = subtitle.lines.length ? subtitle.fontSize + (subtitle.lines.length - 1) * subtitleLH : 0;
    const titleSubGap = title.lines.length && subtitle.lines.length ? 12 : 0;
    blockH = titleH + titleSubGap + subtitleH + tagGap + tagRowH;
    layoutText = top => {
      const titleStart = 0.6;
      const titleBuilt = buildTerminalLines(
        title, textX, top + title.fontSize * 0.92, titleLH, maxTextWidth, title.fontSize, TITLE_CELL_RATIO,
        C.text, C.monoFont, titleStart, 0.11, C.accent, C.bg, 'title',
      );
      const subtitleTop = top + titleH + titleSubGap;
      const subtitleStart = title.lines.length ? titleBuilt.endDelay + 0.14 : titleStart;
      const subtitleBuilt = buildTerminalLines(
        subtitle, textX, subtitleTop + subtitle.fontSize * 0.92, subtitleLH, maxTextWidth, subtitle.fontSize, SUBTITLE_CELL_RATIO,
        C.accent, C.monoFont, subtitleStart, 0.08, C.accent, C.bg, 'subtitle',
      );
      finalLine = subtitleBuilt.last || titleBuilt.last || null;
      return { svg: titleBuilt.svg + subtitleBuilt.svg, tagTop: subtitleTop + subtitleH + tagGap };
    };
  }

  const H = Math.max(spriteH, blockH) + pad * 2;
  const blockTop = (H - blockH) / 2;
  const spriteTop = (H - spriteH) / 2;
  const laidOut = layoutText(blockTop);


  let svg = openCover(C, W, H, ' data-template="xiaolan-terminal"');
  // 角色帧坐标系里身体位于 translate(20 18)，整体缩放后再平移到左侧。
  svg += `<g data-xiaolan-layout="mobile" transform="translate(${n1(spriteX - 20 * spriteScale)} ${n1(spriteTop - 18 * spriteScale)}) scale(${spriteScale})">${buildXiaolanTerminalSprite(C)}</g>`;
  svg += laidOut.svg;
  if (tagText) {
    if (tagIsPixel) {
      svg += renderPixelGlyphs(tagText, textX, n1(laidOut.tagTop), tagCell, C.secondary, 'tags');
    } else {
      svg += `<text x="${textX}" y="${n1(laidOut.tagTop + tagSize * 0.88)}" text-anchor="start" font-size="${tagSize}" font-weight="600" fill="${C.secondary}" font-family="${C.uiFont}" letter-spacing="1"><tspan leaf="">${escapeSvgAttribute(tagText)}</tspan></text>`;
    }
  }
  if (finalLine) {
    const finalDelay = finalLine.endDelay;
    const finalCursorX = finalLine.lastCursorX + 3;
    const finalCursorW = Math.max(2, finalLine.cursorW);
    svg += `<rect data-typewriter-cursor="final" x="${finalCursorX.toFixed(1)}" y="${finalLine.cursorY.toFixed(1)}" width="${finalCursorW.toFixed(1)}" height="${finalLine.cursorH.toFixed(1)}" fill="${C.accent}" opacity="0"><animate attributeName="opacity" values="0;1" dur="0.05s" begin="${finalDelay.toFixed(2)}s" fill="freeze"/><animate attributeName="opacity" values="1;1;0;0" dur="1.2s" begin="${(finalDelay + 0.1).toFixed(2)}s" repeatCount="indefinite"/></rect>`;
  }
  svg += `</svg>`;
  return svg;
}

// ─── 模板 4: 画卷展开 ──────────────────────────────────
function templateScrollPainting(C, opts) {
  const W = COVER_W, cx = W / 2;
  const left = COVER_MARGIN, right = W - COVER_MARGIN;
  let body = '';

  // 上方横线:从左到右
  const topLineY = 22;
  body += `<rect x="${left}" y="${topLineY}" width="0" height="1.5" rx="0.75" fill="${C.tertiary}"><animate attributeName="width" values="0;${COVER_CONTENT_W}" dur="0.6s" begin="0.2s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.25 0.1 0.25 1"/></rect>`;

  // 主标题
  const title = layoutLines(opts.title, { fontSize: 28, minFontSize: 24, maxWidth: COVER_CONTENT_W });
  const titleLH = title.fontSize * 1.32;
  const titleBox = textBlockMetrics(title, topLineY + 1.5 + 20, titleLH);
  body += coverText(title, { x: cx, y: titleBox.baseline, lineHeight: titleLH, weight: '500', fill: C.text, font: C.headingFont });

  // 下方横线:从右到左
  const bottomLineY = titleBox.bottom + 16;
  body += `<rect x="${left}" y="${n1(bottomLineY)}" width="0" height="1.5" rx="0.75" fill="${C.tertiary}"><animate attributeName="width" values="0;${COVER_CONTENT_W}" dur="0.5s" begin="1.3s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.25 0.1 0.25 1"/><animate attributeName="x" values="${right};${left}" dur="0.5s" begin="1.3s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.25 0.1 0.25 1"/></rect>`;
  let cursor = bottomLineY + 1.5;

  // 副标题
  const subtitle = layoutLines(opts.subtitle, { fontSize: 15, minFontSize: 14, maxWidth: COVER_CONTENT_W, prefer: 'shrink' });
  const subtitleLH = subtitle.fontSize * 1.5;
  const subtitleBox = textBlockMetrics(subtitle, cursor + 16, subtitleLH);
  body += coverText(subtitle, { x: cx, y: subtitleBox.baseline, lineHeight: subtitleLH, fill: C.tertiary, font: C.serifFont });
  if (subtitle.lines.length) cursor = subtitleBox.bottom;

  // 日期标记 + 作者标记
  const metaBase = cursor + 30;
  const dateStr = opts.date || new Date().toISOString().slice(0, 7).replace('-', '.');
  body += `<g><text x="${left}" y="${n1(metaBase)}" font-size="12" fill="${C.hint}" font-family="${C.uiFont}" letter-spacing="1"><tspan leaf="">${escapeSvgAttribute(dateStr)}</tspan></text><rect x="${left}" y="${n1(metaBase + 6)}" width="72" height="1" fill="${C.light}"/></g>`;

  // 作者标记:显式 author 原样使用;未传时沿用「<topLabel> 出品」;author === false 隐藏
  const derived = (C.topLabel || '').replace(/[·].*/, '').trim();
  const byline = opts.author === false ? ''
    : opts.author ? opts.author
    : derived ? `${derived} 出品` : '';
  if (byline) {
    const bylineMax = COVER_CONTENT_W - measureCoverText(dateStr, 12, 1) - 24;
    const bylineSize = Math.max(11, Math.min(12, Math.floor(12 * bylineMax / Math.max(1, measureCoverText(byline, 12, 1)) * 10) / 10));
    body += `<g><text x="${right}" y="${n1(metaBase)}" text-anchor="end" font-size="${bylineSize}" fill="${C.hint}" font-family="${C.uiFont}" letter-spacing="1"><tspan leaf="">${byline}</tspan></text><rect x="${right - 72}" y="${n1(metaBase + 6)}" width="72" height="1" fill="${C.light}"/></g>`;
  }

  // 向下滑动
  const hintBase = metaBase + 6 + 30;
  const arrowBase = hintBase + 20;
  body += `<text x="${cx}" y="${n1(hintBase)}" text-anchor="middle" font-size="12" fill="${C.hint}" font-family="${C.uiFont}" letter-spacing="2"><tspan leaf="">向下滑动查看全文</tspan></text>`;
  body += scrollArrow(cx, arrowBase, 14, C.hint, '3.3s');
  const H = arrowBase + 12;

  return `${openCover(C, W, H)}${body}</svg>`;
}

// ─── 模板 5: 聚焦聚光灯 ────────────────────────────────
function templateSpotlight(C, opts) {
  const W = COVER_W, cx = W / 2;
  const tagList = opts.tags ? opts.tags.split(',').map(t => t.trim()).filter(Boolean) : [];
  let cursor = 22;

  // 品牌标签
  let label = '';
  if (C.topLabel) {
    const labelBase = cursor + 11;
    label = `<text x="${cx}" y="${n1(labelBase)}" text-anchor="middle" font-size="12" font-weight="600" fill="${C.accent}" letter-spacing="3" font-family="${C.uiFont}"><tspan leaf="">${C.topLabel} · 深度评测</tspan></text>`;
    cursor = labelBase + 22;
  }

  // 主标题
  const title = layoutLines(opts.title, { fontSize: 30, minFontSize: 24, maxWidth: COVER_CONTENT_W });
  const titleLH = title.fontSize * 1.3;
  const titleBox = textBlockMetrics(title, cursor, titleLH);
  const spotCy = (cursor + titleBox.bottom) / 2;

  // 聚光灯渐变
  const gradientId = `spotlight-${Date.now()}`;
  let body = `<defs><radialGradient id="${gradientId}"><stop offset="0%" stop-color="${C.accent}" stop-opacity="0.12"/><stop offset="60%" stop-color="${C.accent}" stop-opacity="0.04"/><stop offset="100%" stop-color="${C.accent}" stop-opacity="0"/></radialGradient></defs>`;
  body += `<circle cx="${cx}" cy="${n1(spotCy)}" r="0" fill="url(#${gradientId})"><animate attributeName="r" values="0;130" dur="0.8s" begin="0.3s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.25 0.1 0.25 1"/></circle>`;
  body += label;
  if (title.lines.length) {
    const baseline = titleBox.baseline;
    body += `<g transform="translate(${cx},${n1(baseline)})">${coverText(title, { x: 0, y: 0, lineHeight: titleLH, weight: '500', fill: C.text, font: C.headingFont })}</g>`;
  }

  // 粗短线
  const barY = (title.lines.length ? titleBox.bottom : cursor) + 12;
  body += `<rect x="${cx - 32}" y="${n1(barY)}" width="0" height="4" rx="2" fill="${C.accent}" opacity="0"><animate attributeName="width" values="0;64" dur="0.3s" begin="2.5s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.22 1 0.36 1"/><animate attributeName="opacity" values="0;1" dur="0.05s" begin="2.5s" fill="freeze"/></rect>`;
  cursor = barY + 4;

  // 副标题
  const subtitle = layoutLines(opts.subtitle, { fontSize: 15, minFontSize: 14, maxWidth: COVER_CONTENT_W, prefer: 'shrink' });
  const subtitleLH = subtitle.fontSize * 1.5;
  const subtitleBox = textBlockMetrics(subtitle, cursor + 16, subtitleLH);
  body += coverText(subtitle, { x: cx, y: subtitleBox.baseline, lineHeight: subtitleLH, fill: C.tertiary, font: C.serifFont });
  if (subtitle.lines.length) cursor = subtitleBox.bottom;

  // 判断标签
  if (tagList.length >= 2) {
    const tagFont = 12, tagH = 28, gap = 12;
    const widths = tagList.slice(0, 2).map(tag => Math.max(84, measureCoverText(tag, tagFont) + 28));
    const tagY = cursor + 18;
    const x0 = cx - gap / 2 - widths[0];
    const x1 = cx + gap / 2;
    body += `<g><rect x="${n1(x0)}" y="${n1(tagY)}" width="${n1(widths[0])}" height="${tagH}" rx="4" fill="${C.accent}"/><text x="${n1(x0 + widths[0] / 2)}" y="${n1(tagY + 18.5)}" text-anchor="middle" font-size="${tagFont}" font-weight="600" fill="#fff" font-family="${C.uiFont}"><tspan leaf="">${escapeSvgAttribute(tagList[0])}</tspan></text></g>`;
    body += `<g><rect x="${n1(x1)}" y="${n1(tagY)}" width="${n1(widths[1])}" height="${tagH}" rx="4" fill="none" stroke="${C.secondary}" stroke-width="1.5"/><text x="${n1(x1 + widths[1] / 2)}" y="${n1(tagY + 18.5)}" text-anchor="middle" font-size="${tagFont}" font-weight="600" fill="${C.secondary}" font-family="${C.uiFont}"><tspan leaf="">${escapeSvgAttribute(tagList[1])}</tspan></text></g>`;
    cursor = tagY + tagH;
  }

  // 向下滑动
  const hintBase = cursor + 34;
  const arrowBase = hintBase + 20;
  body += `<text x="${cx}" y="${n1(hintBase)}" text-anchor="middle" font-size="12" fill="${C.hint}" font-family="${C.uiFont}" letter-spacing="2"><tspan leaf="">向下滑动查看深度分析</tspan></text>`;
  body += scrollArrow(cx, arrowBase, 14, C.hint, '4.3s');
  const H = arrowBase + 12;

  return `${openCover(C, W, H)}${body}</svg>`;
}

// ─── 模板 6: 极简白描 ──────────────────────────────────
function templateMinimalSketch(C, opts) {
  const W = COVER_W, cx = W / 2;
  let body = '';
  let cursor = 52;

  // 主标题:静态可见，大留白
  const title = layoutLines(opts.title, { fontSize: 28, minFontSize: 24, maxWidth: COVER_CONTENT_W });
  const titleLH = title.fontSize * 1.36;
  const titleBox = textBlockMetrics(title, cursor, titleLH);
  body += coverText(title, { x: cx, y: titleBox.baseline, lineHeight: titleLH, weight: '400', fill: C.text, font: C.headingFont });
  if (title.lines.length) cursor = titleBox.bottom;

  // 细线
  const lineY = cursor + 18;
  body += `<rect x="${cx - 28}" y="${n1(lineY)}" width="0" height="1" rx="0.5" fill="${C.tertiary}" opacity="0.6"><animate attributeName="width" values="0;56" dur="0.8s" begin="1.5s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.22 1 0.36 1"/></rect>`;
  cursor = lineY + 1;

  // 副标题
  const subtitle = layoutLines(opts.subtitle, { fontSize: 15, minFontSize: 14, maxWidth: COVER_CONTENT_W, prefer: 'shrink' });
  const subtitleLH = subtitle.fontSize * 1.6;
  const subtitleBox = textBlockMetrics(subtitle, cursor + 18, subtitleLH);
  body += coverText(subtitle, { x: cx, y: subtitleBox.baseline, lineHeight: subtitleLH, fill: C.tertiary, font: C.serifFont });
  if (subtitle.lines.length) cursor = subtitleBox.bottom;

  // 呼吸圆点
  const dotY = cursor + 48;
  body += `<circle cx="${cx}" cy="${n1(dotY)}" r="4" fill="${C.accent}" opacity="0"><animate attributeName="opacity" values="0;0.3;0.8;0.3;0" dur="2s" begin="2.8s" repeatCount="indefinite"/><animate attributeName="r" values="4;6;4" dur="2s" begin="2.8s" repeatCount="indefinite" calcMode="spline" keyTimes="0;0.5;1" keySplines="0.4 0 0.6 1;0.4 0 0.6 1"/></circle>`;
  const H = dotY + 40;

  return `${openCover(C, W, H)}${body}</svg>`;
}

// ─── 主入口:从主题生成开场动画 ────────────────────────
const TEMPLATES = {
  'ink-wash': templateInkWash,
  'typewriter': templateTypewriter,
  'xiaolan-terminal': templateXiaolanTerminal,
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
    topLabel,
  } = options;

  // 从主题取色(带兜底)
  const C = {
    bg: theme.background_color || '#F5F4ED',
    surface: theme.surface_color || '#FAF9F5',
    accent: theme.accent_color || '#B85235',
    secondary: theme.accent_secondary || theme.trust_blue || '#1B365D',
    text: theme.text_color || '#141413',
    tertiary: theme.tertiary_color || theme.secondary_color || '#6B6A64',
    light: '#D8D5C8',
    hint: '#9CA3AF',
    headingFont: theme.heading_font || "'TsangerJinKai02','Source Han Serif SC','Songti SC',Georgia,serif",
    serifFont: theme.font_family_cn || "'Source Han Serif SC','Songti SC',serif",
    uiFont: theme.ui_font || "'Source Han Sans SC','PingFang SC',sans-serif",
    // Keep broad Latin fallbacks, but never treat font choice as a substitute
    // for static semantic text. WeChat readers may discard early SMIL state.
    monoFont: normalizeTypewriterFont(theme.code_font || "Menlo,Consolas,'Courier New',monospace"),
    // options.topLabel 优先于主题(空字符串表示隐藏);品牌标签与署名在此统一转义
    topLabel: escapeSvgAttribute(topLabel ?? theme.top_label ?? ''),
  };

  const fn = TEMPLATES[template] || TEMPLATES['ink-wash'];
  const safeAuthor = author === false ? false : escapeSvgAttribute(author || '');
  return fn(C, { title, subtitle, tags, date, author: safeAuthor });
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
    ...(opts.topLabel !== null && { topLabel: /^none$/i.test(opts.topLabel.trim()) ? '' : opts.topLabel.trim() }),
    ...(opts.author !== null && { author: (!opts.author.trim() || /^none$/i.test(opts.author.trim())) ? false : opts.author.trim() }),
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

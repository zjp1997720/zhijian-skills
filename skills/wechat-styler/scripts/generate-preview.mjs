#!/usr/bin/env node

/**
 * Theme Preview Generator
 *
 * 为每个主题生成独立 HTML 文件，然后用 iframe 并排嵌入预览页面。
 * 这样 preview 和实际转换输出完全一致，不是简化渲染。
 *
 * Usage:
 *   node scripts/generate-preview.mjs [article.md] [options]
 *
 * Options:
 *   --themes <t1,t2,...>   只渲染指定主题（逗号分隔），默认全部
 *   --output <path>        自定义输出路径，默认 <skill-root>/preview.html
 *
 * Examples:
 *   node scripts/generate-preview.mjs article.md
 *   node scripts/generate-preview.mjs article.md --themes magazine-ink,magazine-indigo,magazine-forest
 *   node scripts/generate-preview.mjs article.md --themes kami,elegant --output /tmp/my-preview.html
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';
import yaml from 'js-yaml';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SKILL_ROOT = path.resolve(__dirname, '..');

const THEMES = [
  'zhijian',
  'kami',
  'elegant',
  'minimal',
  'magazine-ink',
  'magazine-indigo',
  'magazine-forest',
  'modern'
];

const SAMPLE_ARTICLE = `---
title: 主题预览示例
summary: 展示所有主题的排版效果
---

## 这是二级标题

这是一段正文，用来展示正文的字体、字号、行高和颜色。这段文字包含**加粗文本**和\`行内代码\`，以及[链接文本](https://example.com)。

### 这是三级标题

> 这是一段引用文字，用来展示引用块的样式。引用块通常用于摘录、强调或引用他人的话。

#### 列表示例

- 无序列表项 1
- 无序列表项 2
- 无序列表项 3

1. 有序列表项 1
2. 有序列表项 2
3. 有序列表项 3

#### 代码块示例

\`\`\`javascript
function hello() {
  console.log('Hello, World!');
  return true;
}
\`\`\`

#### 表格示例

| 主题 | 风格 | 适用场景 |
|------|------|----------|
| kami | 纸感 | 深度文章 |
| modern | 现代 | 科技产品 |
| elegant | 复古 | 商业案例 |

---

这是分隔线后的内容，用来测试段落间距和整体节奏。
`;

function loadThemeMeta(themeName) {
  const themePath = path.join(SKILL_ROOT, 'themes', `${themeName}.yaml`);
  const theme = yaml.load(fs.readFileSync(themePath, 'utf8'));
  return {
    accent_color: theme.accent_color || '#333',
    description: theme.description || ''
  };
}

function parseArgs() {
  const raw = process.argv.slice(2);
  let articleArg = null;
  let themesArg = null;
  let outputArg = null;

  for (let i = 0; i < raw.length; i++) {
    if (raw[i] === '--themes' && raw[i + 1]) {
      themesArg = raw[++i].split(',').map(t => t.trim()).filter(Boolean);
    } else if (raw[i] === '--output' && raw[i + 1]) {
      outputArg = path.resolve(raw[++i]);
    } else if (!raw[i].startsWith('--') && !articleArg) {
      articleArg = raw[i];
    }
  }
  return { articleArg, themesArg, outputArg };
}

function main() {
  const { articleArg, themesArg, outputArg } = parseArgs();

  // 主题过滤
  const activeThemes = themesArg
    ? THEMES.filter(t => themesArg.includes(t))
    : THEMES;

  if (themesArg && activeThemes.length === 0) {
    console.error(`No matching themes found. Available: ${THEMES.join(', ')}`);
    process.exit(1);
  }

  if (themesArg) {
    console.log(`Filtering to themes: ${activeThemes.join(', ')}`);
  }

  let articlePath;
  if (articleArg) {
    articlePath = path.resolve(articleArg);
    if (!fs.existsSync(articlePath)) {
      console.log(`Article not found: ${articlePath}, using default sample`);
      articlePath = null;
    } else {
      console.log(`Using custom article: ${articlePath}`);
    }
  }

  // 如果没有指定文章，写临时 sample 文件
  let tempSample = null;
  if (!articlePath) {
    console.log('Using default sample article');
    tempSample = path.join(SKILL_ROOT, '_preview_sample_tmp.md');
    fs.writeFileSync(tempSample, SAMPLE_ARTICLE, 'utf8');
    articlePath = tempSample;
  }

  const convertScript = path.join(SKILL_ROOT, 'scripts', 'convert.mjs');

  // frames 目录紧邻最终输出文件，保证相对路径正确
  const finalOutputPath = outputArg || path.join(SKILL_ROOT, 'preview.html');
  const previewDir = path.join(path.dirname(finalOutputPath), '_preview_frames');

  // 清理并重建临时目录
  if (fs.existsSync(previewDir)) {
    fs.rmSync(previewDir, { recursive: true });
  }
  fs.mkdirSync(previewDir, { recursive: true });

  console.log(`Generating preview for ${activeThemes.length} themes...\n`);

  const iframeSrcs = [];

  for (const themeName of activeThemes) {
    console.log(`- ${themeName}`);
    const outputPath = path.join(previewDir, `${themeName}.html`);
    try {
      execSync(
        `node "${convertScript}" "${articlePath}" --theme ${themeName} --output "${outputPath}"`,
        { stdio: 'pipe' }
      );
      iframeSrcs.push({ themeName, outputPath, relPath: `_preview_frames/${themeName}.html` });
    } catch (err) {
      console.error(`  ✗ Failed: ${err.message}`);
    }
  }

  // 清理临时 sample
  if (tempSample && fs.existsSync(tempSample)) {
    fs.unlinkSync(tempSample);
  }

  // 生成预览外壳 HTML
  const cols = iframeSrcs.map(({ themeName, relPath }) => {
    const meta = loadThemeMeta(themeName);
    return `
      <div class="theme-col">
        <div class="theme-label">
          <span class="theme-name" style="color:${meta.accent_color};">${themeName}</span>
          <span class="theme-desc">${meta.description}</span>
        </div>
        <iframe
          src="${relPath}"
          class="theme-frame"
          scrolling="yes"
          frameborder="0"
        ></iframe>
      </div>`;
  }).join('\n');

  const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>WeChat Styler - 主题预览</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; }

    html, body {
      margin: 0;
      padding: 0;
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: #f0ede4;
      font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
    }

    .page {
      display: flex;
      flex-direction: column;
      width: 100%;
      height: 100vh;
    }

    /* 顶部标题栏 */
    .header {
      flex: 0 0 auto;
      text-align: center;
      padding: 20px 24px 16px;
    }
    .header h1 {
      font-size: 20px;
      font-weight: 600;
      color: #1a1a18;
      margin: 0 0 6px;
      letter-spacing: 0.02em;
    }
    .header p {
      font-size: 12px;
      color: #8a8880;
      margin: 0;
    }

    /* 横向滚动轨道 */
    .track {
      flex: 1 1 0;
      display: flex;
      flex-direction: row;
      gap: 12px;
      padding: 0 20px 16px;
      overflow-x: scroll;
      overflow-y: hidden;
      scroll-behavior: smooth;
      /* 不设 snap，这样可以自由滑动 */
    }
    .track::-webkit-scrollbar { height: 5px; }
    .track::-webkit-scrollbar-track { background: #e4e0d7; border-radius: 3px; }
    .track::-webkit-scrollbar-thumb { background: #b0aca3; border-radius: 3px; }

    /* 每列 */
    .theme-col {
      flex: 0 0 460px;
      display: flex;
      flex-direction: column;
      min-width: 0;
    }

    /* 列标题 */
    .theme-label {
      flex: 0 0 auto;
      padding: 8px 4px 6px;
      display: flex;
      align-items: baseline;
      gap: 8px;
    }
    .theme-name {
      font-size: 13px;
      font-weight: 600;
    }
    .theme-desc {
      font-size: 11px;
      color: #8a8880;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    /* iframe 容器 */
    .theme-frame {
      flex: 1 1 0;
      width: 100%;
      border: 1px solid #d8d4cb;
      border-radius: 6px;
      background: #fff;
      display: block;
      /* iframe 自己处理纵向滚动 */
    }
  </style>
</head>
<body>
  <div class="page">
    <div class="header">
      <h1>WeChat Styler 主题预览</h1>
      <p>在主题卡片内滚动查看全文 · 拖动底部滚动条切换主题</p>
    </div>
    <div class="track" id="track">
      ${cols}
    </div>
  </div>

  <script>
    // 鼠标在 track 上（但不在 iframe 内）时，垂直滚动转横向
    // 注意：iframe 内部的 wheel 事件不会冒泡到父页面，天然隔离
    const track = document.getElementById('track');
    track.addEventListener('wheel', (e) => {
      // 如果是水平方向本来就有 deltaX（触控板横扫），直接让浏览器处理
      if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) return;
      e.preventDefault();
      track.scrollLeft += e.deltaY * 1.5;
    }, { passive: false });
  </script>
</body>
</html>`;

  fs.writeFileSync(finalOutputPath, html, 'utf8');

  console.log(`\n✓ Preview generated: ${finalOutputPath}`);
  console.log(`  Frames saved in: ${previewDir}`);
}

main();

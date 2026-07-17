#!/usr/bin/env node

/**
 * WeChat Styler - Markdown to WeChat HTML Converter
 *
 * Converts Markdown articles to beautifully styled HTML for WeChat Official Account
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { execFile } from 'child_process';
import { marked } from 'marked';
import yaml from 'js-yaml';
import { glob } from 'glob';
import { validateHtml, formatReport } from './validate.mjs';
import { applyComponentsPreMarkdown, applyComponentsPostMarkdown, applyPureFallback, applyHighlightPreMarkdown } from './components.mjs';
import { generateCoverAnimation } from './generate-cover-animation.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SKILL_ROOT = path.resolve(__dirname, '..');

// Parse command line arguments
function parseArgs() {
  const args = process.argv.slice(2);
  const options = {
    input: null,
    theme: 'zhijian',
    fontSize: null,
    lineHeight: null,
    accentColor: null,
    backgroundColor: null,
    maxWidth: null,
    output: null,
    components: false,
    cover: false,
    coverTemplate: 'ink-wash',
    coverTitle: null,
    coverSubtitle: null,
    coverTags: null
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    if (!arg.startsWith('--')) {
      if (!options.input) options.input = arg;
      continue;
    }

    const key = arg.slice(2);

    // --components 是布尔参数,不消费下一个 token(除非显式跟 false/0/no)
    if (key === 'components') {
      const next = args[i + 1];
      if (next && !next.startsWith('--')) {
        i++;
        options.components = !/^(0|false|no)$/i.test(next);
      } else {
        options.components = true;
      }
      continue;
    }

    // --cover 是布尔参数,不消费下一个 token(除非显式跟 false/0/no)
    if (key === 'cover') {
      const next = args[i + 1];
      if (next && !next.startsWith('--')) {
        i++;
        options.cover = !/^(0|false|no)$/i.test(next);
      } else {
        options.cover = true;
      }
      continue;
    }

    const value = args[++i];

    switch (key) {
      case 'theme':
        options.theme = value;
        break;
      case 'font-size':
        options.fontSize = parseInt(value);
        break;
      case 'line-height':
        options.lineHeight = parseFloat(value);
        break;
      case 'accent-color':
        options.accentColor = value;
        break;
      case 'background-color':
        options.backgroundColor = value;
        break;
      case 'max-width':
        options.maxWidth = parseInt(value);
        break;
      case 'output':
        options.output = value;
        break;
      case 'cover-title':
        options.coverTitle = value;
        break;
      case 'cover-subtitle':
        options.coverSubtitle = value;
        break;
      case 'cover-tags':
        options.coverTags = value;
        break;
      case 'cover-template':
        options.coverTemplate = value;
        break;
    }
  }

  if (!options.input) {
    console.error('Error: Input file required');
    console.error('Usage: node convert.mjs <input.md> [--theme kami] [--font-size 16] [--line-height 1.55] [--output output.html]');
    process.exit(1);
  }

  return options;
}

// Load theme configuration
function loadTheme(themeName) {
  const themePath = path.join(SKILL_ROOT, 'themes', `${themeName}.yaml`);

  if (!fs.existsSync(themePath)) {
    console.error(`Error: Theme "${themeName}" not found`);
    process.exit(1);
  }

  const themeContent = fs.readFileSync(themePath, 'utf8');
  const theme = yaml.load(themeContent);
  return normalizeTheme({
    surface_color: theme.background_color,
    tertiary_color: theme.secondary_color,
    ui_font: theme.font_family_cn,
    border_color: theme.divider_color,
    tag_bg: theme.code_bg,
    ...theme
  });
}

const presetDefaults = {
  'kami-document': {
    type_scale: { h1: 29, h2: 21, h3: 18, body: 16, caption: 12, code: 14 },
    rhythm: {
      body_line_height: 1.58,
      heading_line_height: 1.22,
      paragraph_margin: 16,
      section_padding_first: 20,
      section_padding: 32,
      list_item_margin: 8
    },
    block_style: {
      heading_style: 'left-bar',
      quote_style: 'lifted',
      list_style: 'standard',
      code_style: 'document',
      image_style: 'soft-frame'
    },
    top_label: 'ARTICLE'
  },
  'magazine-editorial': {
    type_scale: { h1: 32, h2: 26, h3: 19, body: 16, caption: 12, code: 13 },
    rhythm: {
      body_line_height: 1.75,
      heading_line_height: 1.14,
      paragraph_margin: 18,
      section_padding_first: 22,
      section_padding: 34,
      list_item_margin: 9
    },
    block_style: {
      heading_style: 'rule',
      quote_style: 'pullquote',
      list_style: 'editorial',
      code_style: 'archive',
      image_style: 'editorial-frame'
    },
    top_label: 'VOL. 01'
  },
  'elegant-essay': {
    type_scale: { h1: 28, h2: 23, h3: 18, body: 16, caption: 12, code: 14 },
    rhythm: {
      body_line_height: 1.9,
      heading_line_height: 1.32,
      paragraph_margin: 18,
      section_padding_first: 24,
      section_padding: 36,
      list_item_margin: 10
    },
    block_style: {
      heading_style: 'centered-rule',
      quote_style: 'excerpt',
      list_style: 'essay',
      code_style: 'quiet',
      image_style: 'classic'
    },
    top_label: 'ESSAY'
  },
  'modern-technical': {
    type_scale: { h1: 28, h2: 23, h3: 18, body: 16, caption: 12, code: 14 },
    rhythm: {
      body_line_height: 1.78,
      heading_line_height: 1.24,
      paragraph_margin: 16,
      section_padding_first: 20,
      section_padding: 32,
      list_item_margin: 8
    },
    block_style: {
      heading_style: 'technical',
      quote_style: 'note-card',
      list_style: 'checklist',
      code_style: 'technical',
      image_style: 'doc-frame'
    },
    top_label: 'GUIDE'
  },
  'minimal-notes': {
    type_scale: { h1: 25, h2: 20, h3: 17, body: 15, caption: 12, code: 13 },
    rhythm: {
      body_line_height: 2.0,
      heading_line_height: 1.35,
      paragraph_margin: 18,
      section_padding_first: 22,
      section_padding: 34,
      list_item_margin: 9
    },
    block_style: {
      heading_style: 'whitespace',
      quote_style: 'hairline',
      list_style: 'minimal',
      code_style: 'quiet',
      image_style: 'bare'
    },
    top_label: 'NOTE'
  },
  'zhijian-warm-paper': {
    type_scale: { h1: 28, h2: 22, h3: 18, body: 17, caption: 13, code: 14 },
    rhythm: {
      body_line_height: 1.58,
      heading_line_height: 1.22,
      paragraph_margin: 20,
      section_padding_first: 20,
      section_padding: 32,
      list_item_margin: 10
    },
    block_style: {
      heading_style: 'warm-bar',
      quote_style: 'human-callout',
      list_style: 'standard',
      code_style: 'dark-terminal',
      image_style: 'soft-frame'
    },
    top_label: '智见AI'
  }
};

function inferPreset(theme) {
  if (theme.renderer_preset) return theme.renderer_preset;
  if (theme.name === 'zhijian') return 'zhijian-warm-paper';
  if (theme.name?.startsWith('magazine-')) return 'magazine-editorial';
  if (theme.name === 'elegant') return 'elegant-essay';
  if (theme.name === 'modern') return 'modern-technical';
  if (theme.name === 'minimal') return 'minimal-notes';
  return 'kami-document';
}

function mergeObject(defaultValue, themeValue) {
  return { ...(defaultValue || {}), ...(themeValue || {}) };
}

function normalizeTheme(theme) {
  const rendererPreset = inferPreset(theme);
  const defaults = presetDefaults[rendererPreset];

  if (!defaults) {
    console.error(`Error: Renderer preset "${rendererPreset}" not found`);
    console.error(`Supported presets: ${Object.keys(presetDefaults).join(', ')}`);
    process.exit(1);
  }

  const typeScale = mergeObject(defaults.type_scale, theme.type_scale);
  const rhythm = mergeObject(defaults.rhythm, theme.rhythm);
  const blockStyle = mergeObject(defaults.block_style, theme.block_style);

  return {
    ...theme,
    renderer_preset: rendererPreset,
    type_scale: typeScale,
    rhythm,
    block_style: blockStyle,
    top_label: theme.top_label || defaults.top_label,
    font_size: theme.font_size || typeScale.body,
    line_height: theme.line_height || rhythm.body_line_height,
    accent_secondary: theme.accent_secondary || theme.secondary_color,
    surface_color: theme.surface_color || theme.background_color,
    tertiary_color: theme.tertiary_color || theme.secondary_color,
    ui_font: theme.ui_font || theme.font_family_cn,
    border_color: theme.border_color || theme.divider_color,
    tag_bg: theme.tag_bg || theme.code_bg
  };
}

// Parse Markdown with frontmatter
function parseMarkdown(content) {
  const frontmatterRegex = /^---\n([\s\S]*?)\n---\n([\s\S]*)$/;
  const match = content.match(frontmatterRegex);

  if (match) {
    const frontmatter = yaml.load(match[1]);
    const markdown = match[2];
    return { frontmatter, markdown };
  }

  return { frontmatter: {}, markdown: content };
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}

function escapeAttr(value = '') {
  return escapeHtml(value).replaceAll('"', '&quot;');
}

function bgSpan(theme, text, bg = theme.background_color) {
  return `<span style="background-color:${bg};">${text}</span>`;
}

function imageStyle(radius) {
  return `max-width:100%;border-radius:${radius};width:100%;height:auto !important;display:block;margin:0 auto;box-sizing:border-box;`;
}

/**
 * 任务列表 checkbox 处理:marked 把 - [x] / - [ ] 渲染成
 * <input checked disabled type="checkbox"> 前缀。<input> 在公众号被剥离,
 * 这里替换成可视化字符 ✓ / ☐,保留语义不破版。
 */
function processTaskListItem(text, theme) {
  return text.replace(
    /^<input\s+([^>]*?)type="checkbox"\s*([^>]*?)>\s*/,
    (match, before, after) => {
      const isChecked = /checked/i.test(before) || /checked/i.test(after);
      const color = isChecked ? theme.accent_color : theme.tertiary_color;
      return `<span style="font-family:${theme.ui_font};color:${color};margin-right:4px;">${isChecked ? '✓' : '☐'}</span> `;
    }
  );
}

/**
 * 构建占位符板块:把 Markdown 里的「【插入:xxx】」转成居中虚线灰框。
 * 用于「图床没准备好但想先看排版」的工作流。克制中性灰,不抢正文视觉。
 */
function buildPlaceholder(label, theme) {
  // 背景取比正文背景略浅一档的灰,边框用细分隔色
  const borderColor = theme.divider_color || '#CCCCCC';
  const bg = '#FAFAFA';
  const labelColor = theme.tertiary_color || '#999999';
  const escapedLabel = escapeHtml(label.trim());
  return `<section style="text-align:center;margin:24px 0;padding:20px 16px;border:1px dashed ${borderColor};background-color:${bg};border-radius:4px;">\n  <p style="font-family:${theme.ui_font};font-size:13px;color:${labelColor};margin:0;background-color:${bg};">📷 待补素材:${escapedLabel}</p>\n</section>\n`;
}

/**
 * 占位符 pre-markdown:把独占一行的【插入:xxx】换成临时 HTML block 标记。
 * marked 遇到 HTML block 会原样保留,不包 <p>,避免 block section 嵌套进 inline p。
 */
function applyPlaceholdersPreMarkdown(markdown) {
  // 匹配行首(可选空白)+ 【插入:xxx】 + 行尾;非独占行的不处理(保留原文)
  return markdown.replace(/^([ \t]*)【插入:([^\】]+)】[ \t]*$/gm, (match, indent, label) => {
    return `${indent}<div data-ph="${escapeAttr(label.trim())}"></div>`;
  });
}

/**
 * 占位符 post-markdown:把临时 <div data-ph="xxx"> 换成完整 placeholder section。
 */
function applyPlaceholdersPostMarkdown(html, theme) {
  return html.replace(/<div data-ph="([^"]*)"><\/div>/g, (_, labelRaw) => {
    // 还原 escapeAttr 转义
    const label = labelRaw
      .replaceAll('&quot;', '"')
      .replaceAll('&amp;', '&')
      .replaceAll('&lt;', '<')
      .replaceAll('&gt;', '>');
    return buildPlaceholder(label, theme);
  });
}

function replaceBackground(html, theme, bg) {
  return html.replaceAll(`background-color:${theme.background_color};`, `background-color:${bg};`);
}

function toneBlockContent(html, theme, bg, color = theme.secondary_color) {
  let toned = replaceBackground(html, theme, bg).replaceAll(`color:${theme.text_color};`, `color:${color};`);
  
  // 移除列表作为最后一个元素时最外层的 margin-bottom 声明
  toned = toned.replace(/(<(?:ul|ol)[^>]+?margin:\s*0\s+0\s+\d+px\s*(?:;)?)(?=[^>]*>[\s\S]*<\/(?:ul|ol)>\s*$)/i, (match) => {
    return match.replace(/margin:\s*0\s+0\s+\d+px\s*(?:;)?/i, 'margin:0;');
  });

  // 移除段落或最后一个块级元素的 margin-bottom 声明，避免 blockquote 内部底部留白和外部 padding 叠加
  toned = toned.replace(/(margin:\s*0\s+0\s+\d+px\s*(?:;)?)(?![\s\S]*margin:\s*0\s+0\s+\d+px)/i, 'margin:0;');
  
  return toned;
}

// Common style generators
function createHeadingBase(theme, weight = 500, color = theme.text_color, textAlign = null) {
  const alignStyle = textAlign ? `text-align:${textAlign};` : '';
  return `font-family:${theme.heading_font};font-weight:${weight};color:${color};word-break:break-word;background-color:${theme.background_color};${alignStyle}`;
}

function createTextBase(theme, fontFamily = theme.font_family_cn) {
  return `font-family:${fontFamily};color:${theme.text_color};background-color:${theme.background_color};`;
}

function createCodeStyle(theme, scale) {
  return `font-family:${theme.code_font};font-size:${scale.code}px;background-color:${theme.code_bg};color:${theme.code_color};`;
}

function softRule(theme, {
  width = '38%',
  maxWidth = 180,
  margin = '28px 0',
  align = 'center',
  color = theme.divider_color
} = {}) {
  const ruleMargin = align === 'left' ? '0 auto 0 0' : align === 'right' ? '0 0 0 auto' : '0 auto';
  const maxWidthStyle = maxWidth ? `max-width:${maxWidth}px;` : '';
  return `<section style="margin:${margin};background-color:${theme.background_color};"><section style="width:${width};${maxWidthStyle}border-top:1px solid ${color};height:0;margin:${ruleMargin};background-color:${theme.background_color};"><span><br /></span></section></section>\n`;
}

function createBaseRenderer(theme) {
  const renderer = new marked.Renderer();
  const scale = theme.type_scale;
  const rhythm = theme.rhythm;

  renderer.paragraph = (text) => {
    if (text.trim().startsWith('<section style="text-align:center')) {
      return `${text}\n`;
    }
    const indent = rhythm.paragraph_indent || 0;
    const indentStyle = indent > 0 ? `text-indent:${indent}em;` : '';
    return `<p style="font-family:${theme.font_family_cn};font-size:${scale.body}px;font-weight:400;color:${theme.text_color};line-height:${rhythm.body_line_height};letter-spacing:0.008em;text-align:justify;margin:0 0 ${rhythm.paragraph_margin}px;padding:0;${indentStyle}word-break:break-word;background-color:${theme.background_color};">${bgSpan(theme, text)}</p>\n`;
  };

  renderer.strong = (text) => {
    return `<strong style="color:${theme.accent_color};font-weight:500;background-color:${theme.background_color};">${bgSpan(theme, text)}</strong>`;
  };

  renderer.codespan = (code) => {
    const escapedCode = escapeHtml(code);
    return `<code style="font-family:${theme.code_font};font-size:${scale.code}px;color:${theme.code_color};background-color:${theme.code_bg};padding:2px 6px;border-radius:3px;"><span style="background-color:${theme.code_bg};">${escapedCode}</span></code>`;
  };

  renderer.code = (code) => {
    const escapedCode = escapeHtml(code);
    return `<pre style="font-family:${theme.code_font};font-size:${scale.code}px;color:${theme.code_color};background-color:${theme.code_bg};padding:14px 16px;border-radius:6px;overflow-x:auto;margin:0 0 ${rhythm.paragraph_margin}px;line-height:1.5;white-space:pre-wrap;word-break:break-word;"><code style="font-family:${theme.code_font};background-color:${theme.code_bg};color:${theme.code_color};">${escapedCode}</code></pre>\n`;
  };

  renderer.blockquote = (quote) => {
    const quoteContent = toneBlockContent(quote, theme, theme.quote_bg);
    return `<section style="background-color:${theme.quote_bg};border-left:2px solid ${theme.quote_border};padding:10px 16px;margin:0 0 ${rhythm.paragraph_margin}px;border-radius:0 6px 6px 0;">\n${quoteContent}</section>\n`;
  };

  renderer.image = (href, title, text) => {
    const alt = text || title || '';
    return `<section style="text-align:center;margin:0;background-color:${theme.background_color};">
    <img src="${escapeAttr(href)}" alt="${escapeAttr(alt)}" style="${imageStyle('6px')}">
</section>
<p style="font-family:${theme.ui_font};font-size:${scale.caption}px;color:${theme.tertiary_color};text-align:center;margin:2px 0 ${rhythm.paragraph_margin}px;word-break:break-word;background-color:${theme.background_color};">${bgSpan(theme, alt)}</p>\n`;
  };

  renderer.list = (body, ordered) => {
    const tag = ordered ? 'ol' : 'ul';
    const listStyle = ordered ? 'list-style-type:decimal;' : 'list-style-type:disc;';
    return `<${tag} style="font-family:${theme.font_family_cn};font-size:${scale.body}px;color:${theme.text_color};line-height:${rhythm.body_line_height};margin:0 0 ${rhythm.paragraph_margin}px;padding-left:24px;${listStyle}background-color:${theme.background_color};">\n${body}</${tag}>\n`;
  };

  renderer.listitem = (text) => {
    return `<li style="font-family:${theme.font_family_cn};font-size:${scale.body}px;color:${theme.text_color};line-height:${rhythm.body_line_height};text-align:justify;margin:0 0 ${rhythm.list_item_margin}px;word-break:break-word;background-color:${theme.background_color};">${bgSpan(theme, processTaskListItem(text, theme))}</li>\n`;
  };

  renderer.link = (href, title, text) => {
    const titleAttr = title ? ` title="${escapeAttr(title)}"` : '';
    return `<a href="${escapeAttr(href)}"${titleAttr} style="color:${theme.accent_color};text-decoration:underline;text-underline-offset:3px;background-color:${theme.background_color};">${bgSpan(theme, text)}</a>`;
  };

  renderer.hr = () => {
    return softRule(theme, { width: '36%', maxWidth: 168, margin: `${rhythm.paragraph_margin + 10}px 0 ${rhythm.paragraph_margin + 10}px` });
  };

  renderer.table = (header, body) => {
    return `<table style="width:100%;border-collapse:collapse;margin:0 0 ${rhythm.paragraph_margin}px;background-color:${theme.background_color};">
    <thead>${header}</thead>
    <tbody>${body}</tbody>
  </table>\n`;
  };

  renderer.tablerow = (content) => {
    return `<tr>${content}</tr>\n`;
  };

  renderer.tablecell = (content, flags) => {
    const tag = flags.header ? 'th' : 'td';
    const align = flags.align ? `text-align:${flags.align};` : '';
    const weight = flags.header ? `font-weight:${theme.name === 'zhijian' ? 500 : 600};` : '';
    return `<${tag} style="border:1px solid ${theme.border_color};padding:8px 12px;${align}${weight}font-family:${theme.font_family_cn};font-size:${scale.body}px;color:${theme.text_color};background-color:${theme.background_color};">${bgSpan(theme, content)}</${tag}>`;
  };

  return renderer;
}

function createKamiDocumentRenderer(theme) {
  const renderer = createBaseRenderer(theme);
  const scale = theme.type_scale;
  const rhythm = theme.rhythm;
  const base = createHeadingBase(theme, 500);

  renderer.heading = (text, level) => {
    if (level === 1) {
      return `<h1 style="${base}font-size:${scale.h1}px;line-height:${rhythm.heading_line_height};margin:0 0 18px;padding:0;">${bgSpan(theme, text)}</h1>\n`;
    }
    if (level === 2) {
      return `<h2 style="${base}font-size:${scale.h2}px;line-height:1.25;margin:28px 0 14px;padding:0 0 0 11px;border-left:4px solid ${theme.accent_color};border-radius:2px;">${bgSpan(theme, text)}</h2>\n`;
    }
    if (level === 3) {
      return `<h3 style="${base}font-size:${scale.h3}px;font-weight:600;line-height:1.3;margin:22px 0 10px;padding:0;">${bgSpan(theme, text)}</h3>\n`;
    }
    return `<h${level} style="${base}font-size:${scale.body}px;line-height:1.35;margin:18px 0 8px;padding:0;">${bgSpan(theme, text)}</h${level}>\n`;
  };

  return renderer;
}

function createMagazineEditorialRenderer(theme) {
  const renderer = createBaseRenderer(theme);
  const scale = theme.type_scale;
  const rhythm = theme.rhythm;
  const variant = theme.magazine_variant || 'ink-classic';
  const headingBase = createHeadingBase(theme, 600);

  renderer.heading = (text, level) => {
    if (variant === 'indigo-research') {
      if (level === 1) {
        return `<h1 style="${headingBase}font-size:${scale.h1}px;line-height:${rhythm.heading_line_height};margin:0 0 18px;padding:0 0 0 12px;border-left:3px solid ${theme.accent_color};">${bgSpan(theme, text)}</h1>\n`;
      }
      if (level === 2) {
        return `<h2 style="${headingBase}font-size:${scale.h2}px;line-height:${rhythm.heading_line_height};margin:30px 0 14px;padding:0 0 0 10px;border-left:2px solid ${theme.accent_color};">${bgSpan(theme, text)}</h2>\n`;
      }
      if (level === 3) {
        return `<h3 style="font-family:${theme.ui_font};font-weight:600;color:${theme.secondary_color};letter-spacing:1px;text-transform:uppercase;word-break:break-word;background-color:${theme.background_color};font-size:${scale.caption}px;line-height:1.45;margin:22px 0 10px;padding:0;">${bgSpan(theme, text)}</h3>\n`;
      }
    }

    if (variant === 'forest-fieldnote') {
      if (level === 1) {
        return `<h1 style="${headingBase}font-size:${scale.h1}px;line-height:${rhythm.heading_line_height};margin:0 0 10px;padding:0;text-align:center;">${bgSpan(theme, text)}</h1>\n${softRule(theme, { width: '56px', maxWidth: null, margin: '0 0 18px', align: 'center' })}`;
      }
      if (level === 2) {
        return `<h2 style="${headingBase}font-size:${scale.h2}px;line-height:${rhythm.heading_line_height};margin:34px 0 14px;padding:0 0 0 10px;border-left:2px solid ${theme.divider_color};">${bgSpan(theme, text)}</h2>\n`;
      }
      if (level === 3) {
        return `<h3 style="${headingBase}font-size:${scale.h3}px;font-weight:600;line-height:1.35;margin:24px 0 10px;padding:0;color:${theme.secondary_color};">${bgSpan(theme, text)}</h3>\n`;
      }
    }

    if (variant === 'kraft-archive') {
      if (level === 1) {
        return `<h1 style="font-family:${theme.heading_font};font-weight:500;color:${theme.text_color};word-break:break-word;background-color:${theme.surface_color};font-size:${scale.h1}px;line-height:${rhythm.heading_line_height};margin:0 0 18px;padding:12px 14px;">${bgSpan(theme, text, theme.surface_color)}</h1>\n`;
      }
      if (level === 2) {
        return `<h2 style="font-family:${theme.heading_font};font-weight:500;color:${theme.text_color};word-break:break-word;background-color:${theme.surface_color};font-size:${scale.h2}px;line-height:${rhythm.heading_line_height};margin:32px 0 14px;padding:9px 12px;border-left:3px solid ${theme.accent_color};">${bgSpan(theme, text, theme.surface_color)}</h2>\n`;
      }
      if (level === 3) {
        return `<h3 style="${headingBase}font-size:${scale.h3}px;line-height:1.4;margin:24px 0 10px;padding:0 0 6px;border-bottom:1px dotted ${theme.divider_color};">${bgSpan(theme, text)}</h3>\n`;
      }
    }

    if (variant === 'dune-gallery') {
      if (level === 1) {
        return `<h1 style="font-family:${theme.heading_font};font-weight:500;color:${theme.text_color};word-break:break-word;background-color:${theme.background_color};font-size:${scale.h1}px;line-height:${rhythm.heading_line_height};margin:0 0 20px;padding:0;text-align:right;">${bgSpan(theme, text)}</h1>\n`;
      }
      if (level === 2) {
        return `${softRule(theme, { width: '64px', maxWidth: null, margin: '30px 0 12px', align: 'right', color: theme.accent_color })}<h2 style="font-family:${theme.heading_font};font-weight:500;color:${theme.text_color};word-break:break-word;background-color:${theme.background_color};font-size:${scale.h2}px;line-height:${rhythm.heading_line_height};margin:0 0 16px;padding:0;text-align:right;">${bgSpan(theme, text)}</h2>\n`;
      }
      if (level === 3) {
        return `<h3 style="font-family:${theme.ui_font};font-weight:500;color:${theme.secondary_color};word-break:break-word;background-color:${theme.background_color};font-size:${scale.h3}px;line-height:1.45;margin:24px 0 10px;padding:0;text-align:right;">${bgSpan(theme, text)}</h3>\n`;
      }
    }

    if (level === 1) {
      return `<h1 style="${headingBase}font-size:${scale.h1}px;line-height:${rhythm.heading_line_height};margin:0 0 10px;padding:0;">${bgSpan(theme, text)}</h1>\n${softRule(theme, { width: '72px', maxWidth: null, margin: '0 0 18px', align: 'left', color: theme.accent_color })}`;
    }
    if (level === 2) {
      return `<h2 style="${headingBase}font-size:${scale.h2}px;line-height:${rhythm.heading_line_height};margin:32px 0 8px;padding:0;">${bgSpan(theme, text)}</h2>\n${softRule(theme, { width: '52px', maxWidth: null, margin: '0 0 16px', align: 'left', color: theme.divider_color })}`;
    }
    if (level === 3) {
      return `<h3 style="${headingBase}font-size:${scale.h3}px;font-weight:600;line-height:1.28;margin:26px 0 10px;padding:0;color:${theme.secondary_color};">${bgSpan(theme, text)}</h3>\n`;
    }
    return `<h${level} style="${headingBase}font-size:${scale.body}px;line-height:1.35;margin:18px 0 8px;padding:0;">${bgSpan(theme, text)}</h${level}>\n`;
  };

  renderer.strong = (text) => {
    if (variant === 'indigo-research') {
      return `<strong style="color:${theme.accent_color};font-weight:650;background-color:${theme.tag_bg};padding:0 4px;border-radius:3px;">${bgSpan(theme, text, theme.tag_bg)}</strong>`;
    }
    if (variant === 'forest-fieldnote') {
      return `<strong style="color:${theme.accent_color};font-weight:600;background-color:${theme.background_color};">${bgSpan(theme, text)}</strong>`;
    }
    if (variant === 'kraft-archive') {
      return `<strong style="color:${theme.accent_color};font-weight:500;background-color:${theme.surface_color};padding:0 4px;">${bgSpan(theme, text, theme.surface_color)}</strong>`;
    }
    if (variant === 'dune-gallery') {
      return `<strong style="color:${theme.accent_color};font-weight:500;border-bottom:1px solid ${theme.divider_color};background-color:${theme.background_color};">${bgSpan(theme, text)}</strong>`;
    }
    return `<strong style="color:${theme.accent_color};font-weight:600;border-bottom:1px solid ${theme.accent_color};background-color:${theme.background_color};">${bgSpan(theme, text)}</strong>`;
  };

  renderer.codespan = (code) => {
    const escapedCode = escapeHtml(code);
    if (variant === 'indigo-research') {
      return `<code style="font-family:${theme.code_font};font-size:${scale.code}px;color:${theme.code_color};background-color:${theme.code_bg};border:1px solid ${theme.border_color};padding:2px 6px;border-radius:4px;"><span style="background-color:${theme.code_bg};">${escapedCode}</span></code>`;
    }
    if (variant === 'kraft-archive') {
      return `<code style="font-family:${theme.code_font};font-size:${scale.code}px;color:${theme.code_color};background-color:${theme.code_bg};border:1px dotted ${theme.border_color};padding:1px 5px;"><span style="background-color:${theme.code_bg};">${escapedCode}</span></code>`;
    }
    if (variant === 'dune-gallery') {
      return `<code style="font-family:${theme.code_font};font-size:${scale.code}px;color:${theme.code_color};background-color:${theme.background_color};border-bottom:1px solid ${theme.divider_color};padding:1px 2px;"><span style="background-color:${theme.background_color};">${escapedCode}</span></code>`;
    }
    return `<code style="font-family:${theme.code_font};font-size:${scale.code}px;color:${theme.code_color};background-color:${theme.code_bg};padding:2px 6px;border-radius:${variant === 'forest-fieldnote' ? '6px' : '3px'};"><span style="background-color:${theme.code_bg};">${escapedCode}</span></code>`;
  };

  renderer.blockquote = (quote) => {
    if (variant === 'indigo-research') {
      const quoteContent = toneBlockContent(quote, theme, theme.quote_bg);
      return `<section style="background-color:${theme.quote_bg};border:1px solid ${theme.border_color};padding:12px 14px;margin:0 0 ${rhythm.paragraph_margin}px;border-radius:4px;color:${theme.secondary_color};">\n${quoteContent}</section>\n`;
    }
    if (variant === 'forest-fieldnote') {
      const quoteContent = toneBlockContent(quote, theme, theme.quote_bg);
      return `<section style="background-color:${theme.quote_bg};border-left:2px solid ${theme.quote_border};padding:12px 16px;margin:0 0 ${rhythm.paragraph_margin}px;color:${theme.secondary_color};">\n${quoteContent}</section>\n`;
    }
    if (variant === 'kraft-archive') {
      const quoteContent = toneBlockContent(quote, theme, theme.surface_color);
      return `<section style="background-color:${theme.surface_color};border-left:2px solid ${theme.quote_border};padding:14px 18px;margin:0 0 ${rhythm.paragraph_margin}px;color:${theme.secondary_color};">\n${quoteContent}</section>\n`;
    }
    if (variant === 'dune-gallery') {
      const quoteContent = toneBlockContent(quote, theme, theme.background_color);
      return `<section style="background-color:${theme.background_color};padding:16px 8px;margin:0 0 ${rhythm.paragraph_margin}px;text-align:center;font-family:${theme.heading_font};font-size:${scale.body + 2}px;line-height:1.55;color:${theme.secondary_color};">\n${quoteContent}</section>\n`;
    }
    const quoteContent = toneBlockContent(quote, theme, theme.background_color);
    return `<section style="background-color:${theme.background_color};border-left:2px solid ${theme.quote_border};padding:0 0 0 16px;margin:0 0 ${rhythm.paragraph_margin}px;font-family:${theme.heading_font};font-size:${scale.body + 1}px;line-height:1.55;color:${theme.secondary_color};">\n${quoteContent}</section>\n`;
  };

  renderer.code = (code) => {
    const escapedCode = escapeHtml(code);
    if (variant === 'indigo-research') {
      return `<pre style="font-family:${theme.code_font};font-size:${scale.code}px;color:${theme.code_color};background-color:${theme.code_bg};border:1px solid ${theme.border_color};padding:13px 15px;border-radius:6px;overflow-x:auto;margin:0 0 ${rhythm.paragraph_margin}px;line-height:1.5;white-space:pre-wrap;word-break:break-word;"><code style="font-family:${theme.code_font};background-color:${theme.code_bg};color:${theme.code_color};">${escapedCode}</code></pre>\n`;
    }
    if (variant === 'forest-fieldnote') {
      return `<pre style="font-family:${theme.code_font};font-size:${scale.code}px;color:${theme.code_color};background-color:${theme.code_bg};border-left:2px solid ${theme.divider_color};padding:12px 14px;overflow-x:auto;margin:0 0 ${rhythm.paragraph_margin}px;line-height:1.5;white-space:pre-wrap;word-break:break-word;"><code style="font-family:${theme.code_font};background-color:${theme.code_bg};color:${theme.code_color};">${escapedCode}</code></pre>\n`;
    }
    if (variant === 'kraft-archive') {
      return `<pre style="font-family:${theme.code_font};font-size:${scale.code}px;color:${theme.code_color};background-color:${theme.code_bg};border:1px dotted ${theme.accent_color};padding:13px 15px;border-radius:0;overflow-x:auto;margin:0 0 ${rhythm.paragraph_margin}px;line-height:1.5;white-space:pre-wrap;word-break:break-word;"><code style="font-family:${theme.code_font};background-color:${theme.code_bg};color:${theme.code_color};">${escapedCode}</code></pre>\n`;
    }
    if (variant === 'dune-gallery') {
      return `<pre style="font-family:${theme.code_font};font-size:${scale.code}px;color:${theme.code_color};background-color:${theme.code_bg};padding:12px 14px;overflow-x:auto;margin:0 0 ${rhythm.paragraph_margin}px;line-height:1.5;white-space:pre-wrap;word-break:break-word;"><code style="font-family:${theme.code_font};background-color:${theme.code_bg};color:${theme.code_color};">${escapedCode}</code></pre>\n`;
    }
    return `<pre style="font-family:${theme.code_font};font-size:${scale.code}px;color:${theme.code_color};background-color:${theme.code_bg};padding:12px 14px;border-radius:0;overflow-x:auto;margin:0 0 ${rhythm.paragraph_margin}px;line-height:1.5;white-space:pre-wrap;word-break:break-word;"><code style="font-family:${theme.code_font};background-color:${theme.code_bg};color:${theme.code_color};">${escapedCode}</code></pre>\n`;
  };

  renderer.list = (body, ordered) => {
    const tag = ordered ? 'ol' : 'ul';
    const orderedStyle = variant === 'kraft-archive' ? 'upper-roman' : 'decimal-leading-zero';
    const listStyle = ordered ? `list-style-type:${orderedStyle};` : 'list-style-type:none;';
    const listPadding = ordered ? 'padding-left:34px;' : 'padding-left:0;';
    const markerMap = {
      'ink-classic': '— ',
      'indigo-research': '> ',
      'forest-fieldnote': '· ',
      'kraft-archive': '# ',
      'dune-gallery': '/ '
    };
    const marker = markerMap[variant] || '— ';
    const markerBg = variant === 'kraft-archive' ? theme.surface_color : theme.background_color;
    const processedBody = ordered
      ? body.replaceAll('__WECHAT_LIST_MARKER__', '')
      : body.replaceAll('__WECHAT_LIST_MARKER__', `<span style="font-family:${theme.ui_font};color:${theme.accent_color};background-color:${markerBg};">${marker}</span>`);
    return `<${tag} style="font-family:${theme.font_family_cn};font-size:${scale.body}px;color:${theme.text_color};line-height:${rhythm.body_line_height};margin:0 0 ${rhythm.paragraph_margin}px;${listPadding}${listStyle}background-color:${theme.background_color};">\n${processedBody}</${tag}>\n`;
  };

  renderer.listitem = (text) => {
    const borderStyle = variant === 'indigo-research' || variant === 'dune-gallery'
      ? `padding:0 0 ${rhythm.list_item_margin}px;`
      : variant === 'forest-fieldnote'
        ? `padding:0 0 0 12px;border-left:2px solid ${theme.divider_color};`
        : variant === 'kraft-archive'
          ? `padding:${rhythm.list_item_margin}px 10px;`
          : `padding:${rhythm.list_item_margin}px 0 0;`;
    const itemBg = variant === 'kraft-archive' ? theme.surface_color : theme.background_color;
    return `<li style="font-family:${theme.font_family_cn};font-size:${scale.body}px;color:${theme.text_color};line-height:${rhythm.body_line_height};text-align:justify;margin:0 0 ${rhythm.list_item_margin}px;${borderStyle}word-break:break-word;background-color:${itemBg};">__WECHAT_LIST_MARKER__${bgSpan(theme, processTaskListItem(text, theme), itemBg)}</li>\n`;
  };

  renderer.image = (href, title, text) => {
    const alt = text || title || '';
    if (variant === 'indigo-research') {
      return `<section style="text-align:center;margin:0 0 8px;background-color:${theme.background_color};">
    <img src="${escapeAttr(href)}" alt="${escapeAttr(alt)}" style="${imageStyle('3px')}">
</section>
<p style="font-family:${theme.ui_font};font-size:${scale.caption}px;color:${theme.tertiary_color};text-align:left;margin:0 0 ${rhythm.paragraph_margin}px;letter-spacing:1px;word-break:break-word;background-color:${theme.background_color};">${bgSpan(theme, alt)}</p>\n`;
    }
    if (variant === 'forest-fieldnote') {
      return `<section style="text-align:center;margin:0 0 8px;background-color:${theme.background_color};">
    <img src="${escapeAttr(href)}" alt="${escapeAttr(alt)}" style="${imageStyle('10px')}">
</section>
<p style="font-family:${theme.font_family_cn};font-size:${scale.caption}px;color:${theme.tertiary_color};text-align:center;margin:0 0 ${rhythm.paragraph_margin}px;word-break:break-word;background-color:${theme.background_color};">${bgSpan(theme, alt)}</p>\n`;
    }
    if (variant === 'kraft-archive') {
      return `<section style="text-align:center;margin:0 0 8px;background-color:${theme.background_color};">
    <img src="${escapeAttr(href)}" alt="${escapeAttr(alt)}" style="${imageStyle('0')}">
</section>
<p style="font-family:${theme.ui_font};font-size:${scale.caption}px;color:${theme.tertiary_color};text-align:left;margin:0 0 ${rhythm.paragraph_margin}px;word-break:break-word;background-color:${theme.background_color};">${bgSpan(theme, `ARCHIVE / ${alt}`)}</p>\n`;
    }
    if (variant === 'dune-gallery') {
      return `<section style="text-align:center;margin:0 0 8px;background-color:${theme.background_color};">
    <img src="${escapeAttr(href)}" alt="${escapeAttr(alt)}" style="${imageStyle('0')}">
</section>
<p style="font-family:${theme.ui_font};font-size:${scale.caption}px;color:${theme.tertiary_color};text-align:right;margin:0 0 ${rhythm.paragraph_margin}px;letter-spacing:1px;text-transform:uppercase;word-break:break-word;background-color:${theme.background_color};">${bgSpan(theme, alt)}</p>\n`;
    }
    return `<section style="text-align:center;margin:0 0 8px;background-color:${theme.background_color};">
    <img src="${escapeAttr(href)}" alt="${escapeAttr(alt)}" style="${imageStyle('2px')}">
</section>
<p style="font-family:${theme.ui_font};font-size:${scale.caption}px;color:${theme.tertiary_color};text-align:left;margin:0 0 ${rhythm.paragraph_margin}px;letter-spacing:1px;text-transform:uppercase;word-break:break-word;background-color:${theme.background_color};">${bgSpan(theme, alt)}</p>\n`;
  };

  return renderer;
}

function createElegantEssayRenderer(theme) {
  const renderer = createBaseRenderer(theme);
  const scale = theme.type_scale;
  const rhythm = theme.rhythm;
  const headingBase = createHeadingBase(theme, 500, theme.accent_color, 'center');

  renderer.heading = (text, level) => {
    if (level === 1) {
      return `<h1 style="${headingBase}font-size:${scale.h1}px;line-height:${rhythm.heading_line_height};margin:0 0 18px;padding:0;">${bgSpan(theme, text)}</h1>\n`;
    }
    if (level === 2) {
      return `${softRule(theme, { width: '48px', maxWidth: null, margin: '32px 0 12px', align: 'center', color: theme.divider_color })}<h2 style="${headingBase}font-size:${scale.h2}px;line-height:${rhythm.heading_line_height};margin:0 0 14px;padding:0;">${bgSpan(theme, text)}</h2>\n`;
    }
    if (level === 3) {
      return `<h3 style="${headingBase}font-size:${scale.h3}px;font-weight:600;line-height:1.35;margin:24px 0 12px;padding:0;">${bgSpan(theme, text)}</h3>\n`;
    }
    return `<h${level} style="${headingBase}font-size:${scale.body}px;line-height:1.4;margin:18px 0 8px;padding:0;">${bgSpan(theme, text)}</h${level}>\n`;
  };

  renderer.blockquote = (quote) => {
    const quoteContent = toneBlockContent(quote, theme, theme.quote_bg);
    return `<section style="background-color:${theme.quote_bg};border-left:1px solid ${theme.quote_border};padding:14px 18px;margin:0 0 ${rhythm.paragraph_margin}px;color:${theme.secondary_color};">\n${quoteContent}</section>\n`;
  };

  renderer.list = (body, ordered) => {
    const tag = ordered ? 'ol' : 'ul';
    const listStyle = ordered ? 'list-style-type:decimal;' : 'list-style-type:disc;';
    return `<${tag} style="font-family:${theme.font_family_cn};font-size:${scale.body}px;color:${theme.text_color};line-height:${rhythm.body_line_height};margin:0 0 ${rhythm.paragraph_margin}px;padding-left:30px;${listStyle}background-color:${theme.background_color};">\n${body}</${tag}>\n`;
  };

  return renderer;
}

function createModernTechnicalRenderer(theme) {
  const renderer = createBaseRenderer(theme);
  const scale = theme.type_scale;
  const rhythm = theme.rhythm;
  const headingBase = createHeadingBase(theme, 650);

  renderer.heading = (text, level) => {
    if (level === 1) {
      return `<h1 style="${headingBase}font-size:${scale.h1}px;line-height:${rhythm.heading_line_height};margin:0 0 16px;padding:0;">${bgSpan(theme, text)}</h1>\n`;
    }
    if (level === 2) {
      return `<h2 style="${headingBase}font-size:${scale.h2}px;line-height:${rhythm.heading_line_height};margin:30px 0 14px;padding:0 0 0 10px;border-left:3px solid ${theme.accent_color};">${bgSpan(theme, text)}</h2>\n`;
    }
    if (level === 3) {
      return `<h3 style="${headingBase}font-size:${scale.h3}px;font-weight:600;line-height:1.3;margin:22px 0 10px;padding:0;">${bgSpan(theme, text)}</h3>\n`;
    }
    return `<h${level} style="${headingBase}font-size:${scale.body}px;line-height:1.35;margin:18px 0 8px;padding:0;">${bgSpan(theme, text)}</h${level}>\n`;
  };

  renderer.strong = (text) => {
    return `<strong style="color:${theme.accent_color};font-weight:600;background-color:${theme.background_color};">${bgSpan(theme, text)}</strong>`;
  };

  renderer.blockquote = (quote) => {
    const quoteContent = toneBlockContent(quote, theme, theme.quote_bg);
    return `<section style="background-color:${theme.quote_bg};border:1px solid ${theme.border_color};padding:12px 14px;margin:0 0 ${rhythm.paragraph_margin}px;border-radius:8px;">\n${quoteContent}</section>\n`;
  };

  renderer.code = (code) => {
    const escapedCode = escapeHtml(code);
    return `<pre style="font-family:${theme.code_font};font-size:${scale.code}px;color:${theme.code_color};background-color:${theme.code_bg};border:1px solid ${theme.border_color};padding:14px 16px;border-radius:8px;overflow-x:auto;margin:0 0 ${rhythm.paragraph_margin}px;line-height:1.5;white-space:pre-wrap;word-break:break-word;"><code style="font-family:${theme.code_font};background-color:${theme.code_bg};color:${theme.code_color};">${escapedCode}</code></pre>\n`;
  };

  renderer.listitem = (text) => {
    return `<li style="font-family:${theme.font_family_cn};font-size:${scale.body}px;color:${theme.text_color};line-height:${rhythm.body_line_height};text-align:justify;margin:0 0 ${rhythm.list_item_margin}px;padding:0 0 ${rhythm.list_item_margin}px;word-break:break-word;background-color:${theme.background_color};">${bgSpan(theme, processTaskListItem(text, theme))}</li>\n`;
  };

  return renderer;
}

function createMinimalNotesRenderer(theme) {
  const renderer = createBaseRenderer(theme);
  const scale = theme.type_scale;
  const rhythm = theme.rhythm;
  const headingBase = createHeadingBase(theme, 500);

  renderer.heading = (text, level) => {
    if (level === 1) {
      return `<h1 style="${headingBase}font-size:${scale.h1}px;line-height:${rhythm.heading_line_height};margin:0 0 22px;padding:0;">${bgSpan(theme, text)}</h1>\n`;
    }
    if (level === 2) {
      return `<h2 style="${headingBase}font-size:${scale.h2}px;line-height:${rhythm.heading_line_height};margin:34px 0 16px;padding:0;">${bgSpan(theme, text)}</h2>\n`;
    }
    if (level === 3) {
      return `<h3 style="${headingBase}font-size:${scale.h3}px;font-weight:600;line-height:1.4;margin:26px 0 12px;padding:0;color:${theme.secondary_color};">${bgSpan(theme, text)}</h3>\n`;
    }
    return `<h${level} style="${headingBase}font-size:${scale.body}px;line-height:1.45;margin:18px 0 8px;padding:0;">${bgSpan(theme, text)}</h${level}>\n`;
  };

  renderer.strong = (text) => {
    return `<strong style="color:${theme.text_color};font-weight:600;background-color:${theme.background_color};">${bgSpan(theme, text)}</strong>`;
  };

  renderer.blockquote = (quote) => {
    const quoteContent = toneBlockContent(quote, theme, theme.background_color);
    return `<section style="background-color:${theme.background_color};border-left:1px solid ${theme.quote_border};padding:0 0 0 14px;margin:0 0 ${rhythm.paragraph_margin}px;color:${theme.secondary_color};">\n${quoteContent}</section>\n`;
  };

  renderer.list = (body, ordered) => {
    const tag = ordered ? 'ol' : 'ul';
    const listStyle = ordered ? 'list-style-type:decimal;' : 'list-style-type:none;';
    return `<${tag} style="font-family:${theme.font_family_cn};font-size:${scale.body}px;color:${theme.text_color};line-height:${rhythm.body_line_height};margin:0 0 ${rhythm.paragraph_margin}px;padding-left:${ordered ? '24px' : '0'};${listStyle}background-color:${theme.background_color};">\n${body}</${tag}>\n`;
  };

  renderer.listitem = (text) => {
    return `<li style="font-family:${theme.font_family_cn};font-size:${scale.body}px;color:${theme.text_color};line-height:${rhythm.body_line_height};text-align:justify;margin:0 0 ${rhythm.list_item_margin}px;padding-left:12px;border-left:1px solid ${theme.divider_color};word-break:break-word;background-color:${theme.background_color};">${bgSpan(theme, processTaskListItem(text, theme))}</li>\n`;
  };

  return renderer;
}

function createZhijianWarmPaperRenderer(theme) {
  const renderer = createBaseRenderer(theme);
  const scale = theme.type_scale;
  const rhythm = theme.rhythm;
  const trustBlue = theme.trust_blue || theme.accent_secondary || '#1B365D';
  const humanAccent = theme.human_accent || '#C96442';
  const primaryText = theme.primary_text || '#A04A2E';

  renderer.heading = (text, level) => {
    const headingFont = `font-family:${theme.heading_font};word-break:break-word;background-color:${theme.background_color};`;
    if (level === 1) {
      return `<h1 style="${headingFont}font-size:${scale.h1}px;font-weight:500;color:${theme.text_color};line-height:${rhythm.heading_line_height};margin:0 0 18px;padding:0;">${bgSpan(theme, text)}</h1>\n`;
    }
    if (level === 2) {
      return `<h2 style="${headingFont}font-size:${scale.h2}px;font-weight:500;color:${theme.text_color};line-height:1.28;margin:30px 0 14px;padding:0 0 0 12px;border-left:4px solid ${theme.accent_color};border-radius:2px;">${bgSpan(theme, text)}</h2>\n`;
    }
    if (level === 3) {
      return `<h3 style="${headingFont}font-size:${scale.h3}px;font-weight:500;color:${trustBlue};line-height:1.32;margin:24px 0 10px;padding:0;">${bgSpan(theme, text)}</h3>\n`;
    }
    return `<h${level} style="${headingFont}font-size:${scale.body}px;font-weight:500;color:${theme.secondary_color};line-height:1.35;margin:18px 0 8px;padding:0;">${bgSpan(theme, text)}</h${level}>\n`;
  };

  renderer.strong = (text) => {
    return `<strong style="color:${primaryText};font-weight:600;background-color:${theme.background_color};">${bgSpan(theme, text)}</strong>`;
  };

  renderer.blockquote = (quote) => {
    const quoteContent = toneBlockContent(quote, theme, theme.surface_color, theme.secondary_color);
    return `<section style="background-color:${theme.surface_color};border-left:3px solid ${humanAccent};padding:12px 16px;margin:0 0 ${rhythm.paragraph_margin}px;border-radius:0 8px 8px 0;">\n${quoteContent}</section>\n`;
  };

  renderer.code = (code) => {
    const escapedCode = escapeHtml(code);
    return `<pre style="font-family:${theme.code_font};font-size:${scale.code}px;color:${theme.code_color};background-color:${theme.code_bg};padding:16px 18px;border-radius:12px;overflow-x:auto;margin:0 0 ${rhythm.paragraph_margin}px;line-height:1.55;white-space:pre-wrap;word-break:break-word;"><code style="font-family:${theme.code_font};background-color:${theme.code_bg};color:${theme.code_color};">${escapedCode}</code></pre>\n`;
  };

  renderer.codespan = (code) => {
    const escapedCode = escapeHtml(code);
    return `<code style="font-family:${theme.code_font};font-size:${scale.code}px;color:${trustBlue};background-color:${theme.trust_bg || '#EEF2F7'};padding:2px 6px;border-radius:4px;"><span style="background-color:${theme.trust_bg || '#EEF2F7'};">${escapedCode}</span></code>`;
  };

  renderer.link = (href, title, text) => {
    const titleAttr = title ? ` title="${escapeAttr(title)}"` : '';
    return `<a href="${escapeAttr(href)}"${titleAttr} style="color:${primaryText};text-decoration:underline;text-underline-offset:3px;text-decoration-color:${theme.border_color};background-color:${theme.background_color};">${bgSpan(theme, text)}</a>`;
  };

  renderer.list = (body, ordered) => {
    const tag = ordered ? 'ol' : 'ul';
    const listStyle = ordered ? 'list-style-type:decimal;' : 'list-style-type:disc;';
    return `<${tag} style="font-family:${theme.font_family_cn};font-size:${scale.body}px;color:${theme.text_color};line-height:${rhythm.body_line_height};margin:0 0 ${rhythm.paragraph_margin}px;padding-left:24px;${listStyle}background-color:${theme.background_color};">\n${body}</${tag}>\n`;
  };

  renderer.listitem = (text) => {
    return `<li style="font-family:${theme.font_family_cn};font-size:${scale.body}px;color:${theme.text_color};line-height:${rhythm.body_line_height};text-align:justify;margin:0 0 ${rhythm.list_item_margin}px;word-break:break-word;background-color:${theme.background_color};">${bgSpan(theme, processTaskListItem(text, theme))}</li>\n`;
  };

  renderer.image = (href, title, text) => {
    const alt = text || title || '';
    return `<section style="text-align:center;margin:0 0 8px;background-color:${theme.background_color};">
    <img src="${escapeAttr(href)}" alt="${escapeAttr(alt)}" style="${imageStyle('8px')}">
</section>
<p style="font-family:${theme.ui_font};font-size:${scale.caption}px;color:${theme.tertiary_color};text-align:center;margin:0 0 ${rhythm.paragraph_margin}px;word-break:break-word;background-color:${theme.background_color};">${bgSpan(theme, alt)}</p>\n`;
  };

  renderer.hr = () => {
    return softRule(theme, { width: '48px', maxWidth: null, margin: `${rhythm.paragraph_margin + 12}px 0`, align: 'center', color: theme.accent_color });
  };

  return renderer;
}

const presetFactories = {
  'kami-document': createKamiDocumentRenderer,
  'magazine-editorial': createMagazineEditorialRenderer,
  'elegant-essay': createElegantEssayRenderer,
  'modern-technical': createModernTechnicalRenderer,
  'minimal-notes': createMinimalNotesRenderer,
  'zhijian-warm-paper': createZhijianWarmPaperRenderer
};

function configureRenderer(theme) {
  const factory = presetFactories[theme.renderer_preset];

  if (!factory) {
    console.error(`Error: Renderer preset "${theme.renderer_preset}" not found`);
    console.error(`Supported presets: ${Object.keys(presetFactories).join(', ')}`);
    process.exit(1);
  }

  return factory(theme);
}

// Generate HTML
function generateHTML(markdown, theme, frontmatter, options = {}) {
  marked.setOptions({
    renderer: configureRenderer(theme),
    breaks: true,
    gfm: true
  });

  // 预处理链:占位符 → 组件(可选)→ marked → 组件 post(可选)→ 占位符 post
  // 组件拓展层默认关闭;启用时升级组件语法为 HTML block,关闭时 fallback 成普通 markdown
  let preprocessedMarkdown = applyPlaceholdersPreMarkdown(markdown);
  if (options.components) {
    preprocessedMarkdown = applyComponentsPreMarkdown(preprocessedMarkdown, theme);
    preprocessedMarkdown = applyHighlightPreMarkdown(preprocessedMarkdown, theme);
  } else {
    preprocessedMarkdown = applyPureFallback(preprocessedMarkdown);
  }
  let content = marked.parse(preprocessedMarkdown);
  if (options.components) {
    content = applyComponentsPostMarkdown(content, theme);
  }
  content = applyPlaceholdersPostMarkdown(content, theme);

  // Split content by h2 headings to create sections
  const sections = content.split(/(?=<h2)/);

  let html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    ${frontmatter.summary ? `<meta name="description" content="${escapeAttr(frontmatter.summary)}">` : ''}
    <title>${frontmatter.title || 'WeChat Article'}</title>
</head>
<body style="margin: 0; padding: 0;">

<!-- 微信公众号复制容器：背景色使用 solid hex，并在外层、内容层、文本层重复声明，降低粘贴后丢失风险 -->
<section data-wechat-root="article" style="background-color:${theme.background_color};padding:0;margin:0;">

<!-- 顶部标签 -->
<section style="max-width:${theme.max_width}px;margin:0 auto;padding:28px 16px 12px;background-color:${theme.background_color};">
    <p style="font-family:${theme.ui_font};font-size:12px;font-weight:${theme.name === 'zhijian' ? 500 : 600};color:${theme.accent_color};letter-spacing:1px;text-transform:uppercase;margin:0 0 8px;background-color:${theme.background_color};"><span style="background-color:${theme.tag_bg};padding:2px 8px;border-radius:3px;">${theme.top_label}</span></p>
    ${softRule(theme, { width: '56px', maxWidth: null, margin: '10px 0 0', align: 'left' })}
</section>

`;

  // Add sections
  sections.forEach((section, index) => {
    if (!section.trim()) return;

    // 第一个 section:如果启用了 --cover,在内容前插入开场动画
    let coverSvg = '';
    if (index === 0 && options.cover) {
      const coverOpts = {
        template: options.coverTemplate || 'ink-wash',
        title: options.coverTitle || frontmatter.title || '',
        subtitle: options.coverSubtitle || frontmatter.summary || '',
        tags: options.coverTags || '',
      };
      const svg = generateCoverAnimation(theme, coverOpts);
      coverSvg = `\n<!-- 开场 SVG 动画 (${coverOpts.template}) -->\n<section style="margin:0;padding:0;line-height:0;">${svg}</section>\n`;
    }

    html += `<!-- 章节 ${index + 1} -->
<section style="max-width:${theme.max_width}px;margin:0 auto;padding:${index === 0 ? theme.rhythm.section_padding_first : theme.rhythm.section_padding}px 16px;background-color:${theme.background_color};">
<section style="background-color:${theme.background_color};padding:0;margin:0;">
${coverSvg}
${section}
</section>
</section>

`;

    // Section rhythm is handled by padding and theme-specific headings, not automatic full-width rules.
  });

  html += `</section>
<!-- 整体背景容器结束 -->

</body>
</html>`;

  return html;
}

// Convert single file
function convertFile(inputPath, theme, options) {
  if (!fs.existsSync(inputPath)) {
    console.error(`Error: Input file not found: ${inputPath}`);
    return false;
  }

  const content = fs.readFileSync(inputPath, 'utf8');
  const { frontmatter, markdown } = parseMarkdown(content);

  // Generate HTML
  const html = generateHTML(markdown, theme, frontmatter, options);

  // Determine output path
  const outputPath = options.output || inputPath.replace(/\.md$/, '_wechat.html');

  // Write output
  fs.writeFileSync(outputPath, html, 'utf8');

  console.log(`✓ Generated: ${outputPath}`);

  // 软门校验:文件照常生成,但打印兼容性报告(ERROR 不阻断,用户能先看效果)
  const report = validateHtml(html);
  console.log(formatReport(report));

  return outputPath;
}

// Main function
async function main() {
  const options = parseArgs();

  console.log(`Theme: ${options.theme}`);

  // Load theme
  const theme = loadTheme(options.theme);

  // Apply custom parameters
  if (options.fontSize) {
    theme.font_size = options.fontSize;
    theme.type_scale.body = options.fontSize;
  }
  if (options.lineHeight) {
    theme.line_height = options.lineHeight;
    theme.rhythm.body_line_height = options.lineHeight;
  }
  if (options.accentColor) theme.accent_color = options.accentColor;
  if (options.backgroundColor) theme.background_color = options.backgroundColor;
  if (options.maxWidth) theme.max_width = options.maxWidth;

  // Check if input contains glob pattern
  if (options.input.includes('*')) {
    console.log(`Converting: ${options.input} (glob pattern)`);

    // Find matching files
    const files = await glob(options.input, { nodir: true });

    if (files.length === 0) {
      console.error(`Error: No files matched pattern: ${options.input}`);
      process.exit(1);
    }

    console.log(`Found ${files.length} file(s)\n`);

    // Convert each file
    const results = [];
    for (const file of files) {
      const inputPath = path.resolve(file);
      console.log(`Converting: ${file}`);
      const outputPath = convertFile(inputPath, theme, { ...options, output: null });
      if (outputPath) results.push(outputPath);
    }

    console.log(`\n✓ Converted ${results.length} file(s)`);
    console.log(`\nUsage:`);
    console.log(`1. Open any HTML file in browser`);
    console.log(`2. Select all (Cmd+A)`);
    console.log(`3. Copy (Cmd+C)`);
    console.log(`4. Paste into WeChat Official Account editor`);
  } else {
    // Single file conversion
    console.log(`Converting: ${options.input}`);
    const inputPath = path.resolve(options.input);
    const outputPath = convertFile(inputPath, theme, options);

    if (outputPath) {
      console.log(`\nUsage:`);
      console.log(`1. Open the HTML file in browser`);
      console.log(`2. Select all (Cmd+A)`);
      console.log(`3. Copy (Cmd+C)`);
      console.log(`4. Paste into WeChat Official Account editor`);

      // Auto-open in default browser (single file only)
      execFile('open', [outputPath], (err) => {
        if (err) console.error(`Warning: Could not auto-open browser: ${err.message}`);
      });
    }
  }
}

main();

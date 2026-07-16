#!/usr/bin/env node

/**
 * WeChat Styler - 公众号 HTML 兼容性校验器
 *
 * 扫描 convert.mjs 产物,检查禁用标签、属性、CSS、函数和外部字体。
 * 所有规则由本脚本确定性执行,不依赖模型自觉。
 *
 * 用法:
 *   node validate.mjs <output.html>           # 独立校验(exit 1 = 有 ERROR)
 *   import { validateHtml } from './validate.mjs'  # convert.mjs 软门调用
 */

import fs from 'fs';
import path from 'path';

// 校验规则定义(顺序即输出顺序)
// 每条规则:name / level(ERROR|WARN) / test(返回匹配描述或 null)
const rules = [
  // ───────────────────────── ERROR 级:禁用标签 ─────────────────────────
  {
    name: '禁用标签 <style>',
    level: 'ERROR',
    test: (line) => /<style[\s>]/i.test(line) ? '公众号会剥离 <style>,样式必须全部内联' : null
  },
  {
    name: '禁用标签 <script>',
    level: 'ERROR',
    test: (line) => /<script[\s>]/i.test(line) ? '公众号会剥离 <script>,脚本无法执行' : null
  },
  {
    name: '禁用标签 <link>',
    level: 'ERROR',
    test: (line) => /<link[\s>]/i.test(line) ? '公众号会剥离 <link>,外部资源无法加载' : null
  },
  {
    name: '禁用标签 <iframe>',
    level: 'ERROR',
    test: (line) => /<iframe[\s>]/i.test(line) ? '公众号禁用 <iframe>' : null
  },
  {
    name: '禁用标签 <input>',
    level: 'ERROR',
    test: (line) => /<input[\s>]/i.test(line) ? '公众号禁用 <input>' : null
  },
  {
    name: 'body 内 <meta>',
    level: 'ERROR',
    test: (line, ctx) => {
      // 只校验 body 内的 meta(head 里的 meta 允许)
      if (ctx.inHead) return null;
      return /<meta[\s>]/i.test(line) ? 'body 内 <meta> 会被公众号剥离' : null;
    }
  },

  // ───────────────────────── ERROR 级:禁用属性 ─────────────────────────
  {
    name: '禁用属性 class=',
    level: 'ERROR',
    test: (line) => /\sclass\s*=/i.test(line) ? '公众号会剥离 class 属性,样式必须内联' : null
  },
  {
    name: '禁用属性 id=',
    level: 'ERROR',
    test: (line, ctx) => {
      // 锚点 href="#xxx" 的目标 id 允许保留(但公众号通常也不支持)
      // 这里只警告真正的 id= 属性
      if (/\sid\s*=/i.test(line) && !/name\s*=/i.test(line)) {
        return '公众号会剥离 id 属性';
      }
      return null;
    }
  },
  {
    name: '禁用属性 contenteditable',
    level: 'ERROR',
    test: (line) => /contenteditable/i.test(line) ? '公众号禁用 contenteditable' : null
  },

  // ───────────────────────── ERROR 级:禁用 CSS ─────────────────────────
  {
    name: '禁用 CSS position',
    level: 'ERROR',
    test: (line) => /position\s*:\s*(fixed|absolute)/i.test(line)
      ? 'position:fixed|absolute 粘贴后错位,改用文档流布局'
      : null
  },
  {
    name: '禁用 CSS display:grid',
    level: 'ERROR',
    test: (line) => /display\s*:\s*grid/i.test(line)
      ? '公众号不支持 display:grid,改用 section 嵌套或 table'
      : null
  },
  {
    name: 'display:flex 兼容性提示',
    level: 'WARN',
    test: (line) => /display\s*:\s*flex/i.test(line)
      ? 'display:flex 在公众号兼容性视客户端而定,建议粘贴后实测'
      : null
  },
  {
    name: '禁用 @media',
    level: 'ERROR',
    test: (line) => /@media/i.test(line) ? '公众号会剥离 @media 媒体查询' : null
  },
  {
    name: '禁用 @keyframes',
    level: 'ERROR',
    test: (line) => /@keyframes/i.test(line) ? '公众号会剥离 @keyframes 动画' : null
  },

  // ───────────────────────── ERROR 级:禁用函数 ─────────────────────────
  {
    name: '禁用 rgba()/hsla()',
    level: 'ERROR',
    test: (line) => /(rgba|hsla)\s*\(/i.test(line)
      ? 'rgba()/hsla() 背景色在编辑器中丢失,必须用 solid hex(如 #1B365D)'
      : null
  },

  // ───────────────────────── ERROR 级:外部字体 ─────────────────────────
  {
    name: '禁用外部字体 @font-face',
    level: 'ERROR',
    test: (line) => /@font-face/i.test(line) && /url\s*\(/i.test(line)
      ? '外部字体加载会降级,版式走样;用系统字体栈'
      : null
  },

  // ───────────────────────── WARN 级:图片 ─────────────────────────
  {
    name: '图片无 alt',
    level: 'WARN',
    test: (line) => {
      const imgMatch = line.match(/<img\s+([^>]*)>/i);
      if (!imgMatch) return null;
      const attrs = imgMatch[1];
      if (!/alt\s*=/i.test(attrs)) return '<img> 缺 alt 属性(无障碍 + 图床失效时的兜底)';
      return null;
    }
  },
  {
    name: '图片偏移风险',
    level: 'WARN',
    test: (line) => {
      const imgMatch = line.match(/<img\s+([^>]*)>/i);
      if (!imgMatch) return null;
      const styleMatch = imgMatch[1].match(/style\s*=\s*"([^"]*)"/i);
      if (!styleMatch) return '<img> 缺 style(粘贴后可能偏左)';
      const style = styleMatch[1];
      const hasMarginAuto = /margin\s*:\s*[^;]*auto/i.test(style);
      const hasDisplayBlock = /display\s*:\s*block/i.test(style);
      if (!hasMarginAuto && !hasDisplayBlock) {
        return '<img> 缺 margin:0 auto 或 display:block(粘贴后可能偏左)';
      }
      return null;
    }
  },
  {
    name: '块级元素缺 style',
    level: 'WARN',
    test: (line) => {
      // 检查 section/p/h2/blockquote 是否缺 style 属性
      const blockMatch = line.match(/^[\s]*<(section|p|h[1-6]|blockquote)(\s+[^>]*)?>/i);
      if (!blockMatch) return null;
      const attrs = blockMatch[2] || '';
      // 允许容器型 section(如注释后的外层)不强制 style,但 p/h2/blockquote 必须
      const tag = blockMatch[1].toLowerCase();
      if (tag === 'section') return null; // section 嵌套复杂,放宽
      if (!/style\s*=/i.test(attrs)) {
        return `<${tag}> 缺 style(粘贴后样式丢失)`;
      }
      return null;
    }
  }
];

/**
 * 校验 HTML 字符串
 * @param {string} html - 产物 HTML
 * @returns {{errors: Array, warnings: Array, passed: boolean}}
 *   - errors/warnings: [{line, name, message}]
 *   - passed: errors.length === 0
 */
export function validateHtml(html) {
  const errors = [];
  const warnings = [];
  const lines = html.split('\n');
  let inHead = false;

  lines.forEach((rawLine, idx) => {
    // 追踪 head 区域(body 内的 meta 才报错)
    if (/<head[\s>]/i.test(rawLine)) inHead = true;
    if (/<\/head>/i.test(rawLine)) inHead = false;

    // 内容剥离:把 <code>...</code>、<pre>...</pre>、<svg>...</svg> 内的文本替换成占位符。
    // code/pre:避免文章正文讨论禁用项时误报(比如文章在讲 rgba() 为什么禁用)。
    // svg:SVG 动画标签(<animate>/<animateTransform>)和属性(viewBox/preserveAspectRatio)
    //      在微信中可用(通过 opencli DOM 注入),不应被规则误报。
    const line = rawLine
      .replace(/<code[^>]*>[\s\S]*?<\/code>/gi, '<code></code>')
      .replace(/<pre[^>]*>[\s\S]*?<\/pre>/gi, '<pre></pre>')
      .replace(/<svg[^>]*>[\s\S]*?<\/svg>/gi, '<svg></svg>');

    const ctx = { inHead };
    const lineNum = idx + 1;

    for (const rule of rules) {
      const message = rule.test(line, ctx);
      if (message) {
        const finding = { line: lineNum, name: rule.name, message };
        if (rule.level === 'ERROR') errors.push(finding);
        else warnings.push(finding);
      }
    }
  });

  return {
    errors,
    warnings,
    passed: errors.length === 0
  };
}

/**
 * 格式化校验报告(终端彩色输出)
 */
export function formatReport(report) {
  const { errors, warnings, passed } = report;
  const RED = '\x1b[31m';
  const YELLOW = '\x1b[33m';
  const GREEN = '\x1b[32m';
  const RESET = '\x1b[0m';
  const DIM = '\x1b[2m';

  if (passed && warnings.length === 0) {
    return `${GREEN}✓ 公众号兼容校验通过${RESET}`;
  }

  let out = '';
  if (!passed) {
    out += `${RED}✗ WeChat HTML 校验失败:${errors.length} ERROR, ${warnings.length} WARN${RESET}\n\n`;
    out += `${RED}ERROR:${RESET}\n`;
    for (const e of errors) {
      out += `  ${RED}L${e.line}${RESET}  ${e.message} ${DIM}(${e.name})${RESET}\n`;
    }
    if (warnings.length > 0) out += '\n';
  } else {
    out += `${YELLOW}⚠ 校验通过,但有 ${warnings.length} 条 WARN:${RESET}\n\n`;
  }

  if (warnings.length > 0) {
    out += `${YELLOW}WARN:${RESET}\n`;
    for (const w of warnings) {
      out += `  ${YELLOW}L${w.line}${RESET}  ${w.message} ${DIM}(${w.name})${RESET}\n`;
    }
  }

  out += `\n${DIM}参考:SKILL.md「公众号兼容硬规则」段落${RESET}`;
  return out;
}

// ───────────────────────── CLI 入口 ─────────────────────────
function parseArgs() {
  const args = process.argv.slice(2);
  if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
    console.error('Usage: node validate.mjs <output.html>');
    console.error('  0 ERROR → exit 0    有 ERROR → exit 1');
    process.exit(args.length === 0 ? 1 : 0);
  }
  return args[0];
}

function main() {
  const inputPath = path.resolve(parseArgs());

  if (!fs.existsSync(inputPath)) {
    console.error(`Error: File not found: ${inputPath}`);
    process.exit(1);
  }

  const html = fs.readFileSync(inputPath, 'utf8');
  const report = validateHtml(html);
  console.log(formatReport(report));

  if (!report.passed) {
    process.exit(1);
  }
}

// 只在直接运行时走 CLI(convert.mjs import 时不触发)
const isDirectRun = process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname);
if (isDirectRun) {
  main();
}

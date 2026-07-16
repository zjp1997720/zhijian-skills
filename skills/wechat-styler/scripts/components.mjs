/**
 * WeChat Styler - 组件拓展层 (Components Layer)
 *
 * 6 个结构化组件,用排印手段 + section/flex 布局呈现,不用 table(公众号灰边)、
 * 不引入新色块。所有颜色/字体从 theme 参数取,各主题自动适配。
 *
 * 两种模式:
 *   - applyComponentsPreMarkdown / applyComponentsPostMarkdown  →  组件模式(--components)
 *   - applyPureFallback                                          →  默认模式(组件语法降级成普通 markdown)
 *
 * 组件语法:
 *   > **xxx**              → 金句块(居中 + 楷体大字 + 上下留白)
 *   > [!NOTE] xxx          → 提示块(墨蓝/主题结构色前缀)
 *   > [!WARNING] xxx       → 警告块(暖陶/主题强调色前缀)
 *   1. [step] xxx          → 步骤序号(圆形/方形序号 + 加粗数字)
 *   :::flow A → B → C :::  → 流程卡片(section + flex 横排 + 箭头)
 *   :::compare tag|title|desc :::  → 对比卡片(section + flex 多栏)
 *   :::timeline date|title|desc ::: → 时间线(竖向圆点 + 竖线)
 */

// ═══════════════════════ 组件 HTML 构建函数 ═══════════════════════
// 所有函数接收 theme 参数,颜色/字体从 theme 取,不写死

/**
 * 金句块:居中 + 楷体(标题字体)+ 大字号 + 上下大留白
 * 无色块、无边框,纯靠排印抬视觉权重
 */
function buildKeyquote(text, theme, subText) {
  const headingFont = theme.heading_font || theme.font_family_cn;
  const bodyFont = theme.font_family_cn;
  const bg = theme.background_color;
  const text_color = theme.text_color;
  const caption_color = theme.tertiary_color || theme.secondary_color || text_color;
  const main = `<p style="font-family:${headingFont};font-size:21px;font-weight:500;color:${text_color};line-height:1.6;letter-spacing:0.04em;margin:0 0 ${subText ? '8px' : '0'};background-color:${bg};">${text}</p>`;
  const sub = subText ? `<p style="font-family:${bodyFont};font-size:14px;color:${caption_color};line-height:1.6;margin:0;background-color:${bg};">${subText}</p>` : '';
  return `<section style="text-align:center;margin:36px 0;background-color:${bg};">${main}${sub}</section>`;
}

/**
 * 提示块:结构色(墨蓝/次要色)前缀 + 同行正文
 * 关键修复:补 font-family,跟正文一致(之前漏写导致继承浏览器默认无衬线)
 */
function buildNote(text, theme) {
  const bodyFont = theme.font_family_cn;
  const uiFont = theme.ui_font || theme.font_family_cn;
  const bg = theme.background_color;
  const text_color = theme.text_color;
  // NOTE 用结构色(accent_secondary 或 secondary_color),不抢行动色
  const color = theme.accent_secondary || theme.secondary_color || theme.text_color;
  return `<section style="margin:0 0 20px;background-color:${bg};"><p style="font-family:${bodyFont};font-size:16px;color:${text_color};line-height:1.75;margin:0;background-color:${bg};"><span style="font-family:${uiFont};font-size:12px;color:${color};letter-spacing:1.5px;font-weight:600;margin-right:10px;background-color:${bg};">提示</span>${text}</p></section>`;
}

/**
 * 警告块:强调色(暖陶/主色)前缀 + 同行正文
 */
function buildWarning(text, theme) {
  const bodyFont = theme.font_family_cn;
  const uiFont = theme.ui_font || theme.font_family_cn;
  const bg = theme.background_color;
  const text_color = theme.text_color;
  // WARNING 用行动色(accent_color)
  const color = theme.accent_color;
  return `<section style="margin:0 0 20px;background-color:${bg};"><p style="font-family:${bodyFont};font-size:16px;color:${text_color};line-height:1.75;margin:0;background-color:${bg};"><span style="font-family:${uiFont};font-size:12px;color:${color};letter-spacing:1.5px;font-weight:600;margin-right:10px;background-color:${bg};">注意</span>${text}</p></section>`;
}

/**
 * 轻量正文标记:底部 1px 暖陶色细线
 * 像讲义边上的铅笔标记,文字保持正文色不变,比加粗醒目,比金句块轻
 * 语法: ==关键词==  在 pre-markdown 阶段替换成内联 HTML span
 */
function buildHighlight(text, theme) {
  const accent = theme.accent_color;
  const bg = theme.background_color;
  return `<span style="border-bottom:1px solid ${accent};padding-bottom:1px;background-color:${bg};">${text}</span>`;
}

/**
 * 轻量标记 pre-markdown 处理:==关键词== → 内联 HTML span
 * 在 applyComponentsPreMarkdown 和 applyPureFallback 之前调用
 */
export function applyHighlightPreMarkdown(md, theme) {
  // ==标记== → 底部细线 span。允许内容中包含单个 = 号（如"六要素 = 心跳"）
  // 排除 === 标题语法：要求 == 前面不是 =，== 后面第一个字符不是 =
  return md.replace(/(?<!=)==([^\n=][^\n]*?)==/g, (_, text) => {
    if (text.endsWith('=')) return `==${text}==`;
    return buildHighlight(text.trim(), theme);
  });
}

/**
 * 步骤序号块:加粗数字 01/02/03 + 正文
 * 不是有序列表,是独立步骤块,每步之间有留白
 */
function buildStepsBlock(steps, theme) {
  const bodyFont = theme.font_family_cn;
  const uiFont = theme.ui_font || theme.font_family_cn;
  const bg = theme.background_color;
  const text_color = theme.text_color;
  const accent = theme.accent_color;
  const items = steps.map(s =>
    `<p style="font-family:${bodyFont};font-size:16px;color:${text_color};line-height:1.8;margin:0 0 16px;background-color:${bg};"><span style="font-family:${uiFont};font-weight:600;color:${accent};font-size:15px;margin-right:12px;background-color:${bg};">${String(s.num).padStart(2, '0')}</span>${s.text}</p>`
  ).join('');
  return `<section style="margin:0 0 24px;background-color:${bg};">${items}</section>`;
}

/**
 * 流程卡片:section + display:flex 横排 + 箭头连接
 * 不用 table(公众号会强制灰边)
 */
function buildFlowCards(steps, theme) {
  const bodyFont = theme.font_family_cn;
  const uiFont = theme.ui_font || theme.font_family_cn;
  const bg = theme.background_color;
  const surface = theme.surface_color || bg;
  const text_color = theme.text_color;
  const divider = theme.divider_color || '#D8D5C8';
  const labelColor = theme.accent_secondary || theme.secondary_color || text_color;
  const arrowColor = theme.accent_color;
  // ≤4 步：flex:1 等分不滚动；≥5 步：加 overflow 横向滚动
  const useScroll = steps.length >= 5;
  const flexStyle = useScroll ? 'flex:0 0 120px;min-width:120px;' : 'flex:1;min-width:0;';
  const cells = [];
  steps.forEach((s, i) => {
    cells.push(`<section style="${flexStyle}text-align:center;padding:10px 6px;background-color:${surface};border:1px solid ${divider};border-radius:6px;box-sizing:border-box;"><p style="font-family:${uiFont};font-size:11px;font-weight:600;color:${labelColor};letter-spacing:1px;margin:0 0 5px;background-color:${surface};">STEP ${String(i + 1).padStart(2, '0')}</p><p style="font-family:${bodyFont};font-size:12px;color:${text_color};line-height:1.4;margin:0;background-color:${surface};">${s}</p></section>`);
    if (i < steps.length - 1) {
      cells.push(`<section style="flex:0 0 auto;display:flex;align-items:center;justify-content:center;color:${arrowColor};font-size:16px;line-height:1;padding:0 3px;background-color:${bg};"><span style="font-size:16px;line-height:1;color:${arrowColor};background-color:${bg};">→</span></section>`);
    }
  });
  const inner = `<section style="display:flex;align-items:stretch;${useScroll ? 'min-width:max-content;' : ''}">${cells.join('')}</section>`;
  if (useScroll) {
    return `<section style="overflow-x:auto;-webkit-overflow-scrolling:touch;background-color:${bg};margin:0 0 12px;padding-bottom:4px;">${inner}</section>`;
  }
  return `<section style="background-color:${bg};margin:0 0 12px;">${inner}</section>`;
}

/**
 * 对比卡片:section + display:flex 多栏
 * highlight 项用强调色描边,其他用分隔色描边
 */
function buildCompareCards(cards, theme) {
  const headingFont = theme.heading_font || theme.font_family_cn;
  const bodyFont = theme.font_family_cn;
  const uiFont = theme.ui_font || theme.font_family_cn;
  const bg = theme.background_color;
  const surface = theme.surface_color || bg;
  const text_color = theme.text_color;
  const caption_color = theme.tertiary_color || theme.secondary_color || text_color;
  const divider = theme.divider_color || '#D8D5C8';
  const accent = theme.accent_color;
  // ≤3 个卡片：flex:1 等分不滚动，内容自动换行（参考 gzh-design）
  // ≥4 个卡片：加 overflow 横向滚动
  const useScroll = cards.length >= 4;
  const flexStyle = useScroll ? 'flex:0 0 170px;min-width:170px;' : 'flex:1;min-width:0;';
  const cells = [];
  cards.forEach((card, i) => {
    const border = card.highlight ? `2px solid ${accent}` : `1px solid ${divider}`;
    const cardBg = card.highlight ? bg : surface;
    const tagColor = card.highlight ? accent : caption_color;
    const isLast = i === cards.length - 1;
    cells.push(`<section style="${flexStyle}text-align:center;padding:10px 8px;border:${border};border-radius:6px;background-color:${cardBg};${isLast ? '' : 'margin-right:6px;'}box-sizing:border-box;"><p style="font-family:${uiFont};font-size:10px;font-weight:600;color:${tagColor};letter-spacing:1px;margin:0 0 6px;background-color:${cardBg};">${card.tag}</p><p style="font-family:${headingFont};font-size:13px;font-weight:500;color:${text_color};margin:0 0 6px;background-color:${cardBg};">${card.title}</p><p style="font-family:${bodyFont};font-size:11px;color:${caption_color};line-height:1.5;margin:0;background-color:${cardBg};">${card.desc}</p></section>`);
  });
  const inner = `<section style="display:flex;align-items:stretch;${useScroll ? 'min-width:max-content;' : ''}">${cells.join('')}</section>`;
  if (useScroll) {
    return `<section style="overflow-x:auto;-webkit-overflow-scrolling:touch;background-color:${bg};margin:0 0 12px;padding-bottom:4px;">${inner}</section>`;
  }
  return `<section style="background-color:${bg};margin:0 0 12px;">${inner}</section>`;
}

/**
 * 时间线:每条用 flex 两列(左圆点+竖线,右内容)
 */
function buildTimeline(entries, theme) {
  const bodyFont = theme.font_family_cn;
  const uiFont = theme.ui_font || theme.font_family_cn;
  const bg = theme.background_color;
  const text_color = theme.text_color;
  const caption_color = theme.tertiary_color || theme.secondary_color || text_color;
  const divider = theme.divider_color || '#D8D5C8';
  const accent = theme.accent_color;
  const rows = entries.map((e, i) => {
    const isLast = i === entries.length - 1;
    const line = isLast ? '' : `<section style="width:1px;background-color:${divider};margin:6px auto 0;height:48px;"><span style="font-size:0;line-height:0;overflow:hidden;background-color:${divider};">&nbsp;</span></section>`;
    return `<section style="display:flex;align-items:flex-start;background-color:${bg};margin:0 0 ${isLast ? '0' : '4px'};"><section style="width:28px;flex-shrink:0;display:flex;flex-direction:column;align-items:center;background-color:${bg};"><section style="width:10px;height:10px;border-radius:50%;background-color:${accent};margin-top:6px;"><span style="font-size:0;line-height:0;overflow:hidden;background-color:${accent};">&nbsp;</span></section>${line}</section><section style="flex:1;padding:0 0 0 8px;background-color:${bg};"><p style="font-family:${uiFont};font-size:11px;font-weight:600;color:${caption_color};letter-spacing:1px;margin:0 0 4px;background-color:${bg};">${e.date}</p><p style="font-family:${bodyFont};font-size:15px;font-weight:500;color:${text_color};margin:0 0 4px;background-color:${bg};">${e.title}</p><p style="font-family:${bodyFont};font-size:14px;color:${caption_color};line-height:1.6;margin:0 0 ${isLast ? '0' : '16px'};background-color:${bg};">${e.desc}</p></section></section>`;
  }).join('');
  return `<section style="background-color:${bg};margin:0 0 16px;">${rows}</section>`;
}

// ═══════════════════════ 默认模式:fallback 成普通 markdown ═══════════════════════

/**
 * 默认模式预处理:把组件语法降级成普通 markdown 元素
 * 用户不传 --components 时调用,保证组件语法不暴露成乱码
 */
export function applyPureFallback(md) {
  // :::flow A → B → C ::: → 有序列表
  md = md.replace(/^:::flow\s*\n([\s\S]*?)\n:::\s*$/gm, (_, body) => {
    const text = body.trim();
    let steps;
    if (text.includes('→') && !text.includes('\n')) {
      steps = text.split('→').map(s => s.trim()).filter(Boolean);
    } else {
      steps = text.split('\n').filter(Boolean).map(l => l.replace(/^→\s*/, '').trim());
    }
    const list = steps.map((s, i) => `${i + 1}. ${s}`).join('\n');
    return `\n${list}\n`;
  });
  // :::compare → 无序列表
  md = md.replace(/^:::compare\s*\n([\s\S]*?)\n:::\s*$/gm, (_, body) => {
    const list = body.trim().split('\n').filter(Boolean).map(row => {
      const parts = row.split('|').map(s => s.trim().replace(/\*/g, ''));
      return `- **${parts[0]}**: ${parts[1] || ''} — ${parts[2] || ''}`;
    }).join('\n');
    return `\n${list}\n`;
  });
  // :::timeline → 无序列表
  md = md.replace(/^:::timeline\s*\n([\s\S]*?)\n:::\s*$/gm, (_, body) => {
    const list = body.trim().split('\n').filter(Boolean).map(row => {
      const parts = row.split('|').map(s => s.trim());
      return `- **${parts[0]}** ${parts[1] || ''}: ${parts[2] || ''}`;
    }).join('\n');
    return `\n${list}\n`;
  });
  // > [!NOTE] / > [!WARNING](单行或多行)→ 去掉标签前缀,保留引用
  md = md.replace(/^> \[!(NOTE|WARNING)\][ \t]*/gm, '> ');
  // 1. [step] xxx → 1. xxx
  md = md.replace(/^(\d+\.) \[step\][ \t]*/gm, '$1 ');
  // ==关键词== → **关键词**（默认模式降级成加粗，允许内容含单个 = 号）
  md = md.replace(/(?<!=)==([^\n=][^\n]*?)==/g, (_, text) => {
    if (text.endsWith('=')) return `==${text}==`;
    return `**${text}**`;
  });
  return md;
}

// ═══════════════════════ 组件模式:升级成 HTML block ═══════════════════════

/**
 * 组件模式预处理:把组件语法替换成 HTML block(marked 原样保留)
 * 关键:HTML block 前后必须有空行包裹,否则 marked 会重新解析
 */
export function applyComponentsPreMarkdown(md, theme) {
  const wrap = (html) => `\n\n${html}\n\n`;

  // 金句块: > **xxx** 或 > **xxx。** 同行后续文字
  // 注意:用 [ \t]* 不用 \s*(\s 会跨行吃掉下一个标题)
  md = md.replace(/^> \*\*([^*\n]+)\*\*[ \t]*([^\n]*)$/gm, (_, mainText, rest) => {
    const sub = rest.trim();
    return sub ? wrap(buildKeyquote(mainText.trim(), theme, sub)) : wrap(buildKeyquote(mainText.trim(), theme));
  });
  // NOTE 块(单行或多行)
  md = md.replace(/^> \[!NOTE\][ \t]*([^\n]*)\n?((?:> .+\n?)+)?/gm, (match, inline, body) => {
    const parts = [inline.trim()];
    if (body) parts.push(body.replace(/^> ?/gm, '').trim());
    const text = parts.filter(Boolean).join(' ');
    return text ? wrap(buildNote(text, theme)) : match;
  });
  // WARNING 块(单行或多行)
  md = md.replace(/^> \[!WARNING\][ \t]*([^\n]*)\n?((?:> .+\n?)+)?/gm, (match, inline, body) => {
    const parts = [inline.trim()];
    if (body) parts.push(body.replace(/^> ?/gm, '').trim());
    const text = parts.filter(Boolean).join(' ');
    return text ? wrap(buildWarning(text, theme)) : match;
  });
  // 流程卡片:支持「单行 A → B → C」和「多行每行一步」
  md = md.replace(/^:::flow\s*\n([\s\S]*?)\n:::\s*$/gm, (_, body) => {
    const text = body.trim();
    let steps;
    if (text.includes('→') && !text.includes('\n')) {
      steps = text.split('→').map(s => s.trim()).filter(Boolean);
    } else {
      steps = text.split('\n').filter(Boolean).map(l => l.replace(/^→\s*/, '').trim());
    }
    return wrap(buildFlowCards(steps, theme));
  });
  // 对比卡片
  md = md.replace(/^:::compare\s*\n([\s\S]*?)\n:::\s*$/gm, (_, body) => {
    const cards = body.trim().split('\n').filter(Boolean).map(row => {
      const parts = row.split('|').map(s => s.trim());
      return { tag: parts[0].replace(/\*/g, ''), title: parts[1] || '', desc: parts[2] || '', highlight: parts[0].includes('**') };
    });
    return wrap(buildCompareCards(cards, theme));
  });
  // 时间线
  md = md.replace(/^:::timeline\s*\n([\s\S]*?)\n:::\s*$/gm, (_, body) => {
    const entries = body.trim().split('\n').filter(Boolean).map(row => {
      const parts = row.split('|').map(s => s.trim());
      return { date: parts[0] || '', title: parts[1] || '', desc: parts[2] || '' };
    });
    return wrap(buildTimeline(entries, theme));
  });
  // [step] 标记保留,post-marked 阶段处理
  return md;
}

/**
 * 组件模式 post-marked:处理 [step] 步骤(需在 marked 产出 <ol><li> 后替换)
 */
export function applyComponentsPostMarkdown(html, theme) {
  return html.replace(/<ol[^>]*>([\s\S]*?)<\/ol>/g, (match, inner) => {
    if (!inner.includes('[step]')) return match;
    const steps = [];
    const re = /<li[^>]*>([\s\S]*?)<\/li>/g;
    let m;
    while ((m = re.exec(inner)) !== null) {
      let text = m[1]
        .replace(/<span[^>]*>\s*\[step\]\s*/g, '')
        .replace(/\[step\]\s*/g, '')
        .replace(/<\/span>/g, '')
        .replace(/<[^>]+>/g, '')
        .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&')
        .trim();
      steps.push({ num: steps.length + 1, text });
    }
    return buildStepsBlock(steps, theme);
  });
}

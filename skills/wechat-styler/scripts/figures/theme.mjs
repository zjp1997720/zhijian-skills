// 主题 YAML → 图解色板。颜色只读不改：过不了对比度由 gates 报错，这里不补救。
const mix = (a, b, t) => `#${[1, 3, 5].map((i) => {
  const [x, y] = [a, b].map((hex) => parseInt(hex.slice(i, i + 2), 16));
  return Math.round(x * (1 - t) + y * t).toString(16).padStart(2, '0');
}).join('')}`;

export function themeTokens(theme) {
  const node = theme.surface_color || theme.background_color;
  return {
    name: theme.name,
    bg: theme.background_color,
    node,
    rule: theme.divider_color,
    text: theme.text_color,
    muted: theme.secondary_color,
    faint: theme.tertiary_color || theme.secondary_color,
    struct: theme.accent_secondary || theme.secondary_color,
    keyFill: node,
    keyStroke: theme.accent_color,
    dot: theme.accent_color,
    // 下沉底 = 背景向分隔线走 80%；强调字优先用主题给的文字版强调色。
    sunken: mix(theme.background_color, theme.divider_color, 0.8),
    keyText: theme.primary_text || theme.accent_color,
    headingFont: String(theme.heading_font || theme.font_family_cn || 'sans-serif').replace(/"/g, "'"),
    headingWeight: theme.heading_weight || 500,
    glyphTitle: theme.name === 'zhijian',
  };
}

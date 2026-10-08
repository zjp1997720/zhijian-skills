import assert from 'node:assert/strict';
import test from 'node:test';

import { generateCoverAnimation } from '../scripts/generate-cover-animation.mjs';

const theme = {
  background_color: '#F5F4ED',
  accent_color: '#B85235',
  accent_secondary: '#1B365D',
  text_color: '#141413',
  tertiary_color: '#6B6A64',
};

function stripAnimations(svg) {
  return svg
    .replace(/<animate(?:Transform)?\b[^>]*\/>/gi, '')
    .replace(/<animate(?:Transform)?\b[^>]*>[\s\S]*?<\/animate(?:Transform)?>/gi, '');
}

function semanticTexts(svg) {
  const textNodes = [...svg.matchAll(/<text\b[^>]*>([\s\S]*?)<\/text>/gi)]
    .map(match => match[1].replace(/<[^>]+>/g, ''))
    .join('\n');
  const pixelLabels = [...svg.matchAll(/data-semantic-text="([^"]+)"/gi)]
    .map(match => match[1])
    .join('\n');
  return `${textNodes}\n${pixelLabels}`;
}

function assertStaticSemanticVisibility(svg, requiredTexts) {
  const stripped = stripAnimations(svg);
  assert.doesNotMatch(stripped, /<animate(?:Transform)?\b/i, 'animation stripping must exercise the fallback');
  const text = semanticTexts(stripped);
  for (const required of requiredTexts) {
    assert.ok(text.includes(required), `text disappears without animations: ${required}`);
  }
  assert.doesNotMatch(stripped, /<text\b[^>]*\sopacity="0"/i, 'semantic text has hidden baseline');
}

test('typewriter renders comma-separated cover tags', () => {
  const svg = generateCoverAnimation(theme, {
    template: 'typewriter',
    title: '十万卡，开始干活了',
    subtitle: '单日峰值50万个作业',
    tags: '曙光8000,十万卡AI超集群,WAIC 2026',
  });

  assert.match(svg, /<tspan leaf="">曙光8000 · 十万卡AI超集群 · WAIC 2026<\/tspan>/);
  assert.match(svg, /<text x="180" y="[\d.]+"[^>]+fill="#1B365D"/);
});

test('typewriter wraps long titles to two lines and keeps them inside the mobile safe width', () => {
  const svg = generateCoverAnimation(theme, {
    template: 'typewriter',
    title: '这是一个明显超过默认安全长度但仍然需要完整显示的打字机标题',
    subtitle: '这是一条同样很长并且需要自动缩小字号避免越过画布左右边界的副标题',
  });

  const title1 = svg.match(/data-typewriter-reveal="title" x="([\d.]+)"/);
  const title2 = svg.match(/data-typewriter-reveal="title-2" x="([\d.]+)"/);
  const subtitle = svg.match(/data-typewriter-reveal="subtitle" x="([\d.]+)"/);
  assert.ok(title1 && title2, 'long title should be typed as two lines');
  assert.ok(subtitle, 'subtitle should be rendered');
  for (const match of [title1, title2, subtitle]) {
    assert.ok(Number(match[1]) >= 10, `line starts outside safe area: ${match[1]}`);
  }
  const titleSize = Number(svg.match(/<text x="[\d.]+" y="[\d.]+"[^>]+font-size="([\d.]+)"/)[1]);
  assert.ok(titleSize <= 28, `title font larger than mobile headline: ${titleSize}`);
  assert.match(svg, /data-typewriter-lines="title"[^>]+data-semantic-text="这是一个明显超过默认安全长度但仍然需要完整显示的打字机标题"/);
});

test('typewriter keeps valid SVG geometry when optional subtitle and tags are absent', () => {
  const svg = generateCoverAnimation(theme, {
    template: 'typewriter',
    title: '只有标题',
  });

  assert.doesNotMatch(svg, /NaN|dur="0s"/);
});

test('typewriter keeps WorkBuddy visible when reader drops or disables all animations', () => {
  const svg = generateCoverAnimation(theme, {
    template: 'typewriter',
    title: 'WorkBuddy Skill机制拆解',
    subtitle: '从How到Why，万字干货',
    tags: 'WorkBuddy,Skill,机制',
  });

  assertStaticSemanticVisibility(svg, [
    'WorkBuddy Skill机制拆解',
    '从How到Why，万字干货',
    'WorkBuddy · Skill · 机制',
    '向下滑动继续阅读',
  ]);

  const titleMatches = [...svg.matchAll(/<text x="[\d.]+" y="[\d.]+"[^>]*font-size="(?:2[2-8](?:\.5)?)"[^>]*>([\s\S]*?)<\/text>/g)];
  assert.ok(titleMatches.length >= 1 && titleMatches.length <= 2, 'title should be at most two whole-line text nodes');
  assert.equal(titleMatches.map(match => match[1].replace(/<[^>]+>/g, '')).join(' '), 'WorkBuddy Skill机制拆解');
  for (const match of titleMatches) {
    assert.doesNotMatch(match[0], /opacity="0"/, 'title characters need a visible static baseline');
  }
});

test('typewriter progressively reveals characters instead of animating the cursor alone', () => {
  const title = 'AB机制';
  const svg = generateCoverAnimation(theme, {
    template: 'typewriter',
    title,
  });

  const reveal = svg.match(/<rect\b[^>]*data-typewriter-reveal="title"[^>]*>[\s\S]*?<\/rect>/)?.[0];
  assert.ok(reveal, 'title needs a dedicated progressive reveal layer');
  assert.match(reveal, /opacity="0"/, 'reveal layer must be transparent when animations are unavailable');
  assert.match(reveal, /<animate attributeName="opacity" values="1;1;0"[^>]+begin="0s"[^>]+fill="remove"/);

  const xAnimation = reveal.match(/<animate attributeName="x"[^>]+>/)?.[0] ?? '';
  const widthAnimation = reveal.match(/<animate attributeName="width"[^>]+>/)?.[0] ?? '';
  assert.match(xAnimation, /calcMode="discrete"/, 'text reveal must advance in character steps');
  assert.match(widthAnimation, /calcMode="discrete"/, 'text reveal must advance in character steps');

  const xValues = xAnimation.match(/values="([^"]+)"/)?.[1].split(';') ?? [];
  assert.equal(xValues.length, [...title].length + 1, 'reveal needs one position per typed character');

  const cursor = svg.match(/<rect\b[^>]*data-typewriter-cursor="title"[^>]*>[\s\S]*?<\/rect>/)?.[0] ?? '';
  assert.match(cursor, /opacity="0"/, 'future cursors need a transparent baseline');
  assert.match(cursor, /repeatCount="indefinite"/, 'active cursor should blink while the line is typing');

  assertStaticSemanticVisibility(svg, [title]);
});

test('all cover templates keep semantic text visible without animations', () => {
  const cases = [
    ['ink-wash', ['WorkBuddy机制', '从How到Why', '向下滑动开始阅读']],
    ['xiaolan-terminal', ['WorkBuddy机制', '从How到Why', 'Skill / 机制']],
    ['scroll-painting', ['WorkBuddy机制', '从How到Why', '向下滑动查看全文']],
    ['spotlight', ['WorkBuddy机制', '从How到Why', '向下滑动查看深度分析']],
    ['minimal-sketch', ['WorkBuddy机制', '从How到Why']],
  ];

  for (const [template, required] of cases) {
    const svg = generateCoverAnimation({
      ...theme,
      top_label: '智见AI',
      heading_font: "'Source Han Serif SC',serif",
      font_family_cn: "'Source Han Serif SC',serif",
      ui_font: "'Source Han Sans SC',sans-serif",
    }, {
      template,
      title: 'WorkBuddy机制',
      subtitle: '从How到Why',
      tags: 'Skill,机制',
      date: '2026.08',
      author: '智见AI',
    });
    assertStaticSemanticVisibility(svg, required);
  }
});

test('xiaolan-terminal embeds the canonical high-density pixel IP without machine-local paths', () => {
  const svg = generateCoverAnimation(theme, {
    template: 'xiaolan-terminal',
    title: 'Qoder:',
    subtitle: 'beyond code',
    tags: 'Agent,Context',
  });

  assert.match(svg, /data-template="xiaolan-terminal"/);
  assert.match(svg, /data-ip="zhijian-xiaolan"/);
  assert.match(svg, /data-ip-source="canonical-pet-v2"/);
  assert.match(svg, /data-ip-render="high-density-pixel"/);
  assert.match(svg, /data-ip-source-sha256="bea0a78d1d435feb9b6465be41db5144bf529c459da698228a2c9ce1d17ed931"/);
  assert.match(svg, /data-xiaolan-asset="eyes-open"[^>]+data-xiaolan-render="native-svg-pixels"/);
  assert.match(svg, /data-xiaolan-asset="eyes-closed"[^>]+data-xiaolan-render="native-svg-pixels"/);
  assert.match(svg, /data-xiaolan-asset="wave-mid"[^>]+data-xiaolan-render="native-svg-pixels"/);
  assert.match(svg, /data-xiaolan-asset="wave-high"[^>]+data-xiaolan-render="native-svg-pixels"/);
  assert.ok((svg.match(/<path\b/g) ?? []).length >= 100, 'native pixel frames should preserve high-density shading');
  assert.doesNotMatch(svg, /<image\b/i, 'WeChat strips href from SVG image nodes');
  assert.doesNotMatch(svg, /(?:href|xlink:href)=/i, 'Xiaolan frames must not depend on removable image references');
  assert.match(svg, /data-xiaolan-part="terminal-prompt"[^>]+aria-label="terminal prompt"/);
  assert.ok(Buffer.byteLength(svg, 'utf8') < 500_000, 'native pixel frames should stay within the opening SVG size budget');
  assertStaticSemanticVisibility(svg, ['Qoder:', 'beyond code', 'Agent / Context']);
});

test('xiaolan-terminal loops through blank, type, hold, and right-to-left erase phases', () => {
  const svg = generateCoverAnimation(theme, {
    template: 'xiaolan-terminal',
    title: 'Qoder:',
    subtitle: 'beyond code',
  });

  const reveal = svg.match(/<rect\b[^>]*data-typewriter-reveal="terminal-loop"[^>]*>[\s\S]*?<\/rect>/)?.[0] ?? '';
  assert.match(svg, /data-terminal-loop="4\.00s"/);
  assert.match(svg, /data-terminal-phase-order="blank-type-hold-erase"/);
  assert.match(reveal, /repeatCount="indefinite"/);
  assert.match(reveal, /calcMode="discrete"/);
  assert.match(svg, /data-typewriter-cursor="terminal-loop"[^>]*>[\s\S]*?repeatCount="indefinite"/);
  assert.doesNotMatch(svg, /data-typewriter-cursor="final"/);
});

test('xiaolan-terminal renders supported Latin copy as a true square-grid font', () => {
  const svg = generateCoverAnimation(theme, {
    template: 'xiaolan-terminal',
    title: 'Qoder:',
    subtitle: 'beyond code',
  });

  assert.match(svg, /data-pixel-text="title"[^>]+data-semantic-text="Qoder:"/);
  assert.match(svg, /data-pixel-text="subtitle"[^>]+data-semantic-text="beyond code"/);
  assert.ok((svg.match(/data-pixel-glyph=/g) ?? []).length >= 12, 'the line should use bitmap glyph groups');
  assert.ok((svg.match(/data-pixel-cell=/g) ?? []).length >= 80, 'the glyphs need enough square cells to read as dot matrix');
  assert.match(svg, /shape-rendering="crispEdges"/);
  assertStaticSemanticVisibility(svg, ['Qoder:', 'beyond code']);
});

test('xiaolan-terminal falls back to visible terminal text for unsupported Chinese glyphs', () => {
  const svg = generateCoverAnimation(theme, {
    template: 'xiaolan-terminal',
    title: '小蓝开始工作',
    subtitle: 'Agent ready',
  });

  assert.match(svg, /data-typewriter-reveal="title"/);
  assert.match(svg, /data-pixel-text="subtitle"/);
  assertStaticSemanticVisibility(svg, ['小蓝开始工作', 'Agent ready']);
});

test('xiaolan-terminal renders Latin runs as pixel geometry inside mixed Chinese copy', () => {
  const subtitle = '让 WorkBuddy 持续接住你的项目';
  const svg = generateCoverAnimation(theme, {
    template: 'xiaolan-terminal',
    title: '构建项目分身',
    subtitle,
  });

  const pixelLabels = [...svg.matchAll(/data-pixel-text="[^"]+"[^>]+data-semantic-text="([^"]+)"/g)]
    .map(match => match[1]);
  const fontBackedText = [...svg.matchAll(/<text\b[^>]*>([\s\S]*?)<\/text>/gi)]
    .map(match => match[1].replace(/<[^>]+>/g, ''))
    .join('\n');

  assert.ok(
    pixelLabels.some(label => label.includes('WorkBuddy')),
    'WorkBuddy must use native pixel geometry instead of reader-dependent SVG font glyphs',
  );
  assert.ok(!fontBackedText.includes('WorkBuddy'), 'mixed Latin copy must not fall back to an SVG text node');
  assert.match(svg, new RegExp(`data-semantic-text="${subtitle}"`));
  assertStaticSemanticVisibility(svg, [subtitle]);
});

test('xiaolan-terminal uses a sprite-like whole-character idle and a three-second blink frame', () => {
  const svg = generateCoverAnimation(theme, {
    template: 'xiaolan-terminal',
    title: 'Agent:',
    subtitle: 'ready',
  });

  const idle = svg.match(/<g\b[^>]*data-xiaolan-motion="idle-avatar"[^>]*>[\s\S]*?<\/g>/)?.[0] ?? '';
  const closedFrame = svg.match(/<g\b[^>]*data-xiaolan-frame="eyes-closed"[^>]*>[\s\S]*?<\/g>/)?.[0] ?? '';

  assert.match(idle, /<animateTransform[^>]+type="translate"[^>]+dur="3s"[^>]+repeatCount="indefinite"[^>]+calcMode="discrete"/);
  assert.match(closedFrame, /<animate[^>]+attributeName="opacity"[^>]+dur="3s"[^>]+repeatCount="indefinite"[^>]+calcMode="discrete"/);
});

test('xiaolan-terminal greets readers with a two-beat discrete hand wave', () => {
  const svg = generateCoverAnimation(theme, {
    template: 'xiaolan-terminal',
    title: 'Agent:',
    subtitle: 'ready',
  });

  const greeting = svg.match(/<g\b[^>]*data-xiaolan-motion="wave-greeting"[^>]*>[\s\S]*?<\/g>/)?.[0] ?? '';
  const midFrame = svg.match(/<g\b[^>]*data-xiaolan-frame="wave-mid"[^>]*>[\s\S]*?<\/g>/)?.[0] ?? '';
  const highFrame = svg.match(/<g\b[^>]*data-xiaolan-frame="wave-high"[^>]*>[\s\S]*?<\/g>/)?.[0] ?? '';

  assert.match(greeting, /data-wave-loop="6s"/);
  assert.match(greeting, /data-wave-sequence="idle-mid-high-mid-high-mid-idle"/);
  assert.match(midFrame, /values="0;1;0;1;0;1;0;0"/);
  assert.match(highFrame, /values="0;0;1;0;1;0;0;0"/);
  assert.match(midFrame, /dur="6s"[^>]+repeatCount="indefinite"[^>]+calcMode="discrete"/);
  assert.match(highFrame, /dur="6s"[^>]+repeatCount="indefinite"[^>]+calcMode="discrete"/);
});

test('typewriter uses a monospace stack for mixed Chinese and English subtitles', () => {
  const svg = generateCoverAnimation({
    ...theme,
    code_font: "'SF Mono','JetBrains Mono',Menlo,monospace",
    font_family_cn: "'Source Han Serif SC','Songti SC',serif",
  }, {
    template: 'typewriter',
    title: 'AI写完，还不能交付',
    subtitle: '从 Markdown 到 Word 和 PDF',
  });

  const subtitleStart = svg.match(/<text x="[\d.]+" y="[\d.]+"[^>]+fill="#6B6A64" font-family="([^"]+)"/);
  assert.ok(subtitleStart, 'subtitle text should be rendered');
  assert.equal(subtitleStart[1], "'JetBrains Mono',Menlo,monospace");
});

test('typewriter font stack uses broadly available Latin fallbacks', () => {
  const svg = generateCoverAnimation({
    ...theme,
    code_font: "'SF Mono','JetBrains Mono',Menlo,monospace",
    font_family_cn: "'Source Han Serif SC','Songti SC',serif",
  }, {
    template: 'typewriter',
    title: 'WorkBuddy Skill机制拆解',
    subtitle: '从How到Why，万字干货',
  });

  const fontFamilies = [...svg.matchAll(/font-family="([^"]+)"/g)]
    .map(match => match[1])
    .filter(font => font.includes('Courier') || font.includes('Mono'));

  assert.ok(fontFamilies.length > 0, 'typewriter should emit font-family attributes');
  for (const font of fontFamilies) {
    assert.ok(!/^'SF Mono'/.test(font), `SF Mono must not lead a reader-facing stack: ${font}`);
    assert.match(font, /Menlo|Consolas|Courier New/, `missing broadly available Latin fallback: ${font}`);
    assert.match(font, /,monospace$/, `missing generic fallback: ${font}`);
  }
});

const ALL_TEMPLATES = ['ink-wash', 'typewriter', 'xiaolan-terminal', 'scroll-painting', 'spotlight', 'minimal-sketch'];
const mobileTheme = { ...theme, top_label: '学校AI落地' };

function fontSizes(svg) {
  return [...svg.matchAll(/<text\b[^>]*font-size="([\d.]+)"[^>]*>([\s\S]*?)<\/text>/g)]
    .map(match => ({ size: Number(match[1]), text: match[2].replace(/<[^>]+>/g, '') }));
}

test('all cover templates use a phone-width viewBox and readable minimum font sizes', () => {
  for (const template of ALL_TEMPLATES) {
    for (const title of ['学校 AI 推不动的根本原因', '真做过 VS 只会讲']) {
      const svg = generateCoverAnimation(mobileTheme, {
        template,
        title,
        subtitle: '67 份问卷：八成在用，只有 4 人有稳定流程',
        tags: 'Skill,机制',
        author: '学校AI落地 · 02',
      });
      const viewBox = svg.match(/viewBox="0 0 ([\d.]+) ([\d.]+)"/);
      assert.ok(viewBox, `${template}: missing viewBox`);
      assert.equal(Number(viewBox[1]), 360, `${template}: viewBox must be phone width`);
      assert.ok(Number(viewBox[2]) <= 300, `${template}: opening is too tall (${viewBox[2]})`);
      assert.match(svg, /max-width:480px/);
      assert.doesNotMatch(svg, /NaN|undefined|<line\b|<style\b|\sclass=|rgba\(/i, `${template}: invalid or WeChat-unsafe output`);
      const sizes = fontSizes(svg).filter(item => item.text !== '↓');
      for (const { size, text } of sizes) {
        assert.ok(size >= 12, `${template}: "${text}" renders at ${size}px`);
      }
      if (template !== 'xiaolan-terminal') {
        const titleSize = Math.max(...sizes.map(item => item.size));
        assert.ok(titleSize >= 22 && titleSize <= 30, `${template}: headline size ${titleSize}`);
      }
    }
  }
});

test('long CJK titles wrap to two lines while short titles stay on one line', () => {
  for (const template of ['ink-wash', 'scroll-painting', 'spotlight', 'minimal-sketch']) {
    const long = generateCoverAnimation(mobileTheme, { template, title: '学校 AI 推不动的根本原因', subtitle: '答案在第一批跑通的老师身上' });
    const titleNode = long.match(/<text\b[^>]*data-semantic-text="学校 AI 推不动的根本原因"[^>]*>([\s\S]*?)<\/text>/);
    assert.ok(titleNode, `${template}: long title should become a two-line text node`);
    const lines = [...titleNode[1].matchAll(/<tspan leaf="" x="[-\d.]+" y="[-\d.]+">([^<]+)<\/tspan>/g)].map(match => match[1]);
    assert.deepEqual(lines, ['学校 AI 推不动的', '根本原因'], `${template}: unexpected line break`);

    const short = generateCoverAnimation(mobileTheme, { template, title: '真做过 VS 只会讲' });
    assert.match(short, /<tspan leaf="">真做过 VS 只会讲<\/tspan>/, `${template}: short title should stay on one line`);
    assertStaticSemanticVisibility(long, ['学校 AI 推不动的根本原因', '答案在第一批跑通的老师身上']);
  }
});

test('xiaolan-terminal and typewriter keep wrapped mixed titles semantically whole', () => {
  for (const template of ['xiaolan-terminal', 'typewriter']) {
    const svg = generateCoverAnimation(mobileTheme, {
      template,
      title: '学校 AI 推不动的根本原因',
      subtitle: '67 份问卷：八成在用，只有 4 人有稳定流程',
    });
    assertStaticSemanticVisibility(svg, ['学校 AI 推不动的根本原因', '67 份问卷：八成在用，只有 4 人有稳定流程']);
  }
});

test('cover brand label and byline honour topLabel and author overrides', () => {
  const base = { title: '标题', subtitle: '副标题' };
  for (const template of ['ink-wash', 'spotlight']) {
    assert.match(generateCoverAnimation(mobileTheme, { ...base, template }), />学校AI落地/);
    assert.doesNotMatch(generateCoverAnimation(mobileTheme, { ...base, template, topLabel: '' }), /学校AI落地/);
  }
  const scroll = options => generateCoverAnimation(mobileTheme, { ...base, template: 'scroll-painting', ...options });
  assert.match(scroll({}), /<tspan leaf="">学校AI落地 出品<\/tspan>/);
  assert.match(scroll({ author: '学校AI落地 · 02' }), /<tspan leaf="">学校AI落地 · 02<\/tspan>/);
  assert.doesNotMatch(scroll({ author: '学校AI落地 · 02' }), /出品/);
  assert.doesNotMatch(scroll({ author: false }), /出品|学校AI落地/);
});

test('scroll arrow bounces relative to its own anchor', () => {
  const svg = generateCoverAnimation(mobileTheme, { template: 'scroll-painting', title: '标题' });
  assert.match(svg, /<g transform="translate\(180,[\d.]+\)"><text x="0" y="0"[^>]*><tspan leaf="">↓<\/tspan><animateTransform[^>]+values="0 0;0 6;0 0"/);
});

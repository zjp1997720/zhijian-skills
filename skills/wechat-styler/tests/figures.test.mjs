import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { after, before, describe, test } from 'node:test';
import os from 'node:os';
import { fileURLToPath } from 'node:url';

import yaml from 'js-yaml';

import { Fig, SpecError, W, balance, fixed, stripAnimation } from '../scripts/figures/core.mjs';
import { buildFigure } from '../scripts/figures/figure.mjs';
import { loadFont, resolveFigureFont } from '../scripts/figures/fonts.mjs';
import { checkRendered, checkStructure, checkTheme } from '../scripts/figures/gates.mjs';
import { staticMarkdown } from '../scripts/figures/pipeline.mjs';
import { themeTokens } from '../scripts/figures/theme.mjs';
import { launchBrowser, makeTestFont } from './figures-helpers.mjs';

const root = path.dirname(fileURLToPath(import.meta.url));
const skillRoot = path.dirname(root);
const showcase = JSON.parse(fs.readFileSync(path.join(root, 'fixtures/figure-showcase.json'), 'utf8'));
const SPECS = Object.fromEntries(showcase.figures.map((f) => [f.id, f]));
const copy = (value) => JSON.parse(JSON.stringify(value));
const loadThemeYaml = (name) => yaml.load(fs.readFileSync(path.join(skillRoot, 'themes', `${name}.yaml`), 'utf8'));
const THEME_NAMES = fs.readdirSync(path.join(skillRoot, 'themes')).map((f) => f.replace('.yaml', '')).sort();
const TOKENS = themeTokens(loadThemeYaml('zhijian'));
const font = makeTestFont(`${JSON.stringify(showcase)}0123456789 这是一个远远超过十三个字的结论式标题写法第几版`);
const good = (id = 'stack', options = {}) => buildFigure(copy(SPECS[id]), TOKENS, { font, ...options });
const mutate = (fig, fn) => ({ ...fig, svg: fn(fig.svg), qa: fn(fig.qa) });
const withExtra = (fig, extra) => mutate(fig, (s) => s.replace('</svg>', `${extra}</svg>`));

describe('结构白名单', () => {
  test('范例全部干净', () => {
    for (const id of Object.keys(SPECS)) assert.deepEqual(checkStructure(good(id).svg), [], id);
  });

  test('拦下未验证的标签和属性', () => {
    const { svg } = good();
    for (const [bad, want] of [
      ['<style>a{}</style>', 'tag-not-allowed:style'],
      ['<image href="x"/>', 'tag-not-allowed:image'],
      ['<g id="a"></g>', 'id-attribute'],
      ['<text x="1" y="1" font-size="10">小</text>', 'font-too-small:10'],
      ['<rect><animate attributeName="width" values="1;2" dur="1s"/></rect>', 'anim-attr-not-allowed:width'],
      ['<g>', 'malformed-svg'],
    ]) {
      const issues = checkStructure(svg.replace('</svg>', `${bad}</svg>`));
      assert.ok(issues.some((i) => i.includes(want)), `${bad}: ${issues}`);
    }
  });

  test('拦下超过 30KB 的图', () => {
    const svg = good().svg.replace('</svg>', `<path d="${'M0 0'.repeat(12000)}"/></svg>`);
    assert.ok(checkStructure(svg).some((i) => i.includes('too-large')));
  });

  test('对比度不足亮红灯', () => {
    assert.deepEqual(checkTheme(TOKENS), []);
    assert.ok(checkTheme({ ...TOKENS, faint: '#CCCCCC' }).length);
  });
});

describe('主题', () => {
  // 引擎层的现状：这些主题的三级文字色达不到图解 12px 小字要求的 4.5:1。convert 目前只开放 zhijian。
  const KNOWN_CONTRAST_FAILURES = {
    elegant: ['muted/bg', 'faint/bg'],
    kami: ['faint/bg'],
    'magazine-forest': ['faint/bg'],
    'magazine-indigo': ['faint/bg'],
    'magazine-ink': ['faint/bg'],
    minimal: ['muted/bg', 'faint/bg'],
    modern: ['muted/bg', 'faint/bg'],
    zhijian: [],
  };

  test('zhijian 推导出的色板和原色板相同', () => {
    const { bg, node, sunken, rule, text, muted, faint, struct, keyFill, keyStroke, keyText, dot } = TOKENS;
    assert.deepEqual(
      { bg, node, sunken, rule, text, muted, faint, struct, keyFill, keyStroke, keyText, dot },
      { bg: '#F5F4ED', node: '#FAF9F5', sunken: '#e8e6dc', rule: '#E5E3D8', text: '#141413', muted: '#504E49', faint: '#6B6A64', struct: '#1B365D', keyFill: '#FAF9F5', keyStroke: '#B85235', keyText: '#A04A2E', dot: '#B85235' },
    );
  });

  test('引擎对 8 个主题都能生成；对比度不足的如实报出，不改色', () => {
    assert.deepEqual(THEME_NAMES, Object.keys(KNOWN_CONTRAST_FAILURES));
    for (const name of THEME_NAMES) {
      const tokens = themeTokens(loadThemeYaml(name));
      for (const spec of showcase.figures) assert.deepEqual(checkStructure(buildFigure(copy(spec), tokens, { font }).svg), [], `${name}/${spec.id}`);
      const pairs = checkTheme(tokens).map((issue) => issue.match(/^contrast:(.+)=/)[1]);
      assert.deepEqual(pairs, KNOWN_CONTRAST_FAILURES[name], name);
    }
  });
});

describe('字体', () => {
  const none = () => false;
  const only = (target) => (p) => p === target;

  test('按 --figure-font、环境变量、字体目录的顺序查找', () => {
    const base = { platform: 'darwin', home: '/h' };
    const dirHit = '/h/Library/Fonts/LXGWWenKai-Medium.ttf';
    assert.equal(resolveFigureFont({ ...base, flag: '/a.ttf', env: { WECHAT_STYLER_FIGURE_FONT: '/b.ttf' }, exists: () => true }).source, '--figure-font');
    assert.equal(resolveFigureFont({ ...base, flag: '/a.ttf', env: { WECHAT_STYLER_FIGURE_FONT: '/b.ttf' }, exists: only('/b.ttf') }).source, 'WECHAT_STYLER_FIGURE_FONT');
    const found = resolveFigureFont({ ...base, env: {}, exists: only(dirHit) });
    assert.equal(found.path, dirHit);
    assert.equal(resolveFigureFont({ ...base, flag: '/a.ttf', env: {}, exists: only(dirHit) }).note, '--figure-font 指向的字体不存在：/a.ttf');
  });

  test('没有字体不报错，标题退回 <text> 并用主题标题字体', () => {
    assert.equal(resolveFigureFont({ platform: 'darwin', home: '/h', env: {}, exists: none }).path, null);
    const fig = buildFigure(copy(SPECS.cycle), TOKENS, { font: null });
    assert.match(fig.svg, /<text [^>]*font-family="'LXGW WenKai'[^>]*><tspan leaf="">问题变成修复<\/tspan><\/text>/);
    assert.deepEqual(checkStructure(fig.svg), []);
  });

  test('zhijian 有字体转路径，其他主题用 <text>', () => {
    assert.ok(!good('stack').svg.includes('能用之前的四层'));
    const other = buildFigure(copy(SPECS.stack), themeTokens(loadThemeYaml('kami')), { font });
    assert.match(other.svg, /font-family="'TsangerJinKai02'[^>]*><tspan leaf="">能用之前的四层/);
  });

  test('所有 <text> 都带 tspan leaf', () => {
    for (const id of Object.keys(SPECS)) {
      const { svg } = buildFigure(copy(SPECS[id]), TOKENS, { font: null });
      for (const [inner] of svg.matchAll(/<text\b[^>]*>.*?<\/text>/g)) assert.match(inner, /<text\b[^>]*><tspan leaf="">[^<]*<\/tspan><\/text>/);
    }
  });
});

describe('中英混排', () => {
  const PHRASES = ['你创建的 Skill', 'AI 复盘提议', 'What 和 How 都有了', '2026 年', '90%'];
  const phraseFont = makeTestFont(`${PHRASES.join('')}${JSON.stringify(showcase)}`);
  const fig = (spec, options) => buildFigure({ id: 'x', type: 'route', title: '换个地方执行', conclusion: '入口不变', ...spec }, TOKENS, options);
  const ROUTE = { source: { label: '你创建的 Skill', sub: '放在哪' }, targets: [{ label: 'AI 复盘提议', sub: '项目级' }, { label: '用户级', sub: 'What 和 How' }] };
  const textRuns = (svg) => [...svg.matchAll(/<text\b[^>]*>(.*?)<\/text>/g)].map((m) => m[1].replace(/<[^>]+>/g, ''));

  test('拉丁段不出现在任何 <text> 内，中文段还在', () => {
    const { svg, notes } = fig(ROUTE, { font: phraseFont });
    const runs = textRuns(svg);
    assert.ok(runs.every((t) => !/[A-Za-z0-9]/.test(t)), runs.join('|'));
    assert.ok(runs.includes('你创建的'));
    assert.ok(runs.includes('复盘提议'));
    assert.match(svg, /aria-label="你创建的 Skill"/);
    assert.deepEqual(notes, []);
    assert.doesNotMatch(svg, /data-glyph/);
  });

  test('纯中文不拆段，不加分组', () => {
    const { svg } = good('stack');
    assert.match(svg, /<text [^>]*><tspan leaf="">运行环境<\/tspan><\/text>/);
  });

  test('拉丁段宽度算进对齐：居中时两段关于 x 对称', () => {
    const f = new Fig({}, TOKENS, { font: phraseFont });
    const markup = f.text('AI 复盘', 180, 100, 14, '#000', { anchor: 'middle' });
    const x = Number(markup.match(/<text x="([\d.]+)"/)[1]);
    assert.match(markup, /<path d="M/);
    // AI 和空格共 3 个 0.6em，“复盘”2 个 1em，总宽 53.2，起点 153.4，中文段从 153.4 + 25.2 开始
    assert.ok(Math.abs(x - 178.6) < 0.11, String(x));
    assert.doesNotMatch(markup, /text-anchor/);
  });

  test('无字体时保留 <text>，并标出风险', () => {
    const { svg, notes } = fig(ROUTE, { font: null });
    assert.ok(textRuns(svg).includes('你创建的 Skill'));
    assert.ok(notes.includes('你创建的 Skill'));
  });

  test('有真实字体时单张仍不超过 30KB', (t) => {
    const found = resolveFigureFont();
    if (!found.path) return t.skip('本机没有 LXGWWenKai-Medium.ttf');
    const real = loadFont(found.path);
    for (const id of Object.keys(SPECS)) assert.deepEqual(checkStructure(buildFigure(copy(SPECS[id]), TOKENS, { font: real }).svg), [], id);
    const { svg } = fig(ROUTE, { font: real });
    assert.ok(textRuns(svg).every((text) => !/[A-Za-z0-9]/.test(text)));
    assert.deepEqual(checkStructure(svg), []);
    return undefined;
  });
});

describe('规格', () => {
  test('放不下的直接报错', () => {
    const bad = (mutator, id = 'stack') => {
      const spec = copy(SPECS[id]);
      mutator(spec);
      assert.throws(() => buildFigure(spec, TOKENS, { font }), SpecError);
    };
    bad((s) => { s.title = '这是一个远远超过十三个字的结论式标题写法'; });
    bad((s) => { s.layers[0].label = '超过十二个字的节点文字写在这里了'; });
    bad((s) => { s.rows[1].key = true; }, 'bars');
    bad((s) => { s.type = 'pie'; });
    bad((s) => { delete s.conclusion; });
  });

  test('两行折法不留孤行', () => {
    const lines = balance('调研、设计、开发都快了，中间两次转述还是那么长的这件事', 15, 320);
    assert.equal(lines.length, 2);
    assert.ok(Math.min(...lines.map((x) => [...x].length)) > 6);
  });

  test('定点舍入在中点取偶数', () => {
    assert.equal(fixed(0.25), '0.2');
    assert.equal(fixed(0.75), '0.8');
    assert.equal(fixed(-0.04), '-0.0');
    assert.equal(fixed(12.34), '12.3');
  });
});

describe('渲染检查', () => {
  let browser = null;
  let page = null;
  let skipReason = '';

  before(async () => {
    const launched = await launchBrowser();
    browser = launched.browser;
    skipReason = launched.reason;
    if (browser) page = await browser.newPage({ viewport: { width: W, height: 900 } });
  });
  after(async () => {
    if (browser) await browser.close();
  });

  const issues = async (fig) => (await checkRendered(page, fig)).issues;
  const rendered = (name, fn) => test(name, async (t) => {
    if (!browser) return t.skip(skipReason);
    return fn();
  });
  const has = (list, want) => assert.ok(list.some((i) => i.includes(want)), `${want} 不在 ${JSON.stringify(list)}`);

  rendered('范例全部通过', async () => {
    for (const id of Object.keys(SPECS)) assert.deepEqual(await issues(good(id)), [], id);
  });

  rendered('8 个主题的几何和动画检查都通过（有字体和无字体）', async () => {
    for (const name of THEME_NAMES) {
      const tokens = themeTokens(loadThemeYaml(name));
      for (const spec of [SPECS.stack, SPECS.cycle]) {
        assert.deepEqual(await issues(buildFigure(copy(spec), tokens, { font })), [], `${name}/${spec.id}`);
        assert.deepEqual(await issues(buildFigure(copy(spec), tokens, { font: null })), [], `${name}/${spec.id}/无字体`);
      }
    }
  });

  rendered('删掉动画等于终态，定格不少于 2 秒', async () => {
    const fig = good('sequence');
    assert.doesNotMatch(stripAnimation(fig.svg), /<animate/);
    assert.ok((await checkRendered(page, fig)).metrics.hold >= 2);
  });

  rendered('拦下基态隐藏语义内容', async () => {
    const fig = mutate(good('stack'), (s) => s
      .replace('<g><animate attributeName="opacity"', '<g opacity="0"><animate attributeName="opacity"')
      .replace('values="1;1;0;0;1;1"', 'values="0;0;0;0;1;1"'));
    has(await issues(fig), 'hold-too-short');
  });

  rendered('拦下定格过短', async () => {
    has(await issues(good('stack', { holdTail: 0.3 })), 'hold-too-short');
  });

  rendered('拦下文字重叠和出画布', async () => {
    const extra = '<text x="350" y="30" font-size="14" fill="#000">出界的字</text><text x="180" y="28" font-size="12" fill="#000" text-anchor="middle">示例：层层垫高</text>';
    const found = await issues(withExtra(good('stack'), extra));
    has(found, 'text-off-canvas');
    has(found, 'text-overlap');
  });

  rendered('拦下文字压线', async () => {
    has(await issues(withExtra(good('stack'), '<text x="60" y="81" font-size="13" fill="#000">压在分隔线上</text>')), 'text-on-line');
  });

  rendered('拦下文字出框', async () => {
    const fig = good('stack');
    has(await issues({ ...fig, qa: fig.qa.replace(/data-box="[^"]+"/, 'data-box="20,0,40,20"') }), 'text-out-of-box');
  });

  rendered('中心数字放不下时自动缩小', async () => {
    const spec = copy(SPECS.cycle);
    spec.nodes = ['人来实践', 'AI 复盘提议', '人来判断', 'AI 固化'];
    spec.center = { label: '第几版', from: 1, to: 100 };
    assert.deepEqual(await issues(buildFigure(spec, TOKENS, { font })), []);
  });

  rendered('拦下标题或数字压住节点框', async () => {
    has(await issues(withExtra(good('route'), '<path d="M150 90h100v30h-100z" fill="#000"/>')), '压住节点框');
  });

  rendered('拉丁段压线、出框同样被拦下', async () => {
    const f = new Fig({}, TOKENS, { font: makeTestFont('Skill') });
    has(await issues(withExtra(good('stack'), f.text('Skill', 60, 80.5, 13, '#000'))), 'text-on-line:Skill');
    const qa = good('stack');
    const out = { ...qa, qa: qa.qa.replace('</svg>', `${f.text('Skill', 60, 200, 13, '#000', { box: [20, 0, 40, 20] })}</svg>`) };
    has(await issues(out), 'text-out-of-box:Skill');
  });

  rendered('读者端继承字距时文字不被撑开', async () => {
    const { svg } = good('stack');
    const measure = async (spacing) => {
      await page.setContent(`<div style="letter-spacing:${spacing}">${stripAnimation(svg)}</div>`);
      return page.evaluate(() => document.querySelector('text').getBoundingClientRect().width);
    };
    assert.equal(await measure('0.544px'), await measure('0'));
  });

  rendered('拦下不动的图', async () => {
    const fig = good('stack');
    has(await issues({ ...fig, svg: stripAnimation(fig.svg) }), 'not-animated');
  });
});

describe(':::figure 围栏', () => {
  const FENCE = (body) => `:::figure\n${body}\n:::`;
  const BAR = 'id: demo\ntype: stack\ntitle: 能用之前的四层\nconclusion: 四层都垫好才有用\nlayers:\n  - label: 运行环境\n  - label: 验收';
  const ARTICLE = (fence) => `---\ntitle: 示例\n---\n\n# 标题\n\n前面一段。\n\n${fence}\n\n后面一段。\n`;

  function convert(markdown, args = [], env = {}) {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'figure-'));
    const input = path.join(dir, 'a.md');
    const output = path.join(dir, 'a.html');
    fs.writeFileSync(input, markdown);
    const result = spawnSync(process.execPath, [path.join(skillRoot, 'scripts/convert.mjs'), input, '--output', output, '--no-open', '--brand-cta', 'none', ...args],
      { encoding: 'utf8', env: { ...process.env, CHROME_EXECUTABLE: env.chrome ?? process.env.CHROME_EXECUTABLE } });
    return { result, dir, html: fs.existsSync(output) ? fs.readFileSync(output, 'utf8') : null };
  }

  test('组件模式换成内联 SVG，不留 ::: 和 YAML', () => {
    const { result, html } = convert(ARTICLE(FENCE(BAR)), ['--components']);
    assert.equal(result.status, 0, result.stderr);
    assert.match(html, /<section style="margin:20px 0;line-height:0;"><svg viewBox="0 0 360 /);
    assert.equal((html.match(/<svg viewBox="0 0 360 /g) || []).length, 1);
    assert.ok(!html.includes(':::'));
    assert.ok(!html.includes('layers:'));
  });

  test('未开组件模式降级成标题加结论句的引用', () => {
    const { result, html } = convert(ARTICLE(FENCE(BAR)));
    assert.equal(result.status, 0, result.stderr);
    assert.ok(!html.includes('<svg viewBox="0 0 360'));
    assert.ok(!html.includes(':::'));
    assert.ok(!html.includes('layers:'));
    const quoted = convert(ARTICLE('> **能用之前的四层**\n>\n> 四层都垫好才有用'));
    assert.equal(html, quoted.html);
  });

  test('失败时报出图 ID 和原因，不出稿', () => {
    for (const [fence, want] of [
      [FENCE('id: bad-type\ntype: pie\ntitle: 甲\nconclusion: 乙'), /图解 bad-type：type 只能是/],
      [FENCE('id: bad-yaml\nlayers: [unterminated'), /图解 bad-yaml：YAML 解析失败/],
      [FENCE('id: ../evil\ntype: stack'), /id 只能用字母/],
      [':::figure\nid: open\ntype: stack', /没有闭合/],
      [`${FENCE(BAR)}\n\n${FENCE(BAR)}`, /图解 demo：id 重复/],
    ]) {
      const { result, html } = convert(ARTICLE(fence), ['--components']);
      assert.equal(result.status, 1, fence);
      assert.match(result.stderr, want);
      assert.equal(html, null);
    }
  });

  test('一篇超过 5 张报错', () => {
    const fences = [1, 2, 3, 4, 5, 6].map((i) => FENCE(BAR.replace('id: demo', `id: f${i}`))).join('\n\n后文。\n\n');
    const { result, html } = convert(ARTICLE(fences), ['--components']);
    assert.equal(result.status, 1);
    assert.match(result.stderr, /图解 f6：一篇不超过 5 张/);
    assert.equal(html, null);
  });

  test('非 zhijian 主题写明只支持 zhijian，不改色也不出稿', () => {
    for (const name of THEME_NAMES.filter((theme) => theme !== 'zhijian')) {
      const { result, html } = convert(ARTICLE(FENCE(BAR)), ['--components', '--theme', name]);
      assert.equal(result.status, 1, name);
      assert.match(result.stderr, new RegExp(`图解 demo：图解目前只支持 zhijian 主题，当前主题是 ${name}`));
      assert.equal(html, null, name);
    }
  });

  test('非 zhijian 主题未开组件模式仍降级成引用', () => {
    const { result, html } = convert(ARTICLE(FENCE(BAR)), ['--theme', 'kami']);
    assert.equal(result.status, 0, result.stderr);
    assert.match(html, /能用之前的四层/);
    assert.ok(!html.includes(':::'));
  });

  test('静态版把围栏换成 Markdown 图片，其余原样保留', () => {
    const source = `---\ntitle: 示例\n---\n\n前文。\n\n${FENCE(BAR)}\n\n\`\`\`\n${FENCE('type: pie')}\n\`\`\`\n\n后文。\n`;
    const out = staticMarkdown(source, path.join('..', 'my figs'));
    assert.ok(out.startsWith('---\ntitle: 示例\n---\n'));
    assert.match(out, /\n!\[能用之前的四层\]\(\.\.\/my%20figs\/demo\.png\)\n/);
    assert.ok(!out.includes('layers:'));
    assert.ok(out.includes('type: pie'), '代码块里的示例不动');
    assert.match(staticMarkdown(FENCE(BAR), ''), /\(demo\.png\)/);
    assert.match(staticMarkdown(FENCE('id: a\ntitle: 甲[乙]'), 'x'), /!\[甲\\\[乙\\\]\]\(x\/a\.png\)/);
  });

  test('--figure-static-md 缺 --figure-png 时报错', () => {
    const { result } = convert(ARTICLE(FENCE(BAR)), ['--components', '--figure-static-md', 'x.md']);
    assert.equal(result.status, 1);
    assert.match(result.stderr, /需要同时带 --components 和 --figure-png/);
  });

  test('--figure-static-md 写出能找到 PNG 的 Markdown', async (t) => {
    const { browser, reason } = await launchBrowser();
    if (!browser) return t.skip(reason);
    await browser.close();
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'figure-static-'));
    const md = path.join(dir, 'out/a.md');
    const { result } = convert(ARTICLE(FENCE(BAR)), ['--components', '--figure-png', path.join(dir, 'figs'), '--figure-static-md', md]);
    assert.equal(result.status, 0, result.stderr);
    const text = fs.readFileSync(md, 'utf8');
    const target = text.match(/!\[能用之前的四层\]\(([^)]+)\)/)?.[1];
    assert.equal(target, '../figs/demo.png');
    assert.ok(fs.existsSync(path.resolve(path.dirname(md), target)));
    assert.ok(!text.includes(':::'));
    return undefined;
  });

  test('代码块里的 :::figure 原样保留', () => {
    const { result, html } = convert(ARTICLE(`\`\`\`\n${FENCE('type: pie')}\n\`\`\``), ['--components']);
    assert.equal(result.status, 0, result.stderr);
    assert.ok(html.includes(':::figure'));
  });

  test('默认转换没有图解时不碰浏览器', () => {
    const { result } = convert('# 标题\n\n一段正文。\n', ['--components'], { chrome: '/missing/chrome' });
    assert.equal(result.status, 0, result.stderr);
    assert.ok(!result.stdout.includes('图解'));
  });

  test('没有可用浏览器时照常出稿并写明没查；要 PNG 则报错', () => {
    const plain = convert(ARTICLE(FENCE(BAR)), ['--components'], { chrome: '/missing/chrome' });
    assert.equal(plain.result.status, 0, plain.result.stderr);
    assert.match(plain.result.stderr, /渲染检查未执行/);
    assert.ok(plain.html);
    const png = convert(ARTICLE(FENCE(BAR)), ['--components', '--figure-png', 'x'], { chrome: '/missing/chrome' });
    assert.equal(png.result.status, 1);
    assert.match(png.result.stderr, /--figure-png 需要浏览器/);
  });

  test('--figure-png 输出 PNG、SVG、联系图和报告', async (t) => {
    const { browser, reason } = await launchBrowser();
    if (!browser) return t.skip(reason);
    await browser.close();
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'figure-png-'));
    const { result, html } = convert(ARTICLE(FENCE(BAR)), ['--components', '--figure-png', dir]);
    assert.equal(result.status, 0, result.stderr);
    assert.ok(html);
    for (const file of ['demo.png', 'demo.svg', 'contact.png', 'report.json']) assert.ok(fs.existsSync(path.join(dir, file)), file);
    const report = JSON.parse(fs.readFileSync(path.join(dir, 'report.json'), 'utf8'));
    assert.equal(report.status, 'pass');
    assert.ok(report.figures[0].hold >= 2);
    return undefined;
  });

  test('无字体时报告写明退回 <text> 和拉丁文风险', async (t) => {
    const { browser, reason } = await launchBrowser();
    if (!browser) return t.skip(reason);
    await browser.close();
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'figure-nofont-'));
    const fence = FENCE(BAR.replace('运行环境', 'AI 运行环境'));
    const input = path.join(dir, 'a.md');
    fs.writeFileSync(input, ARTICLE(fence));
    const result = spawnSync(process.execPath, [path.join(skillRoot, 'scripts/convert.mjs'), input, '--output', path.join(dir, 'a.html'), '--no-open', '--components', '--figure-png', path.join(dir, 'figs')],
      { encoding: 'utf8', env: { ...process.env, HOME: dir, WECHAT_STYLER_FIGURE_FONT: '' } });
    assert.equal(result.status, 0, result.stderr);
    const report = JSON.parse(fs.readFileSync(path.join(dir, 'figs/report.json'), 'utf8'));
    assert.equal(report.font, null);
    assert.ok(report.notes.some((note) => note.includes('退回 <text>')), report.notes.join('|'));
    assert.ok(report.notes.some((note) => note.includes('AI 运行环境')), report.notes.join('|'));
    return undefined;
  });
});

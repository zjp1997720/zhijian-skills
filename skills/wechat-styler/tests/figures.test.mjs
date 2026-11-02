import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { after, before, describe, test } from 'node:test';
import { fileURLToPath } from 'node:url';

import { SpecError, W, balance, fixed, stripAnimation } from '../scripts/figures/core.mjs';
import { buildFigure } from '../scripts/figures/figure.mjs';
import { checkRendered, checkStructure, checkTheme } from '../scripts/figures/gates.mjs';
import { launchBrowser, makeTestFont } from './figures-helpers.mjs';

const root = path.dirname(fileURLToPath(import.meta.url));
const showcase = JSON.parse(fs.readFileSync(path.join(root, 'fixtures/figure-showcase.json'), 'utf8'));
const SPECS = Object.fromEntries(showcase.figures.map((f) => [f.id, f]));
const copy = (value) => JSON.parse(JSON.stringify(value));
const TOKENS = {
  name: 'zhijian', bg: '#F5F4ED', node: '#FAF9F5', sunken: '#E8E6DC', rule: '#E5E3D8', text: '#141413', muted: '#504E49', faint: '#6B6A64',
  struct: '#1B365D', keyFill: '#FAF9F5', keyStroke: '#B85235', keyText: '#A04A2E', dot: '#B85235',
};
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

  rendered('拦下不动的图', async () => {
    const fig = good('stack');
    has(await issues({ ...fig, svg: stripAnimation(fig.svg) }), 'not-animated');
  });
});

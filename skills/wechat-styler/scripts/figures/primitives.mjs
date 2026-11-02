// 六种结构。每个函数画图解区、登记动画，返回图解区底边 y。
import { BUILD_FROM, EASE, INNER, LIN, M, RESET_FROM, RESET_TO, SpecError, W, balance, estWidth, fixed, wrap } from './core.mjs';

const NODE_LABEL_MAX = 12; // 节点文字不超过 12 字

function label(value, where) {
  const text = String(value);
  if ([...text].length > NODE_LABEL_MAX) throw new SpecError(`${where}「${text}」超过 ${NODE_LABEL_MAX} 字，缩短或放到说明里`);
  return text;
}

function need(spec, key, type) {
  if (!(key in spec)) throw new SpecError(`${type} 缺字段 ${key}`);
  return spec[key];
}

function atMostKeys(items, limit, type) {
  if (items.filter((i) => i.key).length > limit) throw new SpecError(`${type} 的 key 最多 ${limit} 个：强调色只给这张图要你看的那一处`);
}

/** 序列或前后对比。按 len 定比例画块；static 行做参照，其余行按序生长，key 块长得慢。 */
function sequence(f, s, y0) {
  const { t } = f;
  const rows = need(s, 'rows', 'sequence');
  const gap = 6;
  let y = y0;
  const unit = Math.min(...rows.map((r) => (INNER - gap * (r.segments.length - 1)) / r.segments.reduce((sum, g) => sum + g.len, 0)));
  let cur = BUILD_FROM + 0.1;
  for (const row of rows) {
    y += 18;
    const animated = !row.static;
    f.add(f.text(row.label, M, y, 13, animated ? t.text : t.muted, { weight: animated ? 600 : null }));
    y += 10;
    let x = M;
    const h = 46;
    const rings = [];
    for (const seg of row.segments) {
      const w = seg.len * unit;
      const key = Boolean(seg.key);
      const size = key ? 15 : 14;
      const text = label(seg.label, '块');
      if (estWidth(text, size) + 4 > w) throw new SpecError(`块「${text}」放不下：len=${seg.len} 宽 ${fixed(w, 0)}px，加大 len 或缩短文字`);
      const cx = x + w / 2;
      const tx = y + h / 2 + size * 0.36;
      if (!animated) {
        const color = key && t.keyFill === t.node ? t.keyText : key ? t.text : t.faint;
        f.add(f.rect(x, y, w, h, key ? t.sunken : t.node, t.rule));
        f.add(f.text(text, cx, tx, 14, color, { anchor: 'middle', box: [x, y, w, h] }));
      } else {
        const [fill, stroke, color] = key ? [t.keyFill, t.keyStroke, t.keyText] : [t.sunken, t.struct, t.text];
        const d = key ? 0.8 : 0.3;
        f.enter(f.rect(0, 0, w, h, fill, stroke, 1.4), cur, d, 'grow', [x, y]);
        f.enter(f.text(text, cx, tx, size, color, { weight: key ? 600 : null, anchor: 'middle', box: [x, y, w, h] }), cur + d - 0.1, 0.2);
        if (key) rings.push([x - 3, y - 3, w + 6, h + 6]);
        cur += d + 0.04;
      }
      x += w + gap;
    }
    for (const r of rings) f.enter(f.rect(...r, 'none', t.keyStroke, 1.6, 10), cur + 0.05, 0.3);
    y += h + 10;
    f.add(f.line(M, y, x - gap, y));
    y += 6;
  }
  if (s.axis) {
    y += 12;
    f.add(f.text(s.axis, M, y, 12, t.faint));
  }
  return y;
}

/** 事件落在时间轴上，游标走过时事件依次出现。span 标一段时长。 */
function timeline(f, s, y) {
  const { t } = f;
  const events = need(s, 'events', 'timeline');
  const ticks = s.ticks || [];
  atMostKeys(events, 2, 'timeline');
  if (events.length < 2 || events.length > 4) throw new SpecError('timeline 放 2–4 个事件，更多就拆成两张');
  const x0 = M + 4;
  const x1 = W - M - 4;
  const spanW = x1 - x0;
  const pos = (a) => x0 + a * spanW;
  const sized = events.map((e) => {
    const lines = balance(need(e, 'label', 'timeline.event'), 13, 150);
    if (lines.length > 3) throw new SpecError(`事件文字超过 3 行：${e.label}`);
    return { e, lines, cw: Math.max(...lines.map((ln) => estWidth(ln, 13))) + 20, ch: lines.length * 19 + 14 };
  });
  const isUp = (e) => (e.side || 'up') === 'up';
  const upH = Math.max(0, ...sized.filter((c) => isUp(c.e)).map((c) => c.ch));
  const downH = Math.max(0, ...sized.filter((c) => !isUp(c.e)).map((c) => c.ch));
  const { span } = s;
  const axisY = y + 14 + upH + (span ? 54 : 32);
  f.add(f.line(x0, axisY, x1, axisY, t.struct, 2));
  ticks.forEach((lab, i) => {
    const tx = x0 + (spanW * i) / Math.max(1, ticks.length - 1);
    f.add(f.line(tx, axisY - 4, tx, axisY + 4, t.struct, 1.4));
    const anchor = i === 0 ? 'start' : i === ticks.length - 1 ? 'end' : 'middle';
    f.add(f.text(lab, tx, axisY + 20, 12, t.faint, { anchor }));
  });
  const sweepFrom = BUILD_FROM + 0.1;
  const sweep = 2.4;
  for (const { e, lines, cw, ch } of sized) {
    const at = need(e, 'at', 'timeline.event');
    const px = pos(at);
    const hit = sweepFrom + at * sweep;
    const up = isUp(e);
    const key = Boolean(e.key);
    const cy = up && !span ? axisY - 32 - ch : up ? axisY - 54 - ch : axisY + 32;
    const cx = Math.min(Math.max(px - cw / 2, M), W - M - cw);
    const [fill, stroke, color] = key ? [t.keyFill, t.keyStroke, t.keyText] : [t.node, t.rule, t.text];
    let mk = f.rect(cx, cy, cw, ch, fill, stroke, key ? 1.4 : 1);
    lines.forEach((ln, j) => {
      mk += f.text(ln, cx + 10, cy + 20 + j * 19, 13, color, { weight: key ? 600 : null, box: [cx, cy, cw, ch] });
    });
    const [linkTop, linkBottom] = up ? [cy + ch, axisY] : [axisY, cy];
    mk = f.line(px, linkTop, px, linkBottom, key ? t.keyStroke : t.rule, 1) + mk;
    mk += `<circle cx="${fixed(px)}" cy="${fixed(axisY)}" r="${key ? 5 : 4}" fill="${key ? t.dot : t.struct}"/>`;
    f.enter(mk, hit, 0.35, 'rise');
  }
  if (span) {
    const sx0 = pos(span.from);
    const sx1 = pos(span.to);
    const by = axisY - 12;
    let mk = f.line(sx0, by, sx1, by, t.keyStroke, 1.6) + f.line(sx0, by - 4, sx0, by + 4, t.keyStroke, 1.6) + f.line(sx1, by - 4, sx1, by + 4, t.keyStroke, 1.6);
    mk += f.text(label(span.label, '时长'), (sx0 + sx1) / 2, by - 8, 15, t.keyText, { weight: 600, anchor: 'middle' });
    f.enter(mk, sweepFrom + span.to * sweep, 0.35);
  }
  f.tracer([[x0, axisY], [x1, axisY]], sweepFrom, sweep);
  return axisY + 28 + (downH ? downH + 16 : 0);
}

/** 层层垫高：自下而上出现，顶部可放入口标签。layers 按自底向上写。 */
function stack(f, s, y0) {
  const { t } = f;
  const layers = need(s, 'layers', 'stack');
  atMostKeys(layers, 1, 'stack');
  if (layers.length < 2 || layers.length > 5) throw new SpecError('stack 放 2–5 层');
  const h = 44;
  const gap = 8;
  let y = y0 + 14;
  const topLabel = s.top;
  const topY = y;
  if (topLabel) y += 42;
  const n = layers.length;
  let at = BUILD_FROM + 0.1;
  layers.forEach((layer, i) => {
    const ly = y + (n - 1 - i) * (h + gap);
    const key = Boolean(layer.key);
    const [fill, stroke, color] = key ? [t.keyFill, t.keyStroke, t.keyText] : [t.node, t.struct, t.text];
    const desc = layer.desc || '';
    const box = [M, ly, INNER, h];
    const lab = label(layer.label, '层');
    if (estWidth(lab, 14) + estWidth(desc, 13) + 38 > INNER) throw new SpecError(`层「${lab}」放不下：名称加说明要控制在一行内，缩短说明「${desc}」`);
    let mk = f.rect(M, ly, INNER, h, fill, stroke, 1.4);
    mk += f.text(lab, M + 12, ly + 27, 14, color, { weight: 600, box });
    if (desc) mk += f.text(desc, W - M - 12, ly + 27, 13, key && t.keyFill !== t.node ? t.keyText : t.muted, { anchor: 'end', box });
    f.enter(mk, at, 0.4, 'rise');
    at += 0.42;
  });
  if (topLabel) {
    const tw = estWidth(topLabel, 13) + 32;
    const tx = (W - tw) / 2;
    let mk = f.rect(tx, topY, tw, 30, t.node, t.keyStroke, 1.6, 15);
    mk += f.text(label(topLabel, '顶部标签'), W / 2, topY + 20, 14, t.keyText, { weight: 600, anchor: 'middle', box: [tx, topY, tw, 30] });
    f.enter(mk, at, 0.4, 'rise');
  }
  return y + n * h + (n - 1) * gap + 2;
}

function qbez(p0, c, p1, n = 14) {
  return Array.from({ length: n + 1 }, (_, i) => {
    const u = i / n;
    return [
      (1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * c[0] + u * u * p1[0],
      (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * c[1] + u * u * p1[1],
    ];
  });
}

/** 一个来源分发到多个去处。内容常驻，小圆点轮流走向每个去处（巡游）。 */
function route(f, s, y) {
  const { t } = f;
  const src = need(s, 'source', 'route');
  const targets = need(s, 'targets', 'route');
  atMostKeys(targets, 1, 'route');
  if (targets.length < 2 || targets.length > 4) throw new SpecError('route 放 2–4 个去处');
  f.mode = 'tour';
  const sw = Math.max(estWidth(src.label, 15) + 36, 136);
  const sh = src.sub ? 56 : 42;
  const sy = y + 16;
  const gap = 8;
  const tw = (INNER - gap * (targets.length - 1)) / targets.length;
  const ty = sy + sh + 74;
  const th = 62;
  const centers = targets.map((_, i) => M + tw / 2 + i * (tw + gap));
  const start = [W / 2, sy + sh];
  const curves = centers.map((cx) => {
    const end = [cx, ty];
    const ctrl = [cx, sy + sh + 18];
    f.add(`<path d="M${fixed(start[0])} ${fixed(start[1])}Q${fixed(ctrl[0])} ${fixed(ctrl[1])} ${fixed(end[0])} ${fixed(end[1])}" fill="none" stroke="${t.struct}" stroke-width="2" stroke-linecap="round"/>`);
    return qbez(start, ctrl, end);
  });
  const box = [(W - sw) / 2, sy, sw, sh];
  f.add(f.rect(...box, t.node, t.struct, 2));
  f.add(f.text(label(src.label, '来源'), W / 2, src.sub ? sy + 24 : sy + 27, 15, t.text, { weight: 600, anchor: 'middle', box }));
  if (src.sub) f.add(f.text(label(src.sub, '来源说明'), W / 2, sy + 43, 12, t.faint, { anchor: 'middle', box }));
  if (s.edge) f.add(f.text(label(s.edge, '连线说明'), W / 2 + 8, sy + sh + 50, 12, t.faint));
  const step = 1.5;
  targets.forEach((tgt, i) => {
    const cx = centers[i];
    const x = cx - tw / 2;
    const key = Boolean(tgt.key);
    const [fill, stroke, color] = key ? [t.keyFill, t.keyStroke, t.keyText] : [t.node, t.rule, t.text];
    const b = [x, ty, tw, th];
    f.add(f.rect(...b, fill, stroke, key ? 1.6 : 1));
    const size = key ? 15 : 14;
    wrap(label(tgt.label, '去处'), size, tw - 10).slice(0, 2).forEach((ln, j) => {
      f.add(f.text(ln, cx, ty + 26 + j * 18, size, color, { weight: 600, anchor: 'middle', box: b }));
    });
    if (tgt.sub) f.add(f.text(label(tgt.sub, '去处说明'), cx, ty + 46, 12, key && t.keyFill !== t.node ? t.keyText : t.faint, { anchor: 'middle', box: b }));
    const a0 = 0.3 + i * step;
    f.tracer(curves[i], a0, 0.7);
    f.glow(f.rect(x - 3, ty - 3, tw + 6, th + 6, 'none', t.keyStroke, 2, 10), [[a0 + 0.65, a0 + step - 0.15]]);
  });
  f.fixedDur = 0.5 + targets.length * step;
  return ty + th + 4;
}

/** 闭环：圆点绕一圈，节点依次亮起；走完一圈后中心数字变成结果。 */
function cycle(f, s, y) {
  const { t } = f;
  const nodes = need(s, 'nodes', 'cycle');
  if (nodes.length < 3 || nodes.length > 5) throw new SpecError('cycle 放 3–5 个节点');
  const center = s.center || {};
  const r = 90;
  const cx = W / 2;
  const cy = y + 30 + r;
  f.add(`<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${t.rule}" stroke-width="2"/>`);
  const step = 0.9;
  const lapFrom = BUILD_FROM - 0.4;
  const n = nodes.length;
  let freeL = M; // 中心数字可用的横向空间，由左右节点挤出来
  let freeR = W - M;
  nodes.forEach((nodeLabel, k) => {
    const a = -Math.PI / 2 + (2 * Math.PI * k) / n;
    const nx = cx + r * Math.cos(a);
    const ny = cy + r * Math.sin(a);
    const lab = label(nodeLabel, '节点');
    const pw = estWidth(lab, 14) + 24;
    const ph = 34;
    const px = Math.min(Math.max(nx - pw / 2, M - 8), W - M + 8 - pw);
    if (Math.abs(ny - cy) < 50) {
      if (nx < cx) freeL = Math.max(freeL, px + pw);
      else freeR = Math.min(freeR, px);
    }
    let mk = f.rect(px, ny - ph / 2, pw, ph, t.node, t.struct, 1.4, 17);
    mk += f.text(lab, px + pw / 2, ny + 5, 14, t.text, { weight: 600, anchor: 'middle', box: [px, ny - ph / 2, pw, ph] });
    const hit = lapFrom + k * step;
    f.add(mk);
    f.glow(f.rect(px - 3, ny - ph / 2 - 3, pw + 6, ph + 6, 'none', t.keyStroke, 2, 20), [[hit, hit + 0.5]]);
  });
  const pts = Array.from({ length: 49 }, (_, i) => {
    const a = -Math.PI / 2 + (2 * Math.PI * i) / 48;
    return [cx + r * Math.cos(a), cy + r * Math.sin(a)];
  });
  f.tracer(pts, lapFrom, step * n);
  const swapAt = lapFrom + step * n;
  if (Object.keys(center).length) {
    if (center.label) f.add(f.text(center.label, cx, cy - 26, 13, t.muted, { anchor: 'middle' }));
    const to = String(need(center, 'to', 'cycle.center'));
    const hasFrom = center.from !== undefined && center.from !== null;
    const room = Math.min(cx - freeL, freeR - cx) * 2 - 16;
    const widest = Math.max(...[to, hasFrom ? String(center.from) : to].map((v) => f.displayWidth(v, 40)));
    // <text> 的盒子比字形路径高，字号上限收一点，才不和上下两行小字碰。
    const big = Math.max(20, Math.trunc(Math.min(f.usesGlyphs(to) ? 40 : 34, (40 * room) / widest)));
    if (hasFrom) {
      f.glow(f.display(String(center.from), cx, cy + 16, big, t.faint), [[RESET_TO, swapAt - 0.15]]);
      f.swap(f.display(to, cx, cy + 16, big, t.keyFill === t.node ? t.keyStroke : t.text),
        [[0, 1, LIN], [RESET_FROM, 1, LIN], [RESET_TO, 0, EASE], [swapAt, 0, LIN], [swapAt + 0.3, 1, EASE]]);
    } else {
      f.add(f.display(to, cx, cy + 16, big, t.text));
    }
    if (center.note) f.add(f.text(center.note, cx, cy + 38, 13, t.muted, { anchor: 'middle' }));
  }
  return cy + r + 24;
}

/** 指标对比：每行一个对象，每列一个指标。条形按序生长，key 行用强调色并圈出。 */
function bars(f, s, y0) {
  const { t } = f;
  const cols = need(s, 'columns', 'bars');
  const rows = need(s, 'rows', 'bars');
  atMostKeys(rows, 1, 'bars');
  if (cols.length < 1 || cols.length > 2 || rows.length < 2 || rows.length > 5) throw new SpecError('bars 放 1–2 列、2–5 行');
  let y = y0 + 10;
  const labelW = Math.max(...rows.map((r) => estWidth(r.label, 13))) + 6;
  const gap = 14;
  const cw = (INNER - labelW - 8 - gap * (cols.length - 1)) / cols.length;
  const xs = cols.map((_, i) => M + labelW + 8 + i * (cw + gap));
  cols.forEach((c, i) => f.add(f.text(label(c.label, '列名'), xs[i], y + 12, 12, t.faint)));
  y += 24;
  let at = BUILD_FROM + 0.1;
  const rh = 58;
  const rings = [];
  for (const row of rows) {
    const key = Boolean(row.key);
    const accentRow = key && t.keyFill === t.node;
    f.add(f.text(label(row.label, '行名'), M, y + 28, 13, accentRow ? t.keyText : t.text, { weight: 600 }));
    cols.forEach((c, i) => {
      const v = row.values[i];
      const frac = Number(v) / Number(c.max);
      if (!(frac > 0 && frac <= 1)) throw new SpecError(`${row.label} 的值 ${v} 超出 max=${c.max}`);
      f.add(f.text(`${c.prefix || ''}${v}${c.suffix || ''}`, xs[i], y + 29, 19, accentRow ? t.keyText : t.text, { weight: 600 }));
      const bw = Math.max(cw * frac, 6);
      f.add(f.rect(xs[i], y + 37, cw, 6, t.sunken, null, 1, 3));
      f.enter(f.rect(0, 0, bw, 6, accentRow ? t.keyStroke : t.struct, null, 1, 3), at, 0.5, 'grow', [xs[i], y + 37]);
      at += 0.12;
    });
    if (key) rings.push(f.rect(M - 6, y + 6, INNER + 12, rh - 6, 'none', t.keyStroke, 1.6, 10));
    at += 0.2;
    y += rh;
  }
  for (const ring of rings) f.enter(ring, at + 0.2, 0.3);
  return y + 2;
}

export const BUILDERS = { sequence, timeline, stack, route, cycle, bars };

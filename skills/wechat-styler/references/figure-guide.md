# 动态图解指南

`:::figure` 把一个判断画成内联 SMIL 动态 SVG。什么时候用图解、什么时候用组件，以及和组件怎么混用，见 `component-guide.md` 的「选图解还是组件」。

三条原则贯穿全程：

- **一图一判断**：`title` 和 `conclusion` 是判断，图解是证据，读者不读正文也能拿到结论。
- **动画在论证**：只有时间、顺序或变化本身就是论点时才动。
- **基态完整**：删掉全部动画，画面就是完整的终态。动画失效的平台只会少了动效。

## 写法

和 `:::flow` 同级，独占一行、前后空行，正文是 YAML。图上的每个数字和事实都要在正文里有出处。

```markdown
:::figure
id: why-layer
type: stack
kicker: 团队撞的是同一批墙
title: 从会用到做精，差一层
conclusion: What 和 How 都有了，缺的是 Why
layers:
  - {label: What, desc: 知道 Skill 是什么}
  - {label: How, desc: 创建、安装、调用都会}
  - {label: Why, desc: 怎么被找到、被加载, key: true}
:::
```

通用字段：`id`（字母、数字、下划线、连字符，一篇内唯一）、`type`、`title`（结论，不超过 13 个汉字）、`conclusion`（读者该带走的那句话，不超过两行，一行约 21 字）、`kicker`（可选眉题）。节点文字不超过 12 字。`key` 是强调色，只给这张图要读者看的那一处。

完成标准：`title` 换成正文里的话也说得通，去掉图解后标题和结论句仍然讲得清判断。

## 选结构

| 要讲的关系 | type | 动法 |
|---|---|---|
| 前后对比、一串步骤、哪一段没变 | `sequence` | 块按序生长，key 块长得慢 |
| 事情发生的先后、隔了多久 | `timeline` | 圆点走过时间轴，事件依次出现 |
| 层层依赖、底层撑上层 | `stack` | 自下而上垫高 |
| 一分多、同一入口换去处 | `route` | 内容常驻，圆点轮流走向每个去处 |
| 闭环、前后数字变化 | `cycle` | 圆点绕一圈，节点依次亮起，中心数字切换 |
| 多个对象比指标 | `bars` | 条形按序生长 |

`route` 的内容始终可见，是最稳妥的动法：读者在哪个时刻看到都完整。

### 各结构字段

- **sequence**：`rows`，每行 `label`、`segments`，可加 `static: true` 做不动的参照行。`segments`：`label`、`len`（比例）、`key`。`axis` 可选，写在最后一行下方。块宽按 `len` 成比例，读者会读成时长或分量；只是步骤没有比例关系时，所有 `len` 写相同的值。
- **timeline**：`events` 2–4 个：`at`（0–1 的位置）、`label`、`side`（`up`/`down`）、`key`。`ticks` 刻度文字可选。`span` 可选：`from`、`to`、`label`。相邻事件放在轴的两侧。
- **stack**：`layers` 2–5 层，**自底向上写**：`label`、`desc`、`key`。名称加说明要放进一行。`top` 可选，是顶部入口标签。
- **route**：`source`：`label`、`sub`。`targets` 2–4 个：`label`、`sub`、`key`。`edge` 可选，是连线说明。
- **cycle**：`nodes` 3–5 个，从顶部顺时针。`center` 可选：`label`、`from`、`to`、`note`。写了 `from` 才会切换数字；放不下时数字自动缩小。
- **bars**：`columns` 1–2 个：`label`、`max`、`prefix`、`suffix`。`rows` 2–5 行：`label`、`values`（顺序对应列）、`key`。值必须大于 0 且不超过 `max`。

## 生成与检查

```bash
node scripts/convert.mjs article.md --components --figure-png <目录> --output article_wechat.html
```

`--figure-png` 写出 `<id>.svg`、`<id>.png`、`contact.png`、`report.json`。不带它也会在有浏览器时跑全部检查，只是不落文件；没有浏览器时照常出稿，并提示渲染检查未执行。浏览器按 `CHROME_EXECUTABLE` 等 `mobile-visual-qa.mjs` 的同一顺序查找。

任何一张不过都不生成 HTML，错误行形如 `图解 <id>：<原因>`，退出码 1：

- **规格放不下**：消息会说哪里放不下，缩短文字或拆图。
- **结构白名单**：`tag-not-allowed`、`anim-attr-not-allowed`、`id-attribute`、`font-too-small`（手机下限 12px）、`too-large`（单张 30KB）。
- **渲染实测**：`text-off-canvas`、`text-out-of-box`、`text-on-line`、`text-overlap`、`not-animated`、`hold-too-short`（定格不足 2 秒，也会拦下基态隐藏语义内容）、`tour-content-moves`。
- **对比度**：`contrast:<前景>/<背景>=<比值>`，低于 4.5 报错，不自动改色。

然后打开 `contact.png` 目检，每行是三个动画中途帧和最右的静态图。完成标准：不读正文判断成立，中途帧看得出动的就是论点，强调色落在要看的那一处，静态图和定格时一样完整。

## 主题

颜色从主题 YAML 读：`bg`=`background_color`，`node`=`surface_color`，`rule`=`divider_color`，`text`=`text_color`，`muted`=`secondary_color`，`faint`=`tertiary_color`，`struct`=`accent_secondary`，`keyStroke` 和 `dot`=`accent_color`。`sunken` 由背景向分隔线混 80% 得到；`keyText` 取 `primary_text`，主题没有这个键时取 `accent_color`。

目前只有 `zhijian` 通过对比度检查。其余 7 个主题的三级文字色给正文说明用，达不到图解 12px 小字的要求：

| 主题 | 不达标 |
|---|---|
| `kami`、`magazine-forest`、`magazine-indigo`、`magazine-ink` | `faint/bg` |
| `elegant`、`minimal`、`modern` | `muted/bg`、`faint/bg` |

用这些主题写 `:::figure` 会报错，按需去掉围栏或换 `zhijian`。

## 字形

`zhijian` 主题的标题和中心数字转路径。字体按 `--figure-font`、环境变量 `WECHAT_STYLER_FIGURE_FONT`、常见字体目录的顺序查找 `LXGWWenKai-Medium.ttf`。找不到或其他主题时退回 `<text>` 并使用主题的 `heading_font`，同时在报告里写明。所有 `<text>` 都带 `<tspan leaf="">`。

有字体时，所有 `<text>` 里连续的拉丁段（英文、数字、半角符号）都转字形路径，中文段留 `<text>`，避开 iOS 微信正式阅读器漏画混排英文的问题（`svg-animation-design.md` 踩坑 14）。无字体时拉丁段留在 `<text>` 里，报告标出风险，这种稿子发布前要换有字体的环境重新生成。

## 默认模式

不带 `--components` 时，围栏降级成“标题加结论句”的引用，不暴露标记。YAML 写坏或缺 `title`、`conclusion` 同样报错。

## 验证状况

- 已验证（2026-11-02，草稿重新加载后回读）：内联 SVG、SMIL 循环动画（44/44，含 `keyTimes`、`keySplines`、`repeatCount`）、`text-anchor`、`font-family`、`width:100%`、`opacity="0"` 都保留。一台手机预览，一篇 5 张图都循环，字号和图宽没有问题。
- **未验证**：正式读者端未核对。拉丁段转路径后的版本未在 iOS 正式阅读器看过，安卓未测，5 张以上未测。首篇发布后要专门看含英文的图，等待 10 秒以上确认不漏字、动画在播。

## 扩展

- **结构**：在 `scripts/figures/primitives.mjs` 加函数并登记到 `BUILDERS`，在 `tests/figures.test.mjs` 覆盖。
- **标签白名单**：`scripts/figures/gates.mjs` 只放行已验证的标签和动画属性。新增前先存一篇草稿，重新加载后回读，确认微信保留再放开。
- 每道检查都配一张坏图验证它能亮红灯，新增检查也要配。

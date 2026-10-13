# Zhijian 主题视觉基线

`theme_revision: v3-paper-ink-2026-10`

这份基线记录智见AI 公众号主题的审美取舍和可执行样式锁。v3 叙事是「纸 · 墨 · 赭 · 字 + 落地线」：标题用判断字（楷体），正文与界面用屏幕字（黑体），颜色只取 v3 调色板，文末用一条短落地线收尾。

## 版本对照

| 维度 | editorial-weighted-2026-07 | 当前基线 v3-paper-ink-2026-10 |
|---|---|---|
| H1 / H2 / H3 | 楷体标题 22/500、18/600 | 霞鹜文楷判断字栈，H2 22/500、H3 18/500，标题统一 500 |
| 正文与列表 | 宋体 15/450/1.68 | 屏幕字（思源黑体栈）15/450/1.68 |
| 图注与元信息 | 黑体 13 | 屏幕字 13，与正文同一字栈 |
| 代码 | Menlo 优先 | JetBrains Mono 优先，近黑 `#141413` 底 |
| 引用文字 | v2 灰蓝（已不在调色板） | 次级文字 `#504E49` |
| 人物强调色 `human_accent` | v2 浅陶（已不在调色板） | 赭石 `#B85235` |
| 文末 | 无 | 短落地线 + 赭石圆点 |

为什么正文改黑体：Android 普遍没有宋体，宋体栈在读者手机上会静默退化成系统黑体，排版效果不可控。v3 把公众号正文直接定为屏幕字。

## 样式锁

- 判断字栈（H1 / H2 / H3、引用开引号）：`'LXGW WenKai','LXGW WenKai Screen','Source Han Serif SC Heavy','Source Han Serif SC VF','Source Han Serif SC','Noto Serif CJK SC',serif`。霞鹜文楷只有 300 / 400 / 500 三档，没有 Bold，标题一律 500（主题键 `heading_weight: 500`），不写 600 / 700 / 900，避免浏览器伪粗。
- H2：22px / 500 / 1.28，4px 赭石 `#B85235` 左线。
- H3：18px / 500 / 1.32，墨蓝 `#1B365D`（公众号特例，允许 18px 判断字）。
- 屏幕字栈（正文、列表、图注、UI）：`'Source Han Sans SC','Noto Sans SC','PingFang SC','Microsoft YaHei','Noto Sans CJK SC',sans-serif`。
- 正文与列表：15px / 450 / 1.68，近黑 `#141413`。
- 图注与元信息：13px / 1.4，弱文字 `#6B6A64`。
- 代码：`'JetBrains Mono',Consolas,'Source Han Sans SC',monospace`；代码块近黑 `#141413` 底、纸色字。
- 普通加粗：赭石文字色 `#A04A2E`；链接：墨蓝 `#1B365D`。
- 引用：墨蓝淡底 `#EEF2F7`，文字 `#504E49`，无左线，开引号与首行同段对齐。
- 文末结尾标记（`end_mark: landing`）：正文最后一段之后、话题标签与结尾引导图之前，居左放一条墨蓝 2px、宽 64px、终点切线水平的短落地线，线终点后 7px（3.5 × 线宽）为直径 10px 的赭石圆点，圆心在线轴上（线宽:点径 = 1:5）。以内联静态 SVG 输出，带 `data-wechat-block="end-mark"`，无动画。全文只此一个赭石圆点装饰。
- 主题所有色值限定在 v3 调色板：`#F5F4ED` `#FAF9F5` `#1B365D` `#B85235` `#141413` `#E5E3D8` `#504E49` `#6B6A64` `#A04A2E` `#EEF2F7`，由 `tests/output-contract.test.mjs` 锁定。

## 字体降级（公众号不嵌字体）

公众号页面不能嵌入字体文件，主题只声明字体名称，读者手机按栈降级：

- 标题：装了霞鹜文楷才显示楷体；多数读者手机没有，会按栈落到思源宋体 / Noto Serif CJK（部分 Android 自带），再落到系统 `serif`；iOS 与多数 Android 最终显示系统宋体或黑体。层级靠字号、500 字重、赭石左线和墨蓝色保持，不依赖楷体本身。
- 正文：iOS 落到 PingFang SC，Android 落到系统 Noto Sans CJK / 厂商黑体，Windows 落到 Microsoft YaHei。
- 验收同时检查声明的字体栈（自动回归）与真机实际回退结果（人工）。本地截图只代表装有霞鹜文楷的开发机，不能代替真机降级检查。

## 视觉证据

- 历史版本实页对照：`../assets/zhijian-theme-version-comparison-2026-07.jpg`（v2 时期，仅作历史参照）
- 当前 390px 移动端基线：`../assets/zhijian-theme-mobile-baseline.png`（开发机，标题为霞鹜文楷，正文由 PingFang SC 承担）
- 可重复输入：`tests/fixtures/zhijian-visual-baseline.md`

生成并验证：

```bash
node scripts/convert.mjs tests/fixtures/zhijian-visual-baseline.md \
  --theme zhijian --no-open --output /tmp/zhijian-visual-baseline.html

npm run qa:mobile -- /tmp/zhijian-visual-baseline.html \
  --expect-zhijian \
  --screenshot assets/zhijian-theme-mobile-baseline.png
```

`--expect-zhijian` 会检查 H2 声明霞鹜文楷栈、H3 为 18px / 500、正文声明屏幕字栈且为 15px / 450 / 1.68，以及文末落地线存在。任何主题调整必须同时更新样式锁、自动回归和移动端基线图；字体变更还要在真实 iOS 与 Android 手机上核对回退字体。

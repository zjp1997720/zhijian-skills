---
name: html-express
description: 把信息密集的内容做成结构化、可读的自包含 HTML——调研报告、对比矩阵、清单、数据看板、决策页。当 Agent 要输出大段信息、对比、指标、时间线，或用户说「做成网页/可视化报告/HTML 报告」时触发。产物是单个可双击打开的 .html 文件。郑重 PDF/简历/PPT/落地页交付请用 kami；视频/动画用 hyperframes；上线部署不在本 skill 范围。
---

# html-express

Agent 的日常 HTML 表达层。当信息密度高、读者要费力扫读时，用**单个自包含 HTML** 代替 Markdown。

> 灵感：Anthropic《Using Claude Code: The unreasonable effectiveness of HTML》—— HTML 是 Agent 最好的表达介质。

## 为什么是 HTML 不是 Markdown

- **信息密度**：HTML 能做结构、对比、交互，Markdown 只能堆文本
- **可读性**：表格、指标、时间线用 Markdown 是灾难，用 HTML 是享受
- **自包含**：一个文件，双击即开，零运行环境，可分享
- **判断准则**：读者要「费力扫读」的，升 HTML；一句话能说清的，留 Markdown

## 路由：该不该用 html-express

| 信号 | 去哪 |
|---|---|
| 要 PDF / 简历 / PPT / 落地页 / 白皮书 | → `kami` |
| 要视频 / 动画 / 字幕 / 转场 | → `hyperframes` |
| 要把大段信息整理成一页可读的网页 | → **本 skill** |
| 一句话能说清的结论 | → 直接回 Markdown |

## 组件清单（10 个）

| 组件 | 适合什么信息 |
|---|---|
| `metric-card` | 关键指标、数据看点（2-4 个并排） |
| `comparison-table` | 多方案横向对比 |
| `data-table` | 结构化数据罗列（非对比） |
| `timeline` | 时间线、里程碑、路线图 |
| `checklist` | 步骤、SOP、检查项 |
| `quote-card` | 判断、原话、金句 |
| `code-block` | 代码、命令、配置 |
| `details` | 长内容折叠（零 JS） |
| `badge` | 状态标签（成功/警示/中性） |
| `columns` | 多视角并置、优劣势对照 |

源码在 `assets/components/`。骨架在 `assets/skeleton.html`，token 在 `assets/tokens.css`。10 个组件的完整效果见 `assets/demo-all.html`（双击打开）。

## 组装流程

1. **识别信息形态** → 对比？清单？指标？时间线？引用？决策？
2. **选组件** → 从清单挑 2-5 个最配的，不强求全用
3. **套骨架** → 复制 `assets/skeleton.html`，把 `tokens.css` 完整内容粘进顶部 `<style>`（替换 `@import`）
4. **填内容** → 数据 > 形容词；不留占位符；缺数据标 `[数据待补：说明]`
5. **产出** → 单个 `.html`，双击即开

### 信息形态 → 组件 路由表

| 信息形态 | 推荐组件 |
|---|---|
| 多方案横向对比 | comparison-table + badge |
| 关键指标 / 数据看点 | metric-card（2-4 个并排） |
| 时间线 / 里程碑 / 路线图 | timeline |
| 步骤 / SOP / 清单 | checklist |
| 大段判断 / 原话 / 金句 | quote-card |
| 代码 / 命令 / 配置 | code-block |
| 长内容折叠 | details |
| 结构化数据罗列 | data-table |
| 多视角并置 | columns |

## 视觉契约（绑定 智见AI DESIGN.md）

token 已在 `assets/tokens.css` 抽好，组件一律引用变量，**不要写死颜色/字号字面值**。

- 背景永远暖纸 `#F5F4ED`，不纯白
- 主行动色暖陶 `#B85235`，结构色墨蓝 `#1B365D`
- 正文链接用 `--accent-text`（`#A04A2E`，对比度安全）
- **`--human`（`#C96442`）只做装饰或 ≥22px 大字，不可做正文小字**（对比度仅 3.7:1）
- 字体靠 fallback，不嵌入字体文件

## 禁止（Agent 最容易犯的）

- ❌ 占位符残留（`[填这里]`、Lorem、TBD）
- ❌ 编造数据、统计；缺数据标 `[数据待补：说明]`
- ❌ 弱表格——该用对比矩阵却堆成清单
- ❌ 渐变、玻璃拟态、霓虹、强阴影（DESIGN.md 明令禁止）
- ❌ 做成营销落地页（那是 kami 的事）

## 参考

- 品牌真源：`04_系统/品牌系统/DESIGN.md`
- 组件速览：`assets/demo-all.html`（双击打开看全套效果）

---
name: wechat-styler
slug: wechat-styler
displayName: WeChat Styler
version: 1.8.0
description: 将 Markdown 文章转换为微信公众号可用的内联样式 HTML，支持多主题切换、结构化组件和 SVG 开场动画。用于公众号排版、文章 HTML 生成、替代不稳定外部排版服务。默认纯净排版,加 --components 启用 Agent 智能改写(组件+开场动画)。
summary: Markdown → 公众号 HTML，多主题 + 组件 + SVG 开场动画。
tags: [wechat, markdown, html, publishing, design]
license: MIT
---

# WeChat Styler - 公众号排版工具

将 Markdown 文章转换为优雅的公众号 HTML，支持多主题切换、结构化组件和 SVG 开场动画。

![WeChat Styler 左右并列效果预览](https://obsidian-1344509300.cos.ap-beijing.myqcloud.com/obsidian/img/wechat-styler-before-after-recent.png)

## 使用方式

```bash
# 默认模式（纯净排版，无组件无动画）
/wechat-styler path/to/article.md
/wechat-styler path/to/article.md --theme kami

# 组件模式（Agent 智能改写 + 开场动画 + 8 种结构化表达）
/wechat-styler path/to/article.md --components

# 批量转换
/wechat-styler "articles/*.md" --theme kami

# 输出到指定路径
/wechat-styler path/to/article.md --output path/to/output.html
```

**两种模式：**
- **默认模式**：直接转换，克制排版，无组件无动画。90% 场景用这个。
- **组件模式（`--components`）**：Agent 分析文章结构，智能改写 Markdown，自动加开场动画。生成前向用户确认。

## 可用主题

| 主题 | 命令 | 风格 | 适用场景 |
|------|------|------|----------|
| zhijian（默认） | `--theme zhijian` | 暖纸感 × 顾问可信度 | 智见AI 品牌内容 |
| kami | `--theme kami` | 纸感编辑排版 | 深度文章、商业分析 |
| magazine-ink | `--theme magazine-ink` | 墨水经典杂志 | 通用杂志内页 |
| magazine-indigo | `--theme magazine-indigo` | 靛蓝研究风 | 技术研究、深度调研 |
| magazine-forest | `--theme magazine-forest` | 森林田野笔记 | 非虚构、自然叙事 |
| elegant | `--theme elegant` | 优雅复古 | 商业案例、知识分享 |
| modern | `--theme modern` | 现代简约 | 科技产品、教程 |
| minimal | `--theme minimal` | 极简主义 | 哲学思考、个人随笔 |

主题详情、YAML 参数、扩展指南见 `references/theme-guide.md`。

## 工作流程

### 默认模式

用户只给文件路径和主题，Agent 直接调用 `convert.mjs` 转换，不做 Markdown 改写。

### 组件模式（`--components`）

Agent **不直接调用 convert**，先执行 5 步智能改写流程：

**第 1 步：分析文章结构**

读完整篇 Markdown，识别适合用组件呈现的内容（表格→对比卡片、流程→步骤块、金句→金句块等）。只改写确实适合的内容，一篇文章组件数量控制在 3-6 个。详见 `references/component-guide.md`。

**⛔ 防重复硬规则**：金句块/提示块/警告块的核心原则是**替换原文，不是追加**。如果原文已经把同样的意思说清楚了，不要在原文后面追加组件重复一遍。正确做法是删掉原文的概括句，只保留视觉权重更高的组件；或者原文已完整表达时不加组件。生成前必须全文扫描确认无重复。

**⛔ 围栏格式硬规则**：`:::compare` / `:::flow` / `:::timeline` 必须独占一行，前后留空行。紧跟正文的 `:::compare` 不会被解析，会以原始 markdown 显示。

**第 2 步：提取开场动画参数**

从文章内容推断标题（frontmatter.title）、副标题（核心观点一句话）、标签（3个以内关键词），并选择模板（见下）。

**第 3 步：向用户确认**

```
组件改写计划:
  • 开场动画(typewriter): 标题「初识 WorkBuddy」/ 副标题「...」/ 标签: ...
  • 「专家对比表」→ 对比卡片
  • 「Ask/Plan/Craft」→ 对比卡片
  • 「用好 WorkBuddy 的核心」→ 金句块
确认后开始生成?
```

**第 4 步：生成前检查（必做）**

调用 convert 之前，必须对改写后的 Markdown 逐条检查 `references/component-guide.md` 的「生成前检查清单」：
- 图片插入位置是否在完整段落之后（不在句子中间）
- 金句块/提示块/警告块是否与原文重复
- `:::compare` / `:::flow` 围栏是否独占一行
- 矩阵对比是否被误转成 compare
- 开场动画标题长度是否超出 viewBox

**第 5 步：生成**

在内存中改写 Markdown（不改原文件），然后调用 convert：

```bash
node scripts/convert.mjs /tmp/rewritten.md --theme zhijian --components \
  --cover --cover-template typewriter \
  --cover-title "..." --cover-subtitle "..." --cover-tags "..."
```

`--components` 启用时自动包含 `--cover`（开场动画）。

## SVG 开场动画

`--components` 模式自动包含开场动画。SVG SMIL 动画只在首次加载时播放，因此只做开场，其他位置用静态组件。

### 5 个模板

| 模板 | 参数值 | 气质 | 适配 |
|------|--------|------|------|
| 墨韵开篇 | `ink-wash` (默认) | 仪式感·墨点晕染 | 方法论、品牌、课程 |
| 打字机流 | `typewriter` | 极客感·逐字打字·光标跟随 | 技术教程、工具介绍 |
| 画卷展开 | `scroll-painting` | 叙事感·双横线·渐入佳境 | 案例、复盘、故事 |
| 聚焦聚光灯 | `spotlight` | 判断感·聚光·标题缩放 | 观点、评测、趋势 |
| 极简白描 | `minimal-sketch` | 克制·留白·呼吸圆点 | 随笔、思考、感悟 |

### Agent 模板选择逻辑

- 「教程/工具/技术/CLI/Agent/开发」→ **typewriter**
- 「案例/复盘/故事/落地/实战记录」→ **scroll-painting**
- 「判断/观点/趋势/评测/分析」→ **spotlight**
- 「随笔/思考/感悟/月度/年度」→ **minimal-sketch**
- 默认/品牌课程/方法论 → **ink-wash**

Agent 选定模板后，在确认环节明确告知用户："我选了 X 模板，因为文章有 Y 特征，你可以换。" 不确定时默认 ink-wash。

模板设计原则和踩坑清单见 `references/svg-animation-design.md`。

## 注入微信编辑器

微信编辑器的粘贴过滤器会剥离 `<animate>` 标签。用 opencli 直接操作 DOM 绕过：

```bash
export OPENCLI_PROFILE=4nwbtdn6
export WX_EDITOR_URL="https://mp.weixin.qq.com/..."
node scripts/inject-to-wechat.mjs article_wechat.html
```

稳定发布模式：

```bash
node scripts/inject-to-wechat.mjs article_wechat.html \
  --reuse-current \
  --title "公众号标题" \
  --summary "转发摘要" \
  --sync-cover-from-body \
  --save-draft \
  --report /tmp/wechat-publish-report.json
```

注入器会轮询定位正文编辑区，避开标题 ProseMirror；同步标题、摘要，并可把正文第一张 2.35:1 图片设为封面；自动压缩超过 2MB 的远程图片；等待微信完成图片转存；保存后验证 `appmsgid`、SVG、动画、图片和正文首尾。使用 `--verify-only --reuse-current` 可以只读检查已经打开的草稿。

详细流程见 `references/opencli-injection.md`。

## 组件拓展层

`--components` 模式启用 8 种结构化表达。默认模式下组件语法优雅降级成普通 markdown。

| 组件 | 语法 | 适用场景 |
|------|------|----------|
| 金句块 | `> **核心观点**` | 文章核心论点 |
| 轻量标记 | `==关键词==` | 正文关键词强调（底部细线） |
| 提示块 | `> [!NOTE] 内容` | 补充说明、技术旁注 |
| 警告块 | `> [!WARNING] 内容` | 注意事项、踩坑提醒 |
| 步骤序号 | `1. [step] 动作` | 操作流程、动作清单 |
| 流程卡片 | `:::flow` 围栏 | 阶段流程 |
| 对比卡片 | `:::compare` 围栏 | 方案 A vs B vs C |
| 时间线 | `:::timeline` 围栏 | 演进历程、项目复盘 |

完整语法示例和设计原则见 `references/component-guide.md`。

**设计原则：** 克制优于装饰 · 颜色从主题取 · 横向卡片 flex:1 等分优先 overflow 兜底 · 矩阵对比保留 table · 卡片内容要短 · 默认沉默

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--theme` | 主题名称 | `zhijian` |
| `--font-size` | 正文字号（px） | 主题默认 |
| `--line-height` | 行高 | 主题默认 |
| `--accent-color` | 强调色 | 主题默认 |
| `--background-color` | 背景色（solid hex） | 主题默认 |
| `--max-width` | 内容最大宽度（px） | `640` |
| `--output` | 输出文件路径 | `<input>_wechat.html` |
| `--components` | 启用组件模式（智能改写+动画+组件） | `false` |
| `--cover` | 生成开场动画（`--components` 自动包含） | `false` |
| `--cover-template` | 开场动画模板 | `ink-wash` |
| `--cover-title` | 开场动画主标题 | 从 frontmatter.title 取 |
| `--cover-subtitle` | 开场动画副标题 | 从 frontmatter.summary 取 |
| `--cover-tags` | 开场动画标签(逗号分隔) | 无 |

### 字号建议

手机端公众号文字显示比电脑端大，主题默认字号在电脑端看着合适，手机端会显挤。建议：

- **长文/信息密度高的文章**：`--font-size 15`（比默认 17 小一号，手机端更舒展）
- **短文/情感类文章**：用主题默认字号即可
- **极简主题 minimal**：默认就偏小，一般不需要调

## 占位符机制

写作时图床还没准备好？在 Markdown 里写占位符，convert 会渲染成居中虚线灰框：

```markdown
【插入:文章开头的视频截图】
```

只支持独占一行的 `【插入:xxx】`（全角方括号）。

## 输出规则

- 输入：`path/to/article.md` → 输出：`path/to/article_wechat.html`
- 完整 HTML，内联样式，可直接复制到公众号编辑器
- convert 后自动运行 `validate.mjs` 软门校验（不阻断，打印报告）

兼容硬规则详情见 `references/wechat-compatibility.md`。

## References

| 文件 | 内容 |
|------|------|
| `references/theme-guide.md` | 8 主题完整配置、Renderer Presets、扩展指南、技术实现 |
| `references/component-guide.md` | 6 组件完整语法示例、设计原则、智能改写规则 |
| `references/svg-animation-design.md` | 5 模板设计原则、技术约束、11 条踩坑清单 |
| `references/wechat-compatibility.md` | 公众号兼容硬规则（ERROR/WARN 详情） |
| `references/opencli-injection.md` | opencli 注入流程、前置条件、封装踩坑 |

---

**版本：** 1.8.0 · **作者：** 大鹏

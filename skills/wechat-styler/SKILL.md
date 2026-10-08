---
name: wechat-styler
slug: wechat-styler
displayName: WeChat Styler
version: 1.14.0
description: "将Markdown排版为公众号HTML；组件、动画及已授权的编辑器注入按需启用。"
summary: Markdown → 可评审的公众号 HTML，可选组件、动画与草稿注入。
tags:
  - wechat
  - markdown
  - html
  - publishing
  - design
license: MIT
disable-model-invocation: true
---

# WeChat Styler

把已定稿或已授权排版的 Markdown 转成可评审公众号 HTML。默认保留正文并自动加入智见品牌首尾 GIF；组件改写、主题开场动画和微信编辑器注入按需加载。

![WeChat Styler 左右并列效果预览](https://obsidian-1344509300.cos.ap-beijing.myqcloud.com/obsidian/img/wechat-styler-before-after-recent.png)

## 分支路由

先选分支，再读取对应 reference。默认转换无需读取组件、动画或编辑器细则。

| 用户需求 | 执行分支 | 读取 |
|---|---|---|
| 公众号排版、HTML、换主题、批量转换 | 默认转换 | `references/conversion-workflow.md`；主题需要判断时再读 `references/theme-guide.md` |
| 结构化组件、丰富排版、开场动画 | 组件与动画 | 默认转换 reference + `references/component-guide.md` + `references/svg-animation-design.md` |
| 注入公众号、保存草稿、核验编辑器中的成品 | 编辑器注入 | `references/opencli-injection.md` + `references/wechat-compatibility.md` |
| 修改 Zhijian 主题视觉基线 | 主题维护 | `references/zhijian-theme-baseline.md` + `references/theme-guide.md` |

任务中出现新需求时只补读新增分支。

## 授权与能力边界

- 用户已授权排版且正文、主题明确时，简报选择并直接生成 HTML 预览，不重复确认。只有缺口会改变原意、关键表达方向或交付格式且无法推断时才问；先完成不受影响的部分。
- 预览生成、编辑器写入和草稿保存是不同动作。沿用会话中已有授权；没有编辑器写入或保存授权时，只交付 HTML 与核验结果。
- 某后端因能力缺失而不可用时，可以选择已授权且满足注入验收条件的后端。遇到明确的权限拒绝或安全策略拒绝时必须停止并报告，不能换工具、CDP、浏览器自动化或间接脚本绕过。
- 不修改输入 Markdown；组件分支在内存或临时文件中改写。

## 工作流

### 1. 默认转换

默认保留正文、不增加正文组件；转换器自动加入品牌开头与结尾 GIF。开场互斥、关闭方式与素材维护见 `references/brand-cta.md`；每次转换读取该规则。按 `references/conversion-workflow.md` 选择主题与参数、运行转换并完成最小 QA。用户只给文件路径时默认使用 `zhijian`。

### 2. 组件与动画

组件分支先通过严格段落密度门，再按 `component-density` 在内存中改写 Markdown。默认 `standard`，只有用户明确要求“克制”或“丰富、激进、多用组件”时改为 `restrained` 或 `rich`。

执行时遵守：

- 金句、NOTE、WARNING 和其他组件替换对应原文，不在正文后重复同一意思。
- `:::compare`、`:::flow`、`:::timeline` 独占一行且前后留空行；矩阵对比保留 table。
- 卡片只放短文本；组件数量、横向布局和完整语法按 `references/component-guide.md`。
- 从正文推断开场标题、副标题和不超过 3 个标签；模板选择与 SVG 技术边界按 `references/svg-animation-design.md`。
- 话题标签：frontmatter 没有 `topics` 时，从正文选 3–4 个写入转换用的 frontmatter（或传 `--topics`）：栏目/合集标签固定在首位，再加 2–3 个对准目标读者或本篇主题的话题；不用「人工智能」「AI」这类泛词，品牌或产品名只在正文确实展示该产品时使用，不超过公众号上限 10 个。用户指定标签或明确不要时照办（`--topics none`）。
- `xiaolan-terminal` 只在用户明确要求小蓝、智见小蓝或品牌 IP 时使用。
- 生成前完成组件 reference 中的检查清单，然后运行转换与移动端视觉 QA。

### 3. 质量验收

正式候选必须满足：

- 严格段落密度门通过；不靠缩小字号、放大行高或增加组件掩盖阅读墙。
- 390px 视口无横向溢出、坏图和图片 URL 异常重复；图片去重检查为严格模式。
- 引用、标题层级、暖陶色基线和卡片在移动端显示正常。
- 组件没有重复正文，围栏没有泄漏，正文语义未被改写。
- 代码围栏中的换行编译为显式 `<br>`；不能只依赖 `\n` 与 `white-space:pre-wrap`。
- 兼容硬规则按 `references/wechat-compatibility.md` 通过后，才进入编辑器注入。

### 4. 编辑器注入

仅在授权范围内按 `references/opencli-injection.md` 执行。发布命令始终带 `--report`；保存草稿后必须以页面可见信号或报告中的新 `appmsgid` / 历史变化核对真实保存，不把命令成功当作保存证据。

报告至少保留：阶段、脱敏错误、图片状态、封面策略、代码块硬换行计数、正文首尾、草稿保存证据和可直接执行的恢复动作。失败后优先用只读验证定位，不盲目重复写入。

## 输出合同

- 默认输入 `article.md`，输出同目录 `article_wechat.html`；也可显式指定输出路径。
- 输出为完整内联样式 HTML，可复制或在获授权后注入公众号编辑器。
- 占位图、参数、主题、输出路径和命令见 `references/conversion-workflow.md`。
- 品牌 GIF 位于文章首尾，正文中间使用静态组件。明确启用 SVG 开场动画时只保留结尾 GIF。
- 开场动画承担文章标题：启用 `--cover` 时自动移除正文开头的一级标题（首个非空行的 `# 标题`），动画标题依次取 `--cover-title`、frontmatter.title、该一级标题；正文中段的一级标题不受影响，确需保留时传 `--keep-h1`。
- 话题标签渲染在正文末尾（结尾 GIF 之前），结构复刻公众号编辑器原生 `a.wx_topic_link`，斜体 14px；注入后编辑器识别为话题，保存即生效。

## References

| 文件 | 何时读取 |
|---|---|
| `references/conversion-workflow.md` | 默认转换、参数、主题、占位符与 390px QA |
| `references/theme-guide.md` | 主题选择、YAML 参数或扩展主题 |
| `references/component-guide.md` | 组件语法、密度预算、改写与检查清单 |
| `references/svg-animation-design.md` | 动画模板选择、SVG 技术约束与回归要求 |
| `references/wechat-compatibility.md` | 公众号兼容硬规则 |
| `references/opencli-injection.md` | 已授权的编辑器注入、封面、图片、保存证据与恢复 |
| `references/zhijian-theme-baseline.md` | Zhijian 主题样式锁与移动端视觉基线 |

---

**版本：** 1.13.1 · **作者：** 大鹏

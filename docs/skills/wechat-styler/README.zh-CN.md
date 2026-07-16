# WeChat Styler · 公众号排版 Skill

[English](README.md)

把 Markdown 一键排成可直接粘进公众号编辑器的内联 HTML。8 套有版式人格的主题,确定性兼容校验,可选组件拓展层,零外部 CSS。

## Agent 安装

```bash
npx skills add zjp1997720/wechat-styler -g -a codex --skill wechat-styler -y
```

任何能加载 SKILL.md 的 Agent 运行时都能用(Codex、Claude Code、OpenCode 等)。

## 环境要求

- Node.js 18+
- `marked`、`js-yaml`、`glob`(由 skill 运行时自动安装,或手动 `npm install`)

## 它解决什么问题

- **一次转好,粘贴不丢格式。** 所有样式内联,背景色全部 solid hex,从浏览器复制直接粘进公众号编辑器——颜色、对齐、引用块都不丢。
- **8 套主题有真正的版式人格。** 不是换色卡。`magazine-ink` 是经典杂志内页,`magazine-indigo` 是研究栏 + 全大写标题,`magazine-forest` 是田野笔记 + 居中楷体标题。每套主题有自己的标题结构、引用样式、列表 marker、代码块。
- **可选组件拓展层(`--components`)。** 6 个结构化组件(金句块、提示块、警告块、步骤序号、流程卡片、对比卡片、时间线),用于可视化对比、流程和要点。默认关闭——90% 的场景用纯净排版;需要结构化呈现时显式启用。全部用 section + flex,不用 table(公众号编辑器会给 table 加灰边)。
- **兼容性是脚本硬门,不靠模型自觉。** `validate.mjs` 扫描产物,检查公众号会剥离的所有东西(`<style>`、`class`、`rgba()`、`position:fixed`、`@media`……),带行号打印报告。convert 自动跑,也能独立跑给 CI 用。
- **占位符机制。** 图床没准备好?Markdown 里写 `【插入:文章开头截图】`,渲染成虚线占位框。图来了换成 `![alt](url)` 就行。

## 怎么工作的

三个组件,各管一件事:

1. **`scripts/convert.mjs`** — 用 `marked` 解析 Markdown,按主题对应的 renderer(6 个 preset 支撑 8 套主题)渲染,输出全内联 HTML。
2. **`scripts/components.mjs`** — 可选组件拓展层(6 个结构化组件,`--components` 启用)。
3. **`scripts/validate.mjs`** — 按公众号兼容规则扫产物(5 类 ERROR + 3 类 WARN)。convert 内软门调用,也能独立运行返回 exit code。
3. **`themes/*.yaml`** — 一个主题一个文件。颜色、字体、字号、间距、版式风格都在里面。加主题 = 丢一个 yaml 进去,不用改代码。

**一个关键设计选择:主题是 YAML 参数,不是重组件库。** 这样 skill 保持轻、跨模型稳定、好扩展。当主题需要结构差异时(比如 5 套 magazine 变体),renderer 通过 `magazine_variant` 走不同分支——同一个脚本,不同版式人格。

## 触发示例

```
用 magazine-ink 主题把这篇文章排成公众号:
$wechat-styler path/to/article.md --theme magazine-ink

批量转换整个目录:
$wechat-styler "articles/*.md" --theme kami

校验已有 HTML 文件:
$wechat-styler 然后运行: node scripts/validate.mjs path/to/output.html
```

## 关于品牌主题

默认主题 `zhijian` 是作者自己的品牌主题(暖纸感 + 陶土行动色 + 墨蓝结构色,从一套品牌设计系统派生而来)。它作为**示例**保留——展示「如何把一套品牌系统固化进 skill」。

想做成你自己的:复制 `themes/zhijian.yaml`,改颜色、字体、`top_label`,换个名字。就这么简单。

## 仓库结构

```
.
├── README.md                # 英文文档
├── README.zh-CN.md          # 本文件
├── LICENSE                  # MIT
├── SKILL.md                 # Agent 工作流入口
├── agents/openai.yaml       # Agent UI 元数据
├── scripts/
│   ├── convert.mjs          # Markdown → 公众号 HTML
│   ├── validate.mjs         # 公众号兼容性校验
│   └── generate-preview.mjs # 主题预览页生成器
└── themes/
    ├── zhijian.yaml         # 示例品牌主题(暖纸感)
    ├── kami.yaml            # 纸感文档
    ├── magazine-ink.yaml    # 杂志经典
    ├── magazine-indigo.yaml # 研究栏
    ├── magazine-forest.yaml # 田野笔记
    ├── elegant.yaml         # 复古随笔
    ├── modern.yaml          # 现代教程
    └── minimal.yaml         # 极简笔记
```

## 设计立场

- **克制优于装饰。** 主题靠留白、细线、字体分层建立质感——不靠卡片、缎带、关键词逐段下划线。视觉定位是「安静可信」,不是「热闹花哨」。
- **兼容性是脚本,不是愿望。** 校验规则里的每一条,都是公众号编辑器真的会剥离或破坏的东西。每次 convert 都跑。
- **YAML 主题,不是组件库。** 加主题不该改代码。结构人格放在 renderer 的 variant 分支里,表面人格放在 YAML 里。

## 协议

MIT — 见 [LICENSE](LICENSE)。

# 主题指南

> 8 套主题的完整配置参数、Renderer Presets、主题预览用法、扩展指南和技术实现。
> SKILL.md 只保留主题概览表,本文档承载详情。

## 主题概览

| 主题 | 命令 | 风格 | 适用场景 |
|------|------|------|----------|
| zhijian(默认) | `--theme zhijian` | 暖纸感 × 顾问可信度 | 智见AI 品牌内容 |
| kami | `--theme kami` | 纸感编辑排版 | 深度文章、商业分析 |
| magazine-ink | `--theme magazine-ink` | 墨水经典杂志 | 通用杂志内页 |
| magazine-indigo | `--theme magazine-indigo` | 靛蓝研究风 | 技术研究、深度调研 |
| magazine-forest | `--theme magazine-forest` | 森林田野笔记 | 非虚构、自然叙事 |
| elegant | `--theme elegant` | 优雅复古 | 商业案例、知识分享 |
| modern | `--theme modern` | 现代简约 | 科技产品、教程 |
| minimal | `--theme minimal` | 极简主义 | 哲学思考、个人随笔 |

---

## zhijian（智见AI 品牌主题）— 默认

基于 DESIGN.md 品牌系统，暖纸感 × 顾问可信度。

- 纸感背景 `#F5F4ED`，深暖陶行动色 `#B85235`，墨蓝结构色 `#1B365D`
- 非代码文字统一使用思源宋体 VF：标题和 UI 使用 500 字重，正文使用 400 字重；代码使用 SF Mono
- H2 左侧暖陶竖线，H3 墨蓝色，引用块 Human Accent 左线

```yaml
font_family_cn: 'Source Han Serif SC VF','Source Han Serif SC','Noto Serif CJK SC','Songti SC',STSong,SimSun,Georgia,serif
font_family_en: 'Source Han Serif SC VF','Source Han Serif SC',Georgia,serif
font_size: 17
line_height: 1.58
accent_color: '#B85235'
accent_secondary: '#1B365D'
background_color: '#F5F4ED'
surface_color: '#FAF9F5'
text_color: '#141413'
heading_font: 'Source Han Serif SC VF','Source Han Serif SC','Noto Serif CJK SC','Songti SC',STSong,SimSun,Georgia,serif
ui_font: 'Source Han Serif SC VF','Source Han Serif SC','Noto Serif CJK SC','Songti SC',STSong,SimSun,Georgia,serif
code_font: 'SF Mono','JetBrains Mono',Menlo,Consolas,'Source Han Serif SC VF','Source Han Serif SC',monospace
code_bg: '#30302E'
code_color: '#F5F4ED'
```

**适用场景：** 所有智见AI品牌内容 — 公众号文章、培训讲义、课程内容、方法论分享、AI 落地案例

---

## kami（紙感编辑排版）

warm parchment 纸感背景，ink-blue 单一强调色，中文标题衬线/楷体栈，正文稳定无衬线栈。

```yaml
font_family_cn: 'Inter','TsangerJinKai02','Source Han Sans SC','Noto Sans CJK SC','PingFang SC','Microsoft YaHei',Arial,sans-serif
font_family_en: 'Newsreader','Source Serif 4','Source Serif Pro','Charter',Georgia,'Times New Roman',serif
font_size: 16
line_height: 1.55
accent_color: '#1B365D'
background_color: '#f5f4ed'
surface_color: '#faf9f5'
text_color: '#141413'
secondary_color: '#5e5d59'
heading_font: 'TsangerJinKai02','Source Han Serif SC','Noto Serif CJK SC','Songti SC','STSong',Georgia,serif
code_font: 'JetBrains Mono','SF Mono','Fira Code',Consolas,Monaco,'TsangerJinKai02','Source Han Serif SC',monospace
```

**适用场景：** 公众号深度文章、商业分析、课程内容、正式说明文

---

## magazine 系列（电子杂志 × 电子墨水）

从 `magazine-web-ppt` 迁移来的预设，保留 `ink / paper / tint` 的杂志色彩关系。

| 主题 | 变体 | 字体 / 版式人格 |
|------|------|------------------|
| magazine-ink | `ink-classic` | 无衬线正文 + 衬线标题，细 rule、dash list、pull quote |
| magazine-indigo | `indigo-research` | Inter/SF Pro 正文 + Source Serif 标题，左侧研究栏、note quote |
| magazine-forest | `forest-fieldnote` | 楷体/宋体正文 + 非虚构标题，居中标题、field note 引用 |

**共同特点：**
- 每个 theme 有独立字体栈、字号、行距、段距、标题结构、列表 marker、引用块、代码块和图片说明
- 分隔以留白、短淡线和局部标识为主
- 所有背景色使用 solid hex，在区块与文本 span 上重复声明 `background-color`

---

## elegant（优雅复古）

```yaml
font_family_cn: 'FZShuSong-Z01','Songti SC',STSong,serif
font_family_en: 'Garamond',serif
font_size: 16
line_height: 1.9
accent_color: '#cf4436'
background_color: '#f7f6f1'
heading_font: 'Noto Serif SC','Songti SC',STSong,Georgia,serif
code_font: 'JetBrains Mono','SF Mono',Menlo,Consolas,monospace
```

**适用场景：** 商业案例、深度分析、知识分享

---

## modern（现代简约）

```yaml
font_family_cn: 'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif
font_family_en: 'SF Pro Display','Helvetica Neue',sans-serif
font_size: 16
line_height: 1.8
accent_color: '#007aff'
background_color: '#ffffff'
heading_font: 'PingFang SC','Hiragino Sans GB',sans-serif
code_font: 'SF Mono',Menlo,Consolas,monospace
```

**适用场景：** 科技产品、教程、快讯

---

## minimal（极简主义）

```yaml
font_family_cn: 'Noto Sans SC','PingFang SC',sans-serif
font_family_en: 'Inter','Helvetica Neue',sans-serif
font_size: 15
line_height: 2.0
accent_color: '#333333'
background_color: '#fafafa'
heading_font: 'Noto Sans SC',sans-serif
code_font: 'JetBrains Mono',monospace
```

**适用场景：** 哲学思考、个人随笔、艺术评论

---

## Renderer Presets

主题不只换颜色。每个主题绑定一个 Markdown 渲染人格。

| Preset | 绑定主题 | 版式语气 |
|--------|----------|----------|
| `zhijian-warm-paper` | `zhijian` | 品牌讲义：暖陶竖线标题、墨蓝三级标题、Human Accent 引用 |
| `kami-document` | `kami` | 纸感文档：正式、克制、标题左侧 ink-blue 竖线 |
| `magazine-editorial` | `magazine-*` | 电子杂志家族：通过 `magazine_variant` 分别呈现 classic / research / fieldnote |
| `elegant-essay` | `elegant` | 复古长文：居中标题、舒展行距 |
| `modern-technical` | `modern` | 现代教程：无衬线层级、提示卡片 |
| `minimal-notes` | `minimal` | 极简笔记：低装饰、大留白 |

---

## 主题预览

不确定选哪个主题？用主题预览生成器对比所有主题效果：

```bash
# 生成所有主题的预览页面（使用默认示例文章）
node scripts/generate-preview.mjs

# 使用自定义文章生成预览
node scripts/generate-preview.mjs path/to/your-article.md

# 只预览指定主题（逗号分隔，无空格）
node scripts/generate-preview.mjs article.md --themes magazine-ink,magazine-indigo,magazine-forest
```

---

## 扩展新主题

1. 在 `themes/` 目录创建新主题配置文件：
   ```yaml
   # themes/my-theme.yaml
   name: my-theme
   description: 我的自定义主题
   font_family_cn: 'Custom Font CN'
   font_size: 16
   accent_color: '#ff6b6b'
   background_color: '#f8f9fa'
   heading_font: 'Heading Font'
   code_font: 'Code Font'
   ```
2. 使用：`/wechat-styler article.md --theme my-theme`

---

## 技术实现

**核心脚本：**
| 脚本 | 职责 |
|------|------|
| `scripts/convert.mjs` | Markdown → 公众号 HTML（软门调用 validate） |
| `scripts/validate.mjs` | 公众号兼容性校验（独立可运行 / 被 convert 引用） |
| `scripts/components.mjs` | 组件拓展层（6 个结构化组件，`--components` 启用） |
| `scripts/generate-cover-animation.mjs` | SVG 开场动画生成器（`--cover` 启用） |
| `scripts/inject-to-wechat.mjs` | opencli 注入微信编辑器 |
| `scripts/generate-preview.mjs` | 主题预览页生成器 |

**依赖：** Node.js 18+、marked（Markdown 解析）、js-yaml（YAML 解析）、opencli（注入编辑器时需要，可选）

**目录结构：**
```
wechat-styler/
├── SKILL.md
├── scripts/
│   ├── convert.mjs
│   ├── validate.mjs
│   ├── components.mjs
│   ├── generate-cover-animation.mjs
│   ├── inject-to-wechat.mjs
│   └── generate-preview.mjs
├── themes/
│   ├── zhijian.yaml
│   ├── kami.yaml
│   ├── magazine-{ink,indigo,forest}.yaml
│   ├── elegant.yaml
│   ├── modern.yaml
│   └── minimal.yaml
├── references/
│   ├── theme-guide.md              ← 本文件
│   ├── component-guide.md
│   ├── wechat-compatibility.md
│   ├── opencli-injection.md
│   └── svg-animation-design.md
└── templates/
    └── base.html
```

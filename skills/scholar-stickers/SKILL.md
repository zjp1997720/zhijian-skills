---
name: scholar-stickers
summary: 知识人物贴纸幻灯片生成器——输入人物/朝代/原理，自动查资料、生成素描肖像、产出 16:9 课堂交互页面
description: 生成"人物贴纸"式知识介绍交互页面：适用于介绍思想家/科学家/文学家、学科原理、发展历史的课堂教学场景。当用户要"介绍几位人物""做人物贴纸页面""原理科普演示页""学科发展历史互动页"时触发。输入人物姓名、历史朝代、原理知识等，自动查资料并按固定结构生成 16:9 无滚动幻灯片页面（总览 + 每人一页，点击展开交互）。
read_when:
  - 用户要做人物介绍、知识科普、教学演示交互页面
  - 用户提到"贴纸""人物墙""点谁看谁""课堂翻页页面"
---

# Scholar Stickers · 知识人物贴纸幻灯片生成器

把一组人物（思想家 / 科学家 / 文学家 / 历史人物）或一组概念，做成**单文件 16:9 交互幻灯片**：总览页贴纸墙 → 点击贴纸 → 人物详情页（生平可点击展开）。面向教师课堂投影使用，**零滚动、键盘翻页、后排可读**。

---

## 1. 输入参数

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `figures` | ✅ | 3–6 位人物名单 | 苏格拉底、孔子、卢梭、杜威、皮亚杰 |
| `domain` | ✅ | 学科领域（决定查资料的方向） | 教育哲学 / 经典物理学 / 唐宋文学 |
| `title` | ✅ | 总览页大标题 | 哲学，从惊讶与疑惑开始 |
| `subtitle` | ⬜ | 总览页引言（默认空） | 我们为何教育…… |
| `chapter` | ⬜ | 顶部章节编号（默认 CHAPTER · 01） | CHAPTER · 03 |
| `theme` | ⬜ | 配色主题（默认 `warm-classic`，见 §5.2） | ink-blue / forest |
| `expand_mode` | ⬜ | 生平是否点击展开（默认开） | on / off |

如果用户只给人物名单没给 title/domain，**先按领域拟 2–3 个标题让用户选**，不要自作主张定稿。

---

## 2. 工作流程（五步）

### Step 1 · 资料整理（每人五段式）

用 WebSearch / 本地知识库为每位人物查证并整理以下字段。**所有字段有字数硬限制**（一屏放不下就失败）：

```js
{
  id: 'socrates',            // 拼音 id，用于图片文件名
  name: '苏格拉底',           // 中文姓名
  nameEn: 'Socrates',        // 外文名（中国人物用拼音或字）
  years: '470 BC – 399 BC',  // 生卒年
  keywords: '古希腊 · 街头追问 · 产婆术',   // ≤4 个关键词，· 分隔
  bio: '……约 110 字……',     // 生平：4-5 行以内，3-5 个关键事件
  contribs: [                // 贡献：恰好 3 条，每条 ≤40 字，<b>加粗术语</b>
    '<b>术语</b>：一句话解释。',
    '<b>术语</b>：一句话解释。',
    '<b>术语</b>：一句话解释。'
  ],
  quotes: ['……', '……'],     // 金句：恰好 2 条，每条 ≤30 字
  books: ['《A》', '《B》'],   // 经典文本：恰好 2 本
  inspiration: '……≤22 字，一行说完。'   // 当代启示：单句
}
```

**内容红线**：
- 拿不准的史实标 `[待核实]`，不要编造生卒年、著作名、语录
- 金句必须是**有出处的原文或公认转述**，查不到就换成著作名句
- 中国人物 quotes 优先用原典（文言可保留，加一句白话点题可选）

### Step 2 · 肖像生成（铅笔素描贴纸风）

用当前平台的**文生图**能力（WorkBuddy 为「多模态内容生成」skill，其他平台用自带生图工具）为每位人物生成肖像，统一风格。

**Prompt 模板**（替换 `{描述}`）：

```
Pencil sketch portrait of {人物身份描述：国籍/时代/外貌特征/服装},
graphite pencil drawing on white paper, monochromatic black and white,
hand-drawn white sticker border around the portrait with slightly torn paper edges,
bust composition, classical engraving style
```

外貌描述要写**可识别特征**（胡须/眼镜/帽子/发型/服装），例如：
- 苏格拉底 → `ancient Greek philosopher Socrates, bald head with curly white side hair, long curly white beard, classical Greek toga draped over one shoulder, intense thoughtful gaze`
- 杜威 → `American philosopher John Dewey, round wire-rimmed glasses, small mustache, neat combed gray hair, formal suit with tie, dignified expression`

**调用要点**（平台通用 + WorkBuddy 实测）：
- **通用原则**：用当前平台/工具自带的文生图能力即可，Prompt 统一走上方模板，输出 768×960（或接近竖版比例），PNG 落到交付目录的 `portraits/` 子目录
- **WorkBuddy（2026-08 实测）**：
  1. 先调 `connect_cloud_service` 拿 tempToken（**每次任务重新获取**）
  2. 脚本：定位本机 WorkBuddy 安装目录下的 `resources/app.asar.unpacked/resources/builtin-skills/buddy-multimodal-generation/scripts/buddy-cloud.py`（用 `where buddy-cloud.py` 或按安装路径查找，不要写死用户名）
  3. Python：优先 `python3`，找不到时用 `py -3` 或 `where python` 探测（不要写死绝对路径）
  4. 参数：`image "<prompt>" --resolution 768:960 --token-stdin`
  5. Token 管道传入：`echo -n "<token>" | <python> -u <script> image "..." --token-stdin`
  6. 生成完 `curl -sS -L -o portraits/{id}.png "<result_url>"` 落到交付目录的 `portraits/` 子目录
  7. 若报"250 个任务上限"，等 30 秒重试一次；最多重试 1 次
- 生成后**必须逐张 Read 检查**：人物是否可识别、有没有水印角标（有水印就裁掉或重生成）

### Step 3 · 页面组装

复制 `template.html`（本 skill 目录下）到交付目录，替换：
1. `THEME` 对象 → 配色（见 §5.2）
2. `META` 对象 → title / subtitle / chapter
3. `FIGURES` 数组 → Step 1 的数据
4. 确认 `portraits/` 相对路径图片齐全

### Step 4 · 自检清单

- [ ] 总览页贴纸墙 3×2 排布不错位、hover 回正上浮
- [ ] 每个详情页 4 行齐全：贴纸行 / 生平（默认收起）/ 贡献 / 文本+启示
- [ ] 生平点击展开动画正常、翻页后自动复位收起
- [ ] 键盘 ←→ 翻页、Esc 回总览、底部圆点可点
- [ ] 缩放窗口，stage 始终 16:9 居中无滚动
- [ ] 金句 28px、正文 22px——投影可读
- [ ] 内容无溢出（bio ≤5 行、contribs 每条单行或两行内）

### Step 5 · 交付

`preview_url` 打开 HTML 预览 → `deliver_attachments` 交付 HTML + 全部肖像 PNG + 内容文档 MD（可选）。

---

## 3. 页面结构（固定，不可擅改）

```
SLIDE 0  总览页
├── 顶部条：CHAPTER · NN | BEAT NN（期刊式编号）
├── 左：eyebrow + 大标题（em 斜体朱红强调词）+ 引言 + 点击提示
└── 右：贴纸墙（3 列 × 2 行，各自轻微旋转，hover 回正）

SLIDE 1..N  人物页（每人一页，纵向 4 行）
├── 第 1 行「贴纸行」：肖像(240px 白边贴纸) + 名字块(中64/EN26/年代21/关键词16.5) + 金句块(28px 大引号)
├── 第 2 行「生平」：标题条(点击展开 ▸) + 正文(22px，默认收起)
├── 第 3 行「贡献」：标题 + 3 条 ◆ 列表(22px)
└── 第 4 行「文本+启示」：书签(18px × 2) | ✦ 启示条(20px 单行)

底部条（每页）：导航圆点 | 键盘提示 | 页码 NN / MM
```

**交互**：点贴纸跳详情 / ←→·空格·PgUpPgDn 翻页 / Esc·Home 回总览 / End 到末页 / 生平点击展开（翻页自动复位）。

---

## 4. 设计规范（课堂可读性优先）

### 4.1 版式

- **16:9 固定舞台**：设计稿 1600×900，JS `fitStage()` 计算 `scale = min(vw/1600, vh/900)`，`transform: scale()` 居中；外层深色底。任何屏幕都是标准 16:9 满屏、零滚动。
- 纵向单列流详情页：**"左=人右=事"都不用，用从上到下一条龙**——老师讲课视线沿一条主轴。

### 4.2 字号基线（1600×900 设计稿 px，后排可读底线）

| 层级 | 字号 | 字重 |
|------|------|------|
| 总览大标题 | 80 | 900 |
| 人名（中文） | 64 | 900 |
| 金句 | 28 | 600 |
| 生平 / 贡献正文 | 22 | 400 |
| 启示 | 20 | 400 |
| section 标题 | 19 | 700 |
| 书签 | 18 | 400 |
| 英文名 / 年代 | 26 / 21 | — |
| 关键词 | 16.5 | 400 |

字号上调时 line-height 反向收一点（22px 配 1.7）保持密度；**section 标题必须跟正文同步放大**，它是视线锚点。

### 4.3 字体

```css
'Cormorant Garamond'（拉丁/斜体/数字） + 'Noto Serif SC'（中文标题/正文） + 'Noto Sans SC'（中文辅助）
```

Google Fonts CDN 引入；中英双语标签是固定风格（BIOGRAPHY · 生平事迹）。

### 4.4 配色主题

默认 `warm-classic`（本 skill 视觉签名）：

| 令牌 | 值 | 用途 |
|------|-----|------|
| `--bg` | #f3ebdb | 页面暖米底 |
| `--paper` | #fbf6e8 | 金句块/纸面 |
| `--ink` | #1a1612 | 主文字 |
| `--vermillion` | #b8392a | 朱红强调（标题词/引号/箭头/圆点） |
| `--ink-mute` | #6a5e4a | 辅助文字 |

备选主题（改 `:root` 变量即可）：
- `ink-blue`：vermillion→#2c5a7a，bg→#e9edf2（冷调学术）
- `forest`：vermillion→#3a6b4f，bg→#eaf0e6（自然学科）
- 用户指定品牌色时，只替换 `--vermillion` 和 `--bg` 两个令牌，其余不动。

### 4.5 贴纸样式

白底 padding 7px + 三层投影（近/中/远）+ 旋转 -2.5°~2.5° 错落；hover：rotate(0) translateY(-8px) scale(1.05)。

---

## 5. 模板与资产

- `template.html` —— 参数化完整页面（THEME / META / FIGURES 三个替换点在文件头部有注释标记）
- 肖像统一存 `portraits/{id}.png`（768×960）

## 6. 常见变体

| 需求 | 做法 |
|------|------|
| 加人物 | FIGURES 加条目 + 生成肖像；总览墙自动 3×N 排 |
| 概念/原理页（非人物） | 肖像换成"原理示意贴纸"（生成简笔示意素描图），金句位放原理一句话表述 |
| 发展历史时间线 | 在总览页底部加 timeline ribbon；或详情页 years 行展开时期背景 |
| 不要点击展开 | `expand_mode: off`：删 `.d-bio-content` 折叠 CSS，p 直接显示 |
| 全英文版 | name/n ↔ nameEn 互换，字号各减 2px |

## 7. 红线

- **不虚构**：生卒年、著作、语录必须可查证；查不到换内容，不编
- **不超字数**：bio ≤120 字、inspiration ≤22 字、quotes ≤30 字/条——超了就删减，不是缩小字号
- **不滚动**：任何情况下页面不允许出现滚动条（课堂投影死罪）
- **AI 肖像带水印**：裁掉或重生成，交付前逐张检查

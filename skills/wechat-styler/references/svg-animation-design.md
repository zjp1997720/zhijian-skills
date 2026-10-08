# SVG 开场动画设计指南

> 公众号文章首屏 SVG 动画的设计原则、技术约束和踩坑清单。
> 核心脚本: `scripts/generate-cover-animation.mjs`

## 语义文字硬规则

**标题、副标题、标签、日期、作者和阅读提示必须拥有静态可见基态。** 动画可以驱动光标、线条、墨点、聚光、箭头，以及基态透明的非语义遮罩；语义文字本身保持可见。生成后的 SVG 删除全部 `<animate>` / `<animateTransform>` 后，语义文字仍必须完整可见。

2026-08-31 真实读者端事故证明：把标题拆成逐字符 `<text>` 并设置基态 `opacity="0"`，会让微信读者端在丢失早期 SMIL 终态时永久隐藏 `WorkBuddy`。后台预览正常、本地 Chrome 正常，都不能替代这条静态基态规则。

## 为什么只在开场用动画

SVG SMIL 动画(`<animate>` / `<animateTransform>`)在微信公众号里**只有首次加载时播放**,`fill="freeze"` 播完就冻结在终态。用户向下滚动时动画早就结束了,中间和结尾的动画只能看到静态终态 —— 不如直接用静态组件。

**结论: 只做开场动画,其他位置用 `--components` 的静态组件。**

## 6 个模板

| 模板 | 参数值 | 气质 | 时长 | 适配 |
|------|--------|------|------|------|
| 墨韵开篇 | `ink-wash` (默认) | 仪式感·墨点晕染·东方美学 | 4.5s | 方法论、品牌、课程 |
| 打字机流 | `typewriter` | 极客感·逐字显现·完整兜底 | 6.5s | 技术教程、工具介绍 |
| 小蓝终端 | `xiaolan-terminal` | 品牌感·高精度像素小蓝·挥手问候·轻晃眨眼·循环打字 | 4s 文字 / 6s 角色循环 | 明确要求小蓝/IP 的技术内容 |
| 画卷展开 | `scroll-painting` | 叙事感·双横线·渐入佳境 | 3.8s | 案例、复盘、故事 |
| 聚焦聚光灯 | `spotlight` | 判断感·聚光圆·标题缩放 | 4.5s | 观点、评测、趋势 |
| 极简白描 | `minimal-sketch` | 克制·大留白·呼吸圆点 | 3.5s | 随笔、思考、感悟 |

品牌标签（ink-wash、spotlight）取 `theme.top_label`，画卷右下署名默认为「<top_label> 出品」。非智见AI账号用 `--top-label "<文本>"`（`none` 隐藏）和 `--cover-author "<署名>"`（原样输出、不加「出品」，`none` 隐藏）设置，不再事后改 HTML；首尾 GIF 仍是智见AI素材，必要时加 `--brand-cta none`。

### 墨韵开篇 (ink-wash)

7 层节奏：墨点晕染 → 品牌标签 → 主标题上浮 → 分隔线 → 副标题 → 特性标签(3个) → 分页圆点+下滑提示。viewBox 640×400。

### 打字机流 (typewriter)

主标题→副标题→提示文字**逐字显现**，橙色光标跟随当前字符。viewBox 640×280。关键技术：
- 每行只有一个语义 `<text>` 容器，字符 `<tspan>` 全部基态可见，并使用确定性 x 坐标定位
- 文本上方覆盖同背景色 `<rect>`：基态 `opacity="0"`，SMIL 运行时暂时遮住未输入后缀，`x` / `width` 用 `calcMode="discrete"` 逐字收缩
- 光标基态透明，只在当前行输入期间出现和闪烁；尚未开始的行不会提前出现光标
- 动画被剥离、禁用或漏执行时，遮罩和光标都回到透明基态，完整文字直接可见

**v1.7.2 改动记录**：
- **去掉品牌标签**：zhijian 主题左上角已有智见AI角标，typewriter 不再重复输出品牌标签，避免冗余
- **压缩顶部空档**：viewBox 高度从 360 降到 280，主标题 y 从 160 上移到 65，主标题上沿到页面顶部的间距大幅缩小
- **加大字号**：主标题 36px → 48px，副标题 16px → 26px，提示文字 14px → 18px（手机端原来太小看不清）
- **动画时序不变**：打字间隔和光标速度保持原样，只是起始 y 坐标整体上移
- 主标题、副标题和提示文字统一使用等宽字体栈；中文由字体栈中的中文字体回退，避免中英混排时 `Markdown`、`Word` 等单词内部重叠
- 大写字母字宽 0.72em，小写 0.6em，中文 1em
- 英文字母间额外加 1.5px 间距
- `interval >= dur`(推荐 `dur = interval * 0.8`)
- 提示打完后光标在末尾持续闪烁(亮0.6s灭0.6s)
- 横线用 `<rect>` + `<animate attributeName="width">`(不用 `<line>`)

### 小蓝终端 (xiaolan-terminal)

参考文章里的「左侧角色 + 右侧终端打字」结构。角色以通过 QA 的智见小蓝 v2 桌宠图集为身份源，派生开放眼和闭眼两张高密度像素帧；不再用少量 SVG 基本图形重新描角色。viewBox 640×230。

- 小蓝身份锚点：墨蓝立体终端身体、象牙白脸屏、脸屏左上角 `>_` 终端提示符、右侧点眼、细黑手脚、象牙白与暖陶双按钮；必须从正典资产派生，不允许重新画成粗方块图标。
- 4 秒循环：短暂留白与光标 → 深色标题和暖陶副标题在同一行逐字出现 → 完整停留约 1 秒 → 从右向左按字符擦除 → 重新开始。
- 英文、数字和常用 ASCII 标点使用内建 5×7 方格字库，每个亮点都是独立 `<rect>`；标题、副标题、标签和光标共享同一栅格节奏。
- 中英混排按连续字符段分流：受支持的拉丁字符段仍编译为 5×7 `<rect>`，中文等不支持字符段回退到静态可见的等宽 SVG `<text>`。禁止因为同一行含中文就把 `WorkBuddy` 等英文整行降级为读者端字体字形。
- `wave` 规则：每 6 秒开头使用「放下 → 半抬 → 举高 → 半抬 → 举高 → 回落」离散帧向读者挥手；不旋转或拉伸单根胳膊。挥手帧以当前高精度角色为母版，并参考正典桌宠图集 `waving` 行的姿势。
- `idle` 规则：整只角色用离散的 1–3px 位移模拟精灵帧呼吸；闭眼帧每 3 秒短暂覆盖一次，避免在高精度角色上叠粗糙遮罩。挥手期间暂停眨眼覆盖，避免两组帧互相穿帮。
- 开放眼、闭眼和两张挥手 PNG 作为 Skill 内身份资产读取，生成时解码、缩采样、颜色聚类并编译为原生 SVG `<path>` 像素块；成品不含 `<image>`、data URI、作者机器绝对路径或远程图片。公众号保存会保留这些原生图形。资产缺失时生成立即失败，避免静默降级成低保真角色。
- 短标题与副标题在同一行分色呈现；超出安全宽度时自动改为两行并分别缩放。标签使用 ` / ` 分隔。
- 标题、副标题和标签保留静态可见基态；小蓝动画或打字动画失效时，正文信息仍完整可读。
- 只在用户明确要求「小蓝 / 智见小蓝 / IP / 桌宠式开场」时选用；普通技术文章继续使用 `typewriter`。

### 画卷展开 (scroll-painting)

上方横线从左到右画出 → 标题上浮 → 下方横线从右到左 → 副标题淡入 → 左下日期标记 + 右下作者标记。viewBox 640×380。

### 聚焦聚光灯 (spotlight)

聚光灯径向渐变圆扩散 → 品牌标签 → 标题从 0.3 倍缩放到 1 倍(带弹性) → 粗短线 → 副标题 → 判断标签(实色底+描边底)。viewBox 640×400。

### 极简白描 (minimal-sketch)

纯留白 0.5s → 标题直接淡入(无位移) → 极细线 → 副标题 → 呼吸圆点(唯一动态元素)。viewBox 640×480(更高，留白更大)。

## 技术约束(微信编辑器)

### 可用

| 能力 | 标签/属性 | 备注 |
|------|-----------|------|
| SVG 动画 | `<animate>` | `attributeName` / `values` / `dur` / `begin` / `fill="freeze"` |
| 变换动画 | `<animateTransform>` | `type="translate"` / `type="scale"` / `type="rotate"` |
| 路径动画 | `<animateMotion>` | 沿路径移动(未测试) |
| 文字包裹 | `<tspan leaf="">` | **必须**,否则文字可能被清洗 |
| 无限循环 | `repeatCount="indefinite"` | 用于引导箭头等持续动画 |
| 属性动画 | `attributeName="opacity"` / `r` / `x2` 等 | 属性优于 `style` |

### 禁用(会被剥离)

| 禁止 | 原因 |
|------|------|
| `<style>` / `<script>` | 公众号编辑器剥离 |
| `class=` / `id=` | 编辑器剥离,样式必须内联 |
| CSS `@keyframes` / `animation` | 被忽略 |
| `rgba()` / `hsla()` | 背景色丢失,用 solid hex |
| `position:fixed/absolute` | 粘贴后错位 |

## 7 层节奏设计

开场动画的节奏感比视觉效果更重要。用户打开文章的 0-5 秒决定留存。

| 时间 | 效果 | 动画类型 |
|------|------|----------|
| 0.2s | 墨点晕染(圆形从中心扩散淡出) | `animate r` + `animate opacity` |
| 0.8s | 顶部标签浮现(品牌名) | `animate opacity` |
| 1.2s | 主标题上浮 + 淡入(48px 大字) | `animateTransform translate` + `animate opacity` |
| 1.9s | 分隔线从中心向两侧画出 | `animate x1` + `animate x2` |
| 2.4s | 副标题淡入 | `animate opacity` |
| 3.0s | 特性标签依次淡入(3个,间隔0.3s) | `animate opacity` |
| 4.0s | 分页圆点 + "向下滑动" + 无限循环箭头 ↓ | `animateTransform repeatCount=indefinite` |

### 缓动函数

```xml
<!-- 淡入淡出:ease-out -->
calcMode="spline" keyTimes="0;1" keySplines="0.25 0.1 0.25 1"

<!-- 弹性结束:用于分隔线画出 -->
calcMode="spline" keyTimes="0;1" keySplines="0.22 1 0.36 1"
```

## 配色策略

从主题 yaml 取色,不硬编码:

| 元素 | 取色来源 | 默认值(zhijian) |
|------|----------|------------------|
| 背景 | `theme.background_color` | `#F5F4ED` |
| 主标题 | `theme.text_color` | `#141413` |
| 强调色(标签/线条/墨点) | `theme.accent_color` | `#B85235` |
| 结构色(标签2) | `theme.accent_secondary` | `#1B365D` |
| 副标题 | `theme.tertiary_color` | `#6B6A64` |
| 标题字体 | `theme.heading_font` | 仓耳今楷 |
| 正文字体 | `theme.font_family_cn` | 思源宋体 |
| UI字体 | `theme.ui_font` | 思源黑体 |

## 尺寸策略

- **viewBox**: `640×400`(手机端约占半屏,有仪式感但不挡正文)
- **width**: `100%` + `max-width:640px`(自适应)
- **主标题字号**: `48px`(手机端约 24px,够大够震撼)
- **副标题字号**: `18px`
- **标签字号**: `12px`

## 踩坑清单

### 1. atob() 中文乱码

**问题**: `atob()` 只做 Latin-1 解码,UTF-8 多字节中文会乱码。

**解决**: 用 `TextDecoder('utf-8')` 正确解码:
```js
const binary = atob(b64);
const bytes = new Uint8Array(binary.length);
for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
const text = new TextDecoder('utf-8').decode(bytes);
```

### 2. ProseMirror / UEditor 内容清洗

**问题**: 新版编辑器(ProseMirror)和旧版编辑器(UEditor)都会在 `innerHTML` 设置后异步清洗内容,分步操作(DOM 插入/替换)会被覆盖。

**解决**: 一次性 `innerHTML` 设置完整 HTML,不做后续 DOM 操作。

### 3. 编辑器定位

| 编辑器版本 | URL 特征 | 编辑区选择器 |
|------------|----------|-------------|
| 新版(ProseMirror) | `appmsg_edit`(无 _v2) | `.ProseMirror` |
| 旧版(UEditor) | `appmsg_edit_v2` | `#ueditor_0 [contenteditable=true]` |

`inject-to-wechat.mjs` 自动检测两种编辑器。

### 4. SVG 背景色不融入

**问题**: SVG 动画有自带 `background:#xxx`,或注入在文章主 section 外部,导致背景色与正文不一致。

**解决**:
- SVG 内画一个 `<rect fill="背景色"/>` 覆盖整个 viewBox
- 注入到文章内层 `<section style="max-width:640px...">` 的开始标签之后(背景色容器内部)
- SVG wrapper 用 `<section style="margin:0;padding:0;line-height:0;">` 包裹

### 5. OpenCLI 必须带 --profile

**问题**: 不带 `--profile` 会绑到 `about:blank`,虽然能 `open` 但没有登录态。

**解决**: 先运行 `opencli doctor` 找到当前环境的 profile，再执行 `opencli --profile <profile-name> browser work open <url>`。公开 Skill 禁止内置作者机器上的 profile。

### 6. 粘贴过滤器剥离 animate

**问题**: 通过微信编辑器可视化粘贴时,`<animate>` 标签会被剥离,SVG 变成静态图。

**解决**: 用 opencli `eval` 直接操作 DOM,绕过粘贴过滤器。

### 7. 空段落导致空白

**问题**: 注入后 UEditor 会产生大量空 `<p>&nbsp;</p>`,在 SVG 周围形成可见空白。

**解决**: 注入后清理空段落(但跳过含 SVG/img 的):
```js
for (const p of [...editArea.querySelectorAll("p")]) {
  const t = p.textContent.trim();
  if ((t===""||t==="\u00a0"||p.innerHTML==="<br>") && p.querySelectorAll("svg,img").length===0) p.remove();
}
```

### 8. `<line>` 内的 animate 被剥离(微信)

**问题**: `<line>` 标签内的 `<animate attributeName="x2">` 会被微信客户端剥离,线条永远是一个点。但 `<text>` 内的 `<animate>` 会被保留。

**解决**: 线条用 `<rect>` + `<animate attributeName="width">` 代替 `<line>` + `<animate attributeName="x2">`:
```xml
<!-- ❌ 微信会剥离 animate -->
<line x1="100" y1="100" x2="100" y2="100" stroke="#B85235" stroke-width="2.5">
  <animate attributeName="x2" values="100;300" dur="0.5s" fill="freeze"/>
</line>

<!-- ✓ 微信保留 -->
<rect x="100" y="98.75" width="0" height="2.5" rx="1.25" fill="#B85235" opacity="0">
  <animate attributeName="width" values="0;200" dur="0.5s" fill="freeze"/>
  <animate attributeName="opacity" values="0;1" dur="0.05s" begin="0s" fill="freeze"/>
</rect>
```

### 9. SVG `<image>` 的图片引用在公众号保存后被清空

**问题**: 本地浏览器和公众号编辑器注入后都能显示 `<image href="data:image/png;base64,...">`，但草稿保存后的微信清洗会保留 `<image>` 空节点并删除 `href`。结果是文字、`>_` 和 SMIL 动画仍在，小蓝角色完全消失。

**解决**: 角色帧在生成阶段编译为原生 SVG `<path>` 像素块，帧切换只动画外层 `<g opacity>`。真实草稿回读必须同时满足：`<image>` 为 0、四个 `data-xiaolan-render="native-svg-pixels"` 帧存在、`<path>` 大于 0。

### 10. Chrome 不执行 innerHTML 注入的 SMIL 动画

**问题**: 通过 `innerHTML` 动态注入的 SVG,Chrome 不会触发 SMIL 动画。只有 SVG 首次被解析时才会触发。

**解决**:
- 微信编辑器注入用一次性 `innerHTML` 设置(微信客户端会重新解析 SVG,触发动画)
- 本地预览页面用 `<iframe src="*.svg">` + 重播时重新加载 iframe
- 不要在预览页面用 `innerHTML` 重播动画

### 11. 打字机效果:逐字重叠

**问题**: 逐字打字效果中,如果 `interval`(字间隔)< `dur`(淡入时长),下一个字开始时前一个字还没淡入完,视觉上重叠。大写字母(A)和小写字母(g)也会贴在一起。

**解决**:
1. `interval` 必须 >= `dur`(推荐 `dur = interval * 0.8`)
2. 大写字母字宽用 `0.72em`,小写用 `0.6em`,中文用 `1.0em`
3. 逐字定位的文本统一使用等宽字体栈；中文走中文字体回退
4. 英文字母之间额外加 `1.5px` 间距

### 12. 光标闪烁过快

**问题**: `values="1;0;1;0;1;0"` 在 `dur="1.2s"` 内翻转 3 次,视觉上太急促。

**解决**: 用 `values="1;1;0;0"` + `dur="1.2s"` —— 亮 0.6s 灭 0.6s,模拟真实终端光标。

### 13. 语义文字依赖 SMIL 才可见

**问题**: 真实微信读者端可能丢掉最早一批 SMIL 终态。若标题基态是 `opacity="0"`，丢失动画后该词永久透明；后台预览正常会造成误判。

**解决**:
- 语义文字静态输出，不以 `opacity="0"` 作为基态
- 逐字效果由非语义遮罩完成；遮罩基态必须是 `opacity="0"`，SMIL 只在播放期间把它变成不透明
- 动画失效时优先完整显示，动画正常时再逐字显现
- 每次改模板后运行 `node --test tests/cover-animation.test.mjs`
- 发布前用真实微信读者端等待 10 秒核对完整标题；编辑器动画节点计数不能替代该检查

### 14. 小蓝终端中英混排在 iOS 微信正式阅读器漏掉英文

**问题**: 草稿、本地 Chrome 和公开页 DOM 都包含完整的「让 WorkBuddy 持续接住你的项目」，桌面端也能显示；但 iOS 微信正式阅读器只绘制中文，英文 `WorkBuddy` 留白。公开页 DOM 中对应英文 `<tspan>` 仍存在且可见，说明不是服务端清洗或 SMIL 状态丢失，而是移动读者端对混合脚本 SVG 字形的绘制兼容问题。

**解决**:
- `xiaolan-terminal` 不能以“整行是否全部受 5×7 字库支持”作为渲染分支；必须先按字符能力切成连续的像素段和字体段
- 英文、数字和受支持 ASCII 段强制输出原生 `<rect>` 像素几何；中文段才使用 SVG `<text>`
- 外层保留完整 `data-semantic-text` / `aria-label`，删除全部动画后仍能还原整句语义
- 回归用例必须覆盖精确文案「让 WorkBuddy 持续接住你的项目」，并断言 `WorkBuddy` 出现在像素几何标签中、任何 `<text>` 内容中都不含 `WorkBuddy`

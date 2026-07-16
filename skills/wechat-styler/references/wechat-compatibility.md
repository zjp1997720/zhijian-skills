# 公众号兼容硬规则

> 以下规则由 `scripts/validate.mjs` 确定性执行。
> convert 采用**软门**策略：发现 ERROR 时文件照常生成，末尾打印报告；独立 validate 返回非零退出码给 CI。

## ERROR 级（产物必须为 0）

### 1. 禁用标签

| 标签 | 原因 |
|------|------|
| `<style>` | 公众号会剥离，样式必须全部内联 |
| `<script>` | 公众号会剥离，脚本无法执行 |
| `<link>` | 公众号会剥离，外部资源无法加载 |
| `<iframe>` | 公众号禁用 |
| `<input>` | 公众号禁用 |
| body 内 `<meta>` | 会被公众号剥离 |

### 2. 禁用属性

| 属性 | 原因 |
|------|------|
| `class=` | 公众号会剥离，样式必须内联 |
| `id=` | 公众号会剥离 |
| `contenteditable` | 公众号禁用 |

### 3. 禁用 CSS

| CSS | 原因 |
|-----|------|
| `position:fixed\|absolute` | 粘贴后错位 |
| `display:grid` | 公众号不支持 |
| `@media` | 公众号会剥离 |
| `@keyframes` | 公众号会剥离 |

### 4. 禁用函数

| 函数 | 原因 |
|------|------|
| `rgba()` | 背景色在编辑器中丢失，必须用 solid hex |
| `hsla()` | 同上 |

### 5. 禁用外部字体

`@font-face` 的 `url(...)` 外部引用会加载失败降级，用系统字体栈。

## WARN 级（建议修复）

| 规则 | 说明 |
|------|------|
| `display:flex` | 兼容性视客户端而定，建议粘贴后实测 |
| 图片无 `alt` | 无障碍 + 图床失效时的兜底 |
| 图片偏移风险 | `<img>` 缺 `margin:0 auto` 或 `display:block`，粘贴后可能偏左 |
| 块级元素缺 `style` | `<p>` / `<h2>` / `<blockquote>` 缺 style，粘贴后样式丢失 |

## convert.mjs 已内置的兼容策略（无需手动处理）

- 所有背景色使用 solid hex，不用 `rgba()`
- 外层 section / 内容 section / 文本 span 三层重复声明 `background-color`
- 图片父级 `text-align:center` + 自身 `margin:0 auto;display:block` 双重兜底
- 所有样式内联，不使用 `<style>` 标签或外部 CSS
- `<code>` / `<pre>` / `<svg>` 内容在 validate 时被剥离，避免误报

## SVG 动画特殊兼容

SVG 内的 `<animate>` / `<animateTransform>` 标签在微信客户端可用（通过 opencli DOM 注入），validate 会跳过 SVG 内容不做检查。

详见 `references/svg-animation-design.md` 和 `references/opencli-injection.md`。

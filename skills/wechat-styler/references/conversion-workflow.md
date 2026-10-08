# 默认转换与质量检查

默认转换、组件与动画分支都读取本文件。它不包含组件语法、动画模板或编辑器注入细节。

## 输入与默认值

- 输入为一个 Markdown 文件或匹配多个文件的 glob。
- 未指定主题时使用 `zhijian`。
- 默认输出为输入文件同目录下的 `<name>_wechat.html`。
- 默认模式不改写 Markdown，不添加正文组件；自动加入品牌首尾 GIF。必读 `brand-cta.md` 的开场互斥和去重规则。
- `--components` 的 Markdown 改写由 Agent 完成，`convert.mjs` 只负责渲染。

## 常用命令

`convert.mjs`、`content-density-audit.mjs` 和 `mobile-visual-qa.mjs` 均支持 `--help` / `-h`；帮助模式只显示参数，不转换文件、不启动浏览器。转换器写出 HTML 前自动清理行尾空格并保留一个文件末尾换行，无需手工处理。

```bash
# 默认转换
node scripts/convert.mjs /absolute/path/to/article.md --theme zhijian

# 指定输出
node scripts/convert.mjs /absolute/path/to/article.md \
  --theme kami \
  --output /absolute/path/to/article_wechat.html

# 组件分支：先在临时文件中完成改写与严格密度检查
node scripts/convert.mjs /tmp/rewritten.md \
  --theme zhijian \
  --components --strict-density \
  --cover --cover-template typewriter \
  --cover-title "..." --cover-subtitle "..." --cover-tags "..."
```

`--components` 只启用正文组件；`--cover` 显式启用主题 SVG 开场并自动替换开头 GIF。默认转换无需传这两个参数。

## 主题选择

| 主题 | 风格 | 适用 |
|---|---|---|
| `zhijian` | 暖纸感、顾问可信度 | 智见AI品牌内容，默认 |
| `kami` | 纸感编辑排版 | 深度文章、商业分析 |
| `magazine-ink` | 墨水经典杂志 | 通用杂志内页 |
| `magazine-indigo` | 靛蓝研究风 | 技术研究、深度调研 |
| `magazine-forest` | 森林田野笔记 | 非虚构、自然叙事 |
| `elegant` | 优雅复古 | 商业案例、知识分享 |
| `modern` | 现代简约 | 科技产品、教程 |
| `minimal` | 极简 | 哲学思考、个人随笔 |

主题详情、YAML 参数和扩展规则见 `theme-guide.md`。当前明确主题沿用，不因文章类型自动覆盖。

`zhijian` 视觉基线为 `editorial-weighted-2026-07`：H2/H3 使用仓耳今楷优先栈，正文使用思源宋体 VF 15px / 450 / 1.68，图注和元信息使用思源黑体 13px。大鹏已确认手机端默认正文 15px；字号不能代替段落整理。年长读者、叙事文章或术语密集正文可按明确要求使用 16–17px。

## 转换参数

| 参数 | 说明 | 默认值 |
|---|---|---|
| `--theme` | 主题名称 | `zhijian` |
| `--font-size` | 正文字号 px | 主题默认 |
| `--line-height` | 行高 | 主题默认 |
| `--accent-color` | 强调色 | 主题默认 |
| `--background-color` | 纯色背景 hex | 主题默认 |
| `--max-width` | 内容最大宽度 px | `640` |
| `--output` | 输出文件 | `<input>_wechat.html` |
| `--components` | 组件模式 | `false` |
| `--component-density` | Agent 改写层密度；不传给 `convert.mjs` | `standard` |
| `--strict-density` | 密度失败时停止 | `false`；正式候选必传 |
| `--cover` | SVG 开场，自动替换开头 GIF | `false` |
| `--brand-cta` | `auto` 首尾 GIF、`ending` 仅结尾、`none` 全部关闭 | `auto` |
| `--cover-template` | 动画模板 | `ink-wash` |
| `--cover-title` | 动画主标题 | frontmatter.title，其次正文开头的一级标题 |
| `--keep-h1` | 启用开场动画时仍保留正文开头的一级标题；默认移除以免与动画标题重复 | `false` |
| `--cover-subtitle` | 动画副标题 | frontmatter.summary |
| `--cover-tags` | 逗号分隔标签 | 无 |
| `--top-label` | 顶部标签，同时作为开场动画品牌标签与默认署名来源；`none` 隐藏顶部标签区和动画标签；拉丁字母会被大写显示 | theme.top_label（zhijian 为 `智见AI`） |
| `--cover-author` | 开场署名（scroll-painting 右下），原样输出、不加「出品」；`none` 隐藏 | `<top_label> 出品` |

## 占位图

图片未准备好时可在 Markdown 中使用独占一行的全角占位符：

```markdown
【插入:文章开头的视频截图】
```

转换器会把它渲染为居中虚线灰框。半角方括号或夹在正文中的写法不处理。

## 段落密度

WeChat Styler 不按标点自动拆段。正式候选先运行：

```bash
npm run qa:density -- /absolute/path/to/article.md --strict
```

失败时回到上游 Markdown，按事实、判断、机制、例子、边界和行动的语义切换点拆段。不得靠缩小字号、放大行高或组件装饰掩盖长段。记录中位数、P90、百字长段占比和最长连续长段。

## 390px 视觉 QA

生成后运行：

```bash
npm run qa:mobile -- /absolute/path/to/article_wechat.html \
  --expect-zhijian --strict-image-uniqueness \
  --screenshot /tmp/article-mobile.png
```

使用其他主题时去掉 `--expect-zhijian`。检查：

- 390px 视口无横向溢出、坏图或异常重复图片 URL。
- 引用符号与首行同段对齐，引用未误用左侧竖线。
- H2、正文、图注和元信息符合所选主题层级。
- 围栏标记没有泄漏，卡片没有截断或过度横向滚动。
- 代码块硬换行保留为显式 `<br>`。

转换器会自动运行 `validate.mjs` 软门并打印报告；正式候选仍需严格密度与移动端视觉 QA。具体 ERROR/WARN 定义见 `wechat-compatibility.md`。

## 图片从预览到注入

转换保留图片原引用；包含相对路径、绝对本地路径、`file:`、`data:` 或其他非 HTTP(S) 图片时，转换器提示“仅可本地预览”。这不是已上传或可注入的证明。

1. 注入前检查最终 HTML 的每个正文图片引用。相对路径按原 Markdown 所在目录定位；输出放在其他目录时另核对预览路径。
2. 沿用已有上传授权；没有授权时先准备文件清单，再确认上传。已授权可按 `picgo-upload` Skill 或用户指定图床上传，记录本地文件与绝对 HTTPS URL 的对应关系。动图保留 GIF，不改成静态图。
3. 在单独的发布候选 Markdown/HTML 中替换引用，保留原文和本地预览。非 HTTP(S) 引用全部解决后重新运行兼容与图片检查；远程 URL 存在不代表图片可访问，仍需核验加载。
4. 进入 `references/opencli-injection.md` 的已授权注入流程，由微信转存图片并验证转存结果。

转换器不自动上传；注入器已有的远程图片压缩/重试也不负责上传本地文件。

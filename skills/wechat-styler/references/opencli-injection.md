# opencli 注入微信编辑器

微信编辑器会过滤粘贴内容中的 `<animate>`。`scripts/inject-to-wechat.mjs` 通过 opencli 直接注入 DOM，并负责标题、摘要、封面、图片转存和草稿验证。

## 前置条件

- `opencli doctor` 显示 daemon、extension 和 profile 已连接
- Chrome 已登录微信公众号后台
- 编辑器页面已经打开，或已有可用的编辑器 URL
- 自动图片优化需要 macOS `sips` 和本机 PicGo/PicList 服务

## 推荐用法

```bash
node scripts/inject-to-wechat.mjs article_wechat.html \
  --reuse-current \
  --title "公众号标题" \
  --summary "转发摘要" \
  --sync-cover-from-body \
  --save-draft \
  --report /tmp/wechat-publish-report.json
```

使用 URL 打开编辑器：

```bash
export OPENCLI_PROFILE=4nwbtdn6
export WX_EDITOR_URL="https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2..."
node scripts/inject-to-wechat.mjs article_wechat.html --save-draft
```

只读检查已打开的草稿：

```bash
node scripts/inject-to-wechat.mjs article_wechat.html --reuse-current --verify-only
```

## 运行流程

```text
读取 data-wechat-root 内容根节点
→ 轮询等待正文编辑器
→ 预检并压缩超过 2MB 的远程图片
→ UTF-8 解码后一次性注入正文
→ 等待微信把图片转存到 mmbiz/qpic
→ 对失败图片压缩、换图床并重新注入
→ 独立同步可见标题、#title、摘要和作者
→ 可选把正文第一张图设为公众号封面
→ 校验图片、SVG、动画和正文
→ 可选保存草稿
→ 通过 appmsgid 与历史记录确认保存
```

## 编辑器定位规则

| 区域 | 优先选择器 | 兜底策略 |
|---|---|---|
| 标题 | `.title-editor__input .ProseMirror` | `#title` |
| 正文 | `.rich_media_content .ProseMirror` | 排除标题后高度最大的可见 ProseMirror |
| 旧版正文 | `#ueditor_0 [contenteditable=true]` | 无 |

公众号页面同时存在标题和正文两个 ProseMirror。正文定位必须排除 `.title-editor__input`，禁止使用无约束的 `document.querySelector('.ProseMirror')`。

## 图片策略

- 默认检查远程图片的 `Content-Length`
- 超过 2MB 时下载到临时目录
- 使用 `sips` 转成 JPEG，最长边限制为 1920px，质量 85
- 通过 PicGo/PicList 上传优化图
- 微信转存失败时读取 `data-cacheurl`，强制优化后重试一次
- 验收时排除 `.ProseMirror-separator`，只统计真实内容图片

可调参数：

```bash
--no-optimize-images
--max-image-bytes 2097152
--max-image-width 1920
--image-timeout 60000
```

## 输出契约

`convert.mjs` 在文章根节点输出：

```html
<section data-wechat-root="article">...</section>
```

`wechat-styler` 注入器和 `post2wechat` 都优先读取该节点。旧 HTML 自动回退到 body 中第一个暖纸背景 section。

## 验收标准

注入成功需要同时满足：

- 标题字段和可见标题一致
- 摘要字段与输入一致
- SVG 与 `<animate>` 数量和 HTML 产物一致
- 内容图片数量一致
- 没有 `#imageStatus_root`
- 没有待转存的外部图片
- 保存模式下 URL 包含 `appmsgid`
- 历史记录或页面状态显示已保存

报告中的 URL 会自动隐藏 token。

# 品牌首尾引导

已确认默认行为：每次公众号排版自动在文章开头和结尾各插入一段智见小蓝引导，正文内容保持不变。由 `scripts/brand-cta.mjs` 实际执行，不依赖 Agent 手工追加。

## 样式选择：`--cta-style gif|svg`

- `gif`（默认，1.18.0 起）：Google Flow 生成的 3D 小蓝视频，绿幕抠像后直接键入文章纸色 `#F5F4ED`，标题和副标题已在像素里。外层 section 与 `<img>` 都不写 `background-color`、边框或说明文字，只做 `width:100%;max-width:360px;margin:0 auto;height:auto;display:block`。1.18.1 起 GIF 内小蓝上方留 30px、下方留 18px 纸色（2x 素材），文首 section 加 `padding-top:24px`、文末加 `padding-bottom:28px`，避免贴住纸色卡片上下沿；`zhijian` 主题的纸色外层另加 `root_radius: 12` 圆角。GIF 托管在 COS（URL 与 SHA256 在 manifest），不随 Skill 分发。
- `svg`（备选）：1.17.0 的透明内联 SVG，矢量小蓝 + 路径文字 + SMIL 循环，无需图床。
- 重复处理时换样式会替换，不会叠放；`--brand-cta none|ending` 与样式正交。

## 开场互斥与开关

- 普通转换与 `--components`：开头引导 + 正文 + 结尾引导。
- 用户明确要求原小蓝打招呼或其他主题开场：传 `--cover --cover-template xiaolan-terminal`（或所选模板），保留 SVG 开场和结尾引导，省略开头引导。
- 输入已含带 `<animate*>` 的用户 SVG：同样省略开头引导。检测会排除带 `data-zhijian-cta` 的 SVG，本 Skill 自己的引导不会被当成用户开场。
- 用户要求不放关注/互动引导：传 `--brand-cta none`；仅需结尾：`--brand-cta ending`。默认 `auto`。

## 位置与去重

- 开头引导紧跟文章根节点，在正文第一个元素之前；结尾引导在文末落地线（`end-mark`）和话题标签之后，是根节点最后一个子元素。
- 插入前先清掉所有受管引导，重复处理同一份 HTML 结果不变，不会叠放两份：
  - v7 GIF：`<section data-wechat-cta="opening|ending" data-zhijian-cta="v7-flow-gif">` 外层，以及 `src` 命中 manifest 当前 GIF 文件名或 URL 的 `<img>`。
  - v6 SVG：`<section data-wechat-cta="opening|ending" data-zhijian-cta="v6">` 外层，以及脱离外层的 `<svg data-zhijian-cta="opening|ending">`。
  - 历史 GIF 版 v5（1.16.0 及以前）：外层 `data-wechat-cta` section、带 `data-wechat-cta-image` 的 `<img>`，以及 `src` 命中 manifest `legacy` 中旧文件名或旧 URL 的 `<img>`（含查询参数、被转存到其他域名但保留文件名的情况）。
- 用户其他图片和 SVG 一律保留。

## 输出形态与公众号兼容

默认（`gif`）每段输出为一行：

```html
<section data-wechat-cta="opening" data-zhijian-cta="v7-flow-gif" style="max-width:<主题宽度>px;margin:0 auto 18px;padding:24px 0 0;line-height:0;"><img data-wechat-cta-image="opening" src="https://…/zhijian-cta-opening-flow-376b7c890008.gif" alt="…" width="720" height="272" style="display:block;width:100%;max-width:360px;height:auto;margin:0 auto;border:0;" /></section>
```

结尾引导同构（`720×300`，`margin:24px auto 0`）。`svg` 样式输出为：

```html
<section data-wechat-cta="opening" data-zhijian-cta="v6" style="max-width:<主题宽度>px;margin:0 auto 18px;padding:24px 0 0;line-height:0;"><svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 360 136" style="display:block;width:100%;height:auto;" role="img" aria-label="…" data-alt="…" data-semantic-text="…" data-zhijian-cta="opening">…</svg></section>
```

以下 SVG 兼容规则只适用于 `svg` 样式：

- SVG 内部只用 `<g>`、`<path>`、`<ellipse>` 等基础图形与 `<animate>` / `<animateTransform>`；没有 `id`、`class`、`<style>`、`<defs>`、`<use>`、`<image>`、`<text>`、`url(`、`data:`、渐变和滤镜。分组只用 `data-part`。
- 替代文本放在 `data-alt`（同时保留 `aria-label` 与 `data-semantic-text`）。公众号可能清洗 `aria-*` 与 `data-*`，文字已转成路径，即使属性被剥离画面仍完整。
- `scripts/validate.mjs` 按行把 `<svg>…</svg>` 抹成占位符后再检查，单行引导的 SVG 内部不会被它扫到；内部禁用项由 `tests/brand-cta.test.mjs` 单独断言。
- `--expect-zhijian` 移动端 QA 会检查两段引导没有背景色，且是 v7 Flow GIF 或含 `<path>` 的内联 SVG。

## SVG 备选的动画

全部为 SMIL、`repeatCount="indefinite"`，删掉所有 `<animate*>` 后的静态基态是睁眼站立、文字完整：

- 开头：挥手 3.2s（前半段挥两次后停住）、眨眼 3.8s、上半身呼吸。
- 结尾：递卡片 2.8s、眨眼 4.2s、呼吸。

动画从页面加载起持续循环，没有“只播一次”的定格逻辑；读者滚动到文末时看到的是循环中的某一帧，不存在错过动画的问题。

## 素材

`assets/brand-cta/manifest.json`（版本 `2026-10-13-v7-flow-gif`）三组记录：

- `assets`（默认 GIF）：`url`、`width`、`height`、`frames`、`fps`、`bytes`、`sha256`、`alt`、`source`。开头 720×272、48 帧 @12fps（1076375 字节）；结尾 720×300、72 帧 @10fps（1695438 字节）；均无限循环。来源：Google Flow Omni 1.1 Flash reference-to-video，绿幕抠像后键入 `#F5F4ED`；原始素材在 Vault `05_附件/wechat-cta-flow-20261013`。远端 SHA-256 已核对。GIF 不在仓库内，转换器只引用 URL；替换素材须重新上传并同步 manifest 与测试。
- `fallback`（SVG 备选，`2026-10-13-v6-svg`）：`file`、`sha256`、`viewBox`、`alt`、`format: "inline-svg"`。转换器读取 SVG 时校验 SHA256 和 viewBox，不一致直接报错。SVG 由智见小蓝 v003 矢量源脚本生成，重新生成后复制到本目录并同步 manifest。
- `legacy`：旧 GIF（`2026-09-12-v4` 白底版）的文件名、URL 与 SHA256，只用于历史稿件去重。

GIF 因像素已含纸色，只适用于纸色 `#F5F4ED` 正文；换到其他底色的主题时用 `--cta-style svg` 或 `--brand-cta none`。

首尾引导不作为文章封面；封面使用正文内容图或显式指定图片。

## 未验证项

- v7 GIF：真实公众号草稿保存后图片是否被转存、是否仍循环播放，iOS 与 Android 读者端实看尚未做。
- 以下为 SVG 备选的未验证项：
- 真实公众号编辑器注入、草稿保存后的回读尚未做：需确认 `<path>` 数量、`<animate*>` 仍在，`data-part` 等属性被剥离后角色完整。
- 读者端（iOS 与 Android 微信）尚未实看：需等待 10 秒以上确认循环动画持续，确认 `stroke-dasharray` 缝线保留。
- 两处结构性 opacity：`eyes-closed` 组基态 `opacity="0"`、`ground` 组 `opacity="0.08"`。若被清洗，前者会让闭眼线叠在睁眼上，后者会让脚下阴影变成实心黑椭圆，回读时专门核对。
- 两段 SVG 约 30KB 与 41KB，主要是文字路径；需要压缩时可在生成端降低坐标精度。

纯 HTML 本地预览不代表微信公众号真实读者端验收，发布与保存草稿仍沿用原授权边界。

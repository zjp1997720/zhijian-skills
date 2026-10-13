# 品牌首尾引导

已确认默认行为：每次公众号排版自动在文章开头和结尾各插入一段智见小蓝引导，正文内容保持不变。由 `scripts/brand-cta.mjs` 实际执行，不依赖 Agent 手工追加。

自 1.17.0 起引导为**透明背景的内联 SVG**：矢量小蓝 + 已转成路径的文字 + SMIL 循环动画。外层 section 不写 `background-color`，引导直接吃正文底色，在 `zhijian` 纸色 `#F5F4ED` 上不再出现白底色块；也不再依赖图床或上传。

## 开场互斥与开关

- 普通转换与 `--components`：开头引导 + 正文 + 结尾引导。
- 用户明确要求原小蓝打招呼或其他主题开场：传 `--cover --cover-template xiaolan-terminal`（或所选模板），保留 SVG 开场和结尾引导，省略开头引导。
- 输入已含带 `<animate*>` 的用户 SVG：同样省略开头引导。检测会排除带 `data-zhijian-cta` 的 SVG，本 Skill 自己的引导不会被当成用户开场。
- 用户要求不放关注/互动引导：传 `--brand-cta none`；仅需结尾：`--brand-cta ending`。默认 `auto`。

## 位置与去重

- 开头引导紧跟文章根节点，在正文第一个元素之前；结尾引导在文末落地线（`end-mark`）和话题标签之后，是根节点最后一个子元素。
- 插入前先清掉所有受管引导，重复处理同一份 HTML 结果不变，不会叠放两份：
  - 新版：`<section data-wechat-cta="opening|ending" data-zhijian-cta="v6">` 外层，以及脱离外层的 `<svg data-zhijian-cta="opening|ending">`。
  - 历史 GIF 版（1.16.0 及以前）：外层 `data-wechat-cta` section、带 `data-wechat-cta-image` 的 `<img>`，以及 `src` 命中 manifest `legacy` 中旧文件名或旧 URL 的 `<img>`（含查询参数、被转存到其他域名但保留文件名的情况）。
- 用户其他图片和 SVG 一律保留。

## 输出形态与公众号兼容

每段引导输出为一行：

```html
<section data-wechat-cta="opening" data-zhijian-cta="v6" style="max-width:<主题宽度>px;margin:0 auto 18px;padding:0;line-height:0;"><svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 360 136" style="display:block;width:100%;height:auto;" role="img" aria-label="…" data-alt="…" data-semantic-text="…" data-zhijian-cta="opening">…</svg></section>
```

- SVG 内部只用 `<g>`、`<path>`、`<ellipse>` 等基础图形与 `<animate>` / `<animateTransform>`；没有 `id`、`class`、`<style>`、`<defs>`、`<use>`、`<image>`、`<text>`、`url(`、`data:`、渐变和滤镜。分组只用 `data-part`。
- 替代文本放在 `data-alt`（同时保留 `aria-label` 与 `data-semantic-text`）。公众号可能清洗 `aria-*` 与 `data-*`，文字已转成路径，即使属性被剥离画面仍完整。
- `scripts/validate.mjs` 按行把 `<svg>…</svg>` 抹成占位符后再检查，单行引导的 SVG 内部不会被它扫到；内部禁用项由 `tests/brand-cta.test.mjs` 单独断言。
- `--expect-zhijian` 移动端 QA 会检查两段引导没有背景色且是含 `<path>` 的内联 SVG。

## 动画

全部为 SMIL、`repeatCount="indefinite"`，删掉所有 `<animate*>` 后的静态基态是睁眼站立、文字完整：

- 开头：挥手 3.2s（前半段挥两次后停住）、眨眼 3.8s、上半身呼吸。
- 结尾：递卡片 2.8s、眨眼 4.2s、呼吸。

动画从页面加载起持续循环，没有“只播一次”的定格逻辑；读者滚动到文末时看到的是循环中的某一帧，不存在错过动画的问题。

## 素材

`assets/brand-cta/manifest.json`（版本 `2026-10-13-v6-svg`）记录每段引导的 `file`、`sha256`、`viewBox`、`width`、`height`、`alt` 与 `format: "inline-svg"`。转换器读取 SVG 时校验 SHA256 和 viewBox，不一致直接报错，防止素材被悄悄替换。SVG 由智见小蓝 v003 矢量源脚本生成，重新生成后复制到本目录并同步 manifest。

`legacy` 字段保留旧 GIF（`2026-09-12-v4`，白底、副标题为仓耳今楷、2.4 秒循环）的文件名、URL 与 SHA256，只用于历史稿件去重；GIF 文件本身已不随 Skill 分发。

首尾引导不作为文章封面；封面使用正文内容图或显式指定图片。

## 未验证项

- 真实公众号编辑器注入、草稿保存后的回读尚未做：需确认 `<path>` 数量、`<animate*>` 仍在，`data-part` 等属性被剥离后角色完整。
- 读者端（iOS 与 Android 微信）尚未实看：需等待 10 秒以上确认循环动画持续，确认 `stroke-dasharray` 缝线保留。
- 两处结构性 opacity：`eyes-closed` 组基态 `opacity="0"`、`ground` 组 `opacity="0.08"`。若被清洗，前者会让闭眼线叠在睁眼上，后者会让脚下阴影变成实心黑椭圆，回读时专门核对。
- 两段 SVG 约 30KB 与 41KB，主要是文字路径；需要压缩时可在生成端降低坐标精度。

纯 HTML 本地预览不代表微信公众号真实读者端验收，发布与保存草稿仍沿用原授权边界。

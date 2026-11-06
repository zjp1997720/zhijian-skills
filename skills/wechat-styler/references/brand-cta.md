# 品牌首尾引导

已确认默认行为：每次公众号排版自动在文章开头和结尾各插入一段品牌引导，正文内容保持不变。由 `scripts/brand-cta.mjs` 实际执行，不依赖 Agent 手工追加。

1.19.0 起引导是真人正装照 + 品牌排版的微动态 GIF（2026-11-06 决定：公众号不再使用卡通角色）：开头图是智见AI Logo、「大鹏」、「AI 落地专家」、落地线加赭石圆点、「把 AI 用进真实工作」，右侧是正装照；结尾图是「有用，就留一份」、「点赞 · 收藏 · 转给需要的人」、「关注大鹏，下篇见」，右侧是 Logo；尾图不带落地线与圆点，文末落地线由主题的 `end-mark` 提供。动效为字逐行浮现、落地线画出（仅开头图）、圆点轻微呼吸，停约 5 秒后淡出重来，照片不动；开头图正装照底部渐隐入纸色。

## 样式

- 只有 `gif` 一种（`--cta-style gif` 与不传等价）。GIF 的像素已含纸色 `#F5F4ED`、照片与文字，外层 section 与 `<img>` 都不写 `background-color`、边框或说明文字，`<img>` 只做 `display:block;width:100%;height:auto;margin:0 auto;border:0`，宽度跟随正文列，不再设 `max-width:360px`（素材是 1160 宽，原先 720 宽素材的 360px 上限不再适用）。文首 section 加 `padding-top:24px`、文末加 `padding-bottom:28px`；`zhijian` 主题的纸色外层另有 `root_radius: 12` 圆角。GIF 托管在 COS（URL 与 SHA256 在 manifest），不随 Skill 分发。
- 1.19.0 移除了 `--cta-style svg` 和两个小蓝内联 SVG（`zhijian-cta-opening.svg`、`zhijian-cta-ending.svg`）。传 `--cta-style svg` 会报错；不想要引导用 `--brand-cta none`。
- GIF 因像素已含纸色，只适用于纸色 `#F5F4ED` 正文；其他底色的主题用 `--brand-cta none`。

## 开场互斥与开关

- 普通转换与 `--components`：开头引导 + 正文 + 结尾引导。
- 用户明确要求原小蓝打招呼或其他主题开场：传 `--cover --cover-template xiaolan-terminal`（或所选模板），保留 SVG 开场和结尾引导，省略开头引导。`xiaolan-terminal` 是显式选项，不是引导默认；是否对公众号继续提供，由品牌侧「公众号不用卡通」规则另定。
- 输入已含带 `<animate*>` 的用户 SVG：同样省略开头引导。检测会排除带 `data-zhijian-cta` 的 SVG，本 Skill 自己留下的旧引导不会被当成用户开场。
- 用户要求不放关注/互动引导：传 `--brand-cta none`；仅需结尾：`--brand-cta ending`。默认 `auto`。

## 位置与去重

- 开头引导紧跟文章根节点，在正文第一个元素之前；结尾引导在文末落地线（`end-mark`）和话题标签之后，是根节点最后一个子元素。
- 插入前先清掉所有受管引导，重复处理同一份 HTML 结果不变，不会叠放两份：
  - v8 照片 GIF：`<section data-wechat-cta="opening|ending" data-zhijian-cta="v8-photo-gif">` 外层，以及 `src` 命中 manifest 当前 GIF 文件名或 URL 的 `<img>`。
  - v7 Flow GIF 与 v6 小蓝 SVG：同样按 `data-wechat-cta` 外层、脱离外层的 `<svg data-zhijian-cta="opening|ending">`、`legacy` 中旧 GIF 文件名或 URL 清掉，旧稿重处理会被换成照片版。
  - 历史白底 GIF v5（1.16.0 及以前）：外层 `data-wechat-cta` section、带 `data-wechat-cta-image` 的 `<img>`，以及 `src` 命中 `legacy` 中旧文件名或旧 URL 的 `<img>`（含查询参数、被转存到其他域名但保留文件名的情况）。
- 用户其他图片和 SVG 一律保留。

## 输出形态

每段输出为一行：

```html
<section data-wechat-cta="opening" data-zhijian-cta="v8-photo-gif" style="max-width:<主题宽度>px;margin:0 auto 18px;padding:24px 0 0;line-height:0;"><img data-wechat-cta-image="opening" src="https://…/zhijian-cta-opening-photo-674d9c689c38.gif" alt="…" width="1160" height="498" style="display:block;width:100%;height:auto;margin:0 auto;border:0;" /></section>
```

结尾引导同构（`1160×400`，`margin:24px auto 0`，`padding:0 0 28px`）。`width` / `height` 属性写素材原始尺寸，显示宽度由样式的 `width:100%` 决定；`--expect-zhijian` 移动端 QA 会检查两段引导没有背景色，且标记为 `v8-photo-gif`、图片是 GIF。

## 390px 实页核对（1.19.0，2026-11-06）

用 `tests/fixtures/zhijian-visual-baseline.md` 以 `zhijian` 主题转换，GIF 指到本地文件后在 390px 视口实测：

- 两张图撑满 390px 列宽（缩放 0.336），文字随之缩小：「大鹏」约 32px，「AI 落地专家」约 14px，「把 AI 用进真实工作」与「点赞 · 收藏 · 转给需要的人」约 12px，尾图「有用，就留一份」约 24px、「关注大鹏，下篇见」约 13px。首版（源图小字 24px，手机上约 8px）偏小，已重排放大。
- 落地线：首版尾图自带落地线加圆点，与主题 `end-mark`（正上方 24px）同屏出现两遍，已从尾图去掉；实测整页只剩主题那一条落地线。开头图自带的落地线不与主题的落地线相邻，保留。
- 开头图正装照底部渐隐入纸色，不再有平切的底边。

## 素材

`assets/brand-cta/manifest.json`（版本 `2026-11-06-v8-photo-gif`）两组记录：

- `assets`（默认 GIF）：`url`、`width`、`height`、`frames`、`fps`、`bytes`、`sha256`、`alt`、`source`。开头 1160×498、160 帧 @20fps（413718 字节）；结尾 1160×400、160 帧 @20fps（424209 字节）；均无限循环。来源是本地 HTML 排版（品牌 Logo、正装照抠图、开头图的落地线）经 CDP 逐帧渲染、ffmpeg 调色板出 GIF；源文件在 Vault `05_附件/wechat-cta-photo-20261106`。GIF 不在仓库内，转换器只引用 URL；替换素材须重新上传并同步 manifest 与测试。
- `legacy`：旧版本的文件名、URL 与 SHA256（白底 GIF `2026-09-12-v4`、Flow GIF 1.18.0 与 1.18.1），以及小蓝 SVG 版 `2026-10-13-v6-svg` 的记录（SVG 靠标记识别，不带资产列表），只用于历史稿件去重。

首尾引导不作为文章封面；封面使用正文内容图或显式指定图片。

## 未验证项

- 真实公众号草稿保存后图片是否被转存、是否仍循环播放，iOS 与 Android 读者端实看尚未做。
- 小字行（约 12px）在真机上的可读性，上节只是 390px 实页数值。

纯 HTML 本地预览不代表微信公众号真实读者端验收，发布与保存草稿仍沿用原授权边界。

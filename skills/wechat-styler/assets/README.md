# Visual baselines

- `zhijian-theme-version-comparison-2026-07.jpg`：2026-07 公众号实页新旧主题对照。
- `zhijian-theme-mobile-baseline.png`：`editorial-weighted-2026-07` 在 390px 视口下的可重复基线。
- `xiaolan-terminal-pixel-open.png` / `xiaolan-terminal-pixel-closed.png`：`xiaolan-terminal` 的开放眼与闭眼高密度像素帧。身份源为通过 QA 的智见小蓝 v2 图集（SHA-256 `bea0a78d1d435feb9b6465be41db5144bf529c459da698228a2c9ce1d17ed931`）；两帧保持墨蓝机身、象牙脸屏、点眼、细黑手脚和双按钮，背景为真实透明 Alpha。脸屏左上角的 `>_` 正典提示符由生成器使用同一像素栅格叠加，确保所有姿势位置一致。
- `xiaolan-terminal-wave-mid.png` / `xiaolan-terminal-wave-high.png`：小蓝向读者挥手的半抬与举高手势帧。以现有高精度开眼帧为母版，并以正典桌宠图集 `waving` 行第 1、2 帧作为动作参考；保持透明 Alpha，以 6 秒离散序列循环，不使用连续旋转。

移动端基线由 `tests/fixtures/zhijian-visual-baseline.md` 生成。更新主题时必须重新运行 `references/zhijian-theme-baseline.md` 中的命令，并人工检查标题字体、正文重量、引用对齐和横向溢出。

## Brand CTA GIFs

`brand-cta/manifest.json` records the two default article GIFs, hosted URLs, dimensions and SHA256. Matching local GIFs are included for portable installation and recovery. Generated previews and private source images are not part of this payload.

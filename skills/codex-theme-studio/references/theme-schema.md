# Theme Schema v1

每个主题目录必须包含 `theme.json` 和同目录内的一张 PNG、JPEG 或 WebP。图片文件名必须是 basename，大小不超过 16 MB。

## 必填字段

```json
{
  "schemaVersion": 1,
  "id": "my-theme",
  "name": "My Theme",
  "image": "hero.png",
  "colors": {
    "background": "#F6F5F0",
    "panel": "#FBFAF7",
    "accent": "#536272",
    "secondary": "#273746",
    "text": "#181817"
  }
}
```

颜色接受六位十六进制或受限的 `rgb/rgba`。缺失的安全字段由注入器补默认值。

## 字体

```json
"typography": {
  "uiFamily": "Source Han Serif SC VF, Songti SC, serif",
  "codeFamily": "SF Mono, ui-monospace, monospace",
  "bodyWeight": 500,
  "emphasisWeight": 600,
  "codeWeight": 400
}
```

字体不会随主题自动安装。字体栈必须带系统回退；正文与侧栏使用 `bodyWeight`，选中态和重点控件使用 `emphasisWeight`，代码使用 `codeWeight`。字体值禁止换行和 CSS 分隔字符。

## 圆角与密度

```json
"shape": {
  "controlRadius": 6,
  "cardRadius": 8,
  "heroRadius": 16,
  "composerRadius": 14
},
"density": {
  "homeGap": 24,
  "suggestionMinHeight": 112
}
```

数值单位为像素，注入器按安全范围验证：控件 `0–24`、卡片 `0–32`、Hero `0–40`、输入框 `0–32`、首页间距 `12–40`、建议卡高度 `80–160`。

## 验证

```bash
./scripts/injector.mjs --check-payload --theme-dir /absolute/path/to/theme
```

不要手工拼接注入脚本。用户主题放在运行状态目录，由自定义脚本原子写入；Skill 升级不会覆盖 ID 不同的活动主题。

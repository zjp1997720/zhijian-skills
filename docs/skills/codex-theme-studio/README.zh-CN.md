# Codex Theme Studio

<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="Codex Theme Studio 设计、安装、验证并恢复可逆的 Codex Desktop 主题">
</p>

<p align="center"><strong>把品牌系统和可选的 ImageGen 视觉资产，变成一套可还原、可验证的 macOS Codex Desktop 主题。</strong></p>

<p align="center"><a href="./README.md">English</a> · <a href="https://github.com/zjp1997720/zhijian-skills/tree/main/skills/codex-theme-studio">统一源码</a></p>

当需求已经超出原生配色导出，涉及品牌化皮肤、响应式首页 Banner、任务页背景、注入后视觉修复或完整回退链路时，使用这个 Skill。

这个项目的灵感来源于 [Fei-Away/Codex-Dream-Skin](https://github.com/Fei-Away/Codex-Dream-Skin)。它在上游思路之上，把真实换肤过程沉淀成了可复用的设计、ImageGen、注入、验证与回滚工作流。

## 安装

```bash
npx skills add zjp1997720/zhijian-skills \
  -g -a codex --skill codex-theme-studio --copy -y
```

安装后调用 `$codex-theme-studio`，并提供现有的品牌规范、`codex-theme-v1:` 导出、标注截图和视觉资产。

## 交付内容

- 一份自包含主题目录：图片全部本地化，`theme.json` 经过校验。
- 完整品牌 Token：背景、面板、文字、强调色、选中态、边框、字体和图片位置。
- 可选调用 Codex 内置 `$imagegen`，创作 Banner 或整页背景。
- 只通过本机回环 CDP 注入 CSS 和渲染辅助脚本，不修改签名应用包与 `app.asar`。
- 不可变的原始主题快照和升级前快照，以及暂停、恢复和版本回退命令。
- 对首页、任务页、New Task 瞬时路由、顶部标签、四张功能卡、控件、横向溢出和背景图的严格验证。

ImageGen 不可用时，Skill 会使用随包附带的中性暖纸 Banner。图片生成属于可选宿主能力，不构成安装依赖，也不会静默切换到需要 API Key 的备用通道。

## 工作流程

1. 读取品牌单一事实源，区分 Codex 原生交互与主题自有视觉。
2. 只有设计确实需要时才生成或编辑图片；最终图片必须进入主题目录。
3. 在已安装 Skill 之外组装主题，并完成载荷检查与确定性测试。
4. 默认只安装、不启动；重启正在运行的 Codex 前单独取得明确授权。
5. 验证首页、任务页和 New Task 瞬时状态；一次只修一类缺陷。
6. 交付主题源码、图片来源或提示词、验证证据、备份位置和精确恢复命令。

## 安全机制

运行时只支持官方 macOS Codex（`com.openai.codex`）。它会验证应用身份，把 Chrome DevTools Protocol 限制在 `127.0.0.1`，拒绝外部目标，校验图片路径与大小，保留原生主题键，并通过原子交换安装运行时和主题。

它不会修改应用包、认证信息、代码仓库或对话数据。设计和安装授权不等于停止正在运行应用的授权。

完整边界见[安全与回滚契约](https://github.com/zjp1997720/zhijian-skills/blob/main/skills/codex-theme-studio/references/safety-and-rollback.md)和[验证契约](https://github.com/zjp1997720/zhijian-skills/blob/main/skills/codex-theme-studio/references/verification-contract.md)。

## 环境要求

- macOS 与官方 Codex Desktop
- Node.js 20+
- Bash 和 macOS 标准命令行工具
- 新建位图时可选使用内置 ImageGen 能力

主题运行时不需要 API Key，也不会发起外网请求；唯一实时网络面是本机 DevTools 端点。

## 开发验证

```bash
bash skills/codex-theme-studio/tests/run-tests.sh
node skills/codex-theme-studio/scripts/injector.mjs --check-payload
```

实机 Doctor 检查依赖本机 Codex 安装，因此与跨平台确定性测试分开执行。

## 来源与协议

本项目的灵感来源于 MIT 协议的 [`Fei-Away/Codex-Dream-Skin`](https://github.com/Fei-Away/Codex-Dream-Skin)，注入架构也基于该项目演进而来。本 Skill 增加了通用主题契约、可选 ImageGen 资产、签名与回环校验、不可变备份、响应式路由修复和公开打包。详情见随包提供的 `NOTICE.md`、`UPSTREAM_COMMIT` 和 `LICENSE`。

Codex 与 OpenAI 是其各自权利人的商标。本项目是非官方社区项目，未获得 OpenAI 或上游项目背书。

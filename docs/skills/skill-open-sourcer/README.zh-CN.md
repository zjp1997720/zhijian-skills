# Skill Open Sourcer

<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="Skill Open Sourcer 在统一源码和镜像发布前验证完整 Skill">
</p>

<p align="center"><strong>把本地 Agent Skill 做成完整、经过验证、可以可靠安装的开源发布包。</strong></p>

<p align="center"><a href="./README.md">English</a> · <a href="https://github.com/zjp1997720/zhijian-skills/tree/main/skills/skill-open-sourcer">统一源码</a> · <a href="https://github.com/zjp1997720/skill-open-sourcer">独立镜像</a></p>

当一个本地 Skill 已经成熟，需要变成载荷完整、可独立安装、发布可验证的开源包时使用它。

## Agent 安装

```bash
npx skills add zjp1997720/skill-open-sourcer -g -a codex --skill skill-open-sourcer -y
```

安装前查看仓库里的 skill：

```bash
npx skills add zjp1997720/skill-open-sourcer --list
```

安装后，直接让 Codex 使用 `$skill-open-sourcer`，并给它一个本地 `SKILL.md` 路径或 skill 目录。

## 环境要求

- Python 3
- Git
- Node.js 与 `npx`
- GitHub 发布通道，满足其一即可：
  - 已认证的 `gh` CLI
  - Agent 运行时里的 GitHub MCP/app
  - 已配置并可推送的 `origin` remote

## 功能

- 审计本地 skill 是否适合公开发布。
- 检查明显风险：密钥、个人绝对路径、缓存文件、大型生成物、授权不明资产。
- 打包成 `npx skills` 可识别的结构。
- 生成根目录 README、中文 README 和 LICENSE。
- 发布前校验 skill 结构和 `npx skills` 发现能力。
- 在安全通道可用时发布到 GitHub。
- 输出安装命令、GitHub 元信息建议和发布文案。
- 通过 Registry、独立版本、不可变发布候选、自动生成兼容镜像和可回滚的本地 Harness 链接，统一治理多 Skill 仓库。

## 原理

这个 skill 把“开源一个本地 skill”当成发布流程处理，而不是简单复制文件。

它会先检查环境，再扫描源 skill 的公开风险。风险通过后，才创建一个干净的发布仓库，并按发布形态把 agent 要读的内容和人要看的说明放在合适位置。

具体执行流程写在统一源码的 [`SKILL.md`](https://github.com/zjp1997720/zhijian-skills/blob/main/skills/skill-open-sourcer/SKILL.md)。人通常不需要手动运行其中的辅助脚本。

## 示例请求

```text
Use $skill-open-sourcer to publish ~/.codex/skills/my-skill as an open-source repo.
Use $skill-open-sourcer to package this local SKILL.md for npx skills installation.
Use $skill-open-sourcer to audit this skill before I share it publicly.
```

## 独立镜像结构

```text
.
├── README.md
├── README.zh-CN.md
├── LICENSE
├── SOURCE.json
└── skills/skill-open-sourcer/
    ├── SKILL.md
    ├── agents/openai.yaml
    ├── references/
    └── scripts/
```

## 许可证

[MIT](LICENSE)

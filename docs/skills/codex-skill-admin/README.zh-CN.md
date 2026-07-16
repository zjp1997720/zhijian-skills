# Codex Skill Admin

[English](README.md)

Codex Skill Admin 是一个 Codex 专用的 agent skill，用来通过 Codex 本地 `app-server` API 审计、关闭、恢复和验证本机 Codex skills。

适合在你想节省 prompt token 时使用：它会帮你找出近期没有使用证据的 skill，并把它们关闭，而不是卸载。

## Agent 安装

```bash
npx skills add zjp1997720/codex-skill-admin -g -a codex --skill codex-skill-admin -y
```

安装前查看仓库里有哪些 skill：

```bash
npx skills add zjp1997720/codex-skill-admin --list
```

安装后，直接让 Codex 使用 `$codex-skill-admin` 处理 skill 清理任务。Agent 需要执行的流程写在 `skills/codex-skill-admin/SKILL.md`，人不需要手动跑里面的辅助脚本。

## 环境要求

- 支持 `codex app-server` 的 Codex CLI
- Python 3.10+

## 功能

- 列出当前启用和关闭的 Codex skills。
- 根据本地 Codex session 证据审计近期使用过的 skills。
- 先 dry-run，再关闭近期未使用的已启用 skills。
- 支持低频清理，例如关闭最近 10 天使用不超过 2 次的 skills。
- 从备份恢复上一次关闭操作。
- 统计下一次 Codex prompt 中实际可见的 skill 数量。
- 区分桌面 UI 总数和真正影响 token 的启用数 / prompt 可见数。

## 原理

Codex 会把已启用 skill 的元信息放进 prompt，让模型判断什么时候该用哪个 skill。启用的 skill 越多，prompt 越重；即使很多 skill 当前根本用不上，它们也会占用上下文预算。

这个工具不靠猜。它会读取本机 Codex session 记录，查找哪些 `SKILL.md` 在最近一段时间被真正读过。读过，就算使用过；没读过，或者使用次数不超过你设置的 `--max-uses` 阈值，就进入关闭候选。

关闭不是删除。脚本调用 Codex 本地 `skills/config/write` API，把 skill 标记为 disabled，同时写一份本地备份，后面可以恢复。桌面 UI 顶部的「技能」数字可能不变，因为文件还在；真正影响 token 的是启用数和 prompt 里实际可见的 skill 数。

## 安全默认值

- `disable-unused` 默认只 dry-run，必须传 `--apply` 才会真正关闭。
- `set` 默认只 dry-run，必须传 `--apply` 才会真正写入配置。
- system skills 默认保留。只有明确传 `--include-system` 时才会把 system skills 纳入候选。
- apply 模式的备份写入 `${CODEX_HOME:-$HOME/.codex}/backup/`。
- 备份文件包含本机 skill 路径和使用证据，按私有本机诊断数据处理。

## 示例请求

```text
Use $codex-skill-admin to audit skills I have not used in the last 30 days.
Use $codex-skill-admin to disable skills used at most 2 times in the last 10 days.
Use $codex-skill-admin to restore the last disable run.
Use $codex-skill-admin to verify whether the cleanup reduced prompt-visible skills.
```

桌面 UI 顶部的「技能」数字可能不变，因为它统计的是已安装/已发现的 skill，也包括 disabled 的 skill。真正有用的成功指标是启用数下降、prompt 里实际可见的 skill 数下降。

## 仓库结构

```text
.
├── README.md
├── README.zh-CN.md
├── LICENSE
├── skills.sh.json
└── skills/
    └── codex-skill-admin/
        ├── SKILL.md
        ├── agents/openai.yaml
        ├── scripts/codex_skill_admin.py
        └── references/app-server-protocol.md
```

## 许可证

MIT

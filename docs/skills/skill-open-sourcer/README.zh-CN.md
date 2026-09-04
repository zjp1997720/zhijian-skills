# Skill Open Sourcer

<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="Skill Open Sourcer 通过一个统一 Portfolio 验证并发布完整 Skill">
</p>

<p align="center"><strong>把本地 Agent Skill 做成完整、经过验证、进入智见 Skills 的公开版本。</strong></p>

<p align="center"><a href="./README.md">English</a> · <a href="https://github.com/zjp1997720/zhijian-skills/tree/main/skills/skill-open-sourcer">统一源码</a></p>

当一个本地 Skill 已经成熟，需要公开并支持可靠安装时使用它。所有发布统一进入 `zjp1997720/zhijian-skills`，整个流程不会创建独立 Skill 仓库。

## 安装

```bash
npx skills add zjp1997720/zhijian-skills \
  -g -a codex --skill skill-open-sourcer --copy -y
```

安装后调用 `$skill-open-sourcer`，并提供本地 `SKILL.md` 或 Skill 目录。

## 环境要求

- Python 3、Git、Node.js 与 `npx`
- 已验证的 `zjp1997720/zhijian-skills` 本地工作区
- 用户要求正式发布时，需要该统一仓库的推送权限

## 功能

- 扫描真实字面量密钥、个人路径、缓存、私有数据、越界链接和授权不清的资产；允许运行时读取凭证，并对扫描输出中的命中值统一脱敏。
- 把完整载荷导入 `skills/<name>/`，同步建立中英文文档、Changelog、Registry 和总目录入口。
- 锁定八字段发布故事，选择 `clean-doc` 或 `proof-led` 呈现层级，并拒绝跨 Skill 复用的通用 Hero 模板。
- 验证 Skill、整个 Portfolio、声明测试、README 结构与资产、本地发现和隔离复制安装。
- 用单一 fail-fast 校验器执行隔离安装，同时检查安装退出码、实体化和逐文件 SHA-256，后续 Shell 命令不能掩盖前一步失败。
- 以显式的统一仓库根目录作为 README 共享链接的审计边界。
- 使用顶层 CLI 帮助和只读列表发现，避免帮助探测误触真实安装。
- 默认用 `--skill <name>` 只规划一个 Skill，避免把其他待发布改动带入候选集；只有明确执行 Portfolio 发布波次时才使用 `--all`。
- 记录并复查实时远端 SHA，用 `needs-sync` 和 pre-commit 守卫阻断旧基线 checkout，并通过短生命周期分支与 PR 发布。
- 只合并到统一仓库，只创建 `<skill>/v<version>` Tag。
- 输出统一安装命令和发布文案。

## 原理

这个 Skill 把“开源一个 Skill”定义为向统一 Portfolio 导入。直接提供 `SKILL.md` 只用于识别导入对象，不再触发新建仓库模式。README 会先锁定受众、重复问题、价值、证据、首次动作、安全边界、原生素材和呈现层级；采用 `proof-led` 时，再从 Skill 的真实机制或输出中推导独立构图。`verify_isolated_install.py` 会在临时 HOME 与工作区中以 copy 模式安装单个 Skill，并与统一源码逐文件比较。发布计划绑定实时远端 SHA；临时集成 clone 会冻结原 checkout，直到它完成同步。受治理的 Skill 必须提交 manifest 声明的 `trust_report` 与 `output_quality_scorecard`，被忽略的本地报告不能充当发布证据。统一远端、代码归属、安全扫描、载荷完整性、治理基线、README 证据、安装证明或远端历史连续性任何一项失败，发布都会停止。

## 示例请求

```text
使用 $skill-open-sourcer 把这个本地 Skill 加入智见 Skills 并发布。
使用 $skill-open-sourcer 在导入 Portfolio 前审计这个 SKILL.md。
使用 $skill-open-sourcer 发布这个 Skill 的下一个统一仓库版本。
```

## 统一仓库结构

```text
skills/<name>/          Agent 安装的完整载荷
docs/skills/<name>/     面向人的中英文文档
docs/changelogs/        各 Skill 独立发布记录
registry/skills.json    版本、验证、权限和 Harness 声明
```

## 安全边界

流程不会创建独立 GitHub 仓库、写入镜像元数据、强制推送或改写已发布 Tag。README 链接只能解析到显式选择的统一仓库内部，不能越过仓库边界。缺失证据会继续标记为缺失。

## 许可证

[MIT](../../../LICENSE)

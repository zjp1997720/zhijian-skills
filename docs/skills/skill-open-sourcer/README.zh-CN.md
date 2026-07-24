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

- 扫描密钥、个人路径、缓存、私有数据、越界链接和授权不清的资产。
- 把完整载荷导入 `skills/<name>/`，同步建立中英文文档、Changelog、Registry 和总目录入口。
- 验证 Skill、整个 Portfolio、声明测试、README、本地发现和隔离复制安装。
- 以显式的统一仓库根目录作为 README 共享链接的审计边界。
- 使用顶层 CLI 帮助和只读列表发现，避免帮助探测误触真实安装。
- 只推送统一仓库，只创建 `<skill>/v<version>` Tag。
- 输出统一安装命令和发布文案。

## 原理

这个 Skill 把“开源一个 Skill”定义为向统一 Portfolio 导入。直接提供 `SKILL.md` 只用于识别导入对象，不再触发新建仓库模式。统一远端、代码归属、安全扫描、载荷完整性或安装证据任何一项失败，发布都会停止。

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

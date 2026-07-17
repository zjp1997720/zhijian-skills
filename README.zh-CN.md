# 智见 Skills

<p align="center">
  <img src="./assets/readme/portfolio-hero.svg" width="100%" alt="智见 Skills：由一个统一源码管理八个专注的 Agent Skill">
</p>

<p align="center"><strong>从一个可信源按需安装 Agent Skill；每个安装包都完整，每次发布都独立验证。</strong></p>

<p align="center">
  <a href="./README.md">English</a> ·
  <a href="#选择一个-skill">浏览目录</a> ·
  <a href="./CONTRIBUTING.md">参与贡献</a>
</p>

智见 Skills 是 8 个专注型 Agent Skill 的统一源码，覆盖 Codex 管理、知识系统、内容调研、信息设计与发布流程。

## 30 秒开始使用

查看全部 8 个 Skill：

```bash
npx skills add zjp1997720/zhijian-skills --list
```

只安装当前需要的 Skill：

```bash
npx skills add zjp1997720/zhijian-skills --skill wechat-styler
```

全局安装到指定 Harness：

```bash
npx skills add zjp1997720/zhijian-skills \
  --skill codex-model-routing-team --agent codex --global --copy --yes
```

> 原有独立仓库继续作为自动生成的兼容镜像保留。新的 Issue、功能建议和代码贡献统一进入本仓库。

## 选择一个 Skill

| 场景 | Skill | 直接得到什么 | 文档 |
| --- | --- | --- | --- |
| Codex 管理 | [`codex-doctor`](docs/skills/codex-doctor/README.zh-CN.md) | 只读诊断上下文、配置和工作区漂移 | [文档](docs/skills/codex-doctor/README.zh-CN.md) |
| Codex 管理 | [`codex-model-routing-team`](docs/skills/codex-model-routing-team/README.zh-CN.md) | 把后台任务分配给明确的模型和推理强度 | [文档](docs/skills/codex-model-routing-team/README.zh-CN.md) |
| Codex 管理 | [`codex-skill-admin`](docs/skills/codex-skill-admin/README.zh-CN.md) | 审计、关闭、恢复并验证本地 Codex Skill | [文档](docs/skills/codex-skill-admin/README.zh-CN.md) |
| 知识系统 | [`enterprise-clone-builder`](docs/skills/enterprise-clone-builder/README.zh-CN.md) | 从企业证据构建结构化数字分身仓库 | [文档](docs/skills/enterprise-clone-builder/README.zh-CN.md) |
| 信息设计 | [`html-express`](docs/skills/html-express/README.zh-CN.md) | 把高密度材料做成自包含 HTML 报告 | [文档](docs/skills/html-express/README.zh-CN.md) |
| 发布治理 | [`skill-open-sourcer`](docs/skills/skill-open-sourcer/README.zh-CN.md) | 审计、打包、文档化、验证并发布 Agent Skill | [文档](docs/skills/skill-open-sourcer/README.zh-CN.md) |
| 内容调研 | [`wechat-article-search`](docs/skills/wechat-article-search/README.zh-CN.md) | 把公众号关键词搜索结果输出为结构化 JSON | [文档](docs/skills/wechat-article-search/README.zh-CN.md) |
| 内容发布 | [`wechat-styler`](docs/skills/wechat-styler/README.zh-CN.md) | 把 Markdown 转成公众号兼容的精排内联 HTML | [文档](docs/skills/wechat-styler/README.zh-CN.md) |

## 为什么使用统一仓库

- **只有一个可编辑源。** 所有公开 Skill 都在本仓库 `main` 分支维护。
- **安装包保持完整。** 每个 Skill 依赖的脚本、参考资料、主题和资源都会一起安装。
- **每个 Skill 独立发版。** 版本、Changelog、Tag、测试和独立兼容镜像互不捆绑。

`codex-model-routing-team` 可以手动点名，也可以通过文档提供的 `AGENTS.md` 授权块，在复杂并行任务中自动触发。

## 仓库模型

```text
skills/<name>/          Agent 实际安装的完整载荷
docs/skills/<name>/     面向人的中英文文档
registry/skills.json    版本、镜像、验证和 Harness 支持声明
assets/readme/          Portfolio 视觉资产
```

独立仓库由本仓库通过正常 Commit 自动生成。旧链接和历史继续保留，源码修改与社区协作统一回到这里。

## 贡献与协议

提交 Issue 或 PR 前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。Portfolio 使用 [MIT License](LICENSE)；各 Skill 的第三方声明继续随对应安装包发布。

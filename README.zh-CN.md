# 智见 Skills

这是智见 AI 公开 Skills 的唯一可编辑源码仓库。

## 安装

查看全部可用 Skill：

```bash
npx skills add zjp1997720/zhijian-skills --list
```

只安装一个 Skill：

```bash
npx skills add zjp1997720/zhijian-skills --skill wechat-styler
```

需要全局安装到指定 Harness 时使用：

```bash
npx skills add zjp1997720/zhijian-skills \
  --skill codex-model-routing-team --agent codex --global --copy --yes
```

原有独立仓库继续作为自动生成的兼容镜像保留。新的 Issue、功能建议和代码贡献统一提交到本仓库。

## Skill 列表

| Skill | 用途 | 文档 | 兼容镜像 |
| --- | --- | --- | --- |
| `codex-doctor` | 只读检查 Codex 与工作区健康状态 | [文档](docs/skills/codex-doctor/README.zh-CN.md) | [镜像](https://github.com/zjp1997720/codex-doctor) |
| `codex-model-routing-team` | 使用不同模型和推理强度编排 Codex 后台任务 | [文档](docs/skills/codex-model-routing-team/README.zh-CN.md) | [镜像](https://github.com/zjp1997720/codex-model-routing-team) |
| `codex-skill-admin` | 管理 Codex Skill 的可见、启用、禁用与恢复 | [文档](docs/skills/codex-skill-admin/README.zh-CN.md) | [镜像](https://github.com/zjp1997720/codex-skill-admin) |
| `enterprise-clone-builder` | 构建标准化企业数字分身仓库 | [文档](docs/skills/enterprise-clone-builder/README.zh-CN.md) | [镜像](https://github.com/zjp1997720/enterprise-clone-builder) |
| `html-express` | 把高密度信息做成单文件 HTML 报告 | [文档](docs/skills/html-express/README.zh-CN.md) | [镜像](https://github.com/zjp1997720/html-express) |
| `skill-open-sourcer` | 审计、打包、文档化并发布 Agent Skill | [文档](docs/skills/skill-open-sourcer/README.zh-CN.md) | [镜像](https://github.com/zjp1997720/skill-open-sourcer) |
| `wechat-article-search` | 搜索微信公众号文章 | [文档](docs/skills/wechat-article-search/README.zh-CN.md) | [镜像](https://github.com/zjp1997720/wechat-article-search) |
| `wechat-styler` | 把 Markdown 转为公众号可用 HTML | [文档](docs/skills/wechat-styler/README.zh-CN.md) | [镜像](https://github.com/zjp1997720/wechat-styler) |

`codex-model-routing-team` 既可以手动点名使用，也可以在 Codex 中自动触发。它的中文文档已经提供可复制到 `AGENTS.md` 的长期授权配置。

## 治理方式

- `main` 是唯一可编辑源。
- `skills/<name>/` 是完整安装包。
- `registry/skills.json` 统一声明版本、镜像、验证、安全能力和 Harness 支持。
- 独立仓库由本仓库生成，禁止人工双向编辑。
- 每个 Skill 独立发版并维护 Changelog。

贡献和验证规则见 [CONTRIBUTING.md](CONTRIBUTING.md)。

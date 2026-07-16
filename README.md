# Zhijian Skills

Canonical source for the public Skills maintained by [Zhijian AI](https://github.com/zjp1997720).

## Install

List the available Skills:

```bash
npx skills add zjp1997720/zhijian-skills --list
```

Install one Skill:

```bash
npx skills add zjp1997720/zhijian-skills --skill wechat-styler
```

The standalone repositories remain available as generated compatibility mirrors. New Issues and contributions belong here.

## Skills

| Skill | Purpose | Documentation |
| --- | --- | --- |
| `codex-doctor` | Read-only Codex and workspace health audit | [Docs](docs/skills/codex-doctor/README.md) |
| `codex-model-routing-team` | Model-routed Codex background task orchestration | [Docs](docs/skills/codex-model-routing-team/README.md) |
| `codex-skill-admin` | Codex Skill visibility and enablement administration | [Docs](docs/skills/codex-skill-admin/README.md) |
| `enterprise-clone-builder` | Build a standardized enterprise digital-clone repository | [Docs](docs/skills/enterprise-clone-builder/README.md) |
| `html-express` | Turn dense information into a self-contained HTML report | [Docs](docs/skills/html-express/README.md) |
| `skill-open-sourcer` | Audit, package, document, and publish agent Skills | [Docs](docs/skills/skill-open-sourcer/README.md) |
| `wechat-article-search` | Search WeChat public-account articles | [Docs](docs/skills/wechat-article-search/README.md) |
| `wechat-styler` | Convert Markdown into WeChat-compatible HTML | [Docs](docs/skills/wechat-styler/README.md) |

## Repository model

- `main` is the only editable source.
- `skills/<name>/` contains the complete install payload.
- `registry/skills.json` defines versions, mirrors, validation, capabilities, and Harness support.
- Standalone repositories are generated from this repository through normal commits.
- Every Skill has an independent release version and Changelog.

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution and validation rules.


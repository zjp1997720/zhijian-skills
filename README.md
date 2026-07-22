# Zhijian Skills

<p align="center">
  <img src="./assets/readme/portfolio-hero.svg" width="100%" alt="Zhijian Skills: one canonical portfolio of ten focused Agent Skills">
</p>

<p align="center"><strong>Install focused Agent Skills from one trusted source, with complete payloads and independently verified releases.</strong></p>

<p align="center">
  <a href="./README.zh-CN.md">简体中文</a> ·
  <a href="#choose-a-skill">Browse the catalog</a> ·
  <a href="./CONTRIBUTING.md">Contribute</a>
</p>

Zhijian Skills is the canonical source for ten focused Agent Skills spanning Codex operations and experience, model infrastructure, knowledge systems, research, information design, and publishing.

## Start in 30 seconds

List all ten Skills:

```bash
npx skills add zjp1997720/zhijian-skills --list
```

Install only what you need:

```bash
npx skills add zjp1997720/zhijian-skills --skill wechat-styler
```

Install globally for a specific Harness:

```bash
npx skills add zjp1997720/zhijian-skills \
  --skill codex-model-routing-team --agent codex --global --copy --yes
```

> This is the only publishing repository. New Skills, releases, Issues, and contributions all belong here.

## Choose a Skill

| Area | Skill | Result | Documentation |
| --- | --- | --- | --- |
| Codex control | [`codex-doctor`](docs/skills/codex-doctor/README.md) | Diagnose context, configuration, and workspace drift without changing files | [Docs](docs/skills/codex-doctor/README.md) |
| Codex control | [`codex-model-routing-team`](docs/skills/codex-model-routing-team/README.md) | Route bounded background tasks to explicit models and reasoning levels | [Docs](docs/skills/codex-model-routing-team/README.md) |
| Codex control | [`codex-skill-admin`](docs/skills/codex-skill-admin/README.md) | Audit, disable, restore, and verify local Codex Skills | [Docs](docs/skills/codex-skill-admin/README.md) |
| Codex experience | [`codex-theme-studio`](docs/skills/codex-theme-studio/README.md) | Design, apply, verify, and restore reversible Codex Desktop themes | [Docs](docs/skills/codex-theme-studio/README.md) |
| Knowledge systems | [`enterprise-clone-builder`](docs/skills/enterprise-clone-builder/README.md) | Build a structured enterprise digital-twin repository from evidence | [Docs](docs/skills/enterprise-clone-builder/README.md) |
| Information design | [`html-express`](docs/skills/html-express/README.md) | Turn dense material into a clear, self-contained HTML report | [Docs](docs/skills/html-express/README.md) |
| Release governance | [`skill-open-sourcer`](docs/skills/skill-open-sourcer/README.md) | Audit, package, document, verify, and publish Agent Skills | [Docs](docs/skills/skill-open-sourcer/README.md) |
| Content research | [`wechat-article-search`](docs/skills/wechat-article-search/README.md) | Discover WeChat public-account articles as structured JSON | [Docs](docs/skills/wechat-article-search/README.md) |
| Editorial publishing | [`wechat-styler`](docs/skills/wechat-styler/README.md) | Convert Markdown into polished, WeChat-compatible inline HTML | [Docs](docs/skills/wechat-styler/README.md) |
| Model infrastructure | [`workbuddy-cli-model-bridge`](docs/skills/workbuddy-cli-model-bridge/README.md) | Connect verified CLI subscription models to WorkBuddy through a loopback proxy | [Docs](docs/skills/workbuddy-cli-model-bridge/README.md) |

## Why one Portfolio

- **One editable source.** Every public Skill is maintained on `main` in this repository.
- **Complete installation units.** Supporting scripts, references, themes, and assets travel with each Skill.
- **Independent versions, one repository.** Every Skill owns its version, Changelog, canonical Tag, and tests while sharing this publishing source.

`codex-model-routing-team` can be invoked explicitly. Its documentation also includes an optional `AGENTS.md` authorization block for automatic activation on complex parallel work.

## Repository model

```text
skills/<name>/          complete agent-facing install payload
docs/skills/<name>/     human-facing English and Chinese documentation
registry/skills.json    versions, validation, capabilities, and Harness support
assets/readme/          Portfolio identity assets
```

Every install and release resolves through this repository. The Portfolio does not create or synchronize standalone Skill repositories.

## Contribution and license

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening an Issue or pull request. The Portfolio is released under the [MIT License](LICENSE); bundled Skill notices remain with their respective payloads.

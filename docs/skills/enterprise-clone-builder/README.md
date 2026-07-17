# Enterprise Clone Builder

<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="Enterprise Clone Builder turns company evidence into a structured digital twin">
</p>

<p align="center"><strong>Build a structured enterprise digital twin from local company materials and carefully scoped public evidence.</strong></p>

<p align="center"><a href="./README.zh-CN.md">简体中文</a> · <a href="https://github.com/zjp1997720/zhijian-skills/tree/main/skills/enterprise-clone-builder">Canonical source</a> · <a href="https://github.com/zjp1997720/enterprise-clone-builder">Standalone mirror</a></p>

Use it when a delivery team needs to turn scattered company materials into a reusable, source-traceable knowledge repository.

## Agent Install

```bash
npx skills add zjp1997720/enterprise-clone-builder -g -a codex --skill enterprise-clone-builder -y
```

## What it does

`enterprise-clone-builder` takes a company name + local materials + public website URL, and outputs a complete, standardized enterprise avatar repository:

```
{company-name}-企业分身/
  AGENTS.md                        # System prompt: identity + rules
  00-企业概览.md                    # One-page quick reference
  01-企业画像/                      # 5 dimensions of company profile
  02-原始素材/                      # Raw materials archive (local + web)
  03-内容资产/                      # Structured content assets (4 libraries)
  04-文风样本/                      # Voice analysis (anchors + cues)
  05-调研记录/                      # Quality assurance (claims + gaps)
  06-产出/                          # Output directory for downstream writer
```

This repository can be directly consumed by a downstream writing skill (like `enterprise-clone-writer`) to produce articles, product descriptions, and other content **in the company's own voice**.

## Why

The quality ceiling of an enterprise AI avatar depends on the quality of materials — and the best materials are always local (product manuals, historical articles, customer cases), not on the internet.

This skill is for **service providers** who build enterprise avatars for clients. It standardizes the build process from a half-day manual operation to 1-2 hours, with consistent quality.

## How it works (5 stages)

| Step | What happens |
|---|---|
| **Step 0** | Scan local materials → classify into 7 categories → diagnose coverage gaps |
| **Step 1** | Supplement with web research (only fills gaps, doesn't re-scrape everything) |
| **Step 2** | Extract structured profiles (5 dimensions) + content assets (4 libraries) |
| **Step 3** | Analyze writing style from published content → voice anchors + cues |
| **Step 4** | Build AGENTS.md + overview + quality assurance files |

## Key principles

1. **Local materials first** — local is the primary source, web research supplements gaps
2. **Standardized structure** — all enterprise avatars use the same directory layout
3. **Source traceable** — every fact has a source, evidence vs inference is distinguished
4. **Gap transparent** — information gaps are explicitly marked, not hidden
5. **Fully automated by default** — the user is a professional, not a beginner

## Built-in client intake checklist

The skill includes a 7-category materials checklist that you can export and send to clients before building. Clients organize their files by category, then you point the skill at that folder and start.

Categories: company intro / product materials / customer cases / published content / sales scripts / industry knowledge / brand visuals.

## Files

| File | Purpose |
|---|---|
| `SKILL.md` | Main entry: 5-stage workflow, inputs, outputs, completion criteria |
| `references/directory-spec.md` | Standard directory structure specification |
| `references/local-intake-guide.md` | Local material classification rules + client intake checklist |
| `references/extraction-guide.md` | Structured extraction specification |
| `references/voice-analysis-guide.md` | Voice analysis operations guide |
| `references/web-clipper-usage.md` | Web-clipper invocation reference |

## Compatibility

Works with any agent that can read SKILL.md and execute file operations: Claude Code, Codex, WorkBuddy, OpenCode, etc.

## License

MIT

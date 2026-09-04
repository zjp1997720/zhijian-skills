# Canonical release package

Use this reference when importing a local Skill into Zhijian Skills.

## Repository layout

```text
zhijian-skills/
├── README.md
├── README.zh-CN.md
├── registry/skills.json
├── docs/
│   ├── changelogs/<skill-name>.md
│   └── skills/<skill-name>/
│       ├── README.md
│       ├── README.zh-CN.md
│       └── assets/readme/
└── skills/<skill-name>/
    ├── SKILL.md
    ├── agents/openai.yaml
    ├── scripts/
    ├── references/
    └── assets/
```

Every Skill uses the nested install-payload layout. The Portfolio root must not expose `SKILL.md`, and the Skill payload must not contain human README or marketing files.

## Import contract

1. Extract the public Skill name from frontmatter.
2. Copy only required agent-facing files into `skills/<name>/`.
3. Preserve compatible license and third-party notices inside the payload.
4. Create bilingual human docs under `docs/skills/<name>/`.
5. Create or update `docs/changelogs/<name>.md`.
6. Add a canonical-only Registry record with version, paths, validation, capabilities, and Harnesses.
7. Update root catalogs and deterministic README assets.

For governed packages, keep reusable release evidence inside the install payload and declare it in `manifest.json`:

```json
{
  "maturity_tier": "governed",
  "trust_report": "security/trust-baseline.md",
  "output_quality_scorecard": "references/output-eval-baseline.md"
}
```

Both paths must remain inside the Skill directory and be tracked at `HEAD`. A locally generated or ignored `reports/` file does not count as public release evidence.

Do not create `SOURCE.json`, redirect workflows, repository-specific release roots, standalone Tags, or mirror metadata.

## Documentation contract

The first screen of each Skill document must answer:

1. What is this Skill?
2. What result does it create?
3. How do I install it from `zjp1997720/zhijian-skills`?

Required sections:

```text
# <Skill Display Name>
One concrete value sentence
## Install
## Requirements
## What It Does
## How It Works
## Example Requests
## Safety or Limitations
## License
```

Use `npx skills add zjp1997720/zhijian-skills` in every install example. README visuals live under `docs/skills/<name>/assets/readme/`; essential commands and links stay in Markdown.

## Sanitization checklist

- Replace personal absolute paths with portable placeholders.
- Remove credentials, customer data, private URLs, unpublished prompts, caches, logs, browser profiles, and `.DS_Store`.
- Confirm redistribution rights for every bundled asset and copied code block.
- Preserve compatible upstream license and attribution.
- Reject symlinks that escape the payload.

## Validation checklist

```bash
python3 skills/skill-open-sourcer/scripts/portfolio.py \
  validate-skill skills/<skill-name>
python3 skills/skill-open-sourcer/scripts/portfolio.py \
  audit --repo . --strict
python3 skills/skill-open-sourcer/scripts/audit_release_readme.py \
  --repository-root . \
  docs/skills/<skill-name>/README.md \
  docs/skills/<skill-name>/README.zh-CN.md --strict
python3 -m unittest discover -s tests -v
npx --no-install skills --help
npx --no-install skills add . --list
python3 skills/skill-open-sourcer/scripts/verify_isolated_install.py \
  --repo . --skill <skill-name>
```

`verify_isolated_install.py` creates an isolated HOME and workspace, installs with copy mode, and compares complete SHA-256 manifests. It returns non-zero for preflight, install, materialization, missing-file, extra-file, and changed-content failures. Run it as the verdict command; do not append a success-printing command that can mask its exit code. After pushing, repeat with `--install-source zjp1997720/zhijian-skills` to compare the remote installation against the canonical local payload.

Never run `npx skills add <source> --help` to inspect CLI help. In `skills` CLI 1.5.x, the valid `<source>` may perform a real installation and write `.agents/` plus `skills-lock.json`. Use `npx --no-install skills --help` for help and `npx --no-install skills add . --list` for discovery.

## Publication boundary

Publish only through a short-lived branch and PR into protected canonical `main`, then create only `<skill>/v<version>`. Record and re-check the live remote SHA before merge. When a temporary clone publishes, mark the original checkout `needs-sync` and block commits there until local and remote `main` exactly match. Direct pushes to `main`, `gh repo create`, standalone remotes, per-Skill GitHub repositories, and compatibility mirrors are outside this workflow and forbidden by default.

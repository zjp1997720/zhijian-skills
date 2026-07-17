# Contributing

Open Issues and pull requests in this repository. Standalone Skill repositories are compatibility mirrors and do not accept source changes.

## Pull requests

- Fork the repository and open a pull request against `main`.
- Keep one Skill or one governance concern per pull request.
- Do not include credentials, customer data, personal absolute paths, caches, generated previews, dependencies, reports, or archives.
- Update the Skill Changelog when behavior changes.
- Declare any new network, subprocess, filesystem, or credential capability in the Registry.

## Local validation

```bash
npm ci
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/codex-doctor/tests -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/skill-open-sourcer/tests -v
npm ci --prefix skills/wechat-article-search
npm test --prefix skills/wechat-article-search
npm ci --prefix skills/wechat-styler
npm test --prefix skills/wechat-styler
npx --no-install skills add . --list
python3 skills/skill-open-sourcer/scripts/portfolio.py audit --repo . --strict
```

Default CI has no credentials and does not run live-network checks.

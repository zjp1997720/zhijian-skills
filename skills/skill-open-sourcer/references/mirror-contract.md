# Compatibility Mirror Contract

A compatibility mirror is a generated distribution surface. Its editable source, Issues, and contributions live in `zjp1997720/zhijian-skills`.

Every export contains root documentation, license, contribution guidance, changelog, a complete nested `skills/<name>/` payload, the contribution redirect workflow, and `SOURCE.json`. `SOURCE.json` records the canonical commit, Skill version, payload digest, export digest, and exact generated-file manifest.

The exporter compares the current mirror with the prior generated manifest. Unknown files or edits stop synchronization. Initial conversion requires an explicit reviewed `--adopt`; subsequent releases never overwrite unexplained drift and never force-push.

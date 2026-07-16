# First-wave source inventory

Recorded on 2026-07-16 before canonical import. Local working copies are treated as current user-approved state, including uncommitted files. Public repositories provide history, public documentation, licenses, and compatibility metadata.

| Skill | Selected runtime baseline | Public baseline | Decision | Excluded from payload |
| --- | --- | --- | --- | --- |
| `codex-doctor` | Local Codex copy; entrypoint digest `0f3ecdf0…` | `c79a9ec61720516af821397c5f96ad2753ecf10c` | Runtime files match the public release; import the complete public package | Human README files |
| `enterprise-clone-builder` | No active local copy | `7ccd2c55dd88a4b4d9bfd591abd59a9c870b266d` | Public repository is authoritative | Human README |
| `wechat-styler` | Active vault copy; candidate digest `7e8601e8…` | `f7b593eb854eefce810919cf3d936cd19246a7ff` | Local runtime, references, themes, tests, and publishing scripts win; public repo supplies missing public metadata | Generated previews, preview frames, `node_modules`, human README |
| `wechat-article-search` | Active vault copy; candidate digest `7e25da90…` | `8011e128a7e21d808a89d4ac034d8460ee1abdab` | Local entrypoint, lockfile, package metadata, and script win; public repo supplies agent metadata and license | Human README |
| `html-express` | Active vault copy; candidate digest `53c35ade…` | `c39644b3725ec17152bf92bf8e8de77e6832b176` | Local entrypoint and assets win; public repo supplies agent metadata and license | Internal design/plan notes, human README |
| `skill-open-sourcer` | Active vault copy; candidate digest `efffc092…` | `6f203c0e19cd4b91c24957fc9ae780edd55d9a34` | Local workflow, references, scanners, and tests win; public repo supplies license and historical README | Human README |
| `codex-model-routing-team` | Clean local public-core checkout; digest `157e1eb4…` | `90e7717f0baa0d206db04dabb57fa4adb7a2b457` | Public nested payload is authoritative and matches the clean local checkout | Generated reports, registries, evaluation outputs, archives, local review artifacts |
| `codex-skill-admin` | Local Codex copy; digest `ff5b2254…` | `536c3be4ed7450530cee82b187a251c2939475e0` | Runtime payload matches public nested package; import the public package | Human README and repository governance files |

## Conflict policy

- File-list or digest differences are resolved before import; no source is overwritten in place.
- Candidate behavior is characterized before refactoring.
- Public documentation is retained outside install payloads.
- The original repositories and local directories remain untouched until canonical verification and Symlink cutover.


# codex-theme-studio Changelog

## 1.0.3 — 2026-07-17

- Add an explicitly authorized macOS resident manager that restores the loopback endpoint and injector after a normal Codex launch.
- Keep Codex stopped when the user quits it; the manager waits for the next user launch instead of relaunching the app.
- Disable the resident manager before pause and restore, with a 45-second restart cooldown and official-runtime validation.
- Add deterministic resident-manager safety and lifecycle tests.

## 1.0.2 — 2026-07-17

- Keep the branded homepage Banner active after the user types and Codex unmounts its native suggestion cards.
- Track the persistent homepage feature node separately from optional cards, with stable shell and Hero markers.
- Add strict verification coverage for the typed homepage state and align every runtime version constant with the package version.

## 1.0.1 — 2026-07-17

- Publish and install exclusively through `zjp1997720/zhijian-skills`.
- Remove standalone repository and mirror metadata while preserving the canonical release history.

## 1.0.0 — 2026-07-17

- Establish a governed, self-contained workflow for designing, preparing, installing, verifying, repairing, pausing, and restoring Codex Desktop themes on macOS.
- Generalize the upstream loopback injection engine with portable brand tokens, hero/full-page artwork modes, signature checks, input validation, atomic deployment, and immutable recovery snapshots.
- Add optional built-in ImageGen orchestration for responsive Banners and task-page backgrounds, with a neutral bundled fallback and explicit capability degradation.
- Add deterministic theme, backup, privacy, route, keyboard, native-UI, and verification contracts.
- Add trigger, file-backed output, adversarial, trust, and rollback evidence without publishing user assets, theme exports, screenshots, or private paths.
- Credit `Fei-Away/Codex-Dream-Skin` as the inspiration and upstream source of the injection architecture.

# QA inventory

## Required user-visible behavior

1. Home route shows the selected preset banner, live native heading, every native suggestion card (currently three or four depending on Codex state/build), the real project selector, and native composer.
2. Normal tasks and system routes use one consistent theme background with no Hero art, slogan, brand chrome, or mismatched native backing layer.
3. Sidebar, navigation, messages, approvals, project selector, attachments, composer, menus, hover, focus, and keyboard input remain native and interactive.
4. Decorative layers have `pointer-events: none`; no screenshot or raster UI is used as an overlay.
5. New Task prepaint and the 0/50/150/500ms route samples remain warm paper; mounted cards do not disappear.
6. Official application signature and `app.asar` remain unchanged.
7. Pause, immutable V2 restore, and original-theme Restore are separate reversible operations; final reinstallation returns to V3.

## Automated checks

- Shell and JavaScript syntax checks.
- Payload construction with bundled demo and an isolated custom theme.
- Reject unsupported theme config, unsafe image paths, invalid colors, oversized images, non-loopback WebSocket URLs, and unrecognized renderer targets.
- Exact install/restore round trip for the two TOML settings while preserving unrelated values.
- Empty `HOME` recovery.
- Official app and internal Node signature, Team ID, architecture, and version validation.
- Port collision selection and saved-port reuse.
- PID reuse protection through PID, start time, executable, script path, and command-line matching.
- Immutable V2 snapshot fingerprint, path traversal, symlink, tamper, atomic restore, and manifest checks.
- Strict home verification requires the expected Hero height and `background-size: cover`, at least three visible native cards, centered icons, native controls, and no horizontal overflow.
- Strict task verification requires no background art or brand element, a zero-width top divider, and visible/clickable file tabs.
- Strict system-route verification requires no composer, no brand chrome, and every large native `main-surface-primary` layer to resolve to the same warm-paper color.
- Missing home enhancement hooks report degraded mode while preserving the safe warm-paper shell.

## Visual checks

- Home at normal desktop size: banner crop is readable, text remains live, cards are not clipped, and composer does not overlap content.
- 1440, 1920, and 2304 pixel viewports: Hero, cards, and composer share the content axis without clipping.
- Task route: warm paper stays plain, messages and output panels keep high contrast, and the composer remains reachable.
- Active sidebar session reads as a soft paper tab with no hard blue left rule.
- Header file tabs keep visible text, pointer events, and a bounded width.
- Selected image contains no fake interface controls or raster text intended to impersonate Codex.
- `graphite-paper` contains no brand identity; `zhijian-ai` appears only when explicitly selected.
- Inspect sidebar selection, header, banner edges, cards, project label, composer buttons, scrollbars, focus outlines, dialogs, and menus.

## Release signoff

- Run `tests/run-tests.sh` successfully.
- Install from a clean extracted copy with no global Node.js.
- Complete Pause → Apply, V3 → V2 → V3, and original Restore → V3.
- Capture the three-width home/task matrix and four New Task route samples.
- Confirm `codesign --verify --deep --strict` still succeeds for the official Codex app.
- Build ZIP and record SHA-256.

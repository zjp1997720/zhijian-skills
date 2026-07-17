# Verification contract

## Deterministic checks

Run `tests/run-tests.sh` before installation. It checks shell and JavaScript syntax, theme schema, path and symlink rejection, private-data exclusion, non-destructive config behavior, backup tamper detection, atomic restore, responsive CSS contracts, custom palettes, and payload construction.

Run `injector.mjs --check-payload --theme-dir <dir>` for every prepared theme. A pass proves the files are locally resolvable and safe to embed; it does not prove live layout quality.

## Live core contract

- official app and bundled Node signatures are valid and share the expected team
- CDP is bound to a verified loopback listener
- injected version, stylesheet, main surface, sidebar, and composer exist
- no horizontal document overflow
- every detected workspace tab has a visible, interactive title
- exactly four native home cards remain visible when the known home hook exists
- every card remains a focusable button and is not clipped

## Strict visual contract

- main, sidebar, and selected-session colors match the active theme tokens
- no heavy top divider or opaque overlay hides workspace tabs
- homepage hero is visible, full-bleed, and 224 / 208 / 184 px at desktop / tablet / narrow widths
- home cards use four columns on wide screens and two on medium screens
- suggestion-card icons are geometrically centered within tolerance
- selected conversation has no hard left border
- task pages have no hero artwork in `hero` mode
- task pages contain the image in `all` mode
- homepage brand chrome is non-interactive; task-page brand chrome stays hidden

## Route transition contract

From an existing task, `--sample-new-task <dir>` clicks the real New Task control and samples 0, 50, 150, and 500 ms. It records screenshots and JSON. The first composited frame must use the active theme background, mounted cards may not disappear, and the home route must be observed.

## Required evidence

Capture at least:

- home and task at 1440×900
- home and task at the user's actual viewport when different
- New Task samples from a task route
- selected conversation, workspace tab, four cards, and composer controls
- Banner crop or full-page background at one narrow width

For a public release, also sample 1920×1080 and 2304×1296 when the environment permits. Record unavailable viewports as `missing evidence`.

Strict automation is necessary and incomplete. Visually inspect every final screenshot for hierarchy, cropping, duplicated text, icon optical centering, font fallback, color cast, and decorative clutter.

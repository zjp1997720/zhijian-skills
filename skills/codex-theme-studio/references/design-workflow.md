# Design workflow

## Translate the brand into UI roles

Build a compact token map before editing files:

| Brand input | Theme role | Decision rule |
| --- | --- | --- |
| Primary surface | `background` | Quiet canvas behind the whole shell |
| Elevated surface | `panel` | Composer, cards, and content containers |
| Secondary surface | `panelAlt` | Tabs, chips, code labels |
| Navigation surface | `sidebar` | Distinguishable from main without a heavy split |
| Selection | `selected` | Calm, readable, and free of a hard left rule |
| Brand action | `accent` | Links, focus, caret, and small emphasis only |
| Structural color | `secondary` | Send button, focus outlines, active text |
| Text | `text` / `muted` | Body and secondary hierarchy |
| Artwork | `image` | Homepage hero or intentional page background |

Preserve the user's existing native Codex theme export. The injected layer can match its palette without rewriting native appearance settings.

## Choose the artwork mode

- `hero`: default. Artwork appears in the homepage Banner. Task pages remain quiet and readable.
- `all`: artwork also covers the task-page main surface. Use a low-detail image with broad tonal continuity so text and panels remain legible.

The hero source should be about 2.5:1, ideally 2000×800 or larger. The rendered Banner is much wider; important content belongs near the right-center and must survive vertical crop. Reserve the left 50–55% as a low-detail text-safe zone.

## Preserve product behavior

Theme the existing DOM. Do not replace controls or create fake copies.

- All four native home suggestion cards stay visible, clickable, keyboard-focusable, and aligned.
- Workspace tabs keep their title and close behavior. Styling may clarify them; it may not obscure them.
- The selected conversation uses a paper-tab surface and restrained inset edge. Avoid a hard colored `border-left`.
- The composer keeps all permission, model, microphone, attachment, and send controls.
- The task route stays free of homepage-only brand chrome unless the user explicitly requests otherwise.
- Do not hide a native element merely because its current selector or layout is inconvenient.

## Visual quality bar

- Prefer hierarchy from spacing, proportion, typography, and one accent.
- Avoid gradients, glass blur, particles, ornamental status labels, repeated slogans, and large decorative logos.
- Keep border radii compact and shadows quiet.
- Validate icon centering optically as well as geometrically.
- Use a CJK-capable UI font stack with fallbacks; keep code in a monospace stack.
- Maintain readable contrast. For body text target at least 4.5:1; for large text and non-text UI target at least 3:1.

## Screenshot-driven iteration

Classify every annotation before changing code:

1. native functionality missing or obscured
2. route/first-frame flash
3. geometry, crop, overflow, or alignment
4. palette, contrast, typography, or density
5. decoration that should be removed

Fix in that order. Recheck home, task, narrow viewport, and New Task transition after selector or layout changes.

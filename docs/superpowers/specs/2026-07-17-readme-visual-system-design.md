# Zhijian Skills README Visual System

## Objective

Give the canonical Portfolio and all eight public Skills a coherent, recognizable GitHub presentation without turning documentation into decoration. The first screen must continue to answer what the project does, why it matters, and how to install it.

## Scope

- Redesign the root English and Chinese README files.
- Redesign the English and Chinese README pair for each active Skill.
- Create one Portfolio hero and one domain-specific hero per Skill.
- Export each Skill hero with its generated standalone compatibility mirror.
- Preserve commands, requirements, safety boundaries, examples, and repository links as Markdown.

## Visual Direction

Use the light-theme `ZhiJian AI Warm Paper OS` defined in the brand `DESIGN.md`:

- Background: parchment `#F5F4ED`; never full-canvas pure white or charcoal.
- Cards: ivory `#FAF9F5` with cream borders `#E5E3D8` and no heavy shadow.
- Core accents: structural ink blue `#1B365D` and restrained action clay `#B85235`, each below five percent of the canvas.
- Typography: Source Han Serif / Songti / Georgia serif stack; SF Mono for commands and identifiers.
- Shapes: 8–12 unit working radii, one-pixel structural strokes, generous margins.
- Composition: a quiet editorial identity block paired with one factual domain diagram.
- Dark surfaces: allowed only inside a small code or terminal block when the domain requires it.

Each hero uses a 1200 by 360 viewBox, includes `<title>` and `<desc>`, carries a complete background, keeps essential text at least 16 units, and contains no scripts, remote assets, external fonts, animation, or fragile filters.

## Skill Motifs

| Skill | Domain motif |
| --- | --- |
| `codex-doctor` | diagnostic pulse and verified checks |
| `codex-model-routing-team` | lead node routing bounded worker threads |
| `codex-skill-admin` | visible/disabled Skill registry controls |
| `enterprise-clone-builder` | source materials becoming a structured knowledge tree |
| `html-express` | dense notes becoming a composed HTML information board |
| `skill-open-sourcer` | local Skill passing gates into canonical and mirror releases |
| `wechat-article-search` | query flowing through article results and source labels |
| `wechat-styler` | Markdown blocks becoming a polished WeChat article page |

Skill identity comes from the information diagram, not from adding new decorative colours outside the brand palette.

## Asset Layout

- Portfolio: `assets/readme/portfolio-hero.svg`
- Skill docs: `docs/skills/<skill>/assets/readme/hero.svg`
- Canonical README references remain relative to their own directory.
- Mirror export copies `docs/skills/<skill>/assets/readme/` to root `assets/readme/`, so the same README link works in both locations.

## README Architecture

Root README order:

1. Hero and language switch.
2. One-sentence Portfolio value.
3. List and install commands.
4. Eight-Skill catalog grouped by user outcome.
5. Governance model and compatibility explanation.
6. Contribution and license links.

Skill README order:

1. Hero, language switch, and one-sentence result.
2. Shortest safe install command.
3. Three to five result-oriented capabilities.
4. Plain-language workflow or proof.
5. Example requests.
6. Requirements, safety, and limitations.
7. Compact repository layout and license.

English and Chinese files share structure and facts while using natural language rather than mechanical translation.

## Mirror and Release Contract

The mirror exporter treats README visuals as generated human-facing release files. It copies only files below the declared documentation asset directory, records them in `SOURCE.json`, and remains deterministic. Unknown mirror content still blocks export. Skill install payloads remain unchanged because README assets stay outside `skills/<name>/`.

## Verification

- Render all nine SVGs to PNG at GitHub content width and inspect for clipping, contrast, text scale, and domain relevance.
- Run strict README audit against the canonical repository and every generated mirror preview.
- Run Portfolio audit and all governance tests.
- Verify mirror export determinism and isolated installation remain unchanged.
- Confirm every local README image reference resolves and every SVG contains `<title>`, `<desc>`, and no unsafe element.

## Non-goals

- No runtime Skill behavior changes.
- No screenshot walls, animated SVG, generic AI imagery, adoption claims, or decorative section banners.
- No README files inside agent-facing `skills/<name>/` payloads.

# Release README Design

Use this reference when writing or redesigning the public README for a skill release. The README is the repository's trust entrance and install entrance. It should explain the skill before it decorates the skill.

This method is adapted from [`oil-oil/beautify-github-readme`](https://github.com/oil-oil/beautify-github-readme), licensed under MIT. See `third-party-notices.md` for the attribution and license text.

## 1. Extract the release story

Write these facts before drafting Markdown or drawing an asset:

```text
Project name:
Audience:
Repeated problem:
One-sentence value:
Primary proof:
First successful action:
Requirements or safety boundary:
Native visual material:
Presentation tier: clean-doc / proof-led
Composition ID (proof-led only):
```

`Native visual material` means something the skill truly works with: an interface, generated document, chart, terminal output, transformation, architecture, media artifact, or structured workflow. Empty grids, glowing nodes, stock illustrations, and fake code do not count as proof.

Do not invent adoption, benchmarks, testimonials, compatibility, or capabilities. If the source package has no proof asset, use a concrete example request and expected result in Markdown.

The release story is a required working artifact. Keep it in the task record or release plan; do not publish it as filler in the README.

## 2. Choose one presentation tier

### Clean-doc

Use this tier for infrastructure skills, small utilities, abstract workflows, or releases without legible visual proof.

- Lead with an accessible H1, one concrete sentence, and the install command.
- Use Markdown headings, code blocks, short lists, and one end-to-end example.
- Use zero to three trust or installation badges.
- Skip the hero image. Strong hierarchy and concise copy are the visual system.

### Proof-led

Use this tier when a visual output materially helps a visitor judge the skill: UI, slides, documents, diagrams, media, before/after results, or a recognizable project architecture.

- Use one project-native hero or place one proof board immediately after the first screen.
- Combine identity and proof only when the proof remains readable at GitHub content width.
- Keep screenshots, generated art, photos, and dense artifact walls in PNG/WebP.
- Keep deterministic titles, diagrams, comparison modules, and simple architecture in SVG.

Do not escalate to proof-led merely because an image generator is available. The evidence decides the tier.

### Portfolio anti-template gate

Shared brand tokens are allowed. Shared composition is not. For every proof-led Skill:

- assign one stable lowercase `data-composition` value that names the information structure, such as `diagnostic-report`, `source-to-report`, or `verified-loopback-route`;
- derive the layout from the real mechanism or proof before choosing colors and decoration;
- reject a Hero when removing the repository name makes it interchangeable with another Skill;
- reject a Portfolio set that repeats the same title-left/proof-right frame and changes only labels, colors, or a small motif;
- update the deterministic asset generator and its uniqueness test in the same change.

Different Skills may share typography or brand colors while using different spatial logic: report, route map, switchboard, artboard, evidence graph, before/after, decision lanes, pipeline, result stack, editorial spread, or verified connection path.

## 3. Build the reading order

The first screen must answer:

1. What is this?
2. What result does it create?
3. How do I install or start?

The next screen should provide proof. A reliable order for a skill release is:

```text
Value → Install → Proof → What it does → How it works → Example requests → Requirements and safety → Repository layout → License
```

Use these editing rules:

- Replace internal jargon with a concrete user outcome.
- Explain the mechanism once and remove repeated promises.
- Put the shortest safe install path before advanced configuration.
- Prefer one example that succeeds end to end over many disconnected snippets.
- Keep limitations visible when they affect adoption or safety.
- Keep commands, links, configuration, compatibility, and long explanations in Markdown.
- Put agent procedure in `SKILL.md` and detailed protocol in `references/`; the README stays human-facing.

## 4. Derive the visual system from the project

Choose visual direction in this order:

1. Product semantics: what the skill helps people do.
2. Existing identity: logo, screenshots, design tokens, diagrams, code style, or documentation tone.
3. Audience expectation: technical trust, creative energy, research clarity, or operational confidence.
4. Finish: palette, typography, shapes, motif, density, and composition.

Freeze five decisions before producing an asset:

```text
Palette: background / foreground / primary / accent / muted
Typography: system stack / display scale / section scale / metadata style
Shape: radius / stroke / spacing unit
Motif: one recurring cue taken from the skill's real domain
Composition: sparse editorial / compact technical / expressive gallery
```

Useful mappings:

| Skill character | Honest visual material | Common failure |
| --- | --- | --- |
| CLI or developer tool | terminal rhythm, real commands, logs, precise system map | fake code and neon overload |
| AI workflow | input/output transformation, evidence, relationships | glowing brain imagery |
| Design or media skill | specimens, crop marks, before/after artifacts | portfolio decoration without proof |
| Data or research skill | charts, annotations, source labels, measured spacing | unrelated dashboard chrome |
| Knowledge or document skill | editorial hierarchy, pages, structured workflow | SaaS landing-page cards |

Use one strong composition: annotated specimen, before/after, system map, sequence strip, or artifact wall. Repeating decorative section banners usually increases length without increasing trust.

## 5. Build GitHub-safe assets

Store release-specific assets under `docs/skills/<skill-name>/assets/readme/` with lowercase hyphenated names.

For full-width SVG:

- Start from a `1200`-unit-wide `viewBox`.
- Typical heights are `300–420` for a hero, `120–170` for a section title, and `320–760` for a diagram.
- Add `<title>` and `<desc>` and use meaningful README alt text.
- Use system fonts such as `-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `PingFang SC`, and `sans-serif`.
- Keep essential SVG text at least `16` units and section titles at least `36` units.
- Supply a complete background when contrast depends on it.
- Keep important content away from the edges and render after every meaningful copy change.

Avoid features GitHub may strip or that make the asset fragile:

- scripts and `foreignObject`;
- remote fonts, remote stylesheets, and remote images inside SVG;
- essential animation, hover behavior, or CSS;
- dense small text, large filters, heavy shadows, and generic technical ornament.

Use simple HTML only for alignment and image sizing:

```html
<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="Project name and concrete value">
</p>
```

Essential install or usage information must remain outside the image.

## 6. Preview and verify

Run the deterministic audit from the canonical Portfolio repository:

```bash
python3 <zhijian-skills>/skills/skill-open-sourcer/scripts/audit_release_readme.py \
  --repository-root <zhijian-skills> \
  <zhijian-skills>/docs/skills/<skill-name>/README.md \
  <zhijian-skills>/docs/skills/<skill-name>/README.zh-CN.md --strict
```

`--repository-root` is an explicit safety boundary. It permits shared Portfolio links such as `../../../LICENSE` while still rejecting files and links outside the canonical repository. For a standalone release directory, omit the option and audit that directory directly.

Then render every SVG or raster composition at GitHub content width and inspect:

- clipped text or paths;
- proof that becomes unreadable when scaled;
- weak contrast against light and dark GitHub surroundings;
- missing or vague alt text;
- image weight and broken local references;
- visual material that could belong to an unrelated project;
- duplicated composition IDs or a layout already used by another Portfolio Skill;
- mobile readability and excessive vertical length.

The audit script catches structural defects. Visual judgment remains a manual gate. Prefer the simpler version when two designs communicate equally well.

## 7. Preserve publication boundaries

- Show the local README preview and diff before publishing when the user has not already authorized release.
- Do not add an upstream credit badge, promotional backlink, or “made with” asset to the release README unless the owner explicitly requests it.
- Preserve third-party attribution inside the tool or package that actually incorporates third-party material.
- Never let README polish bypass the safety, ownership, or license scan.

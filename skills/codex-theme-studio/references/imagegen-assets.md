# ImageGen asset contract

Use `$imagegen` only when the theme needs a new or edited raster image. Existing logos, icons, and vector systems should stay in their native format.

## Execution contract

1. Use the built-in ImageGen tool by default. It does not need an API key.
2. Treat a local image as an edit target only after inspecting it with `view_image`. Label references and edit targets explicitly.
3. For project-bound output, copy the selected file from `$CODEX_HOME/generated_images/...` into the prepared theme directory.
4. Do not overwrite the user's existing artwork; create a versioned sibling.
5. Do not switch to the ImageGen CLI/API fallback unless the user explicitly requests or approves that fallback under the ImageGen Skill rules.
6. Inspect the output at full frame and at the intended Codex crop before accepting it.

## Homepage Banner prompt

```text
Use case: stylized-concept
Asset type: Codex Desktop homepage Banner
Primary request: <brand-specific scene or illustration>
Input images: <reference roles, if any>
Style/medium: <brand medium>
Composition/framing: ultra-wide source around 2000×800; reserve the left 55% as calm negative space for live UI text; place the main subject in the right-center; keep all important content away from the outer 8%; design for a much wider responsive crop
Color palette: <theme tokens>
Constraints: no embedded headline, no logo unless explicitly requested, no watermark; strong silhouette at small display size; preserve reference-character identity when supplied
Avoid: dense left-side detail, tiny typography, UI mockups, fake Codex controls, edge-cropped subjects
```

The UI supplies the title and project name. Generated text inside the Banner usually produces duplication and should be excluded.

## Full-page background prompt

```text
Use case: stylized-concept
Asset type: Codex Desktop task-page background
Primary request: <brand atmosphere, texture, or scene>
Style/medium: <brand medium>
Composition/framing: wide 16:10 or 16:9 field; low-detail center reading zone; no single essential focal point; seamless visual continuity under translucent or opaque panels
Color palette: <theme tokens with restrained contrast>
Constraints: no text, no logo, no watermark; broad tonal areas; readable beneath UI; important details stay outside the central content column
Avoid: high-frequency texture, bright hotspots behind text, faces behind the composer, hard horizon through body copy
```

Set `artPlacement` to `all` only after confirming the result remains readable on a task route. Strict verification expects the task background to be present in this mode.

## Optional brand mark

Use a supplied transparent PNG/WebP when possible. If a new raster mark is requested, follow ImageGen's transparent-image workflow and validate the alpha channel. The runtime accepts a brand image up to 4 MB and displays it within roughly 112×24 CSS pixels; test legibility at that size.

# wechat-styler Changelog

## Unreleased

- Run mobile QA without Google Chrome (1.18.2): `mobile-visual-qa.mjs` now resolves the browser as `CHROME_EXECUTABLE` → `CHROME_CHANNEL` → installed Google Chrome → on macOS another installed Chromium browser (Ego Lite, Edge, Brave, Chromium) → Playwright's downloaded Chromium. The report gains a `browser` field naming the source, and launch failures say which source failed and point to `CHROME_EXECUTABLE`. Previously the script hard-coded the `chrome` channel and failed on machines where Chrome was uninstalled.

- Give the brand CTAs breathing room and round the paper card (1.18.1, manifest `2026-10-13-v7.1-flow-gif`). On a real iPhone the 1.18.0 GIFs read as "head-butting": the character filled the full GIF height (about 4px of paper above the raised hand) and the CTA sections had no padding, so the opening sat flush on the article card's top edge and the ending on its bottom edge, while the card itself ended in square corners against WeChat's white page. The GIFs are re-rendered from the same Flow clips with 30px of paper above and 18px below the character inside the 2x asset (opening 800024 bytes, ending 1286172 bytes; size, frames and loop unchanged; previous files moved to `legacy` so reprocessing still removes them). The opening CTA section now has `padding:24px 0 0` and the ending `padding:0 0 28px` (both styles). A new theme key `root_radius` adds `border-radius:<n>px;overflow:hidden` to the article root; `zhijian` sets 12, other themes are unchanged.

- Make Flow-generated paper-colour GIFs the default brand CTA again and keep the SVG as a fallback (1.18.0, manifest `2026-10-13-v7-flow-gif`). The new GIFs are a 3D Xiaolan rendered with Google Flow Omni 1.1 Flash reference-to-video, green-screen keyed onto the exact article paper colour `#F5F4ED`, so there is no colour block and the title/subtitle text is already in the pixels: opening 720x272, 48 frames @12fps, 1076375 bytes; ending 720x300, 72 frames @10fps, 1695438 bytes; both loop forever, hosted on COS with remote SHA-256 verified and recorded in the manifest with source and alt text. The wrapper is `<section data-wechat-cta="opening|ending" data-zhijian-cta="v7-flow-gif">` around one `<img data-wechat-cta-image>` (`width:100%;max-width:360px;height:auto;margin:0 auto;display:block`), with no background, border or caption. New `--cta-style gif|svg` (default `gif`) is plumbed like `--brand-cta`; `svg` emits the unchanged 1.17.0 inline SVG (`data-zhijian-cta="v6"`), now marked `fallback` in the manifest, and the v5 white GIFs stay `legacy`. Reprocessing is idempotent across v5 GIF, v6 SVG and v7 GIF: managed sections, loose SVG roots and GIF images matched by marker, file name or URL are all removed before inserting, so switching style replaces rather than stacks. Order is unchanged: landing end-mark, topic tags, then the ending CTA. `--expect-zhijian` mobile QA accepts the v7 GIF or the SVG (no background either way) and the baseline image is regenerated. Real editor draft save and reader-side playback on iOS/Android are not yet verified.

- Replace the opening and ending brand GIFs with transparent inline SVG (1.17.0, manifest `2026-10-13-v6-svg`). The old GIFs had a white background that showed as a block on the `zhijian` paper body (`#F5F4ED`), and their subtitle used a font not cleared for commercial use. The new CTAs are the ZhiJian Xiaolan v003 flat vector character with text converted to paths and SMIL `indefinite` loops (opening: wave, blink, breathe; ending: hand over a card, blink, breathe), inlined as one line inside `<section data-wechat-cta="opening|ending" data-zhijian-cta="v6">` with no `background-color`, so they take the article paper colour and need no image hosting. The SVG root carries `width="100%"`, `style="display:block;width:100%;height:auto;"`, its viewBox and `data-alt` / `aria-label` alt text; the interior has no `id`, `class`, `<style>`, `<defs>`, `<use>`, `<image>`, `url(` or `data:`, asserted by tests because `validate.mjs` blanks single-line SVG. The converter verifies each file's SHA256 and viewBox against the manifest. Reprocessing stays idempotent: before inserting, it removes current `data-wechat-cta` sections and loose `data-zhijian-cta` SVGs, plus legacy GIF CTAs by `data-wechat-cta-image`, file name or URL from the manifest's new `legacy` field (the GIF files are no longer shipped). The user-SVG-opener check now ignores `data-zhijian-cta` SVGs, so the stock opening CTA is never mistaken for a user animation. `--brand-cta auto|ending|none` and placement (ending CTA after the landing mark and topic tags) are unchanged; `--expect-zhijian` now also fails if a CTA has a background or is not an inline vector SVG. The mobile baseline image is regenerated. Real editor draft save and reader-side playback on iOS/Android are not yet verified.

- Give the `zhijian` theme mobile breathing room (1.16.0, `theme_revision: v3-breathing-2026-10`). Measured at a 390px iPhone viewport against a reference article readers found comfortable, both with identical 36px side margins and 318px text width: the old body had a 25.2px line box (10.2px between lines vs 13.5px), 0.12px tracking because the theme hard-coded `0.008em` and overrode WeChat's inherited ~0.544px, the darkest ink (`#141413`, 16.7:1) and weight 450, which resolves to Medium on Source Han Sans and Regular on PingFang depending on the machine; meanwhile the gap from the last paragraph to the next H2 was 101–116px. Body and lists now use 15px / 400 / 1.9 (28.5px line box), `letter-spacing:0.034em`, and a new `body_text_color` key set to the palette's secondary text `#504E49` (7.5:1, still above WCAG AAA; headings and bold keep `#141413` / clay). Paragraph margin 19 → 16px, list items 10 → 8px, section padding 32 → 20px and a new `rhythm.h2_margin_top` (zhijian 0, default 30) bring the pre-H2 gap to about 56px. Headings declare `letter-spacing:0` so they no longer inherit WeChat's body tracking. `body_letter_spacing` is a new rhythm key (default `0.008em`, so other themes are unchanged). The same article re-rendered scrolls 7490px → 7504px. `--expect-zhijian` now expects 15px / 400 / 28.5px.

- Align the `zhijian` theme with brand v3 (1.15.0, `theme_revision: v3-paper-ink-2026-10`): headings (H1/H2/H3 and the quote mark) now declare the LXGW WenKai display stack at a single weight of 500, since the face has no bold and 600/700/900 would be synthesized; body, lists, captions and UI share the screen sans stack (`'Source Han Sans SC','Noto Sans SC','PingFang SC','Microsoft YaHei','Noto Sans CJK SC',sans-serif`) because Android has no serif CJK face; code prefers JetBrains Mono with no serif CJK fallback. The previous display face is replaced by the OFL-licensed LXGW WenKai stack. Every theme color is now in the v3 palette (`quote_text` #504E49, `human_accent` #B85235, `code_bg` #141413), locked by a test. A new theme key `end_mark: landing` closes the article with a short static ink line (2px × 64px, horizontal end tangent) and one 10px clay dot, left-aligned, after the last paragraph and before topic tags and the ending CTA. `--expect-zhijian` mobile QA now checks the display stack, H3 18px/500, the screen body stack and the ending mark. WeChat pages cannot embed fonts, so readers' phones fall back along the declared stacks; the baseline document records the expected fallbacks.

- Prefer punctuation line breaks over font size in opening titles (1.14.2): when the half after a comma does not fit at the preferred size, the layout now shrinks within the existing floor (titles 22px, xiaolan-terminal 20px) to keep the break after the punctuation mark or 「的」, instead of falling back to a balanced break inside a word (「学校找 AI 培训方，先 / 看他敢不敢…」). Space breaks are tried next, and balanced CJK breaks only when neither fits.

- Stop test runs from flooding the browser with blank tabs (1.14.1): conversion no longer auto-opens the result under `node --test` (`NODE_TEST_CONTEXT`), `CI`, `WECHAT_STYLER_NO_OPEN=1`, or the new `--no-open` flag. Previously every spawned conversion in the suite opened a tab pointing at a temp file that was deleted moments later. The opener-safety test now uses a fake `open` on `PATH` and asserts the exact path it receives, and a new test proves none of the four skip paths call the opener.

- Add WeChat topic tags (1.14.0): `topics` in frontmatter or `--topics a,b,c` renders a closing line of `#topic` links after the last paragraph, before the ending GIF. Each link reproduces the editor's native `a.wx_topic_link[data-topic]` structure in italic 14px, so the live editor parses it as a `topic` mark (verified against the real editor) and saving keeps the tags. Topics accept comma, 、, or whitespace separators with or without `#`, are de-duplicated, capped at WeChat's 10, and `--topics none` disables them. SKILL.md now tells agents to pick 3–4 topics (column tag first, then 2–3 audience/topic tags, no generic words, product names only when the article shows the product) when the source has none.

- Stop repeating the article title under the opening animation (1.13.1): with `--cover`, the leading `# H1` (first non-blank line) is removed from the body and becomes the last fallback for the cover title (`--cover-title` → frontmatter.title → leading H1). Mid-article H1s are untouched, `--keep-h1` opts out, and conversions without `--cover` are unchanged.

- Re-lay out all six opening SVG templates for phones (1.13.0): viewBox width drops from 640 to 360 so one unit ≈ one CSS px in the ~358px mobile column, height grows only with the lines actually used, and `max-width` is 480px on desktop. Headlines now render at about 26–30px on a 390px phone (was ~22px), subtitles at 15–16px (was ~9.5px), and dates, bylines, tags and scroll hints at 12px (was ~6px). Long titles wrap to two `<tspan leaf>` lines (punctuation/「的」→ space → balanced CJK break, never inside Latin words) instead of overflowing; subtitles shrink to 14px before wrapping. `typewriter` types wrapped lines in sequence, `xiaolan-terminal` scales the sprite to the left with a 240-wide terminal column, and the bouncing ↓ arrow no longer doubles its translate during animation. Animation timing, static semantic baselines and `--top-label` / `--cover-author` behaviour are unchanged.

- Expose summary comparison in success, failure, and read-only verification reports, including explicit clearing and omitted-summary states.
- Warn at conversion time when images still require hosting and document the local-preview to publishing-candidate handoff without automatic uploads.

- Strip generated HTML line-end whitespace and emit one terminal newline; preserve source Markdown, code indentation, and explicit hard breaks.
- Add side-effect-free `--help` / `-h` to conversion, density audit, and mobile QA commands; support density checks through installed Skill symlinks.

- Fix `xiaolan-terminal` mixed-script copy disappearing in the published iOS WeChat reader. Mixed Chinese and Latin lines are now segmented by glyph capability: supported Latin runs compile to native 5×7 SVG `<rect>` geometry, unsupported CJK runs keep a static font-backed baseline, and the full sentence remains available through semantic labels. Add the exact `让 WorkBuddy 持续接住你的项目` reader regression so future changes cannot silently restore the whole-line font fallback.
- Preserve fenced-code and prompt line breaks through real WeChat draft persistence. The renderer now emits explicit `<br>` nodes, the injector hardens legacy HTML before writing, and post-save verification rejects any code-block or hard-break count drift after the editor rewrites the DOM.
- Add `xiaolan-terminal`, a brand-specific opening template inspired by the reference article's character-plus-terminal composition. It derives open-eye, closed-eye, and two waving high-density pixel frames from the QA-approved ZhiJian Xiaolan v2 pet asset instead of redrawing the IP with coarse SVG blocks, and restores the canonical `>_` terminal prompt on the face screen. The whole character greets readers with a two-beat discrete hand wave every six seconds, uses restrained 1–3px sprite motion and a three-second blink, while the two-colour 5×7 terminal line repeats a four-second type–hold–right-to-left erase cycle with a static semantic fallback. Unsupported scripts fall back to readable terminal text instead of missing glyphs.
- Preserve oversized animated GIFs during WeChat injection: compress them through bounded `ffmpeg` width, frame-rate, and palette profiles, upload with a stable `.gif` hash name, and retry transfer without degrading the animation to JPEG.
- Report an actionable `ffmpeg` recovery path when animated GIF optimization is unavailable or cannot reach the configured byte limit.

## 1.11.1 — 2026-08-31

- Restore a real character-by-character `typewriter` effect without reintroducing hidden semantic text. A background-coloured reveal cover advances in discrete glyph steps while the complete title remains the animation-free fallback.
- Make reveal covers and cursors transparent by default. If WeChat strips, disables, or misses SMIL state, readers see the complete line instead of missing words or opaque masks.
- Position visible character tspans and reveal boundaries from the same measurements, preventing partial next-character leaks during each step; only the active line shows a blinking cursor.
- Add a regression that fails when the typewriter degenerates into a full static line plus cursor-only movement while retaining the stripped-animation visibility checks.

## 1.11.0 — 2026-08-31

- Make semantic cover text statically visible across all five opening templates. Titles, subtitles, tags, dates, authors, and reading hints no longer depend on SMIL `fill="freeze"` state to appear.
- Rework `typewriter` from per-character hidden text nodes into whole-line visible text, with a decorative cursor animation. This prevents real WeChat readers from permanently hiding early words such as `WorkBuddy` when early animation state is lost.
- Reserve animation for decorative cursors, lines, ink blots, spotlight effects, and arrows; deleting every animation element now leaves all semantic text readable.
- Add regressions for the published failure case and all cover templates: stripped/disabled animations must not hide text, Latin words must not be split per character, and hidden semantic baselines are rejected.
- Document the 2026-08-31 reader-side incident, why editor counts and local Chrome cannot prove reader compatibility, and the required real-reader smoke check after opening changes.

## 1.10.0 — 2026-07-27

- Establish `editorial-weighted-2026-07` as the Zhijian visual baseline: restore Tsanger JinKai headings, 18px/600 H3 hierarchy, 15px/450/1.68 body rhythm, 13px sans-serif metadata, and warm terracotta emphasis while retaining trust-blue links and quotation cards.
- Add a version comparison, a reproducible 390px mobile baseline, and executable typography checks to prevent silent theme drift.

## 1.9.0 — 2026-07-25

- Refine the `zhijian` long-form theme: reserve warm terracotta for chapter/action cues, render ordinary quotations as trust-blue context blocks, restore neutral bold text, and improve mobile reading rhythm.
- Add a type=77 cover state machine that recognizes CSS-background thumbnails and falls back to uploading a local `--cover-file`, selecting it by filename, and completing crop confirmation.
- Treat WeChat qlogo and qpic image hosts as settled instead of reporting them as pending transfers.
- Normalize missing OpenCLI fields and confirm saves through `appmsgid` plus either the saved banner or version history.
- Write a token-redacted diagnostic report on every failed phase with read-only live state and concrete recovery actions.
- Give every optimized remote image a stable hashed basename and stop when PicGo collapses distinct sources to one URL.
- Add restrained, standard, and rich component-density guidance while preserving the standard 3-6 component default.
- Add a 390px mobile visual QA gate for quote alignment, overflow, broken images, duplicate image URLs, and Zhijian heading semantics.
- Keep OpenCLI as the verified WeChat injection backend after Codex Chrome rejected the article editor at the browser-policy boundary; document the no-CDP-bypass rule and the four-part acceptance gate for future backends.
- Remove the author-machine OpenCLI profile default and require an explicit `--profile` or `OPENCLI_PROFILE` value.
- Replace the vulnerable `glob` dependency chain with Node 18-compatible `tinyglobby`; the published install now reports zero known npm vulnerabilities without raising the runtime floor.

## 1.0.3 — 2026-07-17

- Publish and install exclusively through `zjp1997720/zhijian-skills`.

## 1.0.2 — 2026-07-17

- Add a brand-aligned light README hero and polish the bilingual feature explanation.
- Correct workflow numbering and the documented standalone mirror layout.

## 1.0.1 — 2026-07-17

- Open generated HTML with an argument-safe subprocess call so crafted output paths cannot be interpreted by a shell.
- Add a regression test that uses a shell-shaped filename and verifies no injected command runs.

## 1.0.0 — 2026-07-16

- Establish the public Skill governance baseline from the active local 1.8.0 runtime.
- Include themes, component mode, SVG animation, image pipeline, OpenCLI integration, and deterministic tests.

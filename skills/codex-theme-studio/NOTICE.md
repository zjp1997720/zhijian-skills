# Notices

Codex Dream Skin Studio is an **unofficial** customization project and is **not affiliated with, endorsed by, or sponsored by OpenAI**.

## Software license

The MIT License in `LICENSE` applies to the **software source code** in this repository (scripts, CSS, injectors, docs that describe the software, and the abstract demo asset generated for this repo).

It does **not** grant rights to:

- OpenAI or Codex trademarks, product names, logos, or trade dress
- Official Codex / ChatGPT application binaries, `.app` bundles, or `app.asar`
- Any user-supplied images or third-party artwork you drop into a theme
- Character likenesses, franchise art, or celebrity imagery

## Branded artwork

`presets/zhijian-ai/portal-hero-v2.png` is a 智见 AI brand asset. It may be
distributed with this package and used as the `zhijian-ai` preset inside the
official macOS Codex app. The software's MIT license does not grant permission
to extract, resell, rebrand, claim authorship of, or reuse it in unrelated
commercial products. Inactive legacy banners and logos in the private source
checkout are excluded from installation and release packages.

`assets/generic-workflow.svg`, `assets/generic-workflow.png`, and the matching
`graphite-paper` preset are the unbranded default assets covered by the software
license.

## Runtime

This project does not redistribute Node.js. At runtime it validates and uses the Node.js executable already signed and bundled inside the user's official Codex desktop application.

## Security model

Themes are applied through Chromium DevTools Protocol on **loopback only**. While a themed session is running, treat the local debugging port as sensitive: do not run untrusted local software that could attach to it. Use the Restore launcher to tear down the themed session and debugging port.

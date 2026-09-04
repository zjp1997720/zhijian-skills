import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const genericTheme = JSON.parse(await fs.readFile(path.join(root, "assets/theme.json"), "utf8"));
const theme = JSON.parse(await fs.readFile(path.join(root, "presets/zhijian-ai/theme.json"), "utf8"));
const css = await fs.readFile(path.join(root, "assets/dream-skin.css"), "utf8");
const renderer = await fs.readFile(path.join(root, "assets/renderer-inject.js"), "utf8");
const injector = await fs.readFile(path.join(root, "scripts/injector.mjs"), "utf8");
const verificationContract = await fs.readFile(path.join(root, "scripts/verification-contract.mjs"), "utf8");
const image = await fs.readFile(path.join(root, "presets/zhijian-ai/portal-hero-v2.png"));
const genericImage = await fs.readFile(path.join(root, "assets/generic-workflow.png"));

assert.equal(theme.id, "zhijian-warm-paper-os");
assert.equal(theme.name, "智见 AI 工作台");
assert.equal(theme.image, "portal-hero-v2.png");
assert.equal(genericTheme.id, "graphite-paper");
assert.equal(genericTheme.name, "Graphite Paper");
assert.equal(genericTheme.image, "generic-workflow.png");
assert.match(genericTheme.typography.uiFamily, /system-ui/);
assert.equal(genericTheme.typography.bodyWeight, 500);
assert.equal(genericTheme.typography.emphasisWeight, 600);
assert.match(theme.typography.uiFamily, /思源宋体 VF/);
assert.equal(theme.typography.bodyWeight, 500);
assert.equal(theme.typography.emphasisWeight, 600);
assert.deepEqual(
  {
    background: theme.colors.background,
    panel: theme.colors.panel,
    panelAlt: theme.colors.panelAlt,
    accent: theme.colors.accent,
    secondary: theme.colors.secondary,
    text: theme.colors.text,
    sidebar: theme.colors.sidebar,
    selected: theme.colors.selected,
    border: theme.colors.border,
  },
  {
    background: "#F5F4ED",
    panel: "#FAF9F5",
    panelAlt: "#E8E6DC",
    accent: "#B85235",
    secondary: "#1B365D",
    text: "#141413",
    sidebar: "#F5F4ED",
    selected: "#EEECE6",
    border: "#E5E3D8",
  },
);
assert.match(css, /--ds-font-ui:\s*"思源宋体 VF"/);
assert.match(css, /--ds-font-code:\s*"SF Mono"/);
assert.match(css, /html\.codex-dream-skin body\s*\{[^}]*font-family:\s*var\(--ds-font-ui\)[^}]*font-weight:\s*var\(--ds-weight-body\) !important/s);
assert.match(
  css,
  /\[data-thread-find-target="conversation"\][\s\S]*?\[data-markdown-han-text="true"\][^}]*font-family:\s*var\(--ds-font-ui\)[^}]*font-weight:\s*var\(--ds-weight-body\) !important/s,
  "conversation markdown must override Codex's direct system-ui paragraph rule",
);
assert.match(css, /aside\.app-shell-left-panel\s*\{[^}]*font-weight:\s*var\(--ds-weight-body\) !important/s);
assert.match(css, /aside\.app-shell-left-panel button,[\s\S]*?font-weight:\s*var\(--ds-weight-body\) !important/);
assert.match(css, /data-app-action-sidebar-thread-active="true"\]\s*\{[^}]*font-weight:\s*var\(--ds-weight-emphasis\) !important/s);
assert.match(css, /button\[role="tab"\]\[aria-selected="true"\]\s*\{[^}]*font-weight:\s*var\(--ds-weight-emphasis\) !important/s);
assert.match(css, /\.group\\\/home-suggestions button\s*\{[^}]*font-weight:\s*var\(--ds-weight-emphasis\) !important/s);
assert.match(css, /\.ProseMirror\[contenteditable="true"\]\[role="textbox"\][\s\S]*?font-weight:\s*var\(--ds-weight-body\) !important/);
assert.match(css, /pointer-events:\s*none/);
assert.match(css, /@media \(max-width: 680px\)/);
assert.match(css, /data-app-action-sidebar-thread-active="true"/);
assert.match(css, /background:\s*var\(--ds-selected\)/);
assert.match(css, /border-radius:\s*var\(--ds-radius-control\)/);
assert.match(css, /inset 0 0 0 1px rgba\(27, 54, 93, \.06\)/);
assert.match(css, /\[class~="group\/tab"\]/);
assert.match(css, /width:\s*100% !important/);
assert.match(css, /max-width:\s*none !important/);
assert.match(css, /button:not\(\[aria-label\^="Close "\]\)/);
assert.match(css, /\[role="main"\]\.dream-skin-home/);
assert.match(css, /> \.dream-skin-home-content/);
assert.doesNotMatch(css, /dream-skin-home > div\s*\{[^}]*min-height:\s*100%/s);
assert.match(css, /\.dream-skin-home-shell > \.dream-skin-home-hero/);
assert.doesNotMatch(css, /\[role="main"\]:has\(\[data-feature="game-source"\]\):has\(\.group\\\/home-suggestions\)/);
assert.match(css, /height:\s*224px/);
assert.match(css, /height:\s*208px/);
assert.match(css, /height:\s*184px/);
assert.match(css, /background-size:\s*cover/);
assert.match(css, /border-radius:\s*var\(--ds-radius-hero\)/);
assert.match(css, /gap:\s*var\(--ds-home-gap\)/);
assert.match(css, /min-height:\s*var\(--ds-suggestion-min-height\)/);
assert.match(css, /grid-template-columns:\s*repeat\(auto-fit, minmax\(210px, 1fr\)\)/);
assert.match(css, /grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\)/);
assert.match(css, /\.group\\\/home-suggestions button:focus-visible/);
assert.match(css, /width:\s*28px/);
assert.match(css, /height:\s*28px/);
assert.match(css, /justify-content:\s*center !important/);
assert.doesNotMatch(css, /border-left\s*:/);
assert.doesNotMatch(css, /top:\s*100%/);
assert.doesNotMatch(css, /406px/);
assert.doesNotMatch(css, />\s*div:(?:first|nth)-child/);
assert.doesNotMatch(css, /main\.main-surface[^\n{]*\{[^}]*border-bottom/s);
assert.match(css, /main\.main-surface > header\.app-header-tint,\s*html\.codex-dream-skin main > header\s*\{[^}]*background:\s*transparent/s);
assert.match(css, /--color-token-main-surface-primary:\s*var\(--ds-bg\) !important/);
assert.match(css, /--color-token-side-bar-background:\s*var\(--ds-bg\) !important/);
assert.match(css, /--color-token-input-background:\s*var\(--ds-panel\) !important/);
assert.match(css, /--color-token-dropdown-background:\s*var\(--ds-panel\) !important/);
assert.match(css, /--color-token-list-active-selection-background:\s*var\(--ds-selected\) !important/);
assert.match(css, /\[class~="bg-token-main-surface-primary"\][^}]*background-color:\s*var\(--ds-bg\) !important/s);
assert.match(css, /\[class~="group\/tab"\]:has\(> button\[role="tab"\]\[aria-selected="true"\]\)/);
assert.match(css, /\[class\*="--thread-resource-card-row-padding-x:"\][^}]*background:\s*var\(--ds-panel\) !important/s);
assert.doesNotMatch(css, /\[data-dream-tab-title\]::after/);
assert.doesNotMatch(css, /main\.main-surface article|main article/);
assert.match(css, /main\.main-surface,\s*html\.codex-dream-skin main\s*\{/s);
assert.match(css, /main\.main-surface > header\.app-header-tint,\s*html\.codex-dream-skin main > header\s*\{/s);
assert.match(css, /\.dream-skin-composer\.dream-skin-composer\[class\*="ComposerLayoutRoot_"\]/);
assert.match(
  css,
  /--ds-shadow-composer:\s*none/,
  "composer must not paint a rectangular halo around the task-page input",
);
assert.match(
  css,
  /\.dream-skin-composer\.dream-skin-composer\[class\*="ComposerLayoutRoot_"\]\s*\{[^}]*position:\s*relative !important[^}]*border:\s*0 !important[^}]*border-radius:\s*var\(--ds-radius-composer\) !important[^}]*box-shadow:\s*var\(--ds-shadow-composer\) !important/s,
  "composer outer chrome must be route-independent and anchor the focus indicator",
);
assert.match(
  css,
  /\.dream-skin-composer\.dream-skin-composer\[class\*="ComposerLayoutRoot_"\]::after\s*\{[^}]*inset:\s*0[^}]*border:\s*1px solid var\(--ds-border\)[^}]*border-radius:\s*var\(--ds-radius-composer\)/s,
  "composer outline must be independent from the native route-specific border cascade",
);
assert.match(
  css,
  /\.dream-skin-composer \[class\*="ComposerLayoutBody_"\]\s*\{[^}]*background:\s*var\(--ds-panel\) !important[^}]*border-radius:\s*max\(0px, calc\(var\(--ds-radius-composer\) - 1px\)\) !important[^}]*box-shadow:\s*none !important/s,
  "composer inner surface must follow the outer radius without retaining native New Chat chrome",
);
assert.match(
  css,
  /left:\s*0[^}]*top:\s*var\(--ds-radius-composer\)[^}]*width:\s*3px[^}]*height:\s*20px[^}]*z-index:\s*20/s,
  "composer focus indicator must start on the shared outline instead of hanging outside it",
);
assert.match(
  css,
  /\[data-thread-scroll-footer\] \[class\*="bg-gradient-to-t"\]\[class\*="from-token-main-surface-primary"\]\s*\{[^}]*background:\s*transparent !important/s,
  "composer footer must not paint a rectangular gradient backing plate",
);
assert.doesNotMatch(css, /main\.main-surface:not\(\.dream-skin-home-shell\)[\s\S]{0,500}--dream-skin-art/);
assert.doesNotMatch(
  css,
  /backdrop-filter|(?:linear|radial)-gradient|@keyframes|dream-skin-particles|dream-skin-orbit|dream-skin-status|dream-skin-quote/i,
);
assert.doesNotMatch(css, /Microsoft YaHei|SF Pro Text|PingFang SC/);
assert.doesNotMatch(renderer, /dream-skin-logo-mark|dream-skin-logo-wordmark/);
assert.match(renderer, /removeLegacyBrandChrome/);
assert.doesNotMatch(renderer, /dream-skin-particles|dream-skin-orbit|dream-skin-status|dream-skin-quote/);
assert.match(injector, /Page\.addScriptToEvaluateOnNewDocument/);
assert.match(injector, /Page\.removeScriptToEvaluateOnNewDocument/);
assert.match(injector, /Page\.domContentEventFired/);
assert.doesNotMatch(injector, /Page\.loadEventFired/);
assert.doesNotMatch(injector, /setTimeout\([\s\S]{0,100}250\)/);
assert.match(injector, /prepaintBytes/);
assert.match(injector, /prepaintContainsImageData/);
assert.match(injector, /--ds-font-ui/);
assert.match(injector, /--ds-radius-composer/);
assert.match(renderer, /const syncHomeRoute = \(\) =>/);
assert.match(renderer, /classList\.toggle\("dream-skin-home", candidate === home\)/);
assert.match(renderer, /dream-skin-home-content/);
assert.match(renderer, /content\.parentElement !== home/);
assert.match(renderer, /suggestions\?\.parentElement\?\.parentElement/);
assert.match(renderer, /Math\.min\(960,\s*homeRect\.width \* 0\.6\)/);
assert.match(renderer, /style\.position === "relative"/);
assert.match(renderer, /if \(relativeShell\) shell = relativeShell/);
assert.doesNotMatch(renderer, /rect\.width >= homeRect\.width \* 0\.6/);
assert.match(renderer, /syncHomeRoute\(\)/);
assert.doesNotMatch(renderer, /180/);
assert.doesNotMatch(renderer, /attributes:\s*true/);
assert.match(renderer, /requestAnimationFrame/);
assert.match(renderer, /childList:\s*true/);
assert.match(renderer, /subtree:\s*true/);
assert.match(renderer, /new MutationObserver\(\(records\) =>/);
assert.match(renderer, /mutationTouchesShell/);
assert.match(renderer, /cancelAnimationFrame/);
assert.match(renderer, /dream-skin-home-shell/);
assert.match(renderer, /data-dream-tab-title/);
assert.match(renderer, /HOME_MARKERS\.join\(", \."\)/);
assert.match(renderer, /removeLegacyBrandChrome\(\)/);
assert.match(renderer, /const syncComposerSurface = \(\) =>/);
assert.match(renderer, /\.ProseMirror\[contenteditable="true"\]\[role="textbox"\]/);
assert.match(renderer, /classList\.add\("dream-skin-composer"\)/);
assert.doesNotMatch(renderer, /const ensureChrome/);
assert.match(injector, /:scope > header\.app-header-tint, :scope > header/);
assert.match(injector, /\.composer-surface-chrome, \.dream-skin-composer/);
assert.match(injector, /finally \{[\s\S]*delete window\.__DREAM_SKIN_ROUTE_PROBE__/);
assert.match(injector, /if \(window\.__CODEX_DREAM_SKIN_DISABLED__\) return/);
assert.match(injector, /__CODEX_DREAM_SKIN_ROUTE_CLICK_AT__/);
assert.match(injector, /__DREAM_SKIN_FIRST_FRAME__/);
assert.doesNotMatch(verificationContract, /verificationExpectations/);
assert.equal(
  crypto.createHash("sha256").update(image).digest("hex"),
  "85801eb03c46daed14c4f4df43139e02f5b06dd79a781f1c1d801f96f11d1999",
);
assert.equal(image.readUInt32BE(16), 1985);
assert.equal(image.readUInt32BE(20), 794);
assert.equal(
  crypto.createHash("sha256").update(genericImage).digest("hex"),
  "c3378bf9942942f06303dfb34adb94a3dac0a382089553f475816c37197fdac2",
);
assert.equal(genericImage.readUInt32BE(16), 1985);
assert.equal(genericImage.readUInt32BE(20), 794);
console.log("PASS: V3 natural-flow layout, paper-tab session, prepaint lifecycle, cleanup, and anti-slop constraints.");

import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const theme = JSON.parse(await fs.readFile(path.join(root, "assets/theme.json"), "utf8"));
const css = await fs.readFile(path.join(root, "assets/dream-skin.css"), "utf8");
const renderer = await fs.readFile(path.join(root, "assets/renderer-inject.js"), "utf8");
const injector = await fs.readFile(path.join(root, "scripts/injector.mjs"), "utf8");
const verification = await fs.readFile(path.join(root, "scripts/verification-contract.mjs"), "utf8");
const image = await fs.readFile(path.join(root, "assets/default-banner.png"));

assert.equal(theme.id, "warm-paper-starter");
assert.equal(theme.name, "Warm Paper Studio");
assert.equal(theme.image, "default-banner.png");
assert.equal(theme.brandImage, "");
assert.equal(theme.showBrand, true);
assert.equal(theme.artPlacement, "hero");
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
    background: "#F5F3EE",
    panel: "#FAF9F6",
    panelAlt: "#EEECE6",
    accent: "#DA7756",
    secondary: "#1B365D",
    text: "#1D1B16",
    sidebar: "#F1F0EC",
    selected: "#E8E6DC",
    border: "#E4E1DA",
  },
);
assert.match(css, /--ds-ui-font/);
assert.match(css, /--ds-code-font/);
assert.match(css, /pointer-events:\s*none/);
assert.match(css, /@media \(max-width: 680px\)/);
assert.match(css, /data-app-action-sidebar-thread-active="true"/);
assert.match(css, /background:\s*var\(--ds-selected\)/);
assert.match(css, /border-radius:\s*6px/);
assert.match(css, /inset 0 0 0 1px rgba\(27, 54, 93, \.06\)/);
assert.match(css, /\[class~="group\/tab"\]/);
assert.match(css, /data-dream-tab-title/);
assert.match(css, /height:\s*224px/);
assert.match(css, /height:\s*208px/);
assert.match(css, /height:\s*184px/);
assert.match(css, /background-size:\s*cover/);
assert.match(css, /data-dream-art-placement="all"/);
assert.match(css, /grid-template-columns:\s*repeat\(auto-fit, minmax\(210px, 1fr\)\)/);
assert.match(css, /grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\)/);
assert.match(css, /\.group\\\/home-suggestions button:focus-visible/);
assert.doesNotMatch(css, /border-left\s*:/);
assert.doesNotMatch(css, /top:\s*100%/);
assert.doesNotMatch(css, />\s*div:(?:first|nth)-child/);
assert.doesNotMatch(css, /main\.main-surface[^\n{]*\{[^}]*border-bottom/s);
assert.match(css, /main\.main-surface > header\.app-header-tint\s*\{[^}]*background:\s*transparent/s);
assert.doesNotMatch(css, /main\.main-surface:not\(\.dream-skin-home-shell\)[\s\S]{0,500}--dream-skin-art/);
assert.doesNotMatch(
  css,
  /backdrop-filter|(?:linear|radial)-gradient|@keyframes|dream-skin-particles|dream-skin-orbit|dream-skin-status|dream-skin-quote/i,
);
assert.match(renderer, /dream-skin-brand-image/);
assert.match(renderer, /dream-skin-brand-label/);
assert.match(renderer, /THEME\.showBrand === false/);
assert.match(renderer, /data-dream-art-placement/);
assert.doesNotMatch(renderer, /zhijian-ai|logo-wordmark|logo-mark/i);
assert.match(injector, /Page\.addScriptToEvaluateOnNewDocument/);
assert.match(injector, /Page\.removeScriptToEvaluateOnNewDocument/);
assert.match(injector, /Page\.domContentEventFired/);
assert.doesNotMatch(injector, /Page\.loadEventFired/);
assert.match(injector, /expectedColors: theme\?\.colors/);
assert.match(injector, /brandImage/);
assert.match(verification, /options\.expectedColors/);
assert.match(verification, /export function colorsMatch/);
assert.doesNotMatch(renderer, /classList\.(?:add|toggle)\(["']dream-skin-home/);
assert.doesNotMatch(renderer, /attributes:\s*true/);
assert.match(renderer, /requestAnimationFrame/);
assert.match(renderer, /new MutationObserver\(\(records\) =>/);
assert.match(renderer, /mutationTouchesShell/);
assert.match(renderer, /cancelAnimationFrame/);
assert.equal(
  crypto.createHash("sha256").update(image).digest("hex"),
  "62964dffc5c290c7528cf0ce611743755b85f4e28ec59f06339420a05f393668",
);
assert.equal(image.readUInt32BE(16), 2000);
assert.equal(image.readUInt32BE(20), 800);

console.log("PASS: portable starter theme, natural-flow layout, brand options, dynamic colors, and anti-slop constraints.");

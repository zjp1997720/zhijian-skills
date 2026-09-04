import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { evaluateSnapshot, isCodexRendererProbe } from "../scripts/verification-contract.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)));
const fixture = async (name) => JSON.parse(await fs.readFile(path.join(root, "fixtures", name), "utf8"));
const injector = await fs.readFile(path.join(root, "..", "scripts", "injector.mjs"), "utf8");
const verifyShell = await fs.readFile(path.join(root, "..", "scripts", "verify-dream-skin-macos.sh"), "utf8");

const healthyRenderer = {
  primaryRoute: true,
  title: "ChatGPT",
  markers: { root: true, sidebar: true, main: true },
};
assert.equal(isCodexRendererProbe(healthyRenderer), true);
assert.equal(isCodexRendererProbe({ ...healthyRenderer, title: "Codex" }), true);
assert.equal(isCodexRendererProbe({ ...healthyRenderer, primaryRoute: false }), false);
assert.equal(isCodexRendererProbe({ ...healthyRenderer, title: "Other" }), false);
assert.equal(
  isCodexRendererProbe({ ...healthyRenderer, markers: { ...healthyRenderer.markers, sidebar: false } }),
  false,
);

const home = evaluateSnapshot(await fixture("v3-home-state.json"));
assert.equal(home.pass, true);
assert.equal(home.strictVisualPass, true);
assert.equal(home.degraded, false);
assert.deepEqual(home.reasons, []);

const typedHome = structuredClone(await fixture("v3-home-state.json"));
typedHome.home.suggestionsPresent = false;
typedHome.home.cards = [];
typedHome.home.cardColumns = null;
const typedHomeResult = evaluateSnapshot(typedHome);
assert.equal(typedHomeResult.pass, true);
assert.equal(typedHomeResult.strictVisualPass, true);
assert.equal(typedHomeResult.degraded, false);

const task = evaluateSnapshot(await fixture("v3-task-state.json"));
assert.equal(task.pass, true);
assert.equal(task.strictVisualPass, true);
assert.equal(task.degraded, false);

const conversationFontRegression = structuredClone(await fixture("v3-task-state.json"));
conversationFontRegression.shell.typography.conversationNonSerifHanTextCount = 2;
const conversationFontRegressionResult = evaluateSnapshot(conversationFontRegression);
assert.equal(conversationFontRegressionResult.pass, true);
assert.equal(conversationFontRegressionResult.strictVisualPass, false);
assert.match(conversationFontRegressionResult.reasons.join(" "), /conversation-han-font-family/);

const missingConversationFontProbe = structuredClone(await fixture("v3-task-state.json"));
delete missingConversationFontProbe.shell.typography.conversationHanTextCount;
delete missingConversationFontProbe.shell.typography.conversationNonSerifHanTextCount;
const missingConversationFontProbeResult = evaluateSnapshot(missingConversationFontProbe);
assert.equal(missingConversationFontProbeResult.strictVisualPass, false);
assert.match(missingConversationFontProbeResult.reasons.join(" "), /conversation-font-probe-missing/);

const lightTypography = structuredClone(await fixture("v3-task-state.json"));
lightTypography.shell.typography = {
  bodyWeight: 400,
  sidebarWeight: 400,
  sidebarControlWeight: 400,
  mainTextWeight: 400,
  composerWeight: 400,
  emphasisWeights: [500],
};
const lightTypographyResult = evaluateSnapshot(lightTypography);
assert.equal(lightTypographyResult.pass, true);
assert.equal(lightTypographyResult.strictVisualPass, false);
assert.match(lightTypographyResult.reasons.join(" "), /typography/);

const system = evaluateSnapshot(await fixture("v3-system-state.json"));
assert.equal(system.pass, true);
assert.equal(system.strictVisualPass, true);
assert.equal(system.degraded, false);

const degraded = evaluateSnapshot(await fixture("v3-degraded-state.json"));
assert.equal(degraded.pass, true);
assert.equal(degraded.strictVisualPass, false);
assert.equal(degraded.degraded, true);
assert.match(degraded.degradedReasons.join(" "), /home-enhancement-hook-missing/);

const hiddenCard = structuredClone(await fixture("v3-home-state.json"));
hiddenCard.home.cards[2].visible = false;
const hiddenResult = evaluateSnapshot(hiddenCard);
assert.equal(hiddenResult.pass, false);
assert.match(hiddenResult.reasons.join(" "), /home-card-hidden/);

const keyboardFailure = structuredClone(await fixture("v3-home-state.json"));
keyboardFailure.home.cards[0].focusable = false;
const keyboardResult = evaluateSnapshot(keyboardFailure);
assert.equal(keyboardResult.pass, false);
assert.match(keyboardResult.reasons.join(" "), /home-card-not-focusable/);

const threeCardHome = structuredClone(await fixture("v3-home-state.json"));
threeCardHome.home.cards.pop();
threeCardHome.home.cardColumns = 3;
const threeCardResult = evaluateSnapshot(threeCardHome);
assert.equal(threeCardResult.pass, true);
assert.equal(threeCardResult.strictVisualPass, true);

const disabledSingleCard = structuredClone(await fixture("v3-home-state.json"));
disabledSingleCard.home.cards = [{ ...disabledSingleCard.home.cards[0], disabled: true, focusable: false }];
disabledSingleCard.home.cardColumns = 1;
const disabledSingleCardResult = evaluateSnapshot(disabledSingleCard);
assert.equal(disabledSingleCardResult.pass, true);
assert.equal(disabledSingleCardResult.strictVisualPass, true);

const overflow = structuredClone(await fixture("v3-home-state.json"));
overflow.documentOverflow.x = true;
assert.equal(evaluateSnapshot(overflow).pass, false);

const taskArt = structuredClone(await fixture("v3-task-state.json"));
taskArt.task.backgroundImage = "url(blob:unexpected)";
taskArt.task.brandVisible = true;
const taskArtResult = evaluateSnapshot(taskArt);
assert.equal(taskArtResult.pass, true);
assert.equal(taskArtResult.strictVisualPass, false);
assert.match(taskArtResult.reasons.join(" "), /task-background-art|task-brand-visible/);

const legacyBrandChrome = structuredClone(await fixture("v3-home-state.json"));
legacyBrandChrome.chromePresent = true;
legacyBrandChrome.chromePointerEvents = "none";
const legacyBrandChromeResult = evaluateSnapshot(legacyBrandChrome);
assert.equal(legacyBrandChromeResult.pass, true);
assert.equal(legacyBrandChromeResult.strictVisualPass, false);
assert.match(legacyBrandChromeResult.reasons.join(" "), /legacy-brand-chrome-present/);

const splitSurface = structuredClone(await fixture("v3-system-state.json"));
splitSurface.shell.structuralSurfaces[1].backgroundColor = "rgb(249, 249, 247)";
const splitSurfaceResult = evaluateSnapshot(splitSurface);
assert.equal(splitSurfaceResult.pass, true);
assert.equal(splitSurfaceResult.strictVisualPass, false);
assert.match(splitSurfaceResult.reasons.join(" "), /structural-surface-color/);

const hiddenHeaderTab = structuredClone(await fixture("v3-task-state.json"));
hiddenHeaderTab.shell.headerTabs[0].titleVisible = false;
hiddenHeaderTab.shell.headerTabs[0].titleLayerVisible = false;
const hiddenHeaderTabResult = evaluateSnapshot(hiddenHeaderTab);
assert.equal(hiddenHeaderTabResult.pass, false);
assert.match(hiddenHeaderTabResult.reasons.join(" "), /header-tab-hidden/);

const missingHeaderProbe = structuredClone(await fixture("v3-task-state.json"));
missingHeaderProbe.shell.headerTabs = [];
const missingHeaderProbeResult = evaluateSnapshot(missingHeaderProbe);
assert.equal(missingHeaderProbeResult.pass, false);
assert.match(missingHeaderProbeResult.reasons.join(" "), /header-tab-probe-mismatch/);

const opaqueMainHeader = structuredClone(await fixture("v3-task-state.json"));
opaqueMainHeader.shell.topHeaderBackground = "rgb(245, 244, 237)";
const opaqueMainHeaderResult = evaluateSnapshot(opaqueMainHeader);
assert.equal(opaqueMainHeaderResult.strictVisualPass, false);
assert.match(opaqueMainHeaderResult.reasons.join(" "), /workspace-tabs-occluded-by-main-header/);

const offCenterIcon = structuredClone(await fixture("v3-home-state.json"));
offCenterIcon.home.cards[0].iconOffset.x = -4.5;
const offCenterIconResult = evaluateSnapshot(offCenterIcon);
assert.equal(offCenterIconResult.pass, true);
assert.equal(offCenterIconResult.strictVisualPass, false);
assert.match(offCenterIconResult.reasons.join(" "), /home-card-icon-off-center/);

const missingIconGeometry = structuredClone(await fixture("v3-home-state.json"));
missingIconGeometry.home.cards[0].iconOffset = null;
const missingIconGeometryResult = evaluateSnapshot(missingIconGeometry);
assert.equal(missingIconGeometryResult.strictVisualPass, true);

const belowFold = structuredClone(await fixture("v3-home-state.json"));
belowFold.home.hero.inViewport = false;
belowFold.shell.composer.inViewport = false;
const belowFoldResult = evaluateSnapshot(belowFold);
assert.equal(belowFoldResult.pass, false);
assert.match(belowFoldResult.reasons.join(" "), /home-hero-below-fold/);
assert.match(belowFoldResult.reasons.join(" "), /composer-below-fold/);

const doubleChrome = structuredClone(await fixture("v3-home-state.json"));
doubleChrome.shell.composerVisual.body.borderRadius = "25px";
doubleChrome.shell.composerVisual.body.boxShadow = "rgba(0, 0, 0, .12) 0 0 20px";
const doubleChromeResult = evaluateSnapshot(doubleChrome);
assert.equal(doubleChromeResult.pass, true);
assert.equal(doubleChromeResult.strictVisualPass, false);
assert.match(doubleChromeResult.reasons.join(" "), /composer-inner-radius/);
assert.match(doubleChromeResult.reasons.join(" "), /composer-inner-native-shadow/);

const rectangularFrame = structuredClone(await fixture("v3-task-state.json"));
rectangularFrame.shell.composerVisual.surface.boxShadow = "rgba(20, 20, 19, .045) 0 0 12px";
rectangularFrame.shell.composerVisual.surface.after = null;
const rectangularFrameResult = evaluateSnapshot(rectangularFrame);
assert.equal(rectangularFrameResult.pass, true);
assert.equal(rectangularFrameResult.strictVisualPass, false);
assert.match(rectangularFrameResult.reasons.join(" "), /composer-outline-missing/);
assert.match(rectangularFrameResult.reasons.join(" "), /composer-outer-frame-shadow/);

const misplacedFocusIndicator = structuredClone(await fixture("v3-home-state.json"));
misplacedFocusIndicator.shell.composerVisual.surface.before.left = "-1px";
const misplacedFocusIndicatorResult = evaluateSnapshot(misplacedFocusIndicator);
assert.equal(misplacedFocusIndicatorResult.pass, true);
assert.equal(misplacedFocusIndicatorResult.strictVisualPass, false);
assert.match(misplacedFocusIndicatorResult.reasons.join(" "), /composer-focus-indicator-position/);

const visibleComposerBacking = structuredClone(await fixture("v3-task-state.json"));
visibleComposerBacking.shell.composerVisual.backdrops[0].backgroundImage =
  "linear-gradient(to top, rgb(249, 249, 247), rgba(0, 0, 0, 0))";
visibleComposerBacking.shell.composerVisual.backdrops[1].backgroundColor = "rgb(249, 249, 247)";
const visibleComposerBackingResult = evaluateSnapshot(visibleComposerBacking);
assert.equal(visibleComposerBackingResult.pass, true);
assert.equal(visibleComposerBackingResult.strictVisualPass, false);
assert.match(visibleComposerBackingResult.reasons.join(" "), /composer-backing-gradient-visible/);
assert.match(visibleComposerBackingResult.reasons.join(" "), /composer-backing-color-visible/);

assert.match(injector, /collectSessionSnapshot/);
assert.match(injector, /evaluateSnapshot/);
assert.match(injector, /\[0, 50, 150, 500\]/);
assert.match(injector, /Input\.dispatchMouseEvent/);
assert.match(injector, /Emulation\.setDeviceMetricsOverride/);
assert.match(injector, /new-task-samples\.json/);
assert.match(injector, /new-chat-first-frame-not-warm-paper/);
assert.match(injector, /new-chat-control-not-clickable/);
assert.match(injector, /new-task-route-not-observed/);
assert.match(injector, /offset >= 150/);
assert.match(injector, /settledCardCount/);
assert.match(injector, /v3-new-task-first-frame\.png/);
assert.match(injector, /source: "post-click-compositor"/);
assert.match(injector, /candidate\?\.capturedAt >= clickWallAt/);
assert.match(injector, /this\.ws\.close\(\)[\s\S]*CDP WebSocket open timed out/);
assert.match(injector, /cancel: \(\) => finish\(new Error\(`CDP event canceled/);
assert.match(injector, /for \(const \{ session \} of connected\) session\.close\(\)/);
assert.match(verifyShell, /--strict-visual/);
assert.match(injector, /data-markdown-han-text/);
assert.match(injector, /conversationNonSerifHanTextCount/);
assert.match(verifyShell, /--viewport/);
assert.match(verifyShell, /--sample-new-task/);

console.log("PASS: V3 home, task, degraded, keyboard, visibility, overflow, and task-art verification contracts.");

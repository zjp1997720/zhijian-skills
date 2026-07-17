import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { evaluateSnapshot } from "../scripts/verification-contract.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)));
const fixture = async (name) => JSON.parse(await fs.readFile(path.join(root, "fixtures", name), "utf8"));
const injector = await fs.readFile(path.join(root, "..", "scripts", "injector.mjs"), "utf8");
const verifyShell = await fs.readFile(path.join(root, "..", "scripts", "verify-dream-skin-macos.sh"), "utf8");

const home = evaluateSnapshot(await fixture("home-state.json"));
assert.equal(home.pass, true);
assert.equal(home.strictVisualPass, true);
assert.equal(home.degraded, false);
assert.deepEqual(home.reasons, []);

const typedHome = structuredClone(await fixture("home-state.json"));
typedHome.home.suggestionsPresent = false;
typedHome.home.cards = [];
typedHome.home.cardColumns = null;
const typedHomeResult = evaluateSnapshot(typedHome);
assert.equal(typedHomeResult.pass, true);
assert.equal(typedHomeResult.strictVisualPass, true);
assert.equal(typedHomeResult.degraded, false);

const task = evaluateSnapshot(await fixture("task-state.json"));
assert.equal(task.pass, true);
assert.equal(task.strictVisualPass, true);
assert.equal(task.degraded, false);

const degraded = evaluateSnapshot(await fixture("degraded-state.json"));
assert.equal(degraded.pass, true);
assert.equal(degraded.strictVisualPass, false);
assert.equal(degraded.degraded, true);
assert.match(degraded.degradedReasons.join(" "), /home-enhancement-hook-missing/);

const customPalette = structuredClone(await fixture("home-state.json"));
customPalette.shell.mainBackground = "rgb(240, 238, 232)";
customPalette.shell.sidebarBackground = "rgb(233, 231, 223)";
customPalette.home.selectedSession.backgroundColor = "rgb(221, 217, 207)";
const customPaletteResult = evaluateSnapshot(customPalette, {
  expectedColors: { background: "#f0eee8", sidebar: "#e9e7df", selected: "#ddd9cf" },
});
assert.equal(customPaletteResult.strictVisualPass, true);

const hiddenCard = structuredClone(await fixture("home-state.json"));
hiddenCard.home.cards[2].visible = false;
const hiddenResult = evaluateSnapshot(hiddenCard);
assert.equal(hiddenResult.pass, false);
assert.match(hiddenResult.reasons.join(" "), /home-card-hidden/);

const keyboardFailure = structuredClone(await fixture("home-state.json"));
keyboardFailure.home.cards[0].focusable = false;
const keyboardResult = evaluateSnapshot(keyboardFailure);
assert.equal(keyboardResult.pass, false);
assert.match(keyboardResult.reasons.join(" "), /home-card-not-focusable/);

const threeCardHome = structuredClone(await fixture("home-state.json"));
threeCardHome.home.cards.pop();
threeCardHome.home.cardColumns = 3;
const threeCardResult = evaluateSnapshot(threeCardHome);
assert.equal(threeCardResult.pass, false);
assert.match(threeCardResult.reasons.join(" "), /home-card-count/);

const overflow = structuredClone(await fixture("home-state.json"));
overflow.documentOverflow.x = true;
assert.equal(evaluateSnapshot(overflow).pass, false);

const taskArt = structuredClone(await fixture("task-state.json"));
taskArt.task.backgroundImage = "url(blob:unexpected)";
taskArt.task.brandVisible = true;
const taskArtResult = evaluateSnapshot(taskArt);
assert.equal(taskArtResult.pass, true);
assert.equal(taskArtResult.strictVisualPass, false);
assert.match(taskArtResult.reasons.join(" "), /task-background-art|task-brand-visible/);

const fullBackgroundTask = structuredClone(await fixture("task-state.json"));
fullBackgroundTask.task.backgroundImage = "url(blob:theme-background)";
const fullBackgroundResult = evaluateSnapshot(fullBackgroundTask, { expectedArtPlacement: "all" });
assert.equal(fullBackgroundResult.strictVisualPass, true);
const missingFullBackground = structuredClone(await fixture("task-state.json"));
const missingFullBackgroundResult = evaluateSnapshot(missingFullBackground, { expectedArtPlacement: "all" });
assert.equal(missingFullBackgroundResult.strictVisualPass, false);
assert.match(missingFullBackgroundResult.reasons.join(" "), /task-background-art-missing/);

const hiddenHeaderTab = structuredClone(await fixture("task-state.json"));
hiddenHeaderTab.shell.headerTabs[0].titleVisible = false;
hiddenHeaderTab.shell.headerTabs[0].titleLayerVisible = false;
const hiddenHeaderTabResult = evaluateSnapshot(hiddenHeaderTab);
assert.equal(hiddenHeaderTabResult.pass, false);
assert.match(hiddenHeaderTabResult.reasons.join(" "), /header-tab-hidden/);

const missingHeaderProbe = structuredClone(await fixture("task-state.json"));
missingHeaderProbe.shell.headerTabs = [];
const missingHeaderProbeResult = evaluateSnapshot(missingHeaderProbe);
assert.equal(missingHeaderProbeResult.pass, false);
assert.match(missingHeaderProbeResult.reasons.join(" "), /header-tab-probe-mismatch/);

const opaqueMainHeader = structuredClone(await fixture("task-state.json"));
opaqueMainHeader.shell.topHeaderBackground = "rgb(245, 243, 238)";
const opaqueMainHeaderResult = evaluateSnapshot(opaqueMainHeader);
assert.equal(opaqueMainHeaderResult.strictVisualPass, false);
assert.match(opaqueMainHeaderResult.reasons.join(" "), /workspace-tabs-occluded-by-main-header/);

const offCenterIcon = structuredClone(await fixture("home-state.json"));
offCenterIcon.home.cards[0].iconOffset.x = -4.5;
const offCenterIconResult = evaluateSnapshot(offCenterIcon);
assert.equal(offCenterIconResult.pass, true);
assert.equal(offCenterIconResult.strictVisualPass, false);
assert.match(offCenterIconResult.reasons.join(" "), /home-card-icon-off-center/);

const missingIconGeometry = structuredClone(await fixture("home-state.json"));
missingIconGeometry.home.cards[0].iconOffset = null;
const missingIconGeometryResult = evaluateSnapshot(missingIconGeometry);
assert.equal(missingIconGeometryResult.strictVisualPass, false);
assert.match(missingIconGeometryResult.reasons.join(" "), /home-card-icon-off-center/);

assert.match(injector, /collectSessionSnapshot/);
assert.match(injector, /evaluateSnapshot/);
assert.match(injector, /\[0, 50, 150, 500\]/);
assert.match(injector, /Input\.dispatchMouseEvent/);
assert.match(injector, /Emulation\.setDeviceMetricsOverride/);
assert.match(injector, /new-task-samples\.json/);
assert.match(injector, /new-task-first-frame-background-mismatch/);
assert.match(injector, /new-task-control-not-clickable/);
assert.match(injector, /new-task-route-not-observed/);
assert.match(injector, /new-task-first-frame\.png/);
assert.match(injector, /source: "post-click-compositor"/);
assert.match(injector, /candidate\?\.capturedAt >= clickWallAt/);
assert.match(injector, /this\.ws\.close\(\)[\s\S]*CDP WebSocket open timed out/);
assert.match(injector, /cancel: \(\) => finish\(new Error\(`CDP event canceled/);
assert.match(injector, /for \(const \{ session \} of connected\) session\.close\(\)/);
assert.match(verifyShell, /--strict-visual/);
assert.match(verifyShell, /--viewport/);
assert.match(verifyShell, /--sample-new-task/);

console.log("PASS: home, task, degraded, keyboard, visibility, overflow, and task-art verification contracts.");

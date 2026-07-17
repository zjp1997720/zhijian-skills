import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = (file) => fs.readFile(path.join(root, file), "utf8");
const [common, manager, installer, pause, restore] = await Promise.all([
  read("scripts/common-macos.sh"),
  read("scripts/resident-manager-macos.sh"),
  read("scripts/install-resident-manager-macos.sh"),
  read("scripts/pause-dream-skin-macos.sh"),
  read("scripts/restore-dream-skin-macos.sh"),
]);

assert.match(manager, /codex_is_running/);
assert.match(manager, /verified_cdp_endpoint/);
assert.match(manager, /recorded_injector_is_running/);
assert.match(manager, /--restart-existing/);
assert.match(manager, /now - last_restart/);
assert.match(manager, /-lt 45/);
assert.doesNotMatch(manager, /launch_codex_(?:normally|with_cdp)/);

assert.match(installer, /autoRestartNormalLaunch:\s*true/);
assert.match(installer, /<key>RunAtLoad<\/key><true\/>/);
assert.match(installer, /<key>SuccessfulExit<\/key><false\/>/);
assert.match(installer, /plutil -lint/);
assert.match(installer, /PROJECT_ROOT" = "\$INSTALL_ROOT/);
assert.match(installer, /--disable/);

assert.match(common, /disable_resident_manager/);
assert.match(common, /launchctl bootout/);
assert.match(common, /RESIDENT_MANAGER_CONFIG/);
assert.ok(pause.indexOf("disable_resident_manager") < pause.indexOf("stop_recorded_injector"));
assert.ok(restore.indexOf("disable_resident_manager") < restore.indexOf("stop_recorded_injector"));

console.log("PASS: opt-in resident manager, cooldown, official runtime gate, and pause/restore boundaries.");

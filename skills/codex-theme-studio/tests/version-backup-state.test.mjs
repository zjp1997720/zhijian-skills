import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";

const run = promisify(execFile);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const script = path.join(root, "scripts/version-backup-state.mjs");
const temporary = await fs.mkdtemp(path.join(os.tmpdir(), "codex-version-backup-test-"));

async function sha256(file) {
  const contents = await fs.readFile(file);
  return crypto.createHash("sha256").update(contents).digest("hex");
}

async function invoke(...args) {
  return run(process.execPath, [script, ...args], { encoding: "utf8" });
}

async function createFixture(name, { symlink = false } = {}) {
  const fixtureRoot = path.join(temporary, name);
  const installRoot = path.join(fixtureRoot, "install");
  const themeDir = path.join(fixtureRoot, "theme");
  const stateRoot = path.join(fixtureRoot, "state");
  const baseline = path.join(fixtureRoot, "baseline.json");
  await fs.mkdir(path.join(installRoot, "assets"), { recursive: true });
  await fs.mkdir(path.join(installRoot, "scripts"), { recursive: true });
  await fs.mkdir(themeDir, { recursive: true });
  await fs.writeFile(path.join(installRoot, "VERSION"), "1.1.2\n");
  await fs.writeFile(path.join(installRoot, "assets/theme.json"), '{"id":"v2","image":"hero.png"}\n');
  await fs.writeFile(path.join(installRoot, "assets/runtime.css"), "body{background:#f5f4ed}\n");
  await fs.writeFile(path.join(installRoot, "scripts/start.sh"), "#!/bin/bash\necho v2\n", { mode: 0o700 });
  await fs.writeFile(path.join(themeDir, "theme.json"), '{"id":"v2","image":"hero.png"}\n');
  await fs.writeFile(path.join(themeDir, "hero.png"), Buffer.from([1, 2, 3, 4]));
  if (symlink) await fs.symlink(path.join(fixtureRoot, "outside"), path.join(installRoot, "outside-link"));

  const critical = ["VERSION", "assets/theme.json", "assets/runtime.css"];
  const files = {};
  for (const relative of critical) {
    const file = path.join(installRoot, relative);
    const stat = await fs.stat(file);
    files[relative] = { bytes: stat.size, sha256: await sha256(file) };
  }
  await fs.writeFile(baseline, `${JSON.stringify({
    schemaVersion: 1,
    label: "v2-test",
    commit: "fixture",
    version: "1.1.2",
    files,
  }, null, 2)}\n`);
  return { fixtureRoot, installRoot, themeDir, stateRoot, baseline };
}

try {
  const commonSource = await fs.readFile(path.join(root, "scripts/common-macos.sh"), "utf8");
  assert.match(commonSource, /validate_port\(\)/, "shared runtime must own port validation");

  const installerSource = await fs.readFile(path.join(root, "scripts/install-dream-skin-macos.sh"), "utf8");
  assert.match(installerSource, /validate_port "\$PORT"/);
  const startSource = await fs.readFile(path.join(root, "scripts/start-dream-skin-macos.sh"), "utf8");
  assert.match(startSource, /validate_port "\$PORT"/);
  const snapshotCall = installerSource.indexOf("version-backup-state.mjs\" snapshot");
  const deployCall = installerSource.indexOf("\n  deploy_project\n");
  assert.ok(snapshotCall >= 0 && deployCall > snapshotCall, "V2 snapshot must run before deploy_project");
  assert.match(installerSource, /rsync -a --checksum/, "deploy must compare content after timestamp-preserving restores");

  const restoreSource = await fs.readFile(path.join(root, "scripts/restore-version-macos.sh"), "utf8");
  assert.match(restoreSource, /validate_port "\$PORT"/);
  const stopCall = restoreSource.indexOf("stop_recorded_injector");
  const restoreCall = restoreSource.indexOf("version-backup-state.mjs\" restore");
  assert.ok(stopCall >= 0 && restoreCall > stopCall, "injector stop must run before version restore");

  const fixture = await createFixture("happy");
  const first = JSON.parse((await invoke(
    "snapshot",
    "--state-root", fixture.stateRoot,
    "--install-root", fixture.installRoot,
    "--theme-dir", fixture.themeDir,
    "--baseline", fixture.baseline,
  )).stdout);
  assert.equal(first.pass, true);
  assert.equal(first.reused, false);
  assert.equal(first.label, "v2-test");

  const backupRoot = path.join(fixture.stateRoot, "version-backups/v2-test");
  const manifestPath = path.join(backupRoot, "manifest.json");
  const manifestBefore = await fs.readFile(manifestPath, "utf8");
  const second = JSON.parse((await invoke(
    "snapshot",
    "--state-root", fixture.stateRoot,
    "--install-root", fixture.installRoot,
    "--theme-dir", fixture.themeDir,
    "--baseline", fixture.baseline,
  )).stdout);
  assert.equal(second.reused, true);
  assert.equal(await fs.readFile(manifestPath, "utf8"), manifestBefore);

  const verified = JSON.parse((await invoke(
    "verify", "--state-root", fixture.stateRoot, "--label", "v2-test",
  )).stdout);
  assert.equal(verified.pass, true);
  assert.ok(verified.files >= 6);
  for (const relative of ["manifest.json", "engine/VERSION", "theme/theme.json", "theme/hero.png"]) {
    const stat = await fs.stat(path.join(backupRoot, relative));
    assert.equal(stat.mode & 0o077, 0);
  }

  await fs.writeFile(path.join(fixture.installRoot, "VERSION"), "v3\n");
  await fs.writeFile(path.join(fixture.themeDir, "theme.json"), '{"id":"v3","image":"v3.png"}\n');
  await fs.writeFile(path.join(fixture.themeDir, "v3.png"), Buffer.from([9, 9, 9]));
  const restored = JSON.parse((await invoke(
    "restore",
    "--state-root", fixture.stateRoot,
    "--install-root", fixture.installRoot,
    "--theme-dir", fixture.themeDir,
    "--label", "v2-test",
  )).stdout);
  assert.equal(restored.pass, true);
  assert.equal(await fs.readFile(path.join(fixture.installRoot, "VERSION"), "utf8"), "1.1.2\n");
  assert.equal(JSON.parse(await fs.readFile(path.join(fixture.themeDir, "theme.json"))).id, "v2");
  await assert.rejects(fs.access(path.join(fixture.themeDir, "v3.png")));
  assert.equal((await fs.stat(path.join(fixture.installRoot, "scripts/start.sh"))).mode & 0o777, 0o700);

  const generic = await createFixture("generic-label");
  const genericSnapshot = JSON.parse((await invoke(
    "snapshot",
    "--state-root", generic.stateRoot,
    "--install-root", generic.installRoot,
    "--theme-dir", generic.themeDir,
    "--label", "pre-upgrade-1.1.2",
  )).stdout);
  assert.equal(genericSnapshot.pass, true);
  assert.equal(genericSnapshot.label, "pre-upgrade-1.1.2");
  const genericManifest = JSON.parse(await fs.readFile(
    path.join(generic.stateRoot, "version-backups/pre-upgrade-1.1.2/manifest.json"),
    "utf8",
  ));
  assert.equal(genericManifest.sourceVersion, "1.1.2");

  const zeroMode = await createFixture("zero-mode");
  await invoke(
    "snapshot",
    "--state-root", zeroMode.stateRoot,
    "--install-root", zeroMode.installRoot,
    "--theme-dir", zeroMode.themeDir,
    "--baseline", zeroMode.baseline,
  );
  const zeroModeManifestPath = path.join(zeroMode.stateRoot, "version-backups/v2-test/manifest.json");
  const zeroModeManifest = JSON.parse(await fs.readFile(zeroModeManifestPath));
  zeroModeManifest.files.find((item) => item.scope === "engine" && item.path === "assets/runtime.css").restoreMode = 0;
  await fs.writeFile(zeroModeManifestPath, `${JSON.stringify(zeroModeManifest, null, 2)}\n`, { mode: 0o600 });
  await assert.rejects(
    invoke("verify", "--state-root", zeroMode.stateRoot, "--label", "v2-test"),
    (error) => /Invalid restore mode/.test(error.stderr),
  );

  const mismatch = await createFixture("mismatch");
  await fs.appendFile(path.join(mismatch.installRoot, "assets/runtime.css"), "/* changed */\n");
  await assert.rejects(
    invoke(
      "snapshot",
      "--state-root", mismatch.stateRoot,
      "--install-root", mismatch.installRoot,
      "--theme-dir", mismatch.themeDir,
      "--baseline", mismatch.baseline,
    ),
    (error) => /baseline fingerprint mismatch/.test(error.stderr),
  );
  await assert.rejects(fs.access(path.join(mismatch.stateRoot, "version-backups/v2-test")));

  const linked = await createFixture("symlink", { symlink: true });
  await assert.rejects(
    invoke(
      "snapshot",
      "--state-root", linked.stateRoot,
      "--install-root", linked.installRoot,
      "--theme-dir", linked.themeDir,
      "--baseline", linked.baseline,
    ),
    (error) => /symbolic links are not allowed/.test(error.stderr),
  );

  const tampered = await createFixture("tampered");
  await invoke(
    "snapshot",
    "--state-root", tampered.stateRoot,
    "--install-root", tampered.installRoot,
    "--theme-dir", tampered.themeDir,
    "--baseline", tampered.baseline,
  );
  const tamperedBackup = path.join(tampered.stateRoot, "version-backups/v2-test");
  await fs.appendFile(path.join(tamperedBackup, "engine/VERSION"), "tampered\n");
  await assert.rejects(
    invoke("verify", "--state-root", tampered.stateRoot, "--label", "v2-test"),
    (error) => /sha256 mismatch|byte count mismatch/.test(error.stderr),
  );
  const currentBefore = await fs.readFile(path.join(tampered.installRoot, "VERSION"), "utf8");
  await assert.rejects(
    invoke(
      "restore",
      "--state-root", tampered.stateRoot,
      "--install-root", tampered.installRoot,
      "--theme-dir", tampered.themeDir,
      "--label", "v2-test",
    ),
    (error) => /verification failed/.test(error.stderr),
  );
  assert.equal(await fs.readFile(path.join(tampered.installRoot, "VERSION"), "utf8"), currentBefore);

  const traversal = JSON.parse(await fs.readFile(path.join(tamperedBackup, "manifest.json")));
  traversal.files[0].path = "../outside";
  await fs.writeFile(path.join(tamperedBackup, "manifest.json"), `${JSON.stringify(traversal, null, 2)}\n`, { mode: 0o600 });
  await assert.rejects(
    invoke("verify", "--state-root", tampered.stateRoot, "--label", "v2-test"),
    (error) => /invalid manifest path/.test(error.stderr),
  );
} finally {
  await fs.rm(temporary, { recursive: true, force: true });
}

console.log("PASS: immutable version snapshot, fingerprint, permissions, traversal, symlink, tamper, and atomic restore.");

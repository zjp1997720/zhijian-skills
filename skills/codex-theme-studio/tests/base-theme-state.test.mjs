import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";

const run = promisify(execFile);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const script = path.join(root, "scripts/base-theme-state.mjs");
const temporary = await fs.mkdtemp(path.join(os.tmpdir(), "codex-base-theme-test-"));

async function invoke(...args) {
  return run(process.execPath, [script, ...args], { encoding: "utf8" });
}

try {
  const stateRoot = path.join(temporary, "state");
  const themeExport = path.join(temporary, "theme.txt");
  const config = path.join(temporary, "config.toml");
  const globalState = path.join(temporary, "global-state.json");
  await fs.writeFile(themeExport, 'codex-theme-v1:{"variant":"light","theme":{"surface":"#f5f3ee"}}\n');
  await fs.writeFile(config, '[desktop]\nappearanceTheme = "light"\n');
  await fs.writeFile(globalState, '{"recentTasks":["keep-me"]}\n');

  const first = JSON.parse((await invoke(
    "snapshot",
    "--state-root", stateRoot,
    "--theme-export", themeExport,
    "--config", config,
    "--global-state", globalState,
  )).stdout);
  assert.equal(first.pass, true);
  assert.equal(first.reused, false);
  assert.equal(first.files.length, 3);

  const backupRoot = path.join(stateRoot, "base-theme-backup");
  const manifestBefore = await fs.readFile(path.join(backupRoot, "manifest.json"), "utf8");
  const second = JSON.parse((await invoke(
    "snapshot",
    "--state-root", stateRoot,
    "--theme-export", themeExport,
    "--config", config,
    "--global-state", globalState,
  )).stdout);
  assert.equal(second.reused, true);
  assert.equal(await fs.readFile(path.join(backupRoot, "manifest.json"), "utf8"), manifestBefore);

  const verify = JSON.parse((await invoke("verify", "--state-root", stateRoot)).stdout);
  assert.equal(verify.pass, true);
  for (const file of [...verify.files, "manifest.json"]) {
    const stat = await fs.stat(path.join(backupRoot, file));
    assert.equal(stat.mode & 0o077, 0);
  }

  await fs.appendFile(path.join(backupRoot, "config.toml.snapshot"), "# tampered\n");
  await assert.rejects(
    invoke("verify", "--state-root", stateRoot),
    (error) => /sha256 mismatch|byte count mismatch/.test(error.stderr),
  );

  const noGlobalRoot = path.join(temporary, "state-without-global");
  const noGlobal = JSON.parse((await invoke(
    "snapshot",
    "--state-root", noGlobalRoot,
    "--theme-export", themeExport,
    "--config", config,
    "--global-state", path.join(temporary, "missing.json"),
  )).stdout);
  assert.deepEqual(noGlobal.files.sort(), ["codex-theme-v1.txt", "config.toml.snapshot"]);

  const noExportRoot = path.join(temporary, "state-without-export");
  const noExport = JSON.parse((await invoke(
    "snapshot",
    "--state-root", noExportRoot,
    "--config", config,
    "--global-state", globalState,
  )).stdout);
  assert.deepEqual(noExport.files.sort(), ["codex-global-state.json.snapshot", "config.toml.snapshot"]);
} finally {
  await fs.rm(temporary, { recursive: true, force: true });
}

console.log("PASS: base-theme snapshot, idempotency, permissions, optional state, and tamper detection.");

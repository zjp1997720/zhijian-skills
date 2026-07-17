import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";

const [mode, ...args] = process.argv.slice(2);

function valueFor(name, fallback = "") {
  const index = args.indexOf(`--${name}`);
  if (index < 0) return fallback;
  const value = args[index + 1];
  if (!value || value.startsWith("--")) throw new Error(`Missing value for --${name}`);
  return path.resolve(value);
}

async function sha256(file) {
  const contents = await fs.readFile(file);
  return crypto.createHash("sha256").update(contents).digest("hex");
}

async function atomicWrite(file, value, modeBits = 0o600) {
  const temporary = `${file}.${process.pid}.tmp`;
  try {
    await fs.writeFile(temporary, value, { mode: modeBits });
    await fs.rename(temporary, file);
    await fs.chmod(file, modeBits);
  } finally {
    await fs.rm(temporary, { force: true }).catch(() => {});
  }
}

async function verifyBackup(backupRoot) {
  const manifestPath = path.join(backupRoot, "manifest.json");
  let manifest;
  try {
    manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
  } catch (error) {
    throw new Error(`Could not read base-theme manifest: ${error.message}`);
  }
  if (manifest.schemaVersion !== 1 || !manifest.files || typeof manifest.files !== "object") {
    throw new Error("Base-theme manifest schema is not supported.");
  }

  const failures = [];
  for (const [name, expected] of Object.entries(manifest.files)) {
    if (path.basename(name) !== name || !expected?.sha256 || !Number.isInteger(expected.bytes)) {
      failures.push(`${name}: invalid manifest entry`);
      continue;
    }
    const file = path.join(backupRoot, name);
    try {
      const stat = await fs.stat(file);
      const actualHash = await sha256(file);
      if (!stat.isFile()) failures.push(`${name}: not a regular file`);
      if (stat.size !== expected.bytes) failures.push(`${name}: byte count mismatch`);
      if (actualHash !== expected.sha256) failures.push(`${name}: sha256 mismatch`);
      if ((stat.mode & 0o077) !== 0) failures.push(`${name}: permissions are too broad`);
    } catch (error) {
      failures.push(`${name}: ${error.code === "ENOENT" ? "missing" : error.message}`);
    }
  }

  const rootStat = await fs.stat(backupRoot);
  if ((rootStat.mode & 0o077) !== 0) failures.push("backup directory: permissions are too broad");
  if (failures.length) throw new Error(`Base-theme backup verification failed: ${failures.join("; ")}`);

  return {
    pass: true,
    backupRoot,
    createdAt: manifest.createdAt,
    files: Object.keys(manifest.files),
  };
}

async function snapshot() {
  const stateRoot = valueFor("state-root");
  const themeExportPath = valueFor("theme-export");
  const configPath = valueFor("config");
  const globalStatePath = valueFor("global-state");
  if (!stateRoot || !configPath) {
    throw new Error(
      "Usage: base-theme-state.mjs snapshot --state-root <dir> --config <file> [--theme-export <file>] [--global-state <file>]",
    );
  }

  const backupRoot = path.join(stateRoot, "base-theme-backup");
  try {
    await fs.access(path.join(backupRoot, "manifest.json"));
    const verified = await verifyBackup(backupRoot);
    console.log(JSON.stringify({ ...verified, reused: true }));
    return;
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }

  try {
    await fs.access(backupRoot);
    throw new Error(`Refusing to replace incomplete base-theme backup: ${backupRoot}`);
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }

  if (themeExportPath) {
    const exportValue = (await fs.readFile(themeExportPath, "utf8")).trim();
    if (!exportValue.startsWith("codex-theme-v1:")) {
      throw new Error("Base theme export must start with codex-theme-v1:.");
    }
    try {
      JSON.parse(exportValue.slice("codex-theme-v1:".length));
    } catch (error) {
      throw new Error(`Base theme export JSON is invalid: ${error.message}`);
    }
  }
  await fs.access(configPath);

  await fs.mkdir(stateRoot, { recursive: true, mode: 0o700 });
  await fs.chmod(stateRoot, 0o700);
  const temporary = path.join(stateRoot, `.base-theme-backup.${process.pid}.tmp`);
  await fs.rm(temporary, { recursive: true, force: true });
  await fs.mkdir(temporary, { mode: 0o700 });

  const sources = [{ name: "config.toml.snapshot", source: configPath }];
  if (themeExportPath) sources.unshift({ name: "codex-theme-v1.txt", source: themeExportPath });
  if (globalStatePath) {
    try {
      const globalState = JSON.parse(await fs.readFile(globalStatePath, "utf8"));
      if (!globalState || typeof globalState !== "object") throw new Error("expected a JSON object");
      sources.push({ name: "codex-global-state.json.snapshot", source: globalStatePath });
    } catch (error) {
      if (error.code !== "ENOENT") throw new Error(`Global state is not valid JSON: ${error.message}`);
    }
  }

  try {
    const files = {};
    for (const item of sources) {
      const target = path.join(temporary, item.name);
      await fs.copyFile(item.source, target);
      await fs.chmod(target, 0o600);
      const stat = await fs.stat(target);
      files[item.name] = {
        bytes: stat.size,
        sha256: await sha256(target),
        source: item.source,
      };
    }
    const manifest = {
      schemaVersion: 1,
      createdAt: new Date().toISOString(),
      purpose: "Disaster-recovery snapshot of the pre-install Codex appearance and local state.",
      automaticRestore: false,
      files,
    };
    await atomicWrite(path.join(temporary, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
    await fs.rename(temporary, backupRoot);
  } catch (error) {
    await fs.rm(temporary, { recursive: true, force: true }).catch(() => {});
    throw error;
  }

  const verified = await verifyBackup(backupRoot);
  console.log(JSON.stringify({ ...verified, reused: false }));
}

async function main() {
  if (mode === "snapshot") return snapshot();
  if (mode === "verify") {
    const stateRoot = valueFor("state-root");
    if (!stateRoot) throw new Error("Usage: base-theme-state.mjs verify --state-root <dir>");
    console.log(JSON.stringify(await verifyBackup(path.join(stateRoot, "base-theme-backup"))));
    return;
  }
  throw new Error("Usage: base-theme-state.mjs <snapshot|verify> [options]");
}

main().catch((error) => {
  console.error(`Codex Theme Studio: ${error.message}`);
  process.exitCode = 1;
});

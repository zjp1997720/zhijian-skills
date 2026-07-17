import crypto from "node:crypto";
import { constants } from "node:fs";
import fs from "node:fs/promises";
import path from "node:path";

const [mode, ...args] = process.argv.slice(2);
const HASH_PATTERN = /^[a-f0-9]{64}$/;
const LABEL_PATTERN = /^[a-z0-9][a-z0-9._-]{0,63}$/;
const SCOPES = new Set(["engine", "theme"]);

function rawValueFor(name, fallback = "") {
  const index = args.indexOf(`--${name}`);
  if (index < 0) return fallback;
  const value = args[index + 1];
  if (!value || value.startsWith("--")) throw new Error(`Missing value for --${name}`);
  return value;
}

function pathValueFor(name, fallback = "") {
  const value = rawValueFor(name, fallback);
  return value ? path.resolve(value) : "";
}

function validateLabel(label) {
  if (!LABEL_PATTERN.test(label)) throw new Error(`Invalid version backup label: ${label || "missing"}`);
  return label;
}

function validateRelative(relative, context = "manifest") {
  if (typeof relative !== "string" || !relative || path.isAbsolute(relative) || relative.includes("\\")) {
    throw new Error(`${context}: invalid manifest path: ${String(relative)}`);
  }
  const parts = relative.split("/");
  if (parts.some((part) => !part || part === "." || part === "..")) {
    throw new Error(`${context}: invalid manifest path: ${relative}`);
  }
  const normalized = path.posix.normalize(relative);
  if (normalized !== relative || normalized.startsWith("../")) {
    throw new Error(`${context}: invalid manifest path: ${relative}`);
  }
  return relative;
}

function inside(root, relative) {
  const resolved = path.resolve(root, relative);
  const prefix = `${path.resolve(root)}${path.sep}`;
  if (!resolved.startsWith(prefix)) throw new Error(`Path escapes managed root: ${relative}`);
  return resolved;
}

async function readFileNoFollow(file) {
  return fs.readFile(file, { flag: constants.O_RDONLY | constants.O_NOFOLLOW });
}

function sha256Buffer(contents) {
  return crypto.createHash("sha256").update(contents).digest("hex");
}

async function sha256(file) {
  return sha256Buffer(await readFileNoFollow(file));
}

async function atomicWrite(file, value, modeBits = 0o600) {
  const temporary = `${file}.${process.pid}.tmp`;
  try {
    await fs.writeFile(temporary, value, { mode: modeBits, flag: "wx" });
    await fs.rename(temporary, file);
    await fs.chmod(file, modeBits);
  } finally {
    await fs.rm(temporary, { force: true }).catch(() => {});
  }
}

async function readJson(file, label) {
  try {
    return JSON.parse(await fs.readFile(file, "utf8"));
  } catch (error) {
    throw new Error(`Could not read ${label}: ${error.message}`);
  }
}

async function readBaseline(file) {
  const baseline = await readJson(file, "version baseline");
  validateLabel(baseline.label);
  if (baseline.schemaVersion !== 1 || !baseline.files || typeof baseline.files !== "object") {
    throw new Error("Version baseline schema is not supported.");
  }
  for (const [relative, expected] of Object.entries(baseline.files)) {
    validateRelative(relative, "baseline");
    if (!Number.isInteger(expected?.bytes) || expected.bytes < 0 || !HASH_PATTERN.test(expected?.sha256 || "")) {
      throw new Error(`Version baseline entry is invalid: ${relative}`);
    }
  }
  return baseline;
}

async function validateBaselineInstall(installRoot, baseline) {
  const failures = [];
  for (const [relative, expected] of Object.entries(baseline.files)) {
    const file = inside(installRoot, relative);
    try {
      const stat = await fs.lstat(file);
      if (stat.isSymbolicLink()) {
        failures.push(`${relative}: symbolic links are not allowed`);
        continue;
      }
      if (!stat.isFile()) {
        failures.push(`${relative}: not a regular file`);
        continue;
      }
      const actualHash = await sha256(file);
      if (stat.size !== expected.bytes) failures.push(`${relative}: byte count mismatch`);
      if (actualHash !== expected.sha256) failures.push(`${relative}: sha256 mismatch`);
    } catch (error) {
      failures.push(`${relative}: ${error.code === "ENOENT" ? "missing" : error.message}`);
    }
  }
  if (baseline.version) {
    try {
      const version = (await fs.readFile(path.join(installRoot, "VERSION"), "utf8")).trim();
      if (version !== baseline.version) failures.push(`VERSION: expected ${baseline.version}, found ${version}`);
    } catch (error) {
      failures.push(`VERSION: ${error.code === "ENOENT" ? "missing" : error.message}`);
    }
  }
  if (failures.length) throw new Error(`Version baseline fingerprint mismatch: ${failures.join("; ")}`);
}

async function walkRegularFiles(root) {
  const rootStat = await fs.lstat(root);
  if (rootStat.isSymbolicLink() || !rootStat.isDirectory()) {
    throw new Error(`Managed root must be a real directory: ${root}`);
  }
  const files = [];
  async function visit(directory, prefix = "") {
    const entries = await fs.readdir(directory, { withFileTypes: true });
    entries.sort((a, b) => a.name.localeCompare(b.name));
    for (const entry of entries) {
      const relative = prefix ? `${prefix}/${entry.name}` : entry.name;
      validateRelative(relative, "source");
      const source = inside(root, relative);
      const stat = await fs.lstat(source);
      if (stat.isSymbolicLink()) throw new Error(`Source symbolic links are not allowed: ${relative}`);
      if (stat.isDirectory()) await visit(source, relative);
      else if (stat.isFile()) files.push({ relative, source, stat });
      else throw new Error(`Source contains a non-regular file: ${relative}`);
    }
  }
  await visit(root);
  return files;
}

async function copyScopeToBackup(sourceRoot, targetRoot, scope) {
  const sourceFiles = await walkRegularFiles(sourceRoot);
  const manifestFiles = [];
  await fs.mkdir(targetRoot, { recursive: true, mode: 0o700 });
  await fs.chmod(targetRoot, 0o700);
  for (const item of sourceFiles) {
    const contents = await readFileNoFollow(item.source);
    const target = inside(targetRoot, item.relative);
    await fs.mkdir(path.dirname(target), { recursive: true, mode: 0o700 });
    await fs.writeFile(target, contents, { mode: 0o600, flag: "wx" });
    await fs.chmod(target, 0o600);
    manifestFiles.push({
      scope,
      path: item.relative,
      bytes: contents.length,
      sha256: sha256Buffer(contents),
      restoreMode: item.stat.mode & 0o777,
    });
  }
  return manifestFiles;
}

function validateManifestShape(manifest, label) {
  if (manifest.schemaVersion !== 1 || manifest.label !== label || !Array.isArray(manifest.files)) {
    throw new Error("Version backup manifest schema is not supported.");
  }
  const seen = new Set();
  for (const item of manifest.files) {
    if (!SCOPES.has(item?.scope)) throw new Error(`Invalid manifest scope: ${item?.scope}`);
    validateRelative(item.path);
    const key = `${item.scope}/${item.path}`;
    if (seen.has(key)) throw new Error(`Duplicate manifest entry: ${key}`);
    seen.add(key);
    if (!Number.isInteger(item.bytes) || item.bytes < 0 || !HASH_PATTERN.test(item.sha256 || "")) {
      throw new Error(`Invalid manifest entry: ${key}`);
    }
    if (!Number.isInteger(item.restoreMode) || item.restoreMode < 0 || item.restoreMode > 0o777 ||
        (item.restoreMode & 0o400) === 0) {
      throw new Error(`Invalid restore mode: ${key}`);
    }
  }
  return seen;
}

async function verifyBackup(backupRoot, label) {
  const rootStat = await fs.lstat(backupRoot);
  if (rootStat.isSymbolicLink() || !rootStat.isDirectory()) throw new Error("Version backup root is not a real directory.");
  const manifestPath = path.join(backupRoot, "manifest.json");
  const manifestStat = await fs.lstat(manifestPath);
  if (manifestStat.isSymbolicLink() || !manifestStat.isFile()) throw new Error("Version backup manifest is not a regular file.");
  const manifest = await readJson(manifestPath, "version backup manifest");
  const expectedKeys = validateManifestShape(manifest, label);
  const failures = [];
  if ((rootStat.mode & 0o077) !== 0) failures.push("backup directory: permissions are too broad");
  if ((manifestStat.mode & 0o077) !== 0) failures.push("manifest.json: permissions are too broad");
  for (const item of manifest.files) {
    const file = inside(path.join(backupRoot, item.scope), item.path);
    try {
      const stat = await fs.lstat(file);
      if (stat.isSymbolicLink()) {
        failures.push(`${item.scope}/${item.path}: symbolic links are not allowed`);
        continue;
      }
      if (!stat.isFile()) failures.push(`${item.scope}/${item.path}: not a regular file`);
      if (stat.size !== item.bytes) failures.push(`${item.scope}/${item.path}: byte count mismatch`);
      if (await sha256(file) !== item.sha256) failures.push(`${item.scope}/${item.path}: sha256 mismatch`);
      if ((stat.mode & 0o077) !== 0) failures.push(`${item.scope}/${item.path}: permissions are too broad`);
    } catch (error) {
      failures.push(`${item.scope}/${item.path}: ${error.code === "ENOENT" ? "missing" : error.message}`);
    }
  }
  for (const scope of SCOPES) {
    const scopeRoot = path.join(backupRoot, scope);
    const actual = await walkRegularFiles(scopeRoot);
    for (const item of actual) {
      const key = `${scope}/${item.relative}`;
      if (!expectedKeys.has(key)) failures.push(`${key}: unmanifested file`);
    }
  }
  if (failures.length) throw new Error(`Version backup verification failed: ${failures.join("; ")}`);
  return { pass: true, label, backupRoot, createdAt: manifest.createdAt, files: manifest.files.length, manifest };
}

async function snapshot() {
  const stateRoot = pathValueFor("state-root");
  const installRoot = pathValueFor("install-root");
  const themeDir = pathValueFor("theme-dir");
  const baselinePath = pathValueFor("baseline");
  if (!stateRoot || !installRoot || !themeDir || (!baselinePath && !rawValueFor("label"))) {
    throw new Error("Usage: version-backup-state.mjs snapshot --state-root <dir> --install-root <dir> --theme-dir <dir> (--label <label> | --baseline <file>)");
  }
  const baseline = baselinePath ? await readBaseline(baselinePath) : null;
  const label = baseline ? baseline.label : validateLabel(rawValueFor("label"));
  const backupsRoot = path.join(stateRoot, "version-backups");
  const backupRoot = path.join(backupsRoot, label);
  try {
    await fs.access(path.join(backupRoot, "manifest.json"));
    const verified = await verifyBackup(backupRoot, label);
    console.log(JSON.stringify({ ...verified, manifest: undefined, reused: true }));
    return;
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
  try {
    await fs.access(backupRoot);
    throw new Error(`Refusing to replace incomplete version backup: ${backupRoot}`);
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }

  if (baseline) await validateBaselineInstall(installRoot, baseline);
  await fs.mkdir(backupsRoot, { recursive: true, mode: 0o700 });
  await fs.chmod(stateRoot, 0o700);
  await fs.chmod(backupsRoot, 0o700);
  const temporary = path.join(backupsRoot, `.${label}.${process.pid}.tmp`);
  await fs.rm(temporary, { recursive: true, force: true });
  await fs.mkdir(temporary, { mode: 0o700 });
  try {
    const files = [
      ...await copyScopeToBackup(installRoot, path.join(temporary, "engine"), "engine"),
      ...await copyScopeToBackup(themeDir, path.join(temporary, "theme"), "theme"),
    ];
    files.sort((a, b) => `${a.scope}/${a.path}`.localeCompare(`${b.scope}/${b.path}`));
    const manifest = {
      schemaVersion: 1,
      label,
      sourceCommit: baseline?.commit || "",
      sourceVersion: baseline?.version || (await fs.readFile(path.join(installRoot, "VERSION"), "utf8").catch(() => "unknown")).trim(),
      createdAt: new Date().toISOString(),
      immutable: true,
      files,
    };
    await atomicWrite(path.join(temporary, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
    await fs.rename(temporary, backupRoot);
  } catch (error) {
    await fs.rm(temporary, { recursive: true, force: true }).catch(() => {});
    throw error;
  }
  const verified = await verifyBackup(backupRoot, label);
  console.log(JSON.stringify({ ...verified, manifest: undefined, reused: false }));
}

async function copyScopeFromBackup(backupRoot, stageRoot, scope, manifest) {
  await fs.mkdir(stageRoot, { recursive: true, mode: 0o700 });
  await fs.chmod(stageRoot, 0o700);
  for (const item of manifest.files.filter((entry) => entry.scope === scope)) {
    const source = inside(path.join(backupRoot, scope), item.path);
    const target = inside(stageRoot, item.path);
    const contents = await readFileNoFollow(source);
    await fs.mkdir(path.dirname(target), { recursive: true, mode: 0o700 });
    await fs.writeFile(target, contents, { mode: 0o600, flag: "wx" });
    await fs.chmod(target, item.restoreMode);
  }
}

async function verifyStage(stageRoot, scope, manifest) {
  const expected = new Map(manifest.files.filter((item) => item.scope === scope).map((item) => [item.path, item]));
  const actual = await walkRegularFiles(stageRoot);
  if (actual.length !== expected.size) throw new Error(`${scope} restore staging file count mismatch`);
  for (const item of actual) {
    const entry = expected.get(item.relative);
    if (!entry) throw new Error(`${scope}/${item.relative}: unmanifested staging file`);
    if (item.stat.size !== entry.bytes || await sha256(item.source) !== entry.sha256) {
      throw new Error(`${scope}/${item.relative}: restore staging hash mismatch`);
    }
    if ((item.stat.mode & 0o777) !== entry.restoreMode) {
      throw new Error(`${scope}/${item.relative}: restore staging mode mismatch`);
    }
  }
}

async function restore() {
  const stateRoot = pathValueFor("state-root");
  const installRoot = pathValueFor("install-root");
  const themeDir = pathValueFor("theme-dir");
  const label = validateLabel(rawValueFor("label"));
  if (!stateRoot || !installRoot || !themeDir) {
    throw new Error("Usage: version-backup-state.mjs restore --state-root <dir> --install-root <dir> --theme-dir <dir> --label <label>");
  }
  const backupRoot = path.join(stateRoot, "version-backups", label);
  const verified = await verifyBackup(backupRoot, label);
  const manifest = verified.manifest;
  const engineStage = `${installRoot}.restoring.${process.pid}`;
  const themeStage = `${themeDir}.restoring.${process.pid}`;
  const enginePrevious = `${installRoot}.previous.${process.pid}`;
  const themePrevious = `${themeDir}.previous.${process.pid}`;
  for (const item of [engineStage, themeStage, enginePrevious, themePrevious]) {
    await fs.rm(item, { recursive: true, force: true });
  }
  await copyScopeFromBackup(backupRoot, engineStage, "engine", manifest);
  await copyScopeFromBackup(backupRoot, themeStage, "theme", manifest);
  await verifyStage(engineStage, "engine", manifest);
  await verifyStage(themeStage, "theme", manifest);

  let engineMoved = false;
  let engineInstalled = false;
  let themeMoved = false;
  let themeInstalled = false;
  try {
    try {
      await fs.rename(installRoot, enginePrevious);
      engineMoved = true;
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
    }
    await fs.rename(engineStage, installRoot);
    engineInstalled = true;
    try {
      await fs.rename(themeDir, themePrevious);
      themeMoved = true;
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
    }
    await fs.rename(themeStage, themeDir);
    themeInstalled = true;
  } catch (error) {
    if (themeInstalled) await fs.rm(themeDir, { recursive: true, force: true }).catch(() => {});
    if (themeMoved) await fs.rename(themePrevious, themeDir).catch(() => {});
    if (engineInstalled) await fs.rm(installRoot, { recursive: true, force: true }).catch(() => {});
    if (engineMoved) await fs.rename(enginePrevious, installRoot).catch(() => {});
    throw new Error(`Version restore atomic swap failed: ${error.message}`);
  } finally {
    await fs.rm(engineStage, { recursive: true, force: true }).catch(() => {});
    await fs.rm(themeStage, { recursive: true, force: true }).catch(() => {});
  }
  await fs.rm(enginePrevious, { recursive: true, force: true });
  await fs.rm(themePrevious, { recursive: true, force: true });
  console.log(JSON.stringify({ pass: true, label, restoredFiles: manifest.files.length }));
}

async function main() {
  if (mode === "snapshot") return snapshot();
  if (mode === "verify") {
    const stateRoot = pathValueFor("state-root");
    const label = validateLabel(rawValueFor("label"));
    if (!stateRoot) throw new Error("Usage: version-backup-state.mjs verify --state-root <dir> --label <label>");
    const verified = await verifyBackup(path.join(stateRoot, "version-backups", label), label);
    console.log(JSON.stringify({ ...verified, manifest: undefined }));
    return;
  }
  if (mode === "restore") return restore();
  throw new Error("Usage: version-backup-state.mjs <snapshot|verify|restore> [options]");
}

main().catch((error) => {
  console.error(`Codex Theme Studio: ${error.message}`);
  process.exitCode = 1;
});

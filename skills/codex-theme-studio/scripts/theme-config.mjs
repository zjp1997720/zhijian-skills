import fs from "node:fs/promises";
import path from "node:path";

const [mode, configPath, backupPath] = process.argv.slice(2);

// A null value means "snapshot only". Restore may touch only keys listed in
// changedKeys, so appearance changes made after installation are preserved.
const settings = new Map([
  ["appearanceTheme", null],
  ["appearanceDarkCodeThemeId", null],
]);

if (!["install", "restore"].includes(mode) || !configPath || !backupPath) {
  throw new Error("Usage: theme-config.mjs <install|restore> <config-path> <backup-path>");
}

function desktopSection(content) {
  const header = /^\[desktop\]\s*\r?\n/m.exec(content);
  if (!header) return null;
  const bodyStart = header.index + header[0].length;
  const remainder = content.slice(bodyStart);
  const nextHeader = /^\[/m.exec(remainder);
  const bodyEnd = nextHeader ? bodyStart + nextHeader.index : content.length;
  return { bodyStart, bodyEnd, body: content.slice(bodyStart, bodyEnd) };
}

function escapePattern(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function replaceSetting(body, key, line) {
  const pattern = new RegExp(`^${escapePattern(key)}\\s*=.*(?:\\r?\\n)?`, "m");
  if (line === null) return body.replace(pattern, "");
  if (pattern.test(body)) return body.replace(pattern, `${line}\n`);
  const separator = body.length && !body.endsWith("\n") ? "\n" : "";
  return `${body}${separator}${line}\n`;
}

function readSetting(body, key) {
  const match = new RegExp(`^${escapePattern(key)}\\s*=.*$`, "m").exec(body);
  return match ? match[0] : null;
}

async function atomicWrite(file, value, modeBits) {
  const temporary = `${file}.${process.pid}.tmp`;
  try {
    await fs.writeFile(temporary, value, { mode: modeBits });
    await fs.rename(temporary, file);
    await fs.chmod(file, modeBits);
  } finally {
    await fs.rm(temporary, { force: true }).catch(() => {});
  }
}

async function readBackup() {
  try {
    return JSON.parse(await fs.readFile(backupPath, "utf8"));
  } catch (error) {
    if (error.code === "ENOENT") return null;
    throw new Error(`Could not read the theme backup: ${error.message}`);
  }
}

async function markRestored(backup) {
  const restored = {
    ...backup,
    changedKeys: [],
    restoredAt: new Date().toISOString(),
  };
  await atomicWrite(backupPath, `${JSON.stringify(restored, null, 2)}\n`, 0o600);
}

let content;
try {
  content = await fs.readFile(configPath, "utf8");
} catch (error) {
  if (error.code === "ENOENT") throw new Error(`Codex config not found: ${configPath}`);
  throw error;
}

const originalStat = await fs.stat(configPath);
let section = desktopSection(content);
const changedKeys = [...settings.entries()]
  .filter(([, line]) => line !== null)
  .map(([key]) => key);

if (mode === "install") {
  const values = {};
  for (const key of settings.keys()) values[key] = readSetting(section?.body ?? "", key);

  const existing = await readBackup();
  if (!existing) {
    const backup = {
      schemaVersion: 2,
      platform: "darwin",
      createdAt: new Date().toISOString(),
      configPath,
      values,
      changedKeys,
    };
    await fs.mkdir(path.dirname(backupPath), { recursive: true, mode: 0o700 });
    await atomicWrite(backupPath, `${JSON.stringify(backup, null, 2)}\n`, 0o600);
  } else if (existing.schemaVersion === 1 && existing.configPath === configPath && existing.values) {
    const upgraded = { ...existing, schemaVersion: 2, changedKeys };
    await atomicWrite(backupPath, `${JSON.stringify(upgraded, null, 2)}\n`, 0o600);
  } else if (
    existing.schemaVersion !== 2 ||
    existing.configPath !== configPath ||
    !existing.values ||
    !Array.isArray(existing.changedKeys)
  ) {
    throw new Error("Existing theme backup identity or schema does not match this config.");
  }

  if (changedKeys.length) {
    if (!section) {
      content = `${content.trimEnd()}\n\n[desktop]\n`;
      section = desktopSection(content);
    }
    let body = section.body;
    for (const key of changedKeys) body = replaceSetting(body, key, settings.get(key));
    const updated = content.slice(0, section.bodyStart) + body + content.slice(section.bodyEnd);
    await atomicWrite(configPath, updated, originalStat.mode & 0o777);
  }
  console.log("Saved selective theme backup; left Codex appearance settings unchanged.");
} else {
  const backup = await readBackup();
  if (!backup) throw new Error("No selective pre-install theme backup is available.");
  if (
    backup.schemaVersion !== 2 ||
    backup.configPath !== configPath ||
    !backup.values ||
    !Array.isArray(backup.changedKeys) ||
    backup.changedKeys.some((key) => !settings.has(key))
  ) {
    throw new Error("Theme backup identity or schema does not match this config; nothing was restored.");
  }

  if (!backup.changedKeys.length) {
    await markRestored(backup);
    console.log("No installer-managed appearance keys required restoration.");
    process.exit(0);
  }

  if (!section) {
    const hasSavedSetting = backup.changedKeys.some((key) => backup.values[key]);
    if (!hasSavedSetting) {
      await markRestored(backup);
      console.log("Restored the installer-managed appearance keys.");
      process.exit(0);
    }
    content = `${content.trimEnd()}\n\n[desktop]\n`;
    section = desktopSection(content);
  }

  let body = section.body;
  for (const key of backup.changedKeys) body = replaceSetting(body, key, backup.values[key] ?? null);
  const restored = content.slice(0, section.bodyStart) + body + content.slice(section.bodyEnd);
  await atomicWrite(configPath, restored, originalStat.mode & 0o777);
  await markRestored(backup);
  console.log("Restored the installer-managed appearance keys.");
}

import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const forbidden = [
  /\/Users\/(?:zhujinpeng|fei)\b/i,
  /zhijian-ai-(?:mark|wordmark)/i,
  /portal-hero/i,
  /base-codex-theme\.txt/i,
  /deepsight_vault/i,
];

async function walk(directory) {
  const files = [];
  for (const entry of await fs.readdir(directory, { withFileTypes: true })) {
    if (["reports", "node_modules"].includes(entry.name)) continue;
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...await walk(target));
    else if (entry.isFile() && /\.(?:md|json|ya?ml|mjs|js|sh|txt|css|svg)$/.test(entry.name)) files.push(target);
  }
  return files;
}

const thisFile = fileURLToPath(import.meta.url);
for (const file of await walk(root)) {
  if (file === thisFile) continue;
  const source = await fs.readFile(file, "utf8");
  for (const pattern of forbidden) {
    assert.doesNotMatch(source, pattern, `${path.relative(root, file)} contains private or source-project residue`);
  }
}

const installer = await fs.readFile(path.join(root, "scripts/install-dream-skin-macos.sh"), "utf8");
assert.match(installer, /--exclude 'references\/screenshots\/'/);
assert.match(installer, /CREATE_LAUNCHERS="false"/);
assert.match(installer, /LAUNCH_AFTER_INSTALL="false"/);
assert.doesNotMatch(installer, /app\.asar/);

console.log("PASS: public package excludes private paths, private brand assets, bundled user theme exports, and implicit launch behavior.");

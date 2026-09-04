import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const presetsRoot = path.join(root, "presets");
const entries = await fs.readdir(presetsRoot, { withFileTypes: true });
const presets = [];

for (const entry of entries.filter((item) => item.isDirectory()).sort((a, b) => a.name.localeCompare(b.name))) {
  const directory = path.join(presetsRoot, entry.name);
  const [metadata, theme] = await Promise.all([
    fs.readFile(path.join(directory, "preset.json"), "utf8").then(JSON.parse),
    fs.readFile(path.join(directory, "theme.json"), "utf8").then(JSON.parse),
  ]);
  if (metadata.schemaVersion !== 1 || metadata.id !== entry.name) {
    throw new Error(`Preset metadata mismatch: ${entry.name}`);
  }
  const imagePath = path.join(directory, theme.image || "");
  const image = await fs.readFile(imagePath);
  presets.push({
    id: metadata.id,
    name: metadata.name,
    kind: metadata.kind,
    description: metadata.description,
    themeId: theme.id,
    image: theme.image,
    imageSha256: crypto.createHash("sha256").update(image).digest("hex"),
  });
}
if (process.argv.includes("--json")) {
  process.stdout.write(`${JSON.stringify({ schemaVersion: 1, presets }, null, 2)}\n`);
} else {
  for (const preset of presets) {
    process.stdout.write(`${preset.id}\t${preset.name}\t${preset.kind}\t${preset.description}\n`);
  }
}

import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const failures = [];
const required = [
  "SKILL.md",
  "manifest.json",
  "agents/openai.yaml",
  "reports/trust-report.md",
  "reports/output_quality_scorecard.md",
  "references/capability-boundary.md",
  "references/theme-schema.md",
  "references/compatibility-policy.md",
  "references/preset-policy.md",
];

for (const relative of required) {
  try {
    const stat = await fs.stat(path.join(root, relative));
    if (!stat.isFile()) failures.push(`${relative} is not a file`);
  } catch {
    failures.push(`missing ${relative}`);
  }
}

const manifest = JSON.parse(await fs.readFile(path.join(root, "manifest.json"), "utf8"));
const version = (await fs.readFile(path.join(root, "VERSION"), "utf8")).trim();
if (manifest.name !== "codex-theme-studio") failures.push("manifest name mismatch");
if (manifest.version !== version) failures.push("manifest version mismatch");
if (manifest.maturity_tier !== "governed") failures.push("manifest maturity must be governed");
if (!Array.isArray(manifest.missing_evidence)) failures.push("manifest missing_evidence must be an array");

const skill = await fs.readFile(path.join(root, "SKILL.md"), "utf8");
for (const label of ["output contract", "file-backed fixture", "rollback boundary", "trust report", "missing evidence"]) {
  if (!skill.includes(label)) failures.push(`SKILL.md missing governed label: ${label}`);
}

async function walk(directory) {
  const output = [];
  for (const entry of await fs.readdir(directory, { withFileTypes: true })) {
    if ([".git", "release"].includes(entry.name)) continue;
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      if (path.relative(root, full) === path.join("references", "screenshots")) continue;
      output.push(...await walk(full));
    } else {
      output.push(full);
    }
  }
  return output;
}

const textExtensions = new Set([".md", ".json", ".yaml", ".yml", ".js", ".mjs", ".sh", ".command", ".txt"]);
for (const file of await walk(root)) {
  if (!textExtensions.has(path.extname(file))) continue;
  if (path.relative(root, file) === "scripts/audit-skill-package.mjs") continue;
  const source = await fs.readFile(file, "utf8");
  if (/\/Users\/(?!\$CURRENT_USER\b)[^/\s"']+\//.test(source)) {
    failures.push(`absolute macOS user path in ${path.relative(root, file)}`);
  }
  if (/\b(?:大鹏|朱金鹏|jinpeng)\b/i.test(source)) {
    failures.push(`private identity in ${path.relative(root, file)}`);
  }
}

if (failures.length) {
  process.stderr.write(`${failures.map((item) => `FAIL: ${item}`).join("\n")}\n`);
  process.exit(1);
}

process.stdout.write("PASS: governed package structure, version alignment, privacy scan, and required contracts.\n");

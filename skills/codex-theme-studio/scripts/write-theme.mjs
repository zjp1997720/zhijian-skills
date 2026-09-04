import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const [mode, ...args] = process.argv.slice(2);

function valueFor(name, fallback = "") {
  const index = args.indexOf(`--${name}`);
  if (index < 0) return fallback;
  const value = args[index + 1];
  if (!value || value.startsWith("--")) throw new Error(`Missing value for --${name}`);
  return value;
}

function validateHex(value, name) {
  if (!/^#[0-9a-f]{6}$/i.test(value)) throw new Error(`${name} must be a six-digit hex color.`);
  return value.toLowerCase();
}

function validateInteger(value, name, fallback, minimum, maximum) {
  const parsed = Number(value || fallback);
  if (!Number.isInteger(parsed) || parsed < minimum || parsed > maximum) {
    throw new Error(`${name} must be an integer from ${minimum} to ${maximum}.`);
  }
  return parsed;
}

function validateFontFamily(value, name, fallback) {
  const normalized = (value || fallback).trim().slice(0, 240);
  if (!normalized || /[;{}<>\r\n]/.test(normalized)) {
    throw new Error(`${name} contains unsupported CSS characters.`);
  }
  return normalized;
}

async function atomicWrite(file, value) {
  await fs.mkdir(path.dirname(file), { recursive: true, mode: 0o700 });
  const temporary = `${file}.${process.pid}.tmp`;
  try {
    await fs.writeFile(temporary, value, { mode: 0o600 });
    await fs.rename(temporary, file);
    await fs.chmod(file, 0o600);
  } finally {
    await fs.rm(temporary, { force: true }).catch(() => {});
  }
}

const outputDir = path.resolve(valueFor("output-dir", path.join(root, "assets")));
const themePath = path.join(outputDir, "theme.json");

if (mode === "reset-demo") {
  if (outputDir === path.join(root, "assets")) {
    throw new Error("Refusing to delete the bundled demo assets; pass a user --output-dir.");
  }
  await fs.rm(outputDir, { recursive: true, force: true });
  console.log("Restored the bundled abstract demo preset.");
  process.exit(0);
}

if (mode !== "custom") {
  throw new Error("Usage: write-theme.mjs custom [options] | reset-demo --output-dir <dir>");
}

const image = path.basename(valueFor("image", "background.jpg"));
if (!/\.(?:png|jpe?g|webp)$/i.test(image)) throw new Error("image must be a PNG, JPEG, or WebP filename.");
const imagePath = path.join(outputDir, image);
const imageStat = await fs.stat(imagePath);
if (!imageStat.isFile() || imageStat.size < 1 || imageStat.size > 16 * 1024 * 1024) {
  throw new Error("The prepared theme image must be non-empty and no larger than 16 MB.");
}

const name = valueFor("name", "My Codex Workspace").trim().slice(0, 80);
const tagline = valueFor("tagline", "A focused workspace for serious work.").trim().slice(0, 160);
const quote = valueFor("quote", "MAKE SOMETHING USEFUL").trim().slice(0, 80);
const accent = validateHex(valueFor("accent", "#536272"), "accent");
const secondary = validateHex(valueFor("secondary", "#273746"), "secondary");
const highlight = validateHex(valueFor("highlight", "#536272"), "highlight");
const uiFamily = validateFontFamily(
  valueFor("font-ui"),
  "font-ui",
  "ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
);
const codeFamily = validateFontFamily(
  valueFor("font-code"),
  "font-code",
  "SF Mono, ui-monospace, monospace",
);
const bodyWeight = validateInteger(valueFor("body-weight"), "body-weight", 500, 300, 700);
const emphasisWeight = validateInteger(valueFor("emphasis-weight"), "emphasis-weight", 600, 400, 800);
const codeWeight = validateInteger(valueFor("code-weight"), "code-weight", 400, 300, 700);
const controlRadius = validateInteger(valueFor("control-radius"), "control-radius", 6, 0, 24);
const cardRadius = validateInteger(valueFor("card-radius"), "card-radius", 8, 0, 32);
const heroRadius = validateInteger(valueFor("hero-radius"), "hero-radius", 16, 0, 40);
const composerRadius = validateInteger(valueFor("composer-radius"), "composer-radius", 14, 0, 32);
const homeGap = validateInteger(valueFor("home-gap"), "home-gap", 24, 12, 40);
const suggestionMinHeight = validateInteger(
  valueFor("suggestion-min-height"),
  "suggestion-min-height",
  112,
  80,
  160,
);

const custom = {
  schemaVersion: 1,
  id: `custom-${Date.now()}`,
  name: name || "My Codex Workspace",
  brandSubtitle: "",
  tagline: tagline || "A focused workspace for serious work.",
  projectPrefix: "当前项目 · ",
  projectLabel: "工作区",
  statusText: "",
  quote: quote || "MAKE SOMETHING USEFUL",
  image,
  typography: { uiFamily, codeFamily, bodyWeight, emphasisWeight, codeWeight },
  shape: { controlRadius, cardRadius, heroRadius, composerRadius },
  density: { homeGap, suggestionMinHeight },
  colors: {
    background: "#f6f5f0",
    panel: "#fbfaf7",
    panelAlt: "#efede7",
    accent,
    accentAlt: "#7a8794",
    secondary,
    highlight,
    text: "#181817",
    muted: "#676862",
    line: "rgba(24, 24, 23, 0.12)",
  },
};

await atomicWrite(themePath, `${JSON.stringify(custom, null, 2)}\n`);
console.log(`Saved custom theme “${custom.name}”.`);

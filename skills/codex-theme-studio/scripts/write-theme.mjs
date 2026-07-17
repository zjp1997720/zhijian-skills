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

const rawImage = valueFor("image", "background.jpg").trim();
const image = path.basename(rawImage);
if (image !== rawImage) throw new Error("image must stay inside the output directory.");
if (!/\.(?:png|jpe?g|webp)$/i.test(image)) throw new Error("image must be a PNG, JPEG, or WebP filename.");
const imagePath = path.join(outputDir, image);
const imageStat = await fs.lstat(imagePath);
if (imageStat.isSymbolicLink() || !imageStat.isFile() || imageStat.size < 1 || imageStat.size > 16 * 1024 * 1024) {
  throw new Error("The prepared theme image must be non-empty and no larger than 16 MB.");
}

const optionalAsset = async (name, maxBytes) => {
  const raw = valueFor(name, "").trim();
  const filename = path.basename(raw);
  if (!filename) return "";
  if (filename !== raw) throw new Error(`${name} must stay inside the output directory.`);
  if (!/\.(?:png|jpe?g|webp)$/i.test(filename)) throw new Error(`${name} must be a PNG, JPEG, or WebP filename.`);
  const stat = await fs.lstat(path.join(outputDir, filename));
  if (stat.isSymbolicLink() || !stat.isFile() || stat.size < 1 || stat.size > maxBytes) {
    throw new Error(`${name} must be non-empty and no larger than ${maxBytes} bytes.`);
  }
  return filename;
};
const safeFontStack = (name, fallback) => {
  const value = valueFor(name, fallback).trim().slice(0, 180);
  if (!value || /[;{}<>]/.test(value)) throw new Error(`${name} contains unsupported CSS characters.`);
  return value;
};

const name = valueFor("name", "Warm Paper Studio").trim().slice(0, 80);
const brandLabel = valueFor("brand-label", "THEME STUDIO").trim().slice(0, 80);
const brandImage = await optionalAsset("brand-image", 4 * 1024 * 1024);
const tagline = valueFor("tagline", "Design quietly. Build clearly.").trim().slice(0, 160);
const quote = valueFor("quote", "DESIGN · APPLY · VERIFY · RESTORE").trim().slice(0, 80);
const background = validateHex(valueFor("background", "#f5f3ee"), "background");
const panel = validateHex(valueFor("panel", "#faf9f6"), "panel");
const panelAlt = validateHex(valueFor("panel-alt", "#eeece6"), "panel-alt");
const sidebar = validateHex(valueFor("sidebar", "#f1f0ec"), "sidebar");
const selected = validateHex(valueFor("selected", "#e8e6dc"), "selected");
const border = validateHex(valueFor("border", "#e4e1da"), "border");
const paperBlue = validateHex(valueFor("paper-blue", "#e7edf2"), "paper-blue");
const accent = validateHex(valueFor("accent", "#da7756"), "accent");
const accentAlt = validateHex(valueFor("accent-alt", "#cc7d5e"), "accent-alt");
const secondary = validateHex(valueFor("secondary", "#1b365d"), "secondary");
const highlight = validateHex(valueFor("highlight", "#1b365d"), "highlight");
const text = validateHex(valueFor("text", "#1d1b16"), "text");
const muted = validateHex(valueFor("muted", "#69675f"), "muted");
const uiFont = safeFontStack("ui-font", '"Source Han Serif SC", "Songti SC", ui-serif, Georgia, serif');
const codeFont = safeFontStack("code-font", '"SF Mono", ui-monospace, Menlo, monospace');
const artPlacement = valueFor("art-placement", "hero").trim();
if (!["hero", "all"].includes(artPlacement)) throw new Error("art-placement must be hero or all.");

const custom = {
  schemaVersion: 1,
  id: `custom-${Date.now()}`,
  name: name || "Warm Paper Studio",
  brandLabel: brandLabel || name || "THEME STUDIO",
  brandImage,
  showBrand: !args.includes("--hide-brand"),
  fonts: { ui: uiFont, code: codeFont },
  tagline: tagline || "Design quietly. Build clearly.",
  projectPrefix: "Current project · ",
  projectLabel: "工作区",
  statusText: "THEME ONLINE",
  quote: quote || "DESIGN · APPLY · VERIFY · RESTORE",
  image,
  artPlacement,
  colors: {
    background,
    panel,
    panelAlt,
    sidebar,
    selected,
    border,
    paperBlue,
    accent,
    accentAlt,
    secondary,
    highlight,
    text,
    muted,
    line: "rgba(20, 20, 19, 0.12)",
  },
};

await atomicWrite(themePath, `${JSON.stringify(custom, null, 2)}\n`);
console.log(`Saved custom theme “${custom.name}”.`);

import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { colorsMatch, evaluateSnapshot } from "./verification-contract.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const SKIN_VERSION = "1.0.2";
const LOOPBACK_HOSTS = new Set(["127.0.0.1", "localhost", "[::1]"]);
const MAX_ART_BYTES = 16 * 1024 * 1024;

function parseArgs(argv) {
  const options = {
    port: 9341,
    mode: "watch",
    timeoutMs: 30000,
    screenshot: null,
    reload: false,
    themeDir: null,
    strictVisual: false,
    viewportWidth: null,
    viewportHeight: null,
    sampleNewTaskDir: null,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--port") options.port = Number(argv[++i]);
    else if (arg === "--once") options.mode = "once";
    else if (arg === "--watch") options.mode = "watch";
    else if (arg === "--verify") options.mode = "verify";
    else if (arg === "--remove") options.mode = "remove";
    else if (arg === "--check-payload") options.mode = "check";
    else if (arg === "--timeout-ms") options.timeoutMs = Number(argv[++i]);
    else if (arg === "--screenshot") options.screenshot = path.resolve(argv[++i]);
    else if (arg === "--theme-dir") options.themeDir = path.resolve(argv[++i]);
    else if (arg === "--reload") options.reload = true;
    else if (arg === "--strict-visual") options.strictVisual = true;
    else if (arg === "--viewport-width") options.viewportWidth = Number(argv[++i]);
    else if (arg === "--viewport-height") options.viewportHeight = Number(argv[++i]);
    else if (arg === "--sample-new-task") options.sampleNewTaskDir = path.resolve(argv[++i]);
    else throw new Error(`Unknown argument: ${arg}`);
  }
  if (!Number.isInteger(options.port) || options.port < 1024 || options.port > 65535) {
    throw new Error(`Invalid port: ${options.port}`);
  }
  if (!Number.isFinite(options.timeoutMs) || options.timeoutMs < 250 || options.timeoutMs > 120000) {
    throw new Error(`Invalid timeout: ${options.timeoutMs}`);
  }
  if ((options.viewportWidth !== null && (!Number.isInteger(options.viewportWidth) || options.viewportWidth < 640 || options.viewportWidth > 4096)) ||
      (options.viewportHeight !== null && (!Number.isInteger(options.viewportHeight) || options.viewportHeight < 480 || options.viewportHeight > 2160))) {
    throw new Error(`Invalid viewport: ${options.viewportWidth}x${options.viewportHeight}`);
  }
  if ((options.viewportWidth === null) !== (options.viewportHeight === null)) {
    throw new Error("Viewport width and height must be provided together");
  }
  return options;
}

function validatedDebuggerUrl(target, port) {
  const url = new URL(target.webSocketDebuggerUrl);
  if (url.protocol !== "ws:" || !LOOPBACK_HOSTS.has(url.hostname) || Number(url.port) !== port) {
    throw new Error(`Rejected non-loopback CDP WebSocket URL: ${url.href}`);
  }
  return url.href;
}

class CdpSession {
  constructor(target, port) {
    this.target = target;
    this.ws = new WebSocket(validatedDebuggerUrl(target, port));
    this.nextId = 1;
    this.pending = new Map();
    this.listeners = new Map();
    this.closed = false;
  }

  async open() {
    await new Promise((resolve, reject) => {
      const finish = (error) => {
        clearTimeout(timeout);
        this.ws.removeEventListener("open", onOpen);
        this.ws.removeEventListener("error", onError);
        if (error) reject(error);
        else resolve();
      };
      const onOpen = () => finish();
      const onError = () => finish(new Error("CDP WebSocket open failed"));
      const timeout = setTimeout(() => {
        try { this.ws.close(); } catch {}
        finish(new Error("CDP WebSocket open timed out"));
      }, 5000);
      this.ws.addEventListener("open", onOpen, { once: true });
      this.ws.addEventListener("error", onError, { once: true });
    });
    this.ws.addEventListener("message", (event) => this.onMessage(event));
    this.ws.addEventListener("close", () => {
      this.closed = true;
      for (const waiter of this.pending.values()) {
        clearTimeout(waiter.timeout);
        waiter.reject(new Error("CDP socket closed"));
      }
      this.pending.clear();
    });
    await this.send("Runtime.enable");
    await this.send("Page.enable");
    return this;
  }

  onMessage(event) {
    const message = JSON.parse(String(event.data));
    if (message.id) {
      const waiter = this.pending.get(message.id);
      if (!waiter) return;
      clearTimeout(waiter.timeout);
      this.pending.delete(message.id);
      if (message.error) waiter.reject(new Error(`${message.error.message} (${message.error.code})`));
      else waiter.resolve(message.result);
      return;
    }
    for (const listener of this.listeners.get(message.method) ?? []) listener(message.params ?? {});
  }

  on(method, listener) {
    const listeners = this.listeners.get(method) ?? [];
    listeners.push(listener);
    this.listeners.set(method, listeners);
    return () => {
      const current = this.listeners.get(method) ?? [];
      this.listeners.set(method, current.filter((candidate) => candidate !== listener));
    };
  }

  once(method, timeoutMs = 10000) {
    let settled = false;
    let finish = () => {};
    const promise = new Promise((resolve, reject) => {
      let unsubscribe = () => {};
      finish = (error, params) => {
        if (settled) return;
        settled = true;
        clearTimeout(timeout);
        unsubscribe();
        if (error) reject(error);
        else resolve(params);
      };
      const timeout = setTimeout(() => {
        finish(new Error(`CDP event timed out: ${method}`));
      }, timeoutMs);
      unsubscribe = this.on(method, (params) => {
        finish(null, params);
      });
    });
    return {
      promise,
      cancel: () => finish(new Error(`CDP event canceled: ${method}`)),
    };
  }

  send(method, params = {}) {
    if (this.closed) return Promise.reject(new Error("CDP session is closed"));
    return new Promise((resolve, reject) => {
      const id = this.nextId++;
      const timeout = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`CDP command timed out: ${method}`));
      }, 10000);
      this.pending.set(id, { resolve, reject, timeout });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  async evaluate(expression) {
    const result = await this.send("Runtime.evaluate", {
      expression,
      awaitPromise: true,
      returnByValue: true,
      userGesture: false,
    });
    if (result.exceptionDetails) {
      const detail = result.exceptionDetails.exception?.description ?? result.exceptionDetails.text;
      throw new Error(`Renderer evaluation failed: ${detail}`);
    }
    return result.result?.value;
  }

  close() {
    if (!this.closed) this.ws.close();
    this.closed = true;
  }
}

async function listAppTargets(port) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 2000);
  try {
    const response = await fetch(`http://127.0.0.1:${port}/json/list`, { signal: controller.signal });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const targets = await response.json();
    return targets.filter((item) => {
      if (item.type !== "page" || !item.url?.startsWith("app://") || !item.webSocketDebuggerUrl) return false;
      try {
        validatedDebuggerUrl(item, port);
        return true;
      } catch {
        return false;
      }
    });
  } finally {
    clearTimeout(timeout);
  }
}

async function probeSession(session) {
  return session.evaluate(`(() => {
    const markers = {
      shell: Boolean(document.querySelector('main.main-surface')),
      sidebar: Boolean(document.querySelector('aside.app-shell-left-panel')),
      composer: Boolean(document.querySelector('.composer-surface-chrome')),
      main: Boolean(document.querySelector('[role="main"]')),
    };
    return {
      title: document.title,
      href: location.href,
      markers,
      codex: markers.shell && markers.sidebar && (markers.composer || markers.main),
    };
  })()`);
}

async function connectTarget(target, port) {
  return new CdpSession(target, port).open();
}

async function connectCodexTargets(port, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  let lastError;
  while (Date.now() < deadline) {
    try {
      const targets = await listAppTargets(port);
      const connected = [];
      for (const target of targets) {
        let session;
        try {
          session = await connectTarget(target, port);
          const probe = await probeSession(session);
          if (probe?.codex) connected.push({ target, session, probe });
          else session.close();
        } catch (error) {
          session?.close();
          lastError = error;
        }
      }
      if (connected.length) return connected;
      lastError = new Error("No page matched the expected Codex shell markers");
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 350));
  }
  throw new Error(`No verified Codex renderer on 127.0.0.1:${port}: ${lastError?.message ?? "timed out"}`);
}

async function loadTheme(themeDir) {
  const assetsRoot = themeDir ?? path.join(root, "assets");
  const configPath = path.join(assetsRoot, "theme.json");
  let config;
  try {
    const rootStat = await fs.lstat(assetsRoot);
    const configStat = await fs.lstat(configPath);
    if (rootStat.isSymbolicLink() || !rootStat.isDirectory()) throw new Error("Theme root must be a real directory");
    if (configStat.isSymbolicLink() || !configStat.isFile()) throw new Error("theme.json must be a regular file");
    config = await fs.readFile(configPath, "utf8");
  } catch (error) {
    if (themeDir && error.code === "ENOENT") {
      throw new Error(`Explicit theme directory is missing theme.json: ${configPath}`);
    }
    throw error;
  }
  const raw = JSON.parse(config);
  if (raw.schemaVersion !== 1 || typeof raw.image !== "string" || !raw.image) {
    throw new Error(`${configPath} has an unsupported schema or image field`);
  }
  if (path.basename(raw.image) !== raw.image) throw new Error("Theme image must stay inside its theme directory");
  const text = (value, fallback, max) => typeof value === "string" && value.trim()
    ? value.trim().slice(0, max) : fallback;
  const color = (value, fallback) => {
    if (typeof value !== "string") return fallback;
    const normalized = value.trim();
    return /^#[0-9a-f]{6}$/i.test(normalized) || /^rgba?\([0-9., %]+\)$/i.test(normalized)
      ? normalized
      : fallback;
  };
  const fontStack = (value, fallback) => {
    if (typeof value !== "string") return fallback;
    const normalized = value.trim().slice(0, 180);
    return normalized && !/[;{}<>]/.test(normalized) ? normalized : fallback;
  };
  const optionalFilename = (value, field) => {
    if (typeof value !== "string" || !value.trim()) return "";
    const normalized = value.trim();
    if (path.basename(normalized) !== normalized) throw new Error(`${field} must stay inside its theme directory`);
    if (!/\.(?:png|jpe?g|webp)$/i.test(normalized)) throw new Error(`${field} must be PNG, JPEG, or WebP`);
    return normalized;
  };
  const theme = {
    schemaVersion: 1,
    id: text(raw.id, "custom", 80),
    name: text(raw.name, "Codex Theme Studio", 80),
    brandLabel: text(raw.brandLabel, "THEME STUDIO", 80),
    brandImage: optionalFilename(raw.brandImage, "Theme brand image"),
    showBrand: raw.showBrand !== false,
    tagline: text(raw.tagline, "Make something wonderful.", 160),
    projectPrefix: text(raw.projectPrefix, "选择项目 · ", 80),
    projectLabel: text(raw.projectLabel, "◉  选择项目", 80),
    statusText: text(raw.statusText, "DREAM SKIN ONLINE", 80),
    quote: text(raw.quote, "MAKE SOMETHING WONDERFUL", 80),
    image: raw.image,
    artPlacement: raw.artPlacement === "all" ? "all" : "hero",
    fonts: {
      ui: fontStack(raw.fonts?.ui, '"Source Han Serif SC", "Songti SC", ui-serif, Georgia, serif'),
      code: fontStack(raw.fonts?.code, '"SF Mono", ui-monospace, Menlo, monospace'),
    },
    colors: {
      background: color(raw.colors?.background, "#F5F3EE"),
      panel: color(raw.colors?.panel, "#FAF9F6"),
      panelAlt: color(raw.colors?.panelAlt, "#EEECE6"),
      accent: color(raw.colors?.accent, "#DA7756"),
      accentAlt: color(raw.colors?.accentAlt, "#CC7D5E"),
      secondary: color(raw.colors?.secondary, "#1B365D"),
      highlight: color(raw.colors?.highlight, "#1B365D"),
      text: color(raw.colors?.text, "#1D1B16"),
      muted: color(raw.colors?.muted, "#69675F"),
      line: color(raw.colors?.line, "rgba(20, 20, 19, .12)"),
      sidebar: color(raw.colors?.sidebar, "#F1F0EC"),
      selected: color(raw.colors?.selected, "#E8E6DC"),
      border: color(raw.colors?.border, "#E4E1DA"),
      paperBlue: color(raw.colors?.paperBlue, "#E7EDF2"),
    },
  };
  const imagePath = path.join(assetsRoot, theme.image);
  const imageStat = await fs.lstat(imagePath);
  if (imageStat.isSymbolicLink() || !imageStat.isFile() || imageStat.size < 1 || imageStat.size > MAX_ART_BYTES) {
    throw new Error(`Theme image must be a non-empty file no larger than ${MAX_ART_BYTES} bytes`);
  }
  const extension = path.extname(theme.image).toLowerCase();
  if (![".png", ".jpg", ".jpeg", ".webp"].includes(extension)) {
    throw new Error(`Unsupported theme image format: ${extension || "missing"}`);
  }
  let brandImagePath = "";
  let brandImageStat = null;
  if (theme.brandImage) {
    brandImagePath = path.join(assetsRoot, theme.brandImage);
    brandImageStat = await fs.lstat(brandImagePath);
    if (brandImageStat.isSymbolicLink() || !brandImageStat.isFile() || brandImageStat.size < 1 || brandImageStat.size > 4 * 1024 * 1024) {
      throw new Error("Theme brand image must be a non-empty file no larger than 4 MB");
    }
  }
  return { assetsRoot, imagePath, imageStat, brandImagePath, brandImageStat, theme };
}

function buildPrepaintBootstrap(css, theme) {
  const colors = theme.colors || {};
  const variables = {
    "--ds-bg": colors.background,
    "--ds-panel": colors.panel,
    "--ds-panel-2": colors.panelAlt,
    "--ds-sidebar": colors.sidebar,
    "--ds-selected": colors.selected,
    "--ds-border": colors.border,
    "--ds-paper-blue": colors.paperBlue,
    "--ds-green": colors.accent,
    "--ds-lime": colors.accentAlt,
    "--ds-cyan": colors.secondary,
    "--ds-purple": colors.highlight,
    "--ds-text": colors.text,
    "--ds-muted": colors.muted,
    "--ds-line": colors.line,
  };
  return `((cssText, variables, version) => {
    const install = () => {
      if (window.__CODEX_DREAM_SKIN_DISABLED__) return;
      const root = document.documentElement;
      if (!root) return requestAnimationFrame(install);
      root.classList.add("codex-dream-skin");
      if (!root.getAttribute("data-dream-shell")) root.setAttribute("data-dream-shell", "light");
      for (const [name, value] of Object.entries(variables)) {
        if (value && root.style.getPropertyValue(name) !== value) root.style.setProperty(name, value);
      }
      let style = document.getElementById("codex-dream-skin-style");
      if (!style) {
        style = document.createElement("style");
        style.id = "codex-dream-skin-style";
        (document.head || root).appendChild(style);
      }
      if (style.textContent !== cssText) style.textContent = cssText;
      style.dataset.dreamSkinPrepaint = version;
      try {
        const clickedAt = Number(sessionStorage.getItem("__CODEX_DREAM_SKIN_ROUTE_CLICK_AT__"));
        if (!window.__DREAM_SKIN_FIRST_FRAME__) {
          const sample = (at) => ({
            at,
            capturedAt: Date.now(),
            deltaMs: Number.isFinite(clickedAt) && clickedAt > 0 ? Date.now() - clickedAt : null,
            background: getComputedStyle(document.querySelector('main.main-surface') || document.body || root).backgroundColor,
          });
          window.__DREAM_SKIN_FIRST_FRAME__ = sample(performance.now());
          requestAnimationFrame((at) => {
            window.__DREAM_SKIN_FIRST_FRAME__ = sample(at);
            if (Number.isFinite(clickedAt) && clickedAt > 0) {
              sessionStorage.removeItem("__CODEX_DREAM_SKIN_ROUTE_CLICK_AT__");
            }
          });
        }
      } catch {}
    };
    install();
  })(${JSON.stringify(css)}, ${JSON.stringify(variables)}, ${JSON.stringify(SKIN_VERSION)})`;
}

async function loadPayload(themeDir) {
  const [css, template, loaded] = await Promise.all([
    fs.readFile(path.join(root, "assets", "dream-skin.css"), "utf8"),
    fs.readFile(path.join(root, "assets", "renderer-inject.js"), "utf8"),
    loadTheme(themeDir),
  ]);
  const { imagePath, brandImagePath, theme } = loaded;
  const art = await fs.readFile(imagePath);
  const extension = path.extname(imagePath).toLowerCase();
  const mime = extension === ".jpg" || extension === ".jpeg" ? "image/jpeg"
    : extension === ".webp" ? "image/webp" : "image/png";
  const artDataUrl = `data:${mime};base64,${art.toString("base64")}`;
  let brandImageDataUrl = "";
  if (brandImagePath) {
    const brand = await fs.readFile(brandImagePath);
    const brandExtension = path.extname(brandImagePath).toLowerCase();
    const brandMime = brandExtension === ".jpg" || brandExtension === ".jpeg" ? "image/jpeg"
      : brandExtension === ".webp" ? "image/webp" : "image/png";
    brandImageDataUrl = `data:${brandMime};base64,${brand.toString("base64")}`;
  }
  const payload = template
    .replace("__DREAM_SKIN_CSS_JSON__", JSON.stringify(css))
    .replace("__DREAM_SKIN_ART_JSON__", JSON.stringify(artDataUrl))
    .replace("__DREAM_SKIN_BRAND_IMAGE_JSON__", JSON.stringify(brandImageDataUrl))
    .replace("__DREAM_SKIN_THEME_JSON__", JSON.stringify(theme))
    .replace("__DREAM_SKIN_VERSION_JSON__", JSON.stringify(SKIN_VERSION));
  const prepaint = buildPrepaintBootstrap(css, theme);
  return { imageBytes: art.length, payload, prepaint, theme };
}

async function applyToSession(session, payload) {
  return session.evaluate(payload);
}

async function registerPrepaint(session, prepaint) {
  const result = await session.send("Page.addScriptToEvaluateOnNewDocument", { source: prepaint });
  await session.evaluate(prepaint);
  return result.identifier;
}

async function unregisterPrepaint(session, identifier) {
  if (!identifier || session.closed) return;
  await session.send("Page.removeScriptToEvaluateOnNewDocument", { identifier });
}

async function removeFromSession(session) {
  return session.evaluate(`(() => {
    window.__CODEX_DREAM_SKIN_DISABLED__ = true;
    const state = window.__CODEX_DREAM_SKIN_STATE__;
    if (state?.cleanup) return state.cleanup();
    document.documentElement?.classList.remove('codex-dream-skin', 'dream-skin-home', 'dream-skin-home-shell');
    document.documentElement?.removeAttribute('data-dream-shell');
    document.documentElement?.removeAttribute('data-dream-art-placement');
    document.documentElement?.style.removeProperty('--dream-skin-art');
    for (const name of ['--ds-bg', '--ds-panel', '--ds-panel-2', '--ds-sidebar', '--ds-selected',
      '--ds-border', '--ds-paper-blue', '--ds-green', '--ds-lime', '--ds-cyan', '--ds-purple',
      '--ds-text', '--ds-muted', '--ds-line', '--dream-skin-name', '--dream-skin-project-label']) {
      document.documentElement?.style.removeProperty(name);
    }
    document.querySelectorAll('.dream-skin-home, .dream-skin-home-shell').forEach((node) => {
      node.classList.remove('dream-skin-home', 'dream-skin-home-shell');
    });
    document.getElementById('codex-dream-skin-style')?.remove();
    document.getElementById('codex-dream-skin-chrome')?.remove();
    delete window.__CODEX_DREAM_SKIN_STATE__;
    return true;
  })()`);
}

async function verifyRemovedSession(session) {
  return session.evaluate(`(() =>
    !document.documentElement.classList.contains('codex-dream-skin') &&
    !document.getElementById('codex-dream-skin-style') &&
    !document.getElementById('codex-dream-skin-chrome') &&
    !window.__CODEX_DREAM_SKIN_STATE__
  )()`);
}

async function collectSessionSnapshot(session) {
  return session.evaluate(`(() => {
    const boxFromRect = (node, r) => {
      const style = getComputedStyle(node);
      return {
        x: Math.round(r.x), y: Math.round(r.y),
        width: Math.round(r.width), height: Math.round(r.height),
        visible: r.width > 0 && r.height > 0 && style.display !== 'none' && style.visibility !== 'hidden',
      };
    };
    const box = (node) => {
      if (!node) return null;
      const r = node.getBoundingClientRect();
      return boxFromRect(node, r);
    };
    const styleOf = (node) => node ? getComputedStyle(node) : null;
    const paintVisible = (node) => {
      if (!node) return false;
      const own = node.getBoundingClientRect();
      let left = Math.max(0, own.left);
      let top = Math.max(0, own.top);
      let right = Math.min(innerWidth, own.right);
      let bottom = Math.min(innerHeight, own.bottom);
      for (let ancestor = node.parentElement; ancestor && ancestor !== document.body; ancestor = ancestor.parentElement) {
        const style = getComputedStyle(ancestor);
        const clips = style.overflowX !== 'visible' || style.overflowY !== 'visible' ||
          /(?:paint|content|strict)/.test(style.contain || '');
        if (!clips) continue;
        const rect = ancestor.getBoundingClientRect();
        left = Math.max(left, rect.left);
        top = Math.max(top, rect.top);
        right = Math.min(right, rect.right);
        bottom = Math.min(bottom, rect.bottom);
      }
      if (right - left <= 1 || bottom - top <= 1) return false;
      const hit = document.elementFromPoint((left + right) / 2, (top + bottom) / 2);
      return Boolean(hit && (node.contains(hit) || hit.contains(node)));
    };
    const paintClipped = (node) => {
      if (!node) return true;
      const own = node.getBoundingClientRect();
      if (own.left < -1 || own.top < -1 || own.right > innerWidth + 1 || own.bottom > innerHeight + 1) return true;
      for (let ancestor = node.parentElement; ancestor && ancestor !== document.body; ancestor = ancestor.parentElement) {
        const style = getComputedStyle(ancestor);
        const rect = ancestor.getBoundingClientRect();
        const containClips = /(?:paint|content|strict)/.test(style.contain || '');
        if ((containClips || style.overflowX !== 'visible') &&
            (own.left < rect.left - 1 || own.right > rect.right + 1)) return true;
        if ((containClips || style.overflowY !== 'visible') &&
            (own.top < rect.top - 1 || own.bottom > rect.bottom + 1)) return true;
      }
      return false;
    };
    const mainSurface = document.querySelector('main.main-surface') || document.querySelector('main');
    const header = mainSurface?.querySelector(':scope > header.app-header-tint') || null;
    const headerTabs = [...document.querySelectorAll('[class~="group/tab"]')].map((tab) => {
      const titleButton = tab.querySelector('button:not([aria-label^="Close "])');
      const titleStyle = styleOf(titleButton);
      const titleBox = box(titleButton);
      const titleLayer = getComputedStyle(tab, '::after');
      return {
        ...box(tab),
        title: (titleButton?.textContent || '').trim(),
        titleVisible: Boolean(titleBox?.visible) && Number(titleStyle?.opacity || 0) > 0.5 &&
          titleStyle?.color !== 'transparent' && paintVisible(titleButton),
        titleOpacity: Number(titleStyle?.opacity || 0),
        pointerEvents: titleStyle?.pointerEvents ?? 'none',
        titleLayerVisible: titleLayer.content !== 'none' && titleLayer.content !== 'normal' &&
          titleLayer.color !== 'transparent' && paintVisible(tab),
      };
    });
    const workspaceTabCount = [...document.querySelectorAll('[role="tablist"] [role="tab"]')]
      .filter((tab) => box(tab)?.visible).length;
    const sidebarNode = document.querySelector('aside.app-shell-left-panel');
    const composerNode = document.querySelector('.composer-surface-chrome');
    const roleMains = [...document.querySelectorAll('[role="main"]')];
    const home = roleMains.find((candidate) =>
      candidate.querySelector('[data-testid="home-icon"], [data-feature="game-source"], .group\\\\/home-suggestions')) ?? null;
    const feature = home?.querySelector('[data-feature="game-source"]') ?? null;
    const suggestions = home?.querySelector('.group\\\\/home-suggestions') ?? null;
    const suggestionsPresent = Boolean(suggestions);
    const suggestionsRow = suggestions?.parentElement ?? null;
    const layout = suggestionsRow?.parentElement ?? null;
    const heroNode = home?.querySelector('.dream-skin-home-hero') ??
      (layout ? [...layout.children].find((node) => node !== suggestionsRow && node.querySelector?.('[data-feature="game-source"]')) : null);
    const enhancementHookPresent = Boolean(feature && heroNode);
    const groupRect = suggestions?.getBoundingClientRect() ?? null;
    const cards = suggestions && groupRect ? [...suggestions.querySelectorAll('button')].map((node) => {
      const rect = node.getBoundingClientRect();
      const item = boxFromRect(node, rect);
      const iconCell = node.querySelector(':scope > span:first-child > span:first-child');
      const icon = iconCell?.querySelector('svg') ?? null;
      const cellRect = iconCell?.getBoundingClientRect();
      const iconRect = icon?.getBoundingClientRect();
      return {
        ...item,
        tagName: node.tagName,
        role: node.getAttribute('role') || (node.tagName === 'BUTTON' ? 'button' : null),
        focusable: !node.disabled && (node.tabIndex >= 0 || node.tagName === 'BUTTON'),
        clipped: paintClipped(node),
        iconOffset: cellRect && iconRect ? {
          x: (iconRect.left + iconRect.width / 2) - (cellRect.left + cellRect.width / 2),
          y: (iconRect.top + iconRect.height / 2) - (cellRect.top + cellRect.height / 2),
        } : null,
      };
    }) : [];
    const cardRows = [...new Set(cards.filter((card) => card.visible).map((card) => Math.round(card.y / 4) * 4))];
    const cardColumns = cardRows.length ? Math.ceil(cards.filter((card) => card.visible).length / cardRows.length) : null;
    const heroBox = box(heroNode);
    const selectedSession = document.querySelector('aside.app-shell-left-panel [data-app-action-sidebar-thread-active="true"]');
    const selectedStyle = styleOf(selectedSession);
    const chrome = document.getElementById('codex-dream-skin-chrome');
    const brand = chrome?.querySelector('.dream-skin-brand') ?? null;
    const mainStyle = styleOf(mainSurface);
    const sidebarStyle = styleOf(sidebarNode);
    const headerStyle = styleOf(header);
    return {
      schemaVersion: 1,
      mode: home ? 'home' : 'task',
      installed: document.documentElement.classList.contains('codex-dream-skin'),
      version: window.__CODEX_DREAM_SKIN_STATE__?.version ?? null,
      stylePresent: Boolean(document.getElementById('codex-dream-skin-style')),
      chromePresent: Boolean(chrome),
      chromePointerEvents: getComputedStyle(chrome || document.body).pointerEvents,
      viewport: { width: innerWidth, height: innerHeight },
      documentOverflow: {
        x: document.documentElement.scrollWidth > document.documentElement.clientWidth,
        y: document.documentElement.scrollHeight > document.documentElement.clientHeight,
      },
      shell: {
        main: box(mainSurface),
        sidebar: box(sidebarNode),
        composer: box(composerNode),
        mainBackground: mainStyle?.backgroundColor ?? null,
        sidebarBackground: sidebarStyle?.backgroundColor ?? null,
        topBorderBottomWidth: Number.parseFloat(headerStyle?.borderBottomWidth || '0'),
        topHeaderBackground: headerStyle?.backgroundColor ?? null,
        workspaceTabCount,
        headerTabs,
      },
      home: home ? {
        enhancementHookPresent,
        suggestionsPresent,
        hero: heroBox ? {
          ...heroBox,
          backgroundImage: styleOf(heroNode)?.backgroundImage ?? 'none',
          backgroundSize: styleOf(heroNode)?.backgroundSize ?? 'auto',
        } : null,
        cardColumns,
        cards,
        selectedSession: selectedSession ? {
          backgroundColor: selectedStyle?.backgroundColor ?? null,
          borderLeftWidth: Number.parseFloat(selectedStyle?.borderLeftWidth || '0'),
        } : null,
      } : null,
      task: home ? null : {
        backgroundImage: mainStyle?.backgroundImage ?? 'none',
        brandVisible: Boolean(box(brand)?.visible),
      },
    };
  })()`);
}

async function verifySession(session, theme) {
  const snapshot = await collectSessionSnapshot(session);
  return {
    ...snapshot,
    ...evaluateSnapshot(snapshot, {
      expectedVersion: SKIN_VERSION,
      expectedColors: theme?.colors,
      expectedArtPlacement: theme?.artPlacement,
    }),
  };
}

async function waitForVerifiedSession(session, timeoutMs, strictVisual = false, theme = null) {
  const deadline = Date.now() + timeoutMs;
  let lastResult;
  while (Date.now() < deadline) {
    lastResult = await verifySession(session, theme);
    if (lastResult.pass && (!strictVisual || lastResult.strictVisualPass)) return lastResult;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  return lastResult;
}

async function capture(session, outputPath, { settleMs = 300, parkPointer = true } = {}) {
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  if (parkPointer) {
    await session.send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27 });
    await session.send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27 });
    const viewport = await session.evaluate("({ width: innerWidth, height: innerHeight })");
    await session.send("Input.dispatchMouseEvent", {
      type: "mouseMoved",
      x: Math.round(viewport.width * 0.64),
      y: Math.round(viewport.height * 0.62),
      button: "none",
    });
  }
  if (settleMs > 0) await new Promise((resolve) => setTimeout(resolve, settleMs));
  const result = await session.send("Page.captureScreenshot", {
    format: "png",
    fromSurface: true,
    captureBeyondViewport: false,
  });
  await fs.writeFile(outputPath, Buffer.from(result.data, "base64"));
}

async function sampleNewTaskTransition(session, outputDir, theme) {
  await fs.mkdir(outputDir, { recursive: true });
  const before = await collectSessionSnapshot(session);
  const target = await session.evaluate(`(() => {
    window.__DREAM_SKIN_ROUTE_PROBE__?.cleanup?.();
    const candidates = [...document.querySelectorAll('button, a, [role="button"]')];
    const button = candidates.find((node) => {
      const text = (node.textContent || '').trim().toLowerCase();
      const aria = (node.getAttribute('aria-label') || '').trim().toLowerCase();
      const action = node.getAttributeNames().some((name) => name.includes('new-task'));
      return action || text.startsWith('new task') || text.startsWith('new chat') ||
        text === '新任务' || text === '新聊天' || aria === 'new task' || aria === 'new chat' ||
        aria === '新任务' || aria === '新聊天';
    });
    if (!button) return null;
    const rect = button.getBoundingClientRect();
    const x = rect.left + rect.width / 2;
    const y = rect.top + rect.height / 2;
    const hit = document.elementFromPoint(x, y);
    const enabled = !button.disabled && button.getAttribute('aria-disabled') !== 'true';
    const clickable = enabled && rect.width > 0 && rect.height > 0 && button.contains(hit);
    if (!clickable) return { x, y, clickable: false };
    const probe = { clickAt: null, firstFrame: null, cleanup: null };
    const handler = (event) => {
      if (!button.contains(event.target)) return;
      probe.clickAt = performance.now();
      try { sessionStorage.setItem("__CODEX_DREAM_SKIN_ROUTE_CLICK_AT__", String(Date.now())); } catch {}
      requestAnimationFrame((at) => {
        probe.firstFrame = {
          at,
          capturedAt: Date.now(),
          deltaMs: at - probe.clickAt,
          background: getComputedStyle(document.querySelector('main.main-surface') || document.body).backgroundColor,
        };
      });
    };
    document.addEventListener('click', handler, true);
    probe.cleanup = () => document.removeEventListener('click', handler, true);
    window.__DREAM_SKIN_ROUTE_PROBE__ = probe;
    return { x, y, clickable: true };
  })()`);
  if (!target) return { pass: false, reasons: ["new-task-control-missing"], samples: [] };
  if (!target.clickable) return { pass: false, reasons: ["new-task-control-not-clickable"], samples: [] };

  try {
    const clickWallAt = Date.now();
    await session.send("Input.dispatchMouseEvent", { type: "mousePressed", x: target.x, y: target.y, button: "left", clickCount: 1 });
    await session.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: target.x, y: target.y, button: "left", clickCount: 1 });
    const compositorFrame = await session.send("Page.captureScreenshot", {
      format: "png",
      fromSurface: true,
      captureBeyondViewport: false,
    });
    await fs.writeFile(
      path.join(outputDir, "new-task-first-frame.png"),
      Buffer.from(compositorFrame.data, "base64"),
    );
    const firstFrameDeadline = Date.now() + 3000;
    let firstFrame = null;
    while (!firstFrame && Date.now() < firstFrameDeadline) {
      try {
        const candidate = await session.evaluate(
          `window.__DREAM_SKIN_ROUTE_PROBE__?.firstFrame ?? window.__DREAM_SKIN_FIRST_FRAME__ ?? ({
            at: performance.now(),
            capturedAt: Date.now(),
            deltaMs: Date.now() - ${clickWallAt},
            background: getComputedStyle(document.querySelector('main.main-surface') || document.body || document.documentElement).backgroundColor,
            source: "post-click-compositor"
          })`,
        );
        if (candidate?.capturedAt >= clickWallAt) firstFrame = candidate;
      } catch (error) {
        if (!/execution context|context was destroyed/i.test(error.message)) throw error;
      }
      if (!firstFrame) await new Promise((resolve) => setTimeout(resolve, 16));
    }
    if (!firstFrame) throw new Error("New Task first frame timed out");

    const samples = [];
    const sampleStarted = Date.now();
    let previousCardCount = null;
    const reasons = [];
    let homeObserved = false;
    if (before.mode !== "task") reasons.push("new-task-precondition-not-task");
    if (!colorsMatch(firstFrame.background, theme.colors.background)) reasons.push("new-task-first-frame-background-mismatch");
    for (const offset of [0, 50, 150, 500]) {
      const waitMs = offset - (Date.now() - sampleStarted);
      if (waitMs > 0) await new Promise((resolve) => setTimeout(resolve, waitMs));
      const snapshot = await collectSessionSnapshot(session);
      if (snapshot.mode === "home") homeObserved = true;
      const verdict = evaluateSnapshot(snapshot, {
        expectedVersion: SKIN_VERSION,
        expectedColors: theme.colors,
        expectedArtPlacement: theme.artPlacement,
      });
      if (!snapshot.installed || !snapshot.stylePresent || verdict.reasons.includes("main-background-mismatch")) {
        reasons.push(`new-task-prepaint-missing:${offset}ms`);
      }
      const cardCount = snapshot.home?.cards?.filter((card) => card.visible).length ?? 0;
      if (previousCardCount !== null && previousCardCount > 0 && cardCount < previousCardCount) {
        reasons.push(`mounted-cards-disappeared:${offset}ms`);
      }
      previousCardCount = cardCount;
      const label = String(offset).padStart(3, "0");
      const screenshot = path.join(outputDir, `new-task-${label}ms.png`);
      await capture(session, screenshot, { settleMs: 0, parkPointer: false });
      samples.push({ offsetMs: offset, observedAtMs: Date.now() - sampleStarted, snapshot, verdict, screenshot });
    }
    if (!homeObserved) reasons.push("new-task-route-not-observed");
    const result = { pass: reasons.length === 0, firstFrame, reasons, samples };
    await fs.writeFile(path.join(outputDir, "new-task-samples.json"), `${JSON.stringify(result, null, 2)}\n`);
    return result;
  } finally {
    await session.evaluate(`(() => {
      window.__DREAM_SKIN_ROUTE_PROBE__?.cleanup?.();
      delete window.__DREAM_SKIN_ROUTE_PROBE__;
      delete window.__DREAM_SKIN_FIRST_FRAME__;
      try { sessionStorage.removeItem("__CODEX_DREAM_SKIN_ROUTE_CLICK_AT__"); } catch {}
      return true;
    })()`).catch(() => {});
  }
}

async function runOneShot(options) {
  const connected = await connectCodexTargets(options.port, options.timeoutMs);
  const loaded = options.mode === "remove" ? null : await loadPayload(options.themeDir);
  const payload = loaded?.payload ?? null;
  const results = [];
  let screenshotCaptured = false;

  try {
    for (const { target, session, probe } of connected) {
      let prepaintIdentifier = null;
      try {
        if (options.viewportWidth !== null) {
          await session.send("Emulation.setDeviceMetricsOverride", {
            width: options.viewportWidth,
            height: options.viewportHeight,
            deviceScaleFactor: 1,
            mobile: false,
          });
        }
        if (options.mode === "remove") await removeFromSession(session);
        else if (options.mode === "once") {
          await session.evaluate(loaded.prepaint);
          await applyToSession(session, payload);
        }

        if (options.reload) {
          if (options.mode !== "remove") prepaintIdentifier = await registerPrepaint(session, loaded.prepaint);
          const domReady = session.once("Page.domContentEventFired", options.timeoutMs);
          try {
            await session.send("Page.reload", { ignoreCache: true });
            await domReady.promise;
          } catch (error) {
            domReady.cancel();
            await domReady.promise.catch(() => {});
            throw error;
          }
          if (options.mode === "remove") await removeFromSession(session);
          else await applyToSession(session, payload);
        }

        const result = options.mode === "remove"
          ? await verifyRemovedSession(session)
          : await waitForVerifiedSession(session, options.timeoutMs, options.strictVisual, loaded.theme);
        const transition = options.sampleNewTaskDir && options.mode !== "remove"
          ? await sampleNewTaskTransition(session, options.sampleNewTaskDir, loaded.theme)
          : null;
        results.push({ targetId: target.id, title: target.title, url: target.url, probe, result, transition });

        if (options.screenshot && !screenshotCaptured) {
          await capture(session, options.screenshot);
          screenshotCaptured = true;
        }
      } finally {
        try { await unregisterPrepaint(session, prepaintIdentifier); } catch {}
        if (options.viewportWidth !== null) {
          try { await session.send("Emulation.clearDeviceMetricsOverride"); } catch {}
        }
        session.close();
      }
    }
  } finally {
    for (const { session } of connected) session.close();
  }

  console.log(JSON.stringify({
    mode: options.mode,
    version: SKIN_VERSION,
    port: options.port,
    strictVisual: options.strictVisual,
    viewport: options.viewportWidth ? { width: options.viewportWidth, height: options.viewportHeight } : null,
    targets: results,
  }, null, 2));
  const failed = results.length === 0 || results.some((item) => options.mode === "remove"
    ? item.result !== true
    : !item.result?.pass || (options.strictVisual && !item.result?.strictVisualPass) || item.transition?.pass === false);
  if (failed) process.exitCode = 2;
}

async function runWatch(options) {
  const { payload, prepaint } = await loadPayload(options.themeDir);
  const sessions = new Map();
  const rejected = new Set();
  let stopping = false;
  const stop = () => { stopping = true; };
  process.on("SIGINT", stop);
  process.on("SIGTERM", stop);

  while (!stopping) {
    let targets = [];
    try {
      targets = await listAppTargets(options.port);
    } catch (error) {
      console.error(`[dream-skin] ${new Date().toISOString()} ${error.message}`);
      await new Promise((resolve) => setTimeout(resolve, 1000));
      continue;
    }

    const activeIds = new Set(targets.map((target) => target.id));
    for (const [id, record] of sessions) {
      if (!activeIds.has(id) || record.session.closed) {
        try { await unregisterPrepaint(record.session, record.prepaintIdentifier); } catch {}
        record.session.close();
        sessions.delete(id);
      }
    }

    for (const target of targets) {
      if (sessions.has(target.id)) continue;
      let session;
      let prepaintIdentifier = null;
      try {
        session = await connectTarget(target, options.port);
        const probe = await probeSession(session);
        if (!probe?.codex) {
          session.close();
          if (!rejected.has(target.id)) {
            console.error(`[dream-skin] rejected non-Codex app target ${target.id}`);
            rejected.add(target.id);
          }
          continue;
        }
        rejected.delete(target.id);
        prepaintIdentifier = await registerPrepaint(session, prepaint);
        session.on("Page.domContentEventFired", () => {
          void applyToSession(session, payload).catch((error) => {
            console.error(`[dream-skin] full ensure failed: ${error.message}`);
          });
        });
        await applyToSession(session, payload);
        sessions.set(target.id, { session, prepaintIdentifier });
        console.log(`[dream-skin] injected verified Codex target ${target.id} (${target.title || target.url})`);
      } catch (error) {
        try { await unregisterPrepaint(session, prepaintIdentifier); } catch {}
        session?.close();
        console.error(`[dream-skin] inject failed for ${target.id}: ${error.message}`);
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 900));
  }

  for (const { session, prepaintIdentifier } of sessions.values()) {
    try { await unregisterPrepaint(session, prepaintIdentifier); } catch {}
    session.close();
  }
}

try {
  const options = parseArgs(process.argv.slice(2));
  if (options.mode === "check") {
    const loaded = await loadPayload(options.themeDir);
    console.log(JSON.stringify({
      pass: true,
      version: SKIN_VERSION,
      themeId: loaded.theme.id,
      themeName: loaded.theme.name,
      imageBytes: loaded.imageBytes,
      prepaintBytes: Buffer.byteLength(loaded.prepaint),
      prepaintContainsImageData: loaded.prepaint.includes("data:image"),
      payloadBytes: Buffer.byteLength(loaded.payload),
    }, null, 2));
  } else if (options.mode === "watch") {
    await runWatch(options);
  } else {
    await runOneShot(options);
    // Node's built-in WebSocket may keep a successful one-shot process alive
    // while the CDP peer delays its close handshake. All output is complete.
    process.exit(process.exitCode ?? 0);
  }
} catch (error) {
  console.error(`[dream-skin] ${error.stack || error.message}`);
  process.exitCode = 1;
}

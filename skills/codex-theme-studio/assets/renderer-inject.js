((cssText, artDataUrl, themeConfig) => {
  const STATE_KEY = "__CODEX_DREAM_SKIN_STATE__";
  const DISABLED_KEY = "__CODEX_DREAM_SKIN_DISABLED__";
  const STYLE_ID = "codex-dream-skin-style";
  const CHROME_ID = "codex-dream-skin-chrome";
  const SHELL_ATTR = "data-dream-shell";
  const COMPOSER_MARKER = "dream-skin-composer";
  const HOME_MARKERS = [
    "dream-skin-home",
    "dream-skin-home-content",
    "dream-skin-home-shell",
    "dream-skin-home-hero",
  ];
  const VERSION = __DREAM_SKIN_VERSION_JSON__;
  const THEME = themeConfig && typeof themeConfig === "object" ? themeConfig : {};
  const THEME_VARIABLES = [
    "--ds-bg", "--ds-panel", "--ds-panel-2", "--ds-sidebar", "--ds-selected",
    "--ds-border", "--ds-paper-blue", "--ds-green", "--ds-lime", "--ds-cyan",
    "--ds-purple", "--ds-text", "--ds-muted", "--ds-line", "--dream-skin-name",
    "--dream-skin-project-label",
  ];

  const disposeRuntime = (state) => {
    state?.observer?.disconnect();
    if (state?.timer) clearInterval(state.timer);
    if (state?.scheduler?.raf) cancelAnimationFrame(state.scheduler.raf);
    if (state?.resizeHandler) window.removeEventListener("resize", state.resizeHandler);
    if (state?.mediaHandler && state?.mediaQuery) {
      try { state.mediaQuery.removeEventListener("change", state.mediaHandler); } catch {}
    }
    if (state?.artUrl) URL.revokeObjectURL(state.artUrl);
  };

  disposeRuntime(window[STATE_KEY]);
  document.querySelectorAll(`.${HOME_MARKERS.join(", .")}`).forEach((node) => {
    node.classList.remove(...HOME_MARKERS);
  });
  document.querySelectorAll(`.${COMPOSER_MARKER}`).forEach((node) => {
    node.classList.remove(COMPOSER_MARKER);
  });
  window[DISABLED_KEY] = false;

  const artUrl = (() => {
    const comma = artDataUrl.indexOf(",");
    const mime = /^data:([^;,]+)/.exec(artDataUrl)?.[1] || "image/png";
    const binary = atob(artDataUrl.slice(comma + 1));
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
    return URL.createObjectURL(new Blob([bytes], { type: mime }));
  })();

  const cssString = (value) => JSON.stringify(String(value ?? ""));
  const setStyleProperty = (style, name, value) => {
    if (style.getPropertyValue(name) !== value) style.setProperty(name, value);
  };
  const parseRgb = (value) => {
    if (!value || value === "transparent") return null;
    const match = String(value).match(/rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)/i);
    if (!match) return null;
    return { r: Number(match[1]), g: Number(match[2]), b: Number(match[3]) };
  };

  const luminance = ({ r, g, b }) => {
    const channels = [r, g, b].map((channel) => {
      const value = channel / 255;
      return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
  };

  const detectShellMode = () => {
    const root = document.documentElement;
    const body = document.body;
    const classes = `${root?.className || ""} ${body?.className || ""}`.toLowerCase();
    if (/\b(dark|theme-dark|appearance-dark)\b/.test(classes)) return "dark";
    if (/\b(light|theme-light|appearance-light)\b/.test(classes)) return "light";

    const dataTheme = (
      root?.getAttribute("data-theme") || root?.getAttribute("data-appearance") ||
      root?.getAttribute("data-color-mode") || body?.getAttribute("data-theme") ||
      body?.getAttribute("data-appearance") || ""
    ).toLowerCase();
    if (dataTheme.includes("dark")) return "dark";
    if (dataTheme.includes("light")) return "light";

    const samples = [
      body,
      document.querySelector("main.main-surface") || document.querySelector("main"),
      document.querySelector("aside.app-shell-left-panel"),
    ].filter(Boolean);
    let lightVotes = 0;
    let darkVotes = 0;
    for (const node of samples) {
      try {
        const rgb = parseRgb(getComputedStyle(node).backgroundColor);
        if (!rgb) continue;
        const value = luminance(rgb);
        if (value >= 0.55) lightVotes += 1;
        else if (value <= 0.25) darkVotes += 1;
      } catch {}
    }
    if (lightVotes > darkVotes) return "light";
    if (darkVotes > lightVotes) return "dark";
    try { return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"; } catch {}
    return "light";
  };

  const applyTheme = (root) => {
    const colors = THEME.colors || {};
    const accent = colors.accent || "#B85235";
    const secondary = colors.secondary || "#1B365D";
    const variables = {
      "--ds-bg": colors.background || "#F5F4ED",
      "--ds-panel": colors.panel || "#FAF9F5",
      "--ds-panel-2": colors.panelAlt || "#E8E6DC",
      "--ds-sidebar": colors.sidebar || "#F5F4ED",
      "--ds-selected": colors.selected || "#EEECE6",
      "--ds-border": colors.border || "#E5E3D8",
      "--ds-paper-blue": colors.paperBlue || "#EEF2F7",
      "--ds-green": accent,
      "--ds-lime": colors.accentAlt || accent,
      "--ds-cyan": secondary,
      "--ds-purple": colors.highlight || secondary,
      "--ds-text": colors.text || "#141413",
      "--ds-muted": colors.muted || "#6B6A64",
      "--ds-line": colors.line || "rgba(20, 20, 19, .12)",
    };
    for (const [name, value] of Object.entries(variables)) setStyleProperty(root.style, name, value);
    setStyleProperty(root.style, "--dream-skin-name", cssString(THEME.name || "Codex Dream Skin"));
    setStyleProperty(root.style, "--dream-skin-project-label", cssString(THEME.projectLabel || "◉  选择项目"));
  };

  const ensureStyle = (root) => {
    let style = document.getElementById(STYLE_ID);
    if (!style) {
      style = document.createElement("style");
      style.id = STYLE_ID;
      (document.head || root).appendChild(style);
    }
    if (style.textContent !== cssText) style.textContent = cssText;
    if (style.dataset.dreamSkinVersion !== VERSION) style.dataset.dreamSkinVersion = VERSION;
    delete style.dataset.dreamSkinPrepaint;
    return style;
  };

  const ensureTabTitles = () => {
    for (const tab of document.querySelectorAll('[class~="group/tab"]')) {
      const titleButton = tab.querySelector('button:not([aria-label^="Close "])');
      const title = (titleButton?.textContent || "").trim();
      if (title && tab.getAttribute("data-dream-tab-title") !== title) {
        tab.setAttribute("data-dream-tab-title", title);
      }
    }
  };

  const syncComposerSurface = () => {
    const editor = [...document.querySelectorAll('.ProseMirror[contenteditable="true"][role="textbox"]')]
      .find((candidate) => !candidate.closest(".cm-editor")) || null;
    const surface = document.querySelector(".composer-surface-chrome") ||
      editor?.closest('[class*="ComposerLayoutRoot_"]') || editor;
    document.querySelectorAll(`.${COMPOSER_MARKER}`).forEach((node) => {
      if (node !== surface) node.classList.remove(COMPOSER_MARKER);
    });
    surface?.classList.add("dream-skin-composer");
    return surface;
  };

  const syncHomeRoute = () => {
    const roleMains = [...document.querySelectorAll('[role="main"]')];
    const home = roleMains.find((candidate) => candidate.querySelector('[data-feature="game-source"]')) || null;
    for (const candidate of roleMains) candidate.classList.toggle("dream-skin-home", candidate === home);

    const feature = home?.querySelector('[data-feature="game-source"]') || null;
    const suggestions = home?.querySelector('.group\\/home-suggestions') || null;
    const markedShell = home?.querySelector('.dream-skin-home-shell') || null;
    let shell = suggestions?.parentElement?.parentElement || null;
    if (!shell?.contains(feature)) shell = markedShell?.contains(feature) ? markedShell : null;

    if (!shell && home && feature) {
      const homeRect = home.getBoundingClientRect();
      const maxHeight = Math.min(560, Math.max(192, homeRect.height * 0.75));
      const minRailWidth = Math.min(960, homeRect.width * 0.6);
      let relativeShell = null;
      for (let node = feature.parentElement; node && node !== home; node = node.parentElement) {
        const rect = node.getBoundingClientRect();
        const style = getComputedStyle(node);
        if (!relativeShell && style.position === "relative" &&
            rect.width >= minRailWidth && rect.height >= 40 && rect.height <= maxHeight) {
          relativeShell = node;
        }
        if (rect.width >= minRailWidth && rect.height >= 40 && rect.height <= maxHeight) shell = node;
      }
      if (relativeShell) shell = relativeShell;
    }

    const markedHero = home?.querySelector('.dream-skin-home-hero') || null;
    let hero = shell ? [...shell.children].find((node) => node.contains(feature)) || null : null;
    if (!hero && markedHero?.contains(feature)) hero = markedHero;

    let content = shell;
    while (content && content.parentElement !== home) content = content.parentElement;
    if (content?.parentElement !== home) content = null;

    document.querySelectorAll('.dream-skin-home-content').forEach((node) => {
      if (node !== content) node.classList.remove("dream-skin-home-content");
    });
    document.querySelectorAll('.dream-skin-home-shell').forEach((node) => {
      if (node !== shell) node.classList.remove("dream-skin-home-shell");
    });
    document.querySelectorAll('.dream-skin-home-hero').forEach((node) => {
      if (node !== hero) node.classList.remove("dream-skin-home-hero");
    });
    content?.classList.add("dream-skin-home-content");
    shell?.classList.add("dream-skin-home-shell");
    hero?.classList.add("dream-skin-home-hero");
    return { home, content, feature, suggestions, shell, hero };
  };

  const removeLegacyBrandChrome = () => {
    document.getElementById(CHROME_ID)?.remove();
  };

  const ensure = () => {
    if (window[DISABLED_KEY]) return;
    const root = document.documentElement;
    if (!root) return;
    if (!root.classList.contains("codex-dream-skin")) root.classList.add("codex-dream-skin");
    const shell = detectShellMode();
    if (root.getAttribute(SHELL_ATTR) !== shell) root.setAttribute(SHELL_ATTR, shell);
    setStyleProperty(root.style, "--dream-skin-art", `url("${artUrl}")`);
    applyTheme(root);
    ensureStyle(root);
    ensureTabTitles();
    syncComposerSurface();
    syncHomeRoute();
    removeLegacyBrandChrome();
    return shell;
  };

  const scheduler = { raf: 0 };
  const scheduleEnsure = () => {
    if (scheduler.raf || window[DISABLED_KEY]) return;
    scheduler.raf = requestAnimationFrame(() => {
      scheduler.raf = 0;
      ensure();
    });
  };

  const relevantSelector = `#${STYLE_ID}, #${CHROME_ID}, main, aside.app-shell-left-panel, ` +
    '[class~="group/tab"], [data-feature="game-source"], .group\\/home-suggestions, ' +
    '.ProseMirror[contenteditable="true"][role="textbox"]';
  const mutationTouchesShell = (node) => {
    const element = node?.nodeType === Node.ELEMENT_NODE ? node : node?.parentElement;
    if (!element) return false;
    if (element.matches(relevantSelector) || element.querySelector(relevantSelector)) return true;
    return Boolean(element.closest('[class~="group/tab"], [data-feature="game-source"], .group\\/home-suggestions'));
  };
  const observer = new MutationObserver((records) => {
    const relevant = records.some((record) =>
      mutationTouchesShell(record.target) ||
      [...record.addedNodes, ...record.removedNodes].some(mutationTouchesShell));
    if (relevant) scheduleEnsure();
  });
  observer.observe(document.documentElement, { childList: true, subtree: true });
  const resizeHandler = scheduleEnsure;
  window.addEventListener("resize", resizeHandler, { passive: true });
  let mediaQuery = null;
  let mediaHandler = null;
  try {
    mediaQuery = matchMedia("(prefers-color-scheme: dark)");
    mediaHandler = scheduleEnsure;
    mediaQuery.addEventListener("change", mediaHandler);
  } catch {}

  const timer = setInterval(() => {
    if (!window[DISABLED_KEY]) ensure();
  }, 12000);

  const cleanup = () => {
    window[DISABLED_KEY] = true;
    const state = window[STATE_KEY];
    disposeRuntime(state);
    const root = document.documentElement;
    root?.classList.remove("codex-dream-skin", ...HOME_MARKERS);
    root?.removeAttribute(SHELL_ATTR);
    root?.style.removeProperty("--dream-skin-art");
    for (const name of THEME_VARIABLES) root?.style.removeProperty(name);
    document.querySelectorAll(`.${HOME_MARKERS.join(", .")}`).forEach((node) => {
      node.classList.remove(...HOME_MARKERS);
    });
    document.querySelectorAll(`.${COMPOSER_MARKER}`).forEach((node) => {
      node.classList.remove(COMPOSER_MARKER);
    });
    document.querySelectorAll("[data-dream-tab-title]").forEach((node) => node.removeAttribute("data-dream-tab-title"));
    document.getElementById(STYLE_ID)?.remove();
    document.getElementById(CHROME_ID)?.remove();
    delete window[STATE_KEY];
    return true;
  };

  window[STATE_KEY] = {
    ensure,
    cleanup,
    observer,
    timer,
    scheduler,
    resizeHandler,
    mediaQuery,
    mediaHandler,
    artUrl,
    version: VERSION,
    themeId: THEME.id || "custom",
    detectShellMode,
  };
  const shell = ensure();
  return { installed: true, version: VERSION, themeId: THEME.id || "custom", shell };
})(
  __DREAM_SKIN_CSS_JSON__,
  __DREAM_SKIN_ART_JSON__,
  __DREAM_SKIN_THEME_JSON__
)

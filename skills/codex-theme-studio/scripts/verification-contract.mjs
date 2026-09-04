const EXPECTED = {
  version: "1.2.0",
  warmPaper: "#F5F4ED",
  sidebar: "#F5F4ED",
  selected: "#EEECE6",
  panel: "#FAF9F5",
  accent: "#B85235",
  border: "#E5E3D8",
};

const CODEX_RENDERER_TITLES = new Set(["Codex", "ChatGPT"]);

export function isCodexRendererProbe(probe) {
  const markers = probe?.markers ?? {};
  return Boolean(
    probe?.primaryRoute &&
    CODEX_RENDERER_TITLES.has(probe?.title) &&
    markers.root &&
    markers.sidebar &&
    markers.main
  );
}

function visible(box) {
  return Boolean(box?.visible && box.width > 0 && box.height > 0);
}

function rgb(value) {
  if (typeof value !== "string") return null;
  const hex = value.trim().match(/^#([0-9a-f]{6})$/i)?.[1];
  if (hex) return [0, 2, 4].map((offset) => Number.parseInt(hex.slice(offset, offset + 2), 16));
  const functional = value.match(/rgba?\(\s*([\d.]+)[, ]+\s*([\d.]+)[, ]+\s*([\d.]+)/i);
  return functional ? functional.slice(1).map(Number) : null;
}

function sameColor(actual, expected) {
  const left = rgb(actual);
  const right = rgb(expected);
  return Boolean(left && right && left.every((channel, index) => Math.abs(channel - right[index]) <= 2));
}

function transparent(value) {
  if (typeof value !== "string") return false;
  return value === "transparent" || /rgba\([^)]*,\s*0(?:\.0+)?\s*\)$/i.test(value.trim());
}

function expectedHeroHeight(viewportWidth) {
  if (viewportWidth <= 680) return 184;
  if (viewportWidth <= 959) return 208;
  return 224;
}

function expectedCardColumns(viewportWidth, cardCount) {
  if (viewportWidth < 680) return null;
  if (viewportWidth <= 959) return Math.min(2, cardCount);
  return Math.min(4, cardCount);
}

function add(list, condition, reason) {
  if (condition) list.push(reason);
}

function px(value) {
  const parsed = Number.parseFloat(value || "");
  return Number.isFinite(parsed) ? parsed : null;
}

function noShadow(value) {
  return !value || value === "none";
}

export function evaluateSnapshot(snapshot, options = {}) {
  const expectedVersion = options.expectedVersion || EXPECTED.version;
  const theme = options.theme || {};
  const expected = {
    warmPaper: theme.colors?.background || EXPECTED.warmPaper,
    sidebar: theme.colors?.sidebar || theme.colors?.background || EXPECTED.sidebar,
    selected: theme.colors?.selected || EXPECTED.selected,
    panel: theme.colors?.panel || EXPECTED.panel,
    accent: theme.colors?.accent || EXPECTED.accent,
    border: theme.colors?.border || EXPECTED.border,
    bodyWeight: theme.typography?.bodyWeight || 500,
    emphasisWeight: theme.typography?.emphasisWeight || 600,
    composerRadius: theme.shape?.composerRadius ?? 14,
    requiresSerif: /(?:思源宋体|Source Han Serif|(?:^|[,\s"'])serif(?:[,\s"']|$))/i.test(
      theme.typography?.uiFamily || '"思源宋体 VF", "Source Han Serif SC VF", serif',
    ),
  };
  const coreReasons = [];
  const visualReasons = [];
  const degradedReasons = [];

  add(coreReasons, !snapshot || snapshot.schemaVersion !== 1, "unsupported-snapshot");
  if (coreReasons.length) {
    return { pass: false, strictVisualPass: false, degraded: false, reasons: coreReasons, coreReasons, visualReasons, degradedReasons };
  }

  add(coreReasons, !snapshot.installed, "skin-not-installed");
  add(coreReasons, snapshot.version !== expectedVersion, "skin-version-mismatch");
  add(coreReasons, !snapshot.stylePresent, "skin-style-missing");
  add(coreReasons, !visible(snapshot.shell?.main), "main-surface-hidden");
  add(coreReasons, !visible(snapshot.shell?.sidebar), "sidebar-hidden");
  const needsComposer = snapshot.mode === "home" || snapshot.mode === "task";
  if (needsComposer) {
    add(coreReasons, !visible(snapshot.shell?.composer), "composer-hidden");
    add(coreReasons, snapshot.shell?.composer?.inViewport === false, "composer-below-fold");
  }
  add(coreReasons, snapshot.documentOverflow?.x === true, "horizontal-overflow");
  add(visualReasons, !sameColor(snapshot.shell?.mainBackground, expected.warmPaper), "main-not-warm-paper");
  add(visualReasons, !sameColor(snapshot.shell?.sidebarBackground, expected.sidebar), "sidebar-color-mismatch");
  add(visualReasons, Number(snapshot.shell?.topBorderBottomWidth || 0) > 0, "top-divider-visible");
  add(visualReasons, snapshot.chromePresent === true, "legacy-brand-chrome-present");
  const typography = snapshot.shell?.typography;
  add(visualReasons, !typography, "typography-probe-missing");
  if (typography) {
    const baseWeights = [
      ["body", typography.bodyWeight],
      ["sidebar", typography.sidebarWeight],
      ["sidebar-control", typography.sidebarControlWeight],
      ["main-text", typography.mainTextWeight],
    ];
    if (snapshot.mode === "home" || snapshot.mode === "task") {
      baseWeights.push(["composer", typography.composerWeight]);
    }
    for (const [name, weight] of baseWeights) {
      add(visualReasons, !Number.isFinite(weight) || weight < expected.bodyWeight, `typography-${name}-weight`);
    }
    if (snapshot.mode === "task" && expected.requiresSerif) {
      const hanTextCount = typography.conversationHanTextCount;
      const nonSerifHanTextCount = typography.conversationNonSerifHanTextCount;
      add(
        visualReasons,
        !Number.isFinite(hanTextCount) || !Number.isFinite(nonSerifHanTextCount),
        "conversation-font-probe-missing",
      );
      add(
        visualReasons,
        Number.isFinite(nonSerifHanTextCount) && nonSerifHanTextCount > 0,
        "conversation-han-font-family",
      );
    }
    const emphasisWeights = Array.isArray(typography.emphasisWeights) ? typography.emphasisWeights : [];
    emphasisWeights.forEach((weight, index) => {
      add(visualReasons, !Number.isFinite(weight) || weight < expected.emphasisWeight, `typography-emphasis-weight:${index}`);
    });
  }
  const structuralSurfaces = snapshot.shell?.structuralSurfaces;
  add(
    visualReasons,
    snapshot.mode === "system" && (!Array.isArray(structuralSurfaces) || structuralSurfaces.length === 0),
    "structural-surface-probe-missing",
  );
  if (Array.isArray(structuralSurfaces)) {
    structuralSurfaces.forEach((surface, index) => {
      add(visualReasons, !sameColor(surface?.backgroundColor, expected.warmPaper), `structural-surface-color:${index}`);
    });
  }
  const composerVisual = snapshot.shell?.composerVisual || {};
  const composerSurface = composerVisual.surface;
  const composerBody = composerVisual.body;
  const composerBackdrops = Array.isArray(composerVisual.backdrops) ? composerVisual.backdrops : [];
  if (needsComposer) {
    add(visualReasons, !composerSurface || !composerBody, "composer-visual-probe-missing");
    add(visualReasons, !Array.isArray(composerVisual.backdrops), "composer-backing-probe-missing");
  }
  if (needsComposer && composerSurface && composerBody) {
    add(visualReasons, px(composerSurface.borderWidth) !== 0, "composer-native-border-visible");
    add(visualReasons, px(composerSurface.borderRadius) !== expected.composerRadius, "composer-outer-radius");
    add(visualReasons, px(composerBody.borderRadius) !== Math.max(0, expected.composerRadius - 1), "composer-inner-radius");
    add(visualReasons, !sameColor(composerSurface.backgroundColor, expected.panel), "composer-outer-color");
    add(visualReasons, !sameColor(composerBody.backgroundColor, expected.panel), "composer-inner-color");
    add(visualReasons, !noShadow(composerSurface.boxShadow), "composer-outer-frame-shadow");
    add(visualReasons, !noShadow(composerBody.boxShadow), "composer-inner-native-shadow");
    add(visualReasons, composerSurface.position !== "relative", "composer-focus-anchor");
    const outline = composerSurface.after;
    add(visualReasons, !outline, "composer-outline-missing");
    if (outline) {
      const outlineGeometryWrong = outline.position !== "absolute" || px(outline.left) !== 0 ||
        px(outline.top) !== 0 || px(outline.right) !== 0 || px(outline.bottom) !== 0 ||
        px(outline.borderWidth) !== 1 || px(outline.borderRadius) !== expected.composerRadius;
      add(visualReasons, outlineGeometryWrong, "composer-outline-geometry");
      add(visualReasons, !sameColor(outline.borderColor, expected.border), "composer-outline-color");
    }
    if (composerSurface.focusWithin) {
      const indicator = composerSurface.before;
      add(visualReasons, !indicator, "composer-focus-indicator-missing");
      if (indicator) {
        const geometryWrong = indicator.position !== "absolute" || px(indicator.left) !== 0 ||
          px(indicator.top) !== expected.composerRadius || px(indicator.width) !== 3 || px(indicator.height) !== 20;
        add(visualReasons, geometryWrong, "composer-focus-indicator-position");
        add(visualReasons, !sameColor(indicator.backgroundColor, expected.accent), "composer-focus-indicator-color");
      }
    }
  }
  if (needsComposer) {
    composerBackdrops.forEach((backdrop, index) => {
      add(
        visualReasons,
        Boolean(backdrop?.backgroundImage && backdrop.backgroundImage !== "none"),
        `composer-backing-gradient-visible:${index}`,
      );
      add(
        visualReasons,
        !transparent(backdrop?.backgroundColor),
        `composer-backing-color-visible:${index}`,
      );
    });
  }
  const headerTabs = snapshot.shell?.headerTabs || [];
  add(coreReasons, Number(snapshot.shell?.workspaceTabCount || 0) !== headerTabs.length, "header-tab-probe-mismatch");
  add(
    visualReasons,
    Number(snapshot.shell?.workspaceTabCount || 0) > 0 && !transparent(snapshot.shell?.topHeaderBackground),
    "workspace-tabs-occluded-by-main-header",
  );
  for (const [index, tab] of headerTabs.entries()) {
    add(coreReasons, !visible(tab) || !tab.title || (!tab.titleVisible && !tab.titleLayerVisible) || tab.pointerEvents === "none", `header-tab-hidden:${index}`);
  }

  if (snapshot.mode === "home") {
    const home = snapshot.home || {};
    const cards = Array.isArray(home.cards) ? home.cards : [];
    const suggestionsPresent = home.suggestionsPresent !== false;
    add(coreReasons, suggestionsPresent && cards.length === 0, "home-card-count");
    cards.forEach((card, index) => {
      add(coreReasons, !visible(card), `home-card-hidden:${index}`);
      add(
        coreReasons,
        (!card.focusable && !card.disabled) || (card.role !== "button" && card.tagName !== "BUTTON"),
        `home-card-not-focusable:${index}`,
      );
      add(coreReasons, card.clipped === true, `home-card-clipped:${index}`);
      if (home.enhancementHookPresent && suggestionsPresent) {
        add(
          visualReasons,
          card.iconOffset && (Math.abs(card.iconOffset.x) > 1 || Math.abs(card.iconOffset.y) > 1),
          `home-card-icon-off-center:${index}`,
        );
      }
    });

    if (!home.enhancementHookPresent) {
      degradedReasons.push("home-enhancement-hook-missing");
    } else {
      add(visualReasons, !visible(home.hero), "home-hero-hidden");
      add(coreReasons, home.hero?.inViewport === false, "home-hero-below-fold");
      const wantedHeight = expectedHeroHeight(snapshot.viewport?.width || 0);
      add(visualReasons, Math.abs((home.hero?.height || 0) - wantedHeight) > 2, "home-hero-height");
      add(visualReasons, home.hero?.backgroundImage === "none", "home-hero-art-missing");
      add(visualReasons, home.hero?.backgroundSize !== "cover", "home-hero-art-not-full-bleed");
      const wantedColumns = suggestionsPresent ? expectedCardColumns(snapshot.viewport?.width || 0, cards.length) : null;
      if (wantedColumns) add(visualReasons, home.cardColumns !== wantedColumns, "home-card-columns");
    }

    if (home.selectedSession) {
      add(visualReasons, !sameColor(home.selectedSession.backgroundColor, expected.selected), "selected-session-color");
      add(visualReasons, Number(home.selectedSession.borderLeftWidth || 0) > 0, "selected-session-left-rule");
    }
  } else if (snapshot.mode === "task") {
    const task = snapshot.task || {};
    add(visualReasons, task.backgroundImage && task.backgroundImage !== "none", "task-background-art");
    add(visualReasons, task.brandVisible === true, "task-brand-visible");
  } else if (snapshot.mode === "system") {
    const system = snapshot.system || {};
    add(visualReasons, system.backgroundImage && system.backgroundImage !== "none", "system-background-art");
    add(visualReasons, system.brandVisible === true, "system-brand-visible");
  } else {
    coreReasons.push("unknown-route-mode");
  }

  const pass = coreReasons.length === 0;
  const degraded = pass && degradedReasons.length > 0;
  const reasons = [...coreReasons, ...visualReasons, ...degradedReasons];
  return {
    pass,
    strictVisualPass: pass && visualReasons.length === 0 && degradedReasons.length === 0,
    degraded,
    reasons,
    coreReasons,
    visualReasons,
    degradedReasons,
  };
}

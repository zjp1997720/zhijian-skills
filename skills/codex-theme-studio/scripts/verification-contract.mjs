const EXPECTED = {
  version: "1.0.4",
  background: "#F5F3EE",
  sidebar: "#F1F0EC",
  selected: "#E8E6DC",
};

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

export function colorsMatch(actual, expected) {
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
  if (viewportWidth <= 959) return 2;
  return Math.min(4, cardCount);
}

function add(list, condition, reason) {
  if (condition) list.push(reason);
}

export function evaluateSnapshot(snapshot, options = {}) {
  const expectedVersion = options.expectedVersion || EXPECTED.version;
  const expectedArtPlacement = options.expectedArtPlacement === "all" ? "all" : "hero";
  const expectedColors = {
    background: options.expectedColors?.background || EXPECTED.background,
    sidebar: options.expectedColors?.sidebar || EXPECTED.sidebar,
    selected: options.expectedColors?.selected || EXPECTED.selected,
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
  add(coreReasons, !visible(snapshot.shell?.composer), "composer-hidden");
  add(coreReasons, snapshot.documentOverflow?.x === true, "horizontal-overflow");
  add(visualReasons, !colorsMatch(snapshot.shell?.mainBackground, expectedColors.background), "main-background-mismatch");
  add(visualReasons, !colorsMatch(snapshot.shell?.sidebarBackground, expectedColors.sidebar), "sidebar-color-mismatch");
  add(visualReasons, Number(snapshot.shell?.topBorderBottomWidth || 0) > 0, "top-divider-visible");
  add(visualReasons, !snapshot.chromePresent, "brand-chrome-missing");
  add(visualReasons, snapshot.chromePointerEvents !== "none", "brand-chrome-interactive");
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
    add(coreReasons, suggestionsPresent && cards.length !== 4, "home-card-count");
    cards.forEach((card, index) => {
      add(coreReasons, !visible(card), `home-card-hidden:${index}`);
      add(coreReasons, !card.focusable || (card.role !== "button" && card.tagName !== "BUTTON"), `home-card-not-focusable:${index}`);
      add(coreReasons, card.clipped === true, `home-card-clipped:${index}`);
      if (home.enhancementHookPresent && suggestionsPresent) {
        add(
          visualReasons,
          !card.iconOffset || Math.abs(card.iconOffset.x) > 1 || Math.abs(card.iconOffset.y) > 1,
          `home-card-icon-off-center:${index}`,
        );
      }
    });

    if (!home.enhancementHookPresent) {
      degradedReasons.push("home-enhancement-hook-missing");
    } else {
      add(visualReasons, !visible(home.hero), "home-hero-hidden");
      const wantedHeight = expectedHeroHeight(snapshot.viewport?.width || 0);
      add(visualReasons, Math.abs((home.hero?.height || 0) - wantedHeight) > 2, "home-hero-height");
      add(visualReasons, home.hero?.backgroundImage === "none", "home-hero-art-missing");
      add(visualReasons, home.hero?.backgroundSize !== "cover", "home-hero-art-not-full-bleed");
      const wantedColumns = suggestionsPresent ? expectedCardColumns(snapshot.viewport?.width || 0, cards.length) : null;
      if (wantedColumns) add(visualReasons, home.cardColumns !== wantedColumns, "home-card-columns");
    }

    if (home.selectedSession) {
      add(visualReasons, !colorsMatch(home.selectedSession.backgroundColor, expectedColors.selected), "selected-session-color");
      add(visualReasons, Number(home.selectedSession.borderLeftWidth || 0) > 0, "selected-session-left-rule");
    }
  } else if (snapshot.mode === "task") {
    const task = snapshot.task || {};
    if (expectedArtPlacement === "all") {
      add(visualReasons, !task.backgroundImage || task.backgroundImage === "none", "task-background-art-missing");
    } else {
      add(visualReasons, task.backgroundImage && task.backgroundImage !== "none", "task-background-art");
    }
    add(visualReasons, task.brandVisible === true, "task-brand-visible");
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

import { spawnSync } from 'node:child_process';

import {
  buildProbeScript,
  buildVerifyScript,
  parseOpencliJson,
} from './wechat-publish-core.mjs';

export class OpencliError extends Error {
  constructor(message, details = '') {
    super(message);
    this.name = 'OpencliError';
    this.details = details;
  }
}

export function sleep(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

export function runOpencli(profile, session, command, timeoutMs = 30000) {
  const args = ['--profile', profile, 'browser', session, ...command];
  const result = spawnSync('opencli', args, {
    encoding: 'utf8',
    timeout: timeoutMs,
    maxBuffer: 20 * 1024 * 1024,
  });
  if (result.error) throw new OpencliError(result.error.message);
  if (result.status !== 0) {
    throw new OpencliError(`opencli ${command[0]} failed`, result.stderr?.trim() || result.stdout?.trim() || '');
  }
  return result.stdout.trim();
}

export function evaluate(profile, session, script, timeoutMs = 30000) {
  return runOpencli(profile, session, ['eval', script], timeoutMs);
}

export function evaluateJson(profile, session, script, timeoutMs = 30000) {
  return parseOpencliJson(evaluate(profile, session, script, timeoutMs));
}

export function prepareSession(options) {
  if (options.reuseCurrent) {
    let state = '';
    try {
      state = runOpencli(options.profile, options.session, ['state']);
    } catch (error) {
      if (!(error instanceof OpencliError)) throw error;
    }
    if (/^URL:\s+https:\/\/mp\.weixin\.qq\.com/im.test(state)) return state;
    runOpencli(options.profile, options.session, ['bind']);
    const reboundState = runOpencli(options.profile, options.session, ['state']);
    if (!/^URL:\s+https:\/\/mp\.weixin\.qq\.com/im.test(reboundState)) {
      throw new OpencliError('the active Chrome tab is not a WeChat editor');
    }
    return reboundState;
  }
  if (!options.url) throw new OpencliError('editor URL is required unless --reuse-current is used');
  return runOpencli(options.profile, options.session, ['open', options.url]);
}

export async function waitForEditor(options) {
  const deadline = Date.now() + options.timeoutMs;
  while (Date.now() < deadline) {
    try {
      const state = evaluateJson(options.profile, options.session, buildProbeScript());
      if (state.readyState === 'complete' && state.hasBodyEditor) return state;
    } catch (error) {
      if (!(error instanceof OpencliError)) throw error;
    }
    await sleep(500);
  }
  throw new OpencliError(`body editor did not become ready within ${options.timeoutMs}ms`);
}

export async function waitForImageSettlement(options) {
  const deadline = Date.now() + options.timeoutMs;
  let stablePasses = 0;
  let latest = null;
  while (Date.now() < deadline) {
    latest = evaluateJson(options.profile, options.session, buildVerifyScript(options.title));
    if (latest.failedUrls.length > 0) return latest;
    if (latest.pendingImages.length === 0) {
      stablePasses += 1;
      if (stablePasses >= 2) return latest;
    } else {
      stablePasses = 0;
    }
    await sleep(1000);
  }
  if (latest) return latest;
  throw new OpencliError('image verification returned no state');
}

export async function syncCoverFromBody(options) {
  const opened = evaluateJson(options.profile, options.session, `(() => {
    const bodyEditor = document.querySelector(".rich_media_content .ProseMirror") || document.querySelector("#js_editor .ProseMirror");
    const firstImage = bodyEditor?.querySelector("img:not(.ProseMirror-separator)");
    const trigger = document.querySelector("#js_cover_area") || document.querySelector(".js_cover_btn_area");
    if (!firstImage) return JSON.stringify({ ok: false, reason: "body has no cover image" });
    if (!trigger) return JSON.stringify({ ok: false, reason: "cover trigger not found" });
    trigger.click();
    return JSON.stringify({ ok: true });
  })()`);
  if (!opened.ok) throw new OpencliError(opened.reason);
  await sleep(800);
  evaluate(options.profile, options.session, `(() => {
    const option = [...document.querySelectorAll("button,a,li,div,span")]
      .filter((element) => element.children.length === 0 && element.offsetParent !== null)
      .find((element) => /从正文(?:中)?选择/.test((element.textContent || "").trim()));
    if (option) option.click();
    return JSON.stringify({ ok: true, selectedBodySource: Boolean(option) });
  })()`);
  await sleep(1000);
  const selected = evaluateJson(options.profile, options.session, `(() => {
    const dialog = [...document.querySelectorAll("[role=dialog],.weui-desktop-dialog,[class*=dialog]")]
      .find((element) => element.offsetParent !== null);
    const images = dialog ? [...dialog.querySelectorAll("img")] : [];
    const candidate = images.find((image) => image.naturalWidth >= 200 && image.naturalHeight >= 80);
    if (!candidate) return JSON.stringify({ ok: false, reason: "body cover candidate not found" });
    (candidate.closest("label,li,div") || candidate).click();
    return JSON.stringify({ ok: true });
  })()`);
  if (!selected.ok) throw new OpencliError(selected.reason);
  await sleep(500);
  evaluate(options.profile, options.session, `(() => {
    const button = [...document.querySelectorAll("button,a")]
      .find((element) => ["确认", "完成", "下一步"].includes((element.textContent || "").trim()) && element.offsetParent !== null);
    if (button) button.click();
    return JSON.stringify({ ok: true, confirmed: Boolean(button) });
  })()`);
  await sleep(1200);
  const verified = evaluateJson(options.profile, options.session, `(() => {
    const coverArea = document.querySelector("#js_cover_area");
    const styledImage = coverArea
      ? [...coverArea.querySelectorAll("*")].some((element) => /url\\(/.test(element.style.backgroundImage || element.getAttribute("style") || ""))
      : false;
    const hasImage = Boolean(coverArea?.querySelector("img")) || styledImage;
    return JSON.stringify({ ok: hasImage });
  })()`);
  if (!verified.ok) throw new OpencliError('cover selection was not confirmed');
  return verified;
}

export async function saveDraft(options) {
  const result = evaluateJson(options.profile, options.session, `(() => {
    const button = [...document.querySelectorAll("button,a")]
      .find((element) => ["保存为草稿", "保存"].includes((element.textContent || "").trim()) && element.offsetParent !== null);
    if (!button) return JSON.stringify({ ok: false, reason: "save button not found" });
    button.click();
    return JSON.stringify({ ok: true });
  })()`);
  if (!result.ok) throw new OpencliError(result.reason);
  const deadline = Date.now() + options.timeoutMs;
  while (Date.now() < deadline) {
    const state = evaluateJson(options.profile, options.session, `JSON.stringify({
      url: window.location.href,
      saved: (document.body?.innerText || "").includes("已保存"),
      history: [...document.querySelectorAll("#history_pop tr")].slice(1, 3).map((row) => (row.innerText || "").trim())
    })`);
    if (/[?&]appmsgid=\d+/.test(state.url) && (state.saved || state.history.length > 0)) return state;
    await sleep(750);
  }
  throw new OpencliError('draft save was not confirmed');
}

export function redactUrl(url) {
  return url.replace(/([?&]token=)[^&]+/i, '$1[redacted]');
}

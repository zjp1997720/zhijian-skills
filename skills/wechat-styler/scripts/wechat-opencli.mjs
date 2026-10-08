import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
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

function asStringArray(value) {
  return Array.isArray(value) ? value.filter((item) => typeof item === 'string') : [];
}

export function normalizeVerificationState(value) {
  const state = value && typeof value === 'object' ? value : {};
  return {
    ...state,
    failedUrls: asStringArray(state.failedUrls),
    pendingImages: asStringArray(state.pendingImages),
    history: asStringArray(state.history),
    codeBlockCount: Number.isFinite(state.codeBlockCount) ? state.codeBlockCount : 0,
    codeBlockBreakCount: Number.isFinite(state.codeBlockBreakCount) ? state.codeBlockBreakCount : 0,
  };
}

export function normalizeSaveState(value) {
  const state = value && typeof value === 'object' ? value : {};
  const url = typeof state.url === 'string' ? state.url : '';
  const history = asStringArray(state.history);
  const saved = state.saved === true;
  const appmsgid = typeof state.appmsgid === 'string'
    ? state.appmsgid
    : new URL(url || 'https://mp.weixin.qq.com/').searchParams.get('appmsgid') || '';
  const evidence = {
    appmsgid: /^\d+$/.test(appmsgid),
    savedBanner: saved,
    history: history.length > 0,
  };
  return {
    ...state,
    url,
    saved,
    history,
    appmsgid,
    evidence,
    confirmed: evidence.appmsgid && (evidence.savedBanner || evidence.history),
  };
}

export function compareSaveStates(beforeValue, latestValue) {
  const before = normalizeSaveState(beforeValue);
  const latest = normalizeSaveState(latestValue);
  const transition = {
    newAppmsgid: latest.evidence.appmsgid && !before.evidence.appmsgid,
    savedBannerChanged: latest.evidence.savedBanner && !before.evidence.savedBanner,
    historyChanged: latest.evidence.history && latest.history.join('\n') !== before.history.join('\n'),
  };
  return {
    ...latest,
    transition,
    confirmed: transition.newAppmsgid
      || (latest.evidence.appmsgid && (transition.savedBannerChanged || transition.historyChanged)),
  };
}

export function prepareSession(options, run = runOpencli) {
  if (options.reuseCurrent) {
    const probe = () => {
      const state = parseOpencliJson(run(options.profile, options.session,
        ['eval', 'JSON.stringify({url: window.location.href})']));
      let url;
      try { url = new URL(state.url); } catch { return null; }
      const isEditor = url.origin === 'https://mp.weixin.qq.com'
        && url.pathname === '/cgi-bin/appmsg'
        && /^media\/appmsg_edit(?:_v2)?$/.test(url.searchParams.get('t') || '');
      return isEditor ? state : null;
    };
    try {
      const state = probe();
      if (state) return state;
      // A bound non-editor must not silently switch to another user's tab.
      throw new OpencliError('the bound tab is not a WeChat editor');
    } catch (error) {
      // Bind only for an explicitly unbound session, never for permission/policy errors.
      if (!(error instanceof OpencliError)
        || !/no (?:bound |active )?tab|not bound|unbound|session.*not (?:found|initialized)|未绑定/i.test(error.details || error.message)
        || /denied|forbidden|policy|permission|拒绝|权限/i.test(`${error.message} ${error.details}`)) throw error;
    }
    run(options.profile, options.session, ['bind']);
    const rebound = probe();
    if (!rebound) throw new OpencliError('the active Chrome tab is not a WeChat editor');
    return rebound;
  }
  if (!options.url) throw new OpencliError('editor URL is required unless --reuse-current is used');
  return run(options.profile, options.session, ['open', options.url]);
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
  let lastError = null;
  while (Date.now() < deadline) {
    try {
      latest = normalizeVerificationState(
        evaluateJson(options.profile, options.session, buildVerifyScript(options.title)),
      );
      lastError = null;
      if (latest.failedUrls.length > 0) return latest;
      if (latest.ok !== false && latest.pendingImages.length === 0) {
        stablePasses += 1;
        if (stablePasses >= 2) return latest;
      } else {
        stablePasses = 0;
      }
    } catch (error) {
      if (!(error instanceof OpencliError)) throw error;
      lastError = error;
      stablePasses = 0;
    }
    await sleep(1000);
  }
  if (latest) return { ...latest, settlementTimedOut: true };
  throw new OpencliError('image verification returned no state', lastError?.details || lastError?.message || '');
}

const coverStateScript = `(() => {
  const coverArea = document.querySelector("#js_cover_area") || document.querySelector(".js_cover_btn_area");
  if (!coverArea) return JSON.stringify({ ok: false, hasImage: false, reason: "cover area not found" });
  const sources = [...coverArea.querySelectorAll("img,[style*='background']")]
    .flatMap((element) => {
      const values = [element.currentSrc || element.src || "", element.style?.backgroundImage || ""];
      return values.flatMap((value) => value.match(/(?:https?:|blob:|data:image)[^\"')]+/g) || []);
    });
  return JSON.stringify({ ok: true, hasImage: sources.length > 0, sources });
})()`;

function getCoverState(options) {
  return evaluateJson(options.profile, options.session, coverStateScript);
}

async function openCoverPicker(options) {
  const opened = evaluateJson(options.profile, options.session, `(() => {
    const bodyEditor = document.querySelector(".rich_media_content .ProseMirror") || document.querySelector("#js_editor .ProseMirror");
    const firstImage = [...(bodyEditor?.querySelectorAll("img:not(.ProseMirror-separator)") || [])].find((img) =>
      !img.closest('[data-wechat-cta]') && !img.hasAttribute('data-wechat-cta-image') &&
      !/zhijian-cta-(opening|ending)-/.test(img.currentSrc || img.src || '') &&
      !/^(关注大鹏，把 AI 用进真实工作|有用，就留一份：点赞、收藏、转给需要的人)$/.test(img.alt || '')
    );
    const trigger = document.querySelector("#js_cover_area") || document.querySelector(".js_cover_btn_area");
    if (!trigger) return JSON.stringify({ ok: false, reason: "cover trigger not found" });
    trigger.click();
    return JSON.stringify({
      ok: true,
      hasBodyImage: Boolean(firstImage),
      bodyImageSrc: firstImage ? (firstImage.currentSrc || firstImage.src || "") : ""
    });
  })()`);
  if (!opened.ok) throw new OpencliError(opened.reason);
  await sleep(600);
  return opened;
}

function choosePickerSource(options, source) {
  const pattern = source === 'body'
    ? '从正文(?:中)?选择'
    : '从(?:图片|素材)库选择|图片库|素材库|上传图片';
  return evaluateJson(options.profile, options.session, `(() => {
    const option = [...document.querySelectorAll("button,a,li,div,span")]
      .filter((element) => element.children.length === 0 && element.offsetParent !== null)
      .find((element) => new RegExp(${JSON.stringify(pattern)}).test((element.textContent || "").trim()));
    if (option) option.click();
    return JSON.stringify({ ok: true, selected: Boolean(option) });
  })()`);
}

function selectVisibleCoverCandidate(options, expectedSource) {
  return evaluateJson(options.profile, options.session, `(() => {
    const dialog = [...document.querySelectorAll("[role=dialog],.weui-desktop-dialog,[class*=dialog]")]
      .find((element) => element.offsetParent !== null);
    if (!dialog) return JSON.stringify({ ok: false, reason: "cover dialog not found" });
    const expectedSource = ${JSON.stringify(expectedSource || '')};
    const sourceMatches = (value) => {
      if (!value || !expectedSource) return false;
      try {
        const actual = new URL(value, window.location.href);
        const expected = new URL(expectedSource, window.location.href);
        return actual.href === expected.href || actual.pathname === expected.pathname;
      } catch { return value.includes(expectedSource) || expectedSource.includes(value); }
    };
    const media = [...dialog.querySelectorAll("img,[style*='background-image']")]
      .filter((candidate) => candidate.offsetParent !== null)
      .map((candidate) => ({
        element: candidate,
        source: candidate.currentSrc || candidate.src
          || (candidate.style?.backgroundImage || "").match(/(?:https?:|blob:|data:image)[^\"')]+/)?.[0]
          || ""
      }));
    const matched = media.find((candidate) => sourceMatches(candidate.source));
    const bodySpecificDialog = /从正文|正文图片|视频封面/.test((dialog.innerText || "").trim());
    const fallback = bodySpecificDialog
      ? media.find((candidate) => candidate.element.matches("[style*='background-image']")
        || candidate.element.naturalWidth >= 160
        || candidate.element.naturalHeight >= 60)
      : null;
    const candidate = matched || fallback;
    if (!candidate) return JSON.stringify({ ok: false, reason: "body cover candidate not found" });
    const element = candidate.element;
    (element.closest(".weui-desktop-img-picker__item,label,li") || element).click();
    return JSON.stringify({
      ok: true,
      kind: matched ? "matched-body-image" : element.matches("img") ? "body-image" : "body-background"
    });
  })()`);
}

function coverChanged(cover, previousSources = []) {
  if (!cover.hasImage) return false;
  if (previousSources.length === 0) return true;
  return cover.sources.some((source) => !previousSources.includes(source));
}

const coverDialogLookup = `
  const dialogs = [...document.querySelectorAll("mp-image-product-dialog,[role=dialog],.weui-desktop-dialog,[class*=dialog]")]
    .filter((element) => element.getClientRects().length > 0);
  const visibleButtons = (dialog) => [...dialog.querySelectorAll("button,a")]
    .filter((element) => element.getClientRects().length > 0 && !element.disabled
      && element.getAttribute("aria-disabled") !== "true");
  const cropDialog = [...dialogs].reverse().find((dialog) =>
    /编辑封面|裁剪封面|裁剪图片/.test(dialog.innerText || "")
    && (/2\\.35\\s*[:：]\\s*1|1\\s*[:：]\\s*1/.test(dialog.innerText || "")
      || dialog.querySelector("[class*=crop],canvas,img"))
    && visibleButtons(dialog).some((button) => ["确认", "完成"].includes((button.textContent || "").trim())));
`;

export function buildCoverUploadSelectionScript(filename) {
  return `(() => {
${coverDialogLookup}
    const filename = ${JSON.stringify(filename)};
    // Upload may bypass the library and open the crop dialog immediately.
    if (cropDialog) return JSON.stringify({ ok: true, stage: "crop", filename });
    const dialog = [...dialogs].reverse().find((element) =>
      element.querySelector(".weui-desktop-img-picker__img-title,.weui-desktop-img-picker__item"));
    const title = [...(dialog?.querySelectorAll(".weui-desktop-img-picker__img-title,strong,[title]") || [])]
      .filter((element) => element.getClientRects().length > 0)
      .find((element) => {
        const value = (element.textContent || element.getAttribute("title") || "").trim();
        return value === filename || value === filename.replace(/-wechat(?=\\.jpg$)/, "");
      });
    const item = title?.closest(".weui-desktop-img-picker__item,label,li");
    if (item) item.click();
    return JSON.stringify({ ok: Boolean(item), stage: item ? "library" : "waiting", filename });
  })()`;
}

export function buildAdvanceCoverScript() {
  return `(() => {
${coverDialogLookup}
    const labels = ["下一步", "确认", "完成"];
    const dialog = cropDialog || [...dialogs].reverse().find((element) =>
      /封面|图片|素材/.test(element.innerText || "")
      && visibleButtons(element).some((button) => labels.includes((button.textContent || "").trim())));
    const button = dialog && visibleButtons(dialog)
      .find((element) => labels.includes((element.textContent || "").trim()));
    if (button) button.click();
    return JSON.stringify({ ok: true, clicked: button ? (button.textContent || "").trim() : "" });
  })()`;
}

async function advanceCoverFlow(options, previousSources = []) {
  for (let step = 0; step < 5; step += 1) {
    const cover = getCoverState(options);
    if (coverChanged(cover, previousSources)) return cover;
    const action = evaluateJson(options.profile, options.session, buildAdvanceCoverScript());
    if (!action.clicked) break;
    await sleep(800);
  }
  return getCoverState(options);
}

function dismissCoverDialog(options) {
  return evaluateJson(options.profile, options.session, `(() => {
    const dialogs = [...document.querySelectorAll("[role=dialog],.weui-desktop-dialog,[class*=dialog]")]
      .filter((element) => element.offsetParent !== null);
    const dialog = dialogs.at(-1);
    if (!dialog) return JSON.stringify({ ok: true, closed: false });
    const close = [...dialog.querySelectorAll("button,a")]
      .find((element) => ["取消", "关闭"].includes((element.textContent || "").trim()))
      || dialog.querySelector("[aria-label='关闭'],[aria-label='close'],.weui-desktop-icon-btn__close");
    if (close) close.click();
    return JSON.stringify({ ok: true, closed: Boolean(close) });
  })()`);
}

function coverMimeType(filePath) {
  const extension = path.extname(filePath).toLowerCase();
  if (extension === '.png') return 'image/png';
  if (extension === '.webp') return 'image/webp';
  if (extension === '.gif') return 'image/gif';
  return 'image/jpeg';
}

function prepareCoverPayload(filePath) {
  const absolutePath = path.resolve(filePath);
  if (!fs.existsSync(absolutePath)) throw new OpencliError(`cover file not found: ${absolutePath}`);
  const stats = fs.statSync(absolutePath);
  if (!stats.isFile()) throw new OpencliError(`cover path is not a file: ${absolutePath}`);

  let uploadPath = absolutePath;
  let workDir = '';
  if (stats.size > 180 * 1024 && process.platform === 'darwin') {
    workDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wechat-cover-'));
    uploadPath = path.join(workDir, `${path.parse(absolutePath).name}-wechat.jpg`);
    const optimized = spawnSync('sips', [
      '-s', 'format', 'jpeg', '-s', 'formatOptions', '78', '-Z', '1600',
      absolutePath, '--out', uploadPath,
    ], { encoding: 'utf8' });
    if (optimized.status !== 0) {
      fs.rmSync(workDir, { recursive: true, force: true });
      throw new OpencliError('cover optimization failed', optimized.stderr?.trim() || optimized.stdout?.trim() || '');
    }
  }
  const bytes = fs.readFileSync(uploadPath);
  if (bytes.length > 600 * 1024) {
    if (workDir) fs.rmSync(workDir, { recursive: true, force: true });
    throw new OpencliError('cover file is too large for the reliable upload fallback', 'compress it below 600 KB and retry');
  }
  return {
    base64: bytes.toString('base64'),
    filename: path.basename(uploadPath),
    mimeType: coverMimeType(uploadPath),
    cleanup: () => {
      if (workDir) fs.rmSync(workDir, { recursive: true, force: true });
    },
  };
}

async function uploadCoverFile(options, filePath, previousSources = []) {
  dismissCoverDialog(options);
  await sleep(400);
  await openCoverPicker(options);
  choosePickerSource(options, 'library');
  await sleep(700);

  const payload = prepareCoverPayload(filePath);
  try {
    const uploaded = evaluateJson(options.profile, options.session, `(() => {
      const dialogs = [...document.querySelectorAll("[role=dialog],.weui-desktop-dialog,[class*=dialog]")]
        .filter((element) => element.offsetParent !== null);
      const dialog = dialogs.at(-1);
      const inputs = [...document.querySelectorAll("input[type=file]")]
        .filter((input) => !input.accept || /image/i.test(input.accept));
      const input = inputs.find((candidate) => dialog?.contains(candidate)) || inputs.at(-1);
      if (!input) return JSON.stringify({ ok: false, reason: "image-library file input not found" });
      const binary = atob(${JSON.stringify(payload.base64)});
      const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
      const file = new File([bytes], ${JSON.stringify(payload.filename)}, { type: ${JSON.stringify(payload.mimeType)} });
      const transfer = new DataTransfer();
      transfer.items.add(file);
      input.files = transfer.files;
      input.dispatchEvent(new Event("change", { bubbles: true }));
      return JSON.stringify({ ok: true, filename: file.name, bytes: file.size });
    })()`, 60000);
    if (!uploaded.ok) throw new OpencliError(uploaded.reason);

    const deadline = Date.now() + (options.timeoutMs || 30000);
    while (Date.now() < deadline) {
      const currentCover = getCoverState(options);
      if (coverChanged(currentCover, previousSources)) {
        return { ...currentCover, strategy: 'uploaded-file', filename: payload.filename };
      }
      const selected = evaluateJson(options.profile, options.session,
        buildCoverUploadSelectionScript(payload.filename));
      if (selected.ok) {
        const cover = await advanceCoverFlow(options, previousSources);
        if (coverChanged(cover, previousSources)) {
          return { ...cover, strategy: 'uploaded-file', filename: payload.filename };
        }
      }
      await sleep(750);
    }
    throw new OpencliError('uploaded cover did not become selectable in the image library', `filename: ${payload.filename}`);
  } finally {
    payload.cleanup();
  }
}

export async function syncCoverFromBody(options) {
  const existing = getCoverState(options);
  if (existing.hasImage && !options.coverFile) return { ...existing, strategy: 'existing-cover' };
  if (existing.hasImage && options.coverFile) {
    return await uploadCoverFile(options, options.coverFile, existing.sources || []);
  }

  const opened = await openCoverPicker(options);
  let bodyFailure = opened.hasBodyImage ? '' : 'body has no cover image';
  if (opened.hasBodyImage) {
    choosePickerSource(options, 'body');
    await sleep(900);
    const selected = selectVisibleCoverCandidate(options, opened.bodyImageSrc);
    if (selected.ok) {
      await sleep(400);
      const cover = await advanceCoverFlow(options);
      if (cover.hasImage) return { ...cover, strategy: 'body-image', candidateKind: selected.kind };
      bodyFailure = 'cover selection was not confirmed';
    } else {
      bodyFailure = selected.reason || 'body cover candidate not found';
    }
  }

  if (options.coverFile) return await uploadCoverFile(options, options.coverFile);
  throw new OpencliError(
    bodyFailure || 'body cover selection failed',
    'retry with --cover-file <local 2.35:1 image> to use the image-library upload fallback',
  );
}

export async function saveDraft(options) {
  const result = evaluateJson(options.profile, options.session, `(() => {
    const button = [...document.querySelectorAll("button,a")]
      .find((element) => ["保存为草稿", "保存"].includes((element.textContent || "").trim()) && element.offsetParent !== null);
    if (!button) return JSON.stringify({ ok: false, reason: "save button not found" });
    const before = {
      url: window.location.href,
      saved: (document.body?.innerText || "").includes("已保存"),
      history: [...document.querySelectorAll("#history_pop tr")].slice(1, 4).map((row) => (row.innerText || "").trim()).filter(Boolean),
      appmsgid: new URL(window.location.href).searchParams.get("appmsgid") || ""
    };
    button.click();
    return JSON.stringify({ ok: true, before });
  })()`);
  if (!result.ok) throw new OpencliError(result.reason);
  const before = normalizeSaveState(result.before);
  const deadline = Date.now() + options.timeoutMs;
  let latest = normalizeSaveState({});
  while (Date.now() < deadline) {
    latest = normalizeSaveState(evaluateJson(options.profile, options.session, `JSON.stringify({
      url: window.location.href,
      saved: (document.body?.innerText || "").includes("已保存"),
      history: [...document.querySelectorAll("#history_pop tr")].slice(1, 4).map((row) => (row.innerText || "").trim()).filter(Boolean),
      appmsgid: new URL(window.location.href).searchParams.get("appmsgid") || ""
    })`));
    const compared = compareSaveStates(before, latest);
    if (compared.confirmed) return compared;
    await sleep(750);
  }
  throw new OpencliError(
    'draft save was not confirmed',
    `appmsgid=${latest.evidence.appmsgid}; savedBanner=${latest.evidence.savedBanner}; history=${latest.history.length}`,
  );
}

export function redactUrl(url) {
  return url.replace(/([?&]token=)[^&]+/i, '$1[redacted]');
}

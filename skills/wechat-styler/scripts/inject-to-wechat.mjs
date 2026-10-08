#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

import { optimizeContentImages } from './wechat-image-pipeline.mjs';
import {
  buildInjectScript,
  buildInjectScripts,
  buildMetadataScript,
  buildMetadataVerification,
  buildVerifyScript,
  extractArticleDocument,
} from './wechat-publish-core.mjs';
import {
  OpencliError,
  evaluateJson,
  normalizeVerificationState,
  prepareSession,
  redactUrl,
  saveDraft,
  syncCoverFromBody,
  waitForEditor,
  waitForImageSettlement,
} from './wechat-opencli.mjs';

function printUsage() {
  console.log(`Usage: node scripts/inject-to-wechat.mjs <article.html> [options]

Options:
  --profile <name>          opencli profile
  --url <url>               WeChat editor URL
  --session <name>          opencli session (default: work)
  --reuse-current           use the already-open editor tab
  --title <text>            article title; existing title is preserved when omitted
  --summary <text>          article summary; existing summary is preserved when omitted
  --author <text>           article author; existing author is preserved when omitted
  --sync-cover-from-body    use the first body image as the WeChat cover
  --cover-file <path>       upload this local image; replace an existing cover when present
  --save-draft              save and verify the draft after injection
  --verify-only             inspect the current editor without writing
  --no-optimize-images      disable oversized-image optimization
  --max-image-bytes <n>     optimize remote images larger than n bytes
  --max-image-width <n>     resize optimized images to this width
  --image-timeout <ms>      image transfer settlement timeout
  --editor-timeout <ms>     editor readiness timeout
  --report <path>           write a JSON verification report
  -h, --help                show help`);
}

function parseArgs(argv) {
  const options = {
    input: '',
    profile: process.env.OPENCLI_PROFILE || '',
    url: process.env.WX_EDITOR_URL || '',
    session: 'work',
    reuseCurrent: false,
    title: undefined,
    summary: undefined,
    author: undefined,
    syncCoverFromBody: false,
    coverFile: '',
    saveDraft: false,
    verifyOnly: false,
    optimizeImages: true,
    maxImageBytes: 2 * 1024 * 1024,
    maxImageWidth: 1920,
    imageTimeoutMs: 60000,
    editorTimeoutMs: 30000,
    report: '',
  };
  const valueOptions = new Set([
    '--profile', '--url', '--session', '--title', '--summary', '--author', '--cover-file',
    '--max-image-bytes', '--max-image-width', '--image-timeout',
    '--editor-timeout', '--report',
  ]);
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === '--help' || argument === '-h') return { ...options, help: true };
    if (!argument.startsWith('--')) {
      options.input = argument;
      continue;
    }
    if (valueOptions.has(argument) && argv[index + 1] === undefined) {
      throw new Error(`missing value for ${argument}`);
    }
    if (argument === '--profile') options.profile = argv[++index];
    else if (argument === '--url') options.url = argv[++index];
    else if (argument === '--session') options.session = argv[++index];
    else if (argument === '--title') options.title = argv[++index];
    else if (argument === '--summary') options.summary = argv[++index];
    else if (argument === '--author') options.author = argv[++index];
    else if (argument === '--cover-file') options.coverFile = argv[++index];
    else if (argument === '--max-image-bytes') options.maxImageBytes = Number(argv[++index]);
    else if (argument === '--max-image-width') options.maxImageWidth = Number(argv[++index]);
    else if (argument === '--image-timeout') options.imageTimeoutMs = Number(argv[++index]);
    else if (argument === '--editor-timeout') options.editorTimeoutMs = Number(argv[++index]);
    else if (argument === '--report') options.report = argv[++index];
    else if (argument === '--reuse-current') options.reuseCurrent = true;
    else if (argument === '--save-draft') options.saveDraft = true;
    else if (argument === '--sync-cover-from-body') options.syncCoverFromBody = true;
    else if (argument === '--verify-only') options.verifyOnly = true;
    else if (argument === '--no-optimize-images') options.optimizeImages = false;
    else throw new Error(`unknown option: ${argument}`);
  }
  if (options.coverFile) options.syncCoverFromBody = true;
  return options;
}

function assertFinitePositive(value, name) {
  if (!Number.isFinite(value) || value <= 0) throw new Error(`${name} must be a positive number`);
}

function assertOptions(options) {
  if (!options.input) throw new Error('HTML input file is required');
  if (!fs.existsSync(options.input)) throw new Error(`HTML file not found: ${options.input}`);
  if (!options.profile) throw new Error('--profile or OPENCLI_PROFILE is required');
  if (options.coverFile && !fs.existsSync(options.coverFile)) throw new Error(`cover file not found: ${options.coverFile}`);
  if (!options.reuseCurrent && !options.url) throw new Error('--url is required unless --reuse-current is used');
  assertFinitePositive(options.maxImageBytes, '--max-image-bytes');
  assertFinitePositive(options.maxImageWidth, '--max-image-width');
  assertFinitePositive(options.imageTimeoutMs, '--image-timeout');
  assertFinitePositive(options.editorTimeoutMs, '--editor-timeout');
}

function writeReport(reportPath, report) {
  if (!reportPath) return;
  const absolutePath = path.resolve(reportPath);
  fs.mkdirSync(path.dirname(absolutePath), { recursive: true });
  fs.writeFileSync(absolutePath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
}

function sanitizeLiveState(value) {
  if (!value || typeof value !== 'object') return null;
  return { ...value, url: redactUrl(typeof value.url === 'string' ? value.url : '') };
}

function redactText(value) {
  return String(value || '').replace(/([?&]token=)[^&\s]+/gi, '$1[redacted]');
}

function recoveryForPhase(phase, error, options) {
  if (phase === 'validate-input') {
    return [
      'Use the publishing-candidate HTML whose body images have absolute http(s) URLs.',
      'Keep the relative-path HTML for local preview only; do not inject it into the WeChat editor.',
    ];
  }
  if (phase === 'cover') {
    const message = `${error instanceof Error ? error.message : ''} ${error instanceof OpencliError ? error.details : ''}`;
    if (/too large|compress|optimization failed/i.test(message)) {
      return [
        'Compress the local cover below 600 KB, keep a 2.35:1 ratio, and rerun the same command.',
        'On macOS, verify that sips is available if automatic JPEG optimization failed.',
      ];
    }
    if (/file input|image library|selectable/i.test(message) && options?.coverFile) {
      return [
        'Close any stale WeChat cover dialog, reopen the image library, and rerun with the same --cover-file.',
        'If the uploaded filename is already visible in the library, select it manually and run --verify-only.',
      ];
    }
    return [
      'Pass --cover-file <local 2.35:1 image> so the injector can upload through the image library.',
      'If a cover is already visible, rerun with --reuse-current --verify-only to confirm the draft state.',
    ];
  }
  if (phase === 'save-draft' || phase === 'verify-saved-draft') {
    return [
      'Check that the editor URL contains appmsgid and that a manual-save row appears in the history panel.',
      'Rerun with --reuse-current --verify-only --report <path>; this performs a read-only inspection.',
    ];
  }
  if (phase.includes('image') || phase === 'inject-body' || phase === 'verify-content') {
    const message = error instanceof Error ? error.message : '';
    if (/ffmpeg|animated GIF/i.test(message)) {
      return [
        'Install ffmpeg so the injector can preserve and compress oversized animated GIFs, then rerun the same command.',
        'If the GIF still exceeds the configured limit, replace it or raise --max-image-bytes deliberately.',
      ];
    }
    return [
      'Inspect live.failedUrls and live.pendingImages in the report; qlogo/qpic URLs are already treated as settled.',
      'Retry with the default image optimization enabled, or replace the listed external image URLs.',
    ];
  }
  return [
    'Confirm opencli doctor passes and the active Chrome tab is a WeChat article editor.',
    'Rerun with --reuse-current --verify-only --report <path> before making another write attempt.',
  ];
}

function assertLiveState(state, expected, metadata) {
  state = normalizeVerificationState(state);
  const failures = [];
  if (!state.ok) failures.push(state.reason || 'live verification failed');
  if (state.svgCount !== expected.svgCount) failures.push(`SVG count ${state.svgCount}/${expected.svgCount}`);
  if (state.animateCount !== expected.animateCount) failures.push(`animation count ${state.animateCount}/${expected.animateCount}`);
  if (expected.xiaolanNativeFrameCount > 0) {
    if (state.svgImageCount !== 0) failures.push(`Xiaolan SVG image nodes ${state.svgImageCount}/0`);
    if (state.xiaolanNativeFrameCount !== expected.xiaolanNativeFrameCount) {
      failures.push(`Xiaolan native frames ${state.xiaolanNativeFrameCount}/${expected.xiaolanNativeFrameCount}`);
    }
    if (!(state.svgPathCount > 0)) failures.push('Xiaolan native SVG paths are missing');
  }
  if (state.imageCount !== expected.imageUrls.length) failures.push(`image count ${state.imageCount}/${expected.imageUrls.length}`);
  if (state.codeBlockCount !== expected.codeBlockCount) {
    failures.push(`code block count ${state.codeBlockCount}/${expected.codeBlockCount}`);
  }
  if (state.codeBlockBreakCount !== expected.codeBlockBreakCount) {
    failures.push(`code block hard breaks ${state.codeBlockBreakCount}/${expected.codeBlockBreakCount}`);
  }
  if (state.failedUrls.length > 0) failures.push(`${state.failedUrls.length} image transfers failed`);
  if (state.pendingImages.length > 0) failures.push(`${state.pendingImages.length} images are still pending`);
  if (metadata.title !== undefined && state.title !== metadata.title) failures.push('title did not persist');
  if (buildMetadataVerification(state, metadata).summaryMatches === false) failures.push('summary did not persist');
  if (failures.length > 0) throw new Error(failures.join('; '));
}

async function injectAndSettle(options, content, title) {
  const scripts = buildInjectScripts(content);
  let injected = null;
  for (const script of scripts) {
    injected = evaluateJson(options.profile, options.session, script, 60000);
    if (!injected?.ok) break;
  }
  if (!injected?.ok) throw new Error(injected?.reason || 'body injection failed');
  if (injected.chunkCount > 1) {
    console.log(`  正文分段注入: ${injected.chunkCount} 段`);
  }
  return await waitForImageSettlement({
    profile: options.profile,
    session: options.session,
    timeoutMs: options.imageTimeoutMs,
    title,
  });
}

const runtime = {
  options: null,
  phase: 'parse-options',
  sessionReady: false,
  liveState: null,
  metadata: {},
};

async function main() {
  const options = parseArgs(process.argv.slice(2));
  runtime.options = options;
  if (options.help) {
    printUsage();
    return;
  }
  assertOptions(options);
  const sourceHtml = fs.readFileSync(options.input, 'utf8');
  const documentInfo = extractArticleDocument(sourceHtml);
  runtime.phase = 'validate-input';
  if (!options.verifyOnly && documentInfo.nonHttpImageUrls.length > 0) {
    throw new Error(
      `HTML contains ${documentInfo.nonHttpImageUrls.length} non-HTTP image source(s); use a publishing-candidate HTML with absolute image URLs`,
    );
  }
  const metadata = {
    title: options.title ?? (documentInfo.title || undefined),
    summary: options.summary ?? (documentInfo.summary || undefined),
    author: options.author,
  };

  runtime.metadata = metadata;
  runtime.phase = 'prepare-session';
  prepareSession(options);
  runtime.sessionReady = true;
  runtime.phase = 'wait-editor';
  await waitForEditor({
    profile: options.profile,
    session: options.session,
    timeoutMs: options.editorTimeoutMs,
  });

  if (options.verifyOnly) {
    runtime.phase = 'verify-only';
    const liveState = normalizeVerificationState(
      evaluateJson(options.profile, options.session, buildVerifyScript(metadata.title || '')),
    );
    runtime.liveState = liveState;
    const verification = buildMetadataVerification(liveState, metadata);
    const report = { mode: 'verify-only', phase: 'complete', verification, live: sanitizeLiveState(liveState) };
    if (verification.summaryMatches === false) process.exitCode = 1;
    writeReport(options.report, report);
    console.log(JSON.stringify(report, null, 2));
    return;
  }

  let content = documentInfo.content;
  const optimizedMappings = [];
  if (options.optimizeImages) {
    runtime.phase = 'optimize-images';
    const optimized = await optimizeContentImages(content, {
      maxBytes: options.maxImageBytes,
      maxWidth: options.maxImageWidth,
      timeoutMs: options.imageTimeoutMs,
    });
    content = optimized.content;
    optimizedMappings.push(...optimized.mapping.entries());
  }

  runtime.phase = 'inject-body';
  let liveState = await injectAndSettle(options, content, metadata.title || '');
  runtime.liveState = liveState;
  if (liveState.failedUrls.length > 0 && options.optimizeImages) {
    runtime.phase = 'retry-images';
    const retry = await optimizeContentImages(content, {
      forceUrls: liveState.failedUrls,
      maxBytes: options.maxImageBytes,
      maxWidth: options.maxImageWidth,
      timeoutMs: options.imageTimeoutMs,
    });
    if (retry.mapping.size === 0) throw new Error('failed images could not be optimized for retry');
    content = retry.content;
    optimizedMappings.push(...retry.mapping.entries());
    liveState = await injectAndSettle(options, content, metadata.title || '');
    runtime.liveState = liveState;
  }

  runtime.phase = 'metadata';
  evaluateJson(options.profile, options.session, buildMetadataScript(metadata));
  let coverState = null;
  if (options.syncCoverFromBody) {
    runtime.phase = 'cover';
    coverState = await syncCoverFromBody({
      profile: options.profile,
      session: options.session,
      timeoutMs: options.imageTimeoutMs,
      coverFile: options.coverFile,
    });
  }

  runtime.phase = 'verify-content';
  liveState = await waitForImageSettlement({
    profile: options.profile,
    session: options.session,
    timeoutMs: options.imageTimeoutMs,
    title: metadata.title || '',
  });
  runtime.liveState = liveState;
  const expected = extractArticleDocument(`<body>${content}</body>`);
  assertLiveState(liveState, expected, metadata);

  let saveState = null;
  if (options.saveDraft) {
    runtime.phase = 'save-draft';
    saveState = await saveDraft({
      profile: options.profile,
      session: options.session,
      timeoutMs: options.editorTimeoutMs,
    });
    runtime.phase = 'verify-saved-draft';
    liveState = normalizeVerificationState(
      evaluateJson(options.profile, options.session, buildVerifyScript(metadata.title || '')),
    );
    runtime.liveState = liveState;
    assertLiveState(liveState, expected, metadata);
  }

  runtime.phase = 'complete';
  const report = {
    mode: options.saveDraft ? 'saved-draft' : 'injected',
    phase: 'complete',
    optimizedImages: optimizedMappings.length,
    expected: {
      images: expected.imageUrls.length,
      svg: expected.svgCount,
      animations: expected.animateCount,
      xiaolanNativeFrames: expected.xiaolanNativeFrameCount,
      codeBlocks: expected.codeBlockCount,
      codeBlockHardBreaks: expected.codeBlockBreakCount,
    },
    cover: coverState,
    verification: buildMetadataVerification(liveState, runtime.metadata),
    live: sanitizeLiveState(liveState),
    save: saveState ? sanitizeLiveState(saveState) : null,
  };
  writeReport(options.report, report);
  console.log(JSON.stringify(report, null, 2));
}

main().catch((error) => {
  const options = runtime.options;
  let liveState = runtime.liveState;
  if (!liveState && runtime.sessionReady && options) {
    try {
      liveState = normalizeVerificationState(
        evaluateJson(options.profile, options.session, buildVerifyScript(options.title || '')),
      );
    } catch {
      liveState = null;
    }
  }
  const errorReport = {
    mode: 'failed',
    phase: runtime.phase,
    error: {
      name: error instanceof Error ? error.name : 'UnknownError',
      message: redactText(error instanceof Error ? error.message : 'unknown error'),
      details: redactText(error instanceof OpencliError ? error.details : ''),
    },
    recovery: recoveryForPhase(runtime.phase, error, options),
    verification: buildMetadataVerification(liveState, runtime.metadata),
    live: sanitizeLiveState(liveState),
  };
  if (options?.report) {
    try {
      writeReport(options.report, errorReport);
    } catch (reportError) {
      console.error(`wechat failure report could not be written: ${reportError.message}`);
    }
  }
  if (error instanceof OpencliError) {
    console.error(`wechat injection failed: ${error.message}`);
    if (error.details) console.error(error.details.replace(/([?&]token=)[^&\s]+/gi, '$1[redacted]'));
  } else if (error instanceof Error) {
    console.error(`wechat injection failed: ${error.message}`);
  } else {
    console.error('wechat injection failed with an unknown error');
  }
  console.error(`failed phase: ${runtime.phase}`);
  console.error(`recovery: ${errorReport.recovery.join(' ')}`);
  process.exitCode = 1;
});

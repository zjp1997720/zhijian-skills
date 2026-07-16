#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

import { optimizeContentImages } from './wechat-image-pipeline.mjs';
import {
  buildInjectScript,
  buildMetadataScript,
  buildVerifyScript,
  extractArticleDocument,
} from './wechat-publish-core.mjs';
import {
  OpencliError,
  evaluateJson,
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
    profile: process.env.OPENCLI_PROFILE || '4nwbtdn6',
    url: process.env.WX_EDITOR_URL || '',
    session: 'work',
    reuseCurrent: false,
    title: undefined,
    summary: undefined,
    author: undefined,
    syncCoverFromBody: false,
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
    '--profile', '--url', '--session', '--title', '--summary', '--author',
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
  return options;
}

function assertFinitePositive(value, name) {
  if (!Number.isFinite(value) || value <= 0) throw new Error(`${name} must be a positive number`);
}

function assertOptions(options) {
  if (!options.input) throw new Error('HTML input file is required');
  if (!fs.existsSync(options.input)) throw new Error(`HTML file not found: ${options.input}`);
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

function assertLiveState(state, expected, metadata) {
  const failures = [];
  if (!state.ok) failures.push(state.reason || 'live verification failed');
  if (state.svgCount !== expected.svgCount) failures.push(`SVG count ${state.svgCount}/${expected.svgCount}`);
  if (state.animateCount !== expected.animateCount) failures.push(`animation count ${state.animateCount}/${expected.animateCount}`);
  if (state.imageCount !== expected.imageUrls.length) failures.push(`image count ${state.imageCount}/${expected.imageUrls.length}`);
  if (state.failedUrls.length > 0) failures.push(`${state.failedUrls.length} image transfers failed`);
  if (state.pendingImages.length > 0) failures.push(`${state.pendingImages.length} images are still pending`);
  if (metadata.title !== undefined && state.title !== metadata.title) failures.push('title did not persist');
  if (metadata.summary !== undefined && state.summary !== metadata.summary) failures.push('summary did not persist');
  if (failures.length > 0) throw new Error(failures.join('; '));
}

async function injectAndSettle(options, content, title) {
  const injected = evaluateJson(options.profile, options.session, buildInjectScript(content), 60000);
  if (!injected.ok) throw new Error(injected.reason || 'body injection failed');
  return await waitForImageSettlement({
    profile: options.profile,
    session: options.session,
    timeoutMs: options.imageTimeoutMs,
    title,
  });
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    printUsage();
    return;
  }
  assertOptions(options);
  const sourceHtml = fs.readFileSync(options.input, 'utf8');
  const documentInfo = extractArticleDocument(sourceHtml);
  const metadata = {
    title: options.title ?? (documentInfo.title || undefined),
    summary: options.summary ?? (documentInfo.summary || undefined),
    author: options.author,
  };

  prepareSession(options);
  await waitForEditor({
    profile: options.profile,
    session: options.session,
    timeoutMs: options.editorTimeoutMs,
  });

  if (options.verifyOnly) {
    const liveState = evaluateJson(options.profile, options.session, buildVerifyScript(metadata.title || ''));
    const report = { mode: 'verify-only', live: { ...liveState, url: redactUrl(liveState.url || '') } };
    writeReport(options.report, report);
    console.log(JSON.stringify(report, null, 2));
    return;
  }

  let content = documentInfo.content;
  const optimizedMappings = [];
  if (options.optimizeImages) {
    const optimized = await optimizeContentImages(content, {
      maxBytes: options.maxImageBytes,
      maxWidth: options.maxImageWidth,
      timeoutMs: options.imageTimeoutMs,
    });
    content = optimized.content;
    optimizedMappings.push(...optimized.mapping.entries());
  }

  let liveState = await injectAndSettle(options, content, metadata.title || '');
  if (liveState.failedUrls.length > 0 && options.optimizeImages) {
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
  }

  evaluateJson(options.profile, options.session, buildMetadataScript(metadata));
  if (options.syncCoverFromBody) {
    await syncCoverFromBody({
      profile: options.profile,
      session: options.session,
    });
  }

  liveState = await waitForImageSettlement({
    profile: options.profile,
    session: options.session,
    timeoutMs: options.imageTimeoutMs,
    title: metadata.title || '',
  });
  const expected = extractArticleDocument(`<body>${content}</body>`);
  assertLiveState(liveState, expected, metadata);

  let saveState = null;
  if (options.saveDraft) {
    saveState = await saveDraft({
      profile: options.profile,
      session: options.session,
      timeoutMs: options.editorTimeoutMs,
    });
    liveState = evaluateJson(options.profile, options.session, buildVerifyScript(metadata.title || ''));
    assertLiveState(liveState, expected, metadata);
  }

  const report = {
    mode: options.saveDraft ? 'saved-draft' : 'injected',
    optimizedImages: optimizedMappings.length,
    expected: {
      images: expected.imageUrls.length,
      svg: expected.svgCount,
      animations: expected.animateCount,
    },
    live: { ...liveState, url: redactUrl(liveState.url || '') },
    save: saveState ? { ...saveState, url: redactUrl(saveState.url || '') } : null,
  };
  writeReport(options.report, report);
  console.log(JSON.stringify(report, null, 2));
}

main().catch((error) => {
  if (error instanceof OpencliError) {
    console.error(`wechat injection failed: ${error.message}`);
    if (error.details) console.error(error.details.replace(/([?&]token=)[^&\s]+/gi, '$1[redacted]'));
  } else if (error instanceof Error) {
    console.error(`wechat injection failed: ${error.message}`);
  } else {
    console.error('wechat injection failed with an unknown error');
  }
  process.exitCode = 1;
});

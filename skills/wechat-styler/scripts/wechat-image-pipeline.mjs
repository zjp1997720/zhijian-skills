import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';

import { isWeChatHostedImageUrl } from './wechat-image-hosts.mjs';

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function run(command, args) {
  const result = spawnSync(command, args, { encoding: 'utf8', maxBuffer: 10 * 1024 * 1024 });
  if (result.error) {
    throw new Error(`${command} could not start: ${result.error.message}`);
  }
  if (result.status !== 0) {
    const detail = result.stderr?.trim() || result.stdout?.trim() || `exit ${result.status}`;
    throw new Error(`${command} failed: ${detail}`);
  }
  return result.stdout.trim();
}

async function request(url, options, timeoutMs) {
  const response = await fetch(url, { ...options, signal: AbortSignal.timeout(timeoutMs) });
  if (!response.ok) throw new Error(`${options.method || 'GET'} ${url} returned ${response.status}`);
  return response;
}

export function shouldOptimizeImage(contentLength, maxBytes) {
  return Number.isFinite(contentLength) && contentLength > maxBytes;
}

export function isGifImageUrl(url) {
  try {
    const { pathname } = new URL(url);
    return /\.gif$/i.test(pathname);
  } catch {
    return false;
  }
}

export function findRemoteImageUrls(content) {
  const urls = [...content.matchAll(/<img\b[^>]*\bsrc=["']([^"']+)["'][^>]*>/gi)]
    .map((match) => match[1].replaceAll('&amp;', '&'))
    .filter((url) => /^https?:/i.test(url))
    .filter((url) => !isWeChatHostedImageUrl(url));
  return [...new Set(urls)];
}

export function replaceImageUrls(content, mapping) {
  let updated = content;
  for (const [source, target] of mapping.entries()) {
    updated = updated.replace(new RegExp(escapeRegExp(source), 'g'), target);
  }
  return updated;
}

export function optimizedFilenameForUrl(url) {
  const identity = createHash('sha256').update(url).digest('hex').slice(0, 16);
  return `wechat-${identity}.jpg`;
}

export function optimizedGifFilenameForUrl(url) {
  const identity = createHash('sha256').update(url).digest('hex').slice(0, 16);
  return `wechat-${identity}.gif`;
}

function optimizedUploadFilenameForUrl(url) {
  return isGifImageUrl(url) ? optimizedGifFilenameForUrl(url) : optimizedFilenameForUrl(url);
}

export function assertDistinctUploadedUrls(mapping) {
  const owners = new Map();
  for (const [source, target] of mapping.entries()) {
    const previousSource = owners.get(target);
    if (previousSource && previousSource !== source) {
      throw new Error(
        `PicGo returned the same URL for different source images: ${optimizedUploadFilenameForUrl(previousSource)} and ${optimizedUploadFilenameForUrl(source)}. `
        + 'The upload has been stopped to prevent image overwrite; verify the PicGo naming strategy or retry with --no-optimize-images.',
      );
    }
    owners.set(target, source);
  }
}

async function getContentLength(url, timeoutMs) {
  try {
    const response = await request(url, { method: 'HEAD' }, timeoutMs);
    const value = Number(response.headers.get('content-length') || '0');
    return Number.isFinite(value) ? value : 0;
  } catch {
    return 0;
  }
}

export async function downloadRemoteImage(url, destination, timeoutMs = 30000) {
  const response = await request(url, { method: 'GET' }, timeoutMs);
  const bytes = new Uint8Array(await response.arrayBuffer());
  fs.writeFileSync(destination, bytes);
  return destination;
}

function optimizeLocalImage(sourcePath, maxWidth, quality, workDir, targetFilename) {
  if (process.platform !== 'darwin') throw new Error('automatic image resizing currently requires macOS sips');
  const dimensions = run('sips', ['-g', 'pixelWidth', '-g', 'pixelHeight', sourcePath]);
  const widthMatch = dimensions.match(/pixelWidth:\s*(\d+)/);
  const width = Number(widthMatch?.[1] || '0');
  const targetPath = path.join(workDir, targetFilename);
  const args = ['-s', 'format', 'jpeg', '-s', 'formatOptions', String(quality)];
  if (width > maxWidth) args.push('--resampleWidth', String(maxWidth));
  args.push(sourcePath, '--out', targetPath);
  run('sips', args);
  return targetPath;
}

export function gifOptimizationProfiles(maxWidth) {
  const profiles = [
    { width: 1200, fps: 8, colors: 128 },
    { width: 1000, fps: 6, colors: 96 },
    { width: 800, fps: 5, colors: 64 },
    { width: 640, fps: 4, colors: 48 },
    { width: 480, fps: 3, colors: 32 },
  ];
  return profiles.map((profile) => ({ ...profile, width: Math.min(maxWidth, profile.width) }));
}

export function optimizeLocalGif(sourcePath, options) {
  const runCommand = options.runCommand || run;
  const getFileSize = options.getFileSize || ((filePath) => fs.statSync(filePath).size);
  const targetPath = path.join(options.workDir, options.targetFilename);
  let lastSize = 0;
  for (const profile of gifOptimizationProfiles(options.maxWidth)) {
    const filter = [
      `fps=${profile.fps},scale='min(${profile.width},iw)':-2:flags=lanczos,split[s0][s1]`,
      `[s0]palettegen=max_colors=${profile.colors}:stats_mode=diff[p]`,
      '[s1][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle',
    ].join(';');
    runCommand('ffmpeg', [
      '-hide_banner', '-loglevel', 'error', '-y',
      '-i', sourcePath,
      '-vf', filter,
      '-loop', '0',
      targetPath,
    ]);
    lastSize = getFileSize(targetPath);
    if (lastSize <= options.maxBytes) return targetPath;
  }
  throw new Error(
    `animated GIF remains ${lastSize} bytes after ffmpeg optimization; `
    + `raise --max-image-bytes above ${options.maxBytes} or replace the source GIF`,
  );
}

async function uploadWithPicGo(filePath, server, timeoutMs) {
  const response = await request(`${server.replace(/\/$/, '')}/upload`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ list: [filePath] }),
  }, timeoutMs);
  const payload = await response.json();
  const uploadedUrl = Array.isArray(payload?.result) ? payload.result[0] : null;
  if (typeof uploadedUrl !== 'string' || uploadedUrl.length === 0) {
    throw new Error(`PicGo upload returned no URL for ${filePath}`);
  }
  return uploadedUrl;
}

async function optimizeRemoteImage(url, options) {
  const workDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wechat-styler-image-'));
  try {
    const extension = path.extname(new URL(url).pathname) || '.img';
    const sourcePath = path.join(workDir, `source${extension}`);
    await downloadRemoteImage(url, sourcePath, options.timeoutMs);
    const optimizedPath = isGifImageUrl(url)
      ? optimizeLocalGif(sourcePath, {
        maxWidth: options.maxWidth,
        maxBytes: options.maxBytes,
        workDir,
        targetFilename: optimizedGifFilenameForUrl(url),
      })
      : optimizeLocalImage(
        sourcePath,
        options.maxWidth,
        options.quality,
        workDir,
        optimizedFilenameForUrl(url),
      );
    return await uploadWithPicGo(optimizedPath, options.picgoServer, options.timeoutMs);
  } finally {
    fs.rmSync(workDir, { recursive: true, force: true });
  }
}

export async function optimizeContentImages(content, options = {}) {
  const settings = {
    maxBytes: options.maxBytes ?? 2 * 1024 * 1024,
    maxWidth: options.maxWidth ?? 1920,
    quality: options.quality ?? 85,
    timeoutMs: options.timeoutMs ?? 30000,
    picgoServer: options.picgoServer ?? 'http://127.0.0.1:36677',
  };
  const forced = new Set(options.forceUrls || []);
  const optimizeRemote = options.optimizeRemote || optimizeRemoteImage;
  const mapping = new Map();
  for (const url of findRemoteImageUrls(content)) {
    const contentLength = forced.has(url) ? settings.maxBytes + 1 : await getContentLength(url, settings.timeoutMs);
    if (!shouldOptimizeImage(contentLength, settings.maxBytes)) continue;
    const uploadedUrl = await optimizeRemote(url, settings);
    mapping.set(url, uploadedUrl);
    assertDistinctUploadedUrls(mapping);
  }
  return {
    content: replaceImageUrls(content, mapping),
    mapping,
  };
}

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function run(command, args) {
  const result = spawnSync(command, args, { encoding: 'utf8', maxBuffer: 10 * 1024 * 1024 });
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

export function findRemoteImageUrls(content) {
  const urls = [...content.matchAll(/<img\b[^>]*\bsrc=["']([^"']+)["'][^>]*>/gi)]
    .map((match) => match[1].replaceAll('&amp;', '&'))
    .filter((url) => /^https?:/i.test(url))
    .filter((url) => !/(?:mmbiz|qpic)\.(?:cn|com)/i.test(url));
  return [...new Set(urls)];
}

export function replaceImageUrls(content, mapping) {
  let updated = content;
  for (const [source, target] of mapping.entries()) {
    updated = updated.replace(new RegExp(escapeRegExp(source), 'g'), target);
  }
  return updated;
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

function optimizeLocalImage(sourcePath, maxWidth, quality, workDir) {
  if (process.platform !== 'darwin') throw new Error('automatic image resizing currently requires macOS sips');
  const dimensions = run('sips', ['-g', 'pixelWidth', '-g', 'pixelHeight', sourcePath]);
  const widthMatch = dimensions.match(/pixelWidth:\s*(\d+)/);
  const width = Number(widthMatch?.[1] || '0');
  const targetPath = path.join(workDir, `${path.parse(sourcePath).name}-wechat.jpg`);
  const args = ['-s', 'format', 'jpeg', '-s', 'formatOptions', String(quality)];
  if (width > maxWidth) args.push('--resampleWidth', String(maxWidth));
  args.push(sourcePath, '--out', targetPath);
  run('sips', args);
  return targetPath;
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
    const optimizedPath = optimizeLocalImage(sourcePath, options.maxWidth, options.quality, workDir);
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
  const mapping = new Map();
  for (const url of findRemoteImageUrls(content)) {
    const contentLength = forced.has(url) ? settings.maxBytes + 1 : await getContentLength(url, settings.timeoutMs);
    if (!shouldOptimizeImage(contentLength, settings.maxBytes)) continue;
    const uploadedUrl = await optimizeRemoteImage(url, settings);
    mapping.set(url, uploadedUrl);
  }
  return {
    content: replaceImageUrls(content, mapping),
    mapping,
  };
}

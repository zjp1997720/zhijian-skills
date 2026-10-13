import assert from 'node:assert/strict';
import test from 'node:test';

import { resolveBrowserLaunch } from '../scripts/qa-browser.mjs';

const only = (...paths) => (candidate) => paths.includes(candidate);
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const EGO = '/Applications/ego lite.app/Contents/MacOS/ego lite';

test('CHROME_EXECUTABLE wins and must exist', () => {
  const env = { CHROME_EXECUTABLE: '/opt/browser', CHROME_CHANNEL: 'msedge' };
  assert.deepEqual(resolveBrowserLaunch({ env, platform: 'darwin', exists: only('/opt/browser', CHROME) }),
    { executablePath: '/opt/browser', source: 'CHROME_EXECUTABLE' });
  assert.throws(() => resolveBrowserLaunch({ env, platform: 'darwin', exists: only() }), /CHROME_EXECUTABLE not found/);
});

test('CHROME_CHANNEL is honoured before auto-detection', () => {
  assert.deepEqual(resolveBrowserLaunch({ env: { CHROME_CHANNEL: 'msedge' }, platform: 'darwin', exists: only(CHROME) }),
    { channel: 'msedge', source: 'CHROME_CHANNEL' });
});

test('macOS prefers Google Chrome, then another installed Chromium browser', () => {
  assert.deepEqual(resolveBrowserLaunch({ env: {}, platform: 'darwin', exists: only(CHROME, EGO) }),
    { channel: 'chrome', source: 'chrome' });
  assert.deepEqual(resolveBrowserLaunch({ env: {}, platform: 'darwin', exists: only(EGO) }),
    { executablePath: EGO, source: 'installed-chromium' });
});

test('macOS without any browser falls back to Playwright Chromium; other platforms keep the chrome channel', () => {
  assert.deepEqual(resolveBrowserLaunch({ env: {}, platform: 'darwin', exists: only() }), { source: 'playwright-chromium' });
  assert.deepEqual(resolveBrowserLaunch({ env: {}, platform: 'linux', exists: only() }), { channel: 'chrome', source: 'chrome' });
});

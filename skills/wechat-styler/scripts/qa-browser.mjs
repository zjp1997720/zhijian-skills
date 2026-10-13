import fs from 'node:fs';

// Chromium-based browsers that Playwright can drive through `executablePath` when
// Google Chrome itself is not installed. Standard install locations only.
const MAC_CANDIDATES = [
  '/Applications/ego lite.app/Contents/MacOS/ego lite',
  '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
  '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser',
  '/Applications/Chromium.app/Contents/MacOS/Chromium',
];
const MAC_CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

/**
 * Resolve Playwright launch options for mobile QA.
 * Order: CHROME_EXECUTABLE → CHROME_CHANNEL → installed Google Chrome → other
 * installed Chromium browsers → Playwright's own downloaded Chromium.
 */
export function resolveBrowserLaunch({ env = process.env, platform = process.platform, exists = fs.existsSync } = {}) {
  if (env.CHROME_EXECUTABLE) {
    if (!exists(env.CHROME_EXECUTABLE)) throw new Error(`CHROME_EXECUTABLE not found: ${env.CHROME_EXECUTABLE}`);
    return { executablePath: env.CHROME_EXECUTABLE, source: 'CHROME_EXECUTABLE' };
  }
  if (env.CHROME_CHANNEL) return { channel: env.CHROME_CHANNEL, source: 'CHROME_CHANNEL' };
  if (platform === 'darwin') {
    if (exists(MAC_CHROME)) return { channel: 'chrome', source: 'chrome' };
    const found = MAC_CANDIDATES.find((candidate) => exists(candidate));
    if (found) return { executablePath: found, source: 'installed-chromium' };
    return { source: 'playwright-chromium' };
  }
  return { channel: 'chrome', source: 'chrome' };
}

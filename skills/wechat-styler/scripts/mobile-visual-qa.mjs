#!/usr/bin/env node

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

import { chromium } from 'playwright-core';

function parseArgs(argv) {
  const options = {
    input: '',
    screenshot: '',
    width: 390,
    height: 844,
    expectZhijian: false,
    strictImageUniqueness: false,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];
    if (!value.startsWith('--') && !options.input) options.input = value;
    else if (value === '--screenshot') options.screenshot = argv[++index];
    else if (value === '--viewport') {
      const match = String(argv[++index]).match(/^(\d+)x(\d+)$/);
      if (!match) throw new Error('viewport must look like 390x844');
      options.width = Number(match[1]);
      options.height = Number(match[2]);
    } else if (value === '--expect-zhijian') options.expectZhijian = true;
    else if (value === '--strict-image-uniqueness') options.strictImageUniqueness = true;
    else throw new Error(`unknown option: ${value}`);
  }
  if (!options.input) throw new Error('HTML input file is required');
  return options;
}

async function inspect(page, options) {
  return page.evaluate(({ expectZhijian, strictImageUniqueness }) => {
    const textRangeAfter = (mark, paragraph) => {
      const walker = document.createTreeWalker(paragraph, NodeFilter.SHOW_TEXT);
      let textNode = walker.nextNode();
      while (textNode) {
        if (!mark.contains(textNode)) {
          const offset = textNode.data.search(/\S/);
          if (offset >= 0) {
            const range = document.createRange();
            range.setStart(textNode, offset);
            range.setEnd(textNode, Math.min(offset + 1, textNode.length));
            return range.getBoundingClientRect();
          }
        }
        textNode = walker.nextNode();
      }
      return null;
    };
    const root = document.querySelector('[data-wechat-root="article"]');
    if (!root) return { failures: ['article root not found'] };

    const images = [...root.querySelectorAll('img')];
    const imageUrls = images.map((image) => image.currentSrc || image.src || '');
    const duplicateImageUrls = [...new Set(imageUrls.filter((url, index) => url && imageUrls.indexOf(url) !== index))];
    const brokenImages = images.filter((image) => !image.complete || image.naturalWidth === 0).length;
    const quoteReports = [...root.querySelectorAll('[data-wechat-block="quote"]')].map((quote) => {
      const paragraph = quote.querySelector('p');
      const mark = paragraph ? [...paragraph.querySelectorAll('span')].find((span) => span.textContent === '“') : null;
      const markRect = mark?.getBoundingClientRect();
      const textRect = mark && paragraph ? textRangeAfter(mark, paragraph) : null;
      const borderLeftWidth = Number.parseFloat(getComputedStyle(quote).borderLeftWidth || '0');
      return {
        hasMark: Boolean(mark),
        sameParagraph: Boolean(mark && paragraph && mark.parentElement === paragraph),
        topDelta: markRect && textRect ? Number(Math.abs(markRect.top - textRect.top).toFixed(2)) : null,
        lineSeparated: markRect && textRect ? markRect.bottom < textRect.top - 1 : true,
        hasLeftBorder: borderLeftWidth > 0,
      };
    });
    const h2s = [...root.querySelectorAll('h2')];
    const warmBarH2s = h2s.filter((heading) => {
      const style = getComputedStyle(heading);
      return Number.parseFloat(style.borderLeftWidth || '0') >= 3
        && style.borderLeftColor === 'rgb(184, 82, 53)';
    });
    const h3s = [...root.querySelectorAll('h3')];
    const bodyParagraph = [...root.querySelectorAll('p')].find((paragraph) => (
      paragraph.style.textAlign === 'justify'
      && !paragraph.closest('[data-wechat-block="quote"]')
    ));
    const h2Style = h2s[0] ? getComputedStyle(h2s[0]) : null;
    const h3Style = h3s[0] ? getComputedStyle(h3s[0]) : null;
    const bodyStyle = bodyParagraph ? getComputedStyle(bodyParagraph) : null;
    const typography = {
      h2: h2Style ? {
        fontFamily: h2Style.fontFamily,
        fontSize: h2Style.fontSize,
        fontWeight: h2Style.fontWeight,
      } : null,
      h3: h3Style ? {
        fontFamily: h3Style.fontFamily,
        fontSize: h3Style.fontSize,
        fontWeight: h3Style.fontWeight,
      } : null,
      body: bodyStyle ? {
        fontFamily: bodyStyle.fontFamily,
        fontSize: bodyStyle.fontSize,
        fontWeight: bodyStyle.fontWeight,
        lineHeight: bodyStyle.lineHeight,
      } : null,
    };
    const failures = [];
    if (document.documentElement.scrollWidth > window.innerWidth + 1) failures.push('document has horizontal overflow');
    if (root.scrollWidth > root.clientWidth + 1) failures.push('article root has horizontal overflow');
    if (brokenImages > 0) failures.push(`${brokenImages} image(s) failed to load`);
    if (strictImageUniqueness && duplicateImageUrls.length > 0) {
      failures.push(`${duplicateImageUrls.length} duplicate image URL(s) found`);
    }
    quoteReports.forEach((report, index) => {
      if (!report.hasMark || !report.sameParagraph || report.lineSeparated || report.topDelta > 12) {
        failures.push(`quote ${index + 1} mark is not aligned with its first text line`);
      }
      if (expectZhijian && report.hasLeftBorder) failures.push(`quote ${index + 1} unexpectedly has a left border`);
    });
    if (expectZhijian && h2s.length > 0 && warmBarH2s.length !== h2s.length) {
      failures.push(`Zhijian warm-bar H2 count ${warmBarH2s.length}/${h2s.length}`);
    }
    if (expectZhijian && h2Style && !h2Style.fontFamily.includes('TsangerJinKai02')) {
      failures.push('Zhijian H2 does not declare the editorial heading font');
    }
    if (expectZhijian && h3Style && (h3Style.fontSize !== '18px' || h3Style.fontWeight !== '600')) {
      failures.push(`Zhijian H3 expected 18px/600, got ${h3Style.fontSize}/${h3Style.fontWeight}`);
    }
    if (expectZhijian && bodyStyle && (
      bodyStyle.fontSize !== '15px'
      || bodyStyle.fontWeight !== '450'
      || Math.abs(Number.parseFloat(bodyStyle.lineHeight) - 25.2) > 0.2
    )) {
      failures.push(`Zhijian body expected 15px/450/1.68, got ${bodyStyle.fontSize}/${bodyStyle.fontWeight}/${bodyStyle.lineHeight}`);
    }
    return {
      viewport: { width: window.innerWidth, height: window.innerHeight },
      article: { scrollWidth: root.scrollWidth, clientWidth: root.clientWidth },
      images: images.length,
      uniqueImages: new Set(imageUrls).size,
      duplicateImageUrls,
      brokenImages,
      quotes: quoteReports,
      h2Count: h2s.length,
      warmBarH2Count: warmBarH2s.length,
      typography,
      failures,
    };
  }, {
    expectZhijian: options.expectZhijian,
    strictImageUniqueness: options.strictImageUniqueness,
  });
}

let browser;
try {
  const args = process.argv.slice(2);
  if (args.includes('--help') || args.includes('-h')) {
    console.log(`Usage: node scripts/mobile-visual-qa.mjs <article.html> [options]
  --viewport <WxH>           Viewport (default: 390x844)
  --screenshot <path>        Screenshot (default: system temp directory)
  --expect-zhijian            Check Zhijian visual baseline
  --strict-image-uniqueness   Fail on unexpected repeated image URLs
  -h, --help                 Show help without launching a browser
Environment: CHROME_CHANNEL selects browser channel (default: chrome)
Outputs: JSON report and full-page screenshot; exits 1 on QA failure`);
    process.exit(0);
  }
  const options = parseArgs(args);
  const input = path.resolve(options.input);
  if (!fs.existsSync(input)) throw new Error(`HTML file not found: ${input}`);
  const screenshot = path.resolve(
    options.screenshot || path.join(os.tmpdir(), `${path.parse(input).name}-mobile-${options.width}.png`),
  );
  browser = await chromium.launch({ channel: process.env.CHROME_CHANNEL || 'chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: options.width, height: options.height } });
  await page.goto(pathToFileURL(input).href, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts?.ready);
  await page.screenshot({ path: screenshot, fullPage: true });
  const report = await inspect(page, options);
  report.ok = report.failures.length === 0;
  report.input = input;
  report.screenshot = screenshot;
  console.log(JSON.stringify(report, null, 2));
  if (!report.ok) process.exitCode = 1;
} catch (error) {
  console.error(JSON.stringify({ ok: false, error: error.message }, null, 2));
  process.exitCode = 1;
} finally {
  await browser?.close();
}

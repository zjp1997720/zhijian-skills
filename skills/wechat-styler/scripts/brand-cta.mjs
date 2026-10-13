import fs from 'node:fs';
import crypto from 'node:crypto';

const assetDir = new URL('../assets/brand-cta/', import.meta.url);
const manifest = JSON.parse(fs.readFileSync(new URL('manifest.json', assetDir), 'utf8'));
export const brandCtaManifest = manifest;
export const brandCtaAssets = manifest.assets;
// Earlier GIF versions: no longer shipped, only recognised so old drafts are cleaned on reprocessing.
export const legacyBrandCtaAssets = (manifest.legacy || []).flatMap(entry => Object.values(entry.assets || {}));
const escape = s => String(s).replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;');

const svgCache = new Map();
/** Read a CTA SVG, verify it against the manifest and return one line of inline markup. */
export function brandCtaSvg(kind) {
  if (svgCache.has(kind)) return svgCache.get(kind);
  const a = brandCtaAssets[kind];
  if (!a) throw new Error(`unknown brand CTA: ${kind}`);
  const raw = fs.readFileSync(new URL(a.file, assetDir));
  const sha = crypto.createHash('sha256').update(raw).digest('hex');
  if (sha !== a.sha256) throw new Error(`brand CTA ${a.file} sha256 ${sha} does not match manifest`);
  const text = raw.toString('utf8')
    .replace(/<\?xml[\s\S]*?\?>/g, '')
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/>\s+</g, '><')
    .replace(/\s*\n\s*/g, ' ')
    .trim();
  const root = text.match(/^<svg\b([^>]*)>([\s\S]*)<\/svg>$/);
  if (!root) throw new Error(`brand CTA ${a.file} is not a single <svg> root`);
  const viewBox = (root[1].match(/\bviewBox="([^"]+)"/) || [])[1];
  if (viewBox !== a.viewBox) throw new Error(`brand CTA ${a.file} viewBox ${viewBox} does not match manifest ${a.viewBox}`);
  const alt = escape(a.alt);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="${a.viewBox}" preserveAspectRatio="xMidYMin meet" style="display:block;width:100%;height:auto;" role="img" aria-label="${alt}" data-alt="${alt}" data-semantic-text="${alt}" data-zhijian-cta="${kind}">${root[2]}</svg>`;
  svgCache.set(kind, svg);
  return svg;
}

const managedSection = /\n?<section\b[^>]*data-wechat-cta="(?:opening|ending)"[^>]*>[\s\S]*?<\/section>/gi;
const looseSvg = /<svg\b[^>]*data-zhijian-cta="(?:opening|ending)"[^>]*>[\s\S]*?<\/svg>/gi;
// A user/theme opening animation: any animated <svg> that is not one of our own CTA SVGs.
const userSvgOpener = /<svg\b(?![^>]*data-zhijian-cta)[^>]*>(?:(?!<\/svg>)[\s\S])*?<animate(?:Transform|Motion)?\b/i;

/** Remove every managed CTA: current SVG sections/roots plus legacy GIF <img> tags (by marker, file name or URL). */
export function stripBrandCta(html) {
  let result = html.replace(managedSection, '').replace(looseSvg, '');
  const legacy = legacyBrandCtaAssets;
  const files = legacy.map(a => a.file);
  const urls = legacy.map(a => a.url).filter(Boolean);
  return result.replace(/<img\b[^>]*>/gi, tag => {
    if (/\bdata-wechat-cta-image=/i.test(tag)) return '';
    const src = (tag.match(/\bsrc=["']([^"']+)["']/i) || [])[1];
    if (!src) return tag;
    const bare = src.split(/[?#]/)[0];
    return urls.includes(src) || urls.includes(bare) || files.some(file => bare === file || bare.endsWith('/'+file)) ? '' : tag;
  });
}

export function applyBrandCta(html, { mode = 'auto', cover = false, maxWidth = 640 } = {}) {
  if (!['auto','ending','none'].includes(mode)) throw new Error('brand-cta must be auto, ending, or none');
  // Managed wrappers are deliberately flat, so repeated processing is idempotent.
  let result = stripBrandCta(html);
  if (mode === 'none') return result;
  // An explicit/generated SVG opener takes precedence over the stock greeting.
  const hasSvgOpener = cover || userSvgOpener.test(result);
  // No background-color: the transparent SVG takes the article paper colour.
  const block = kind => `<section data-wechat-cta="${kind}" data-zhijian-cta="v6" style="max-width:${Number(maxWidth)}px;margin:${kind === 'opening' ? '0 auto 18px' : '24px auto 0'};padding:0;line-height:0;">${brandCtaSvg(kind)}</section>`;
  const opening = mode === 'auto' && !hasSvgOpener ? block('opening') : '';
  if (!/data-wechat-root="article"/.test(result)) throw new Error('CTA insertion requires the article root');
  result = result.replace(/(<section\b[^>]*data-wechat-root="article"[^>]*>)/i, `$1\n${opening}`);
  result = result.replace(/\n?<\/section>\s*<!-- 整体背景容器结束 -->/, `${block('ending')}\n</section>\n<!-- 整体背景容器结束 -->`);
  return result;
}

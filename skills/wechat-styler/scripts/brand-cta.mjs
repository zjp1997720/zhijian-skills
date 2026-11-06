import fs from 'node:fs';

const assetDir = new URL('../assets/brand-cta/', import.meta.url);
const manifest = JSON.parse(fs.readFileSync(new URL('manifest.json', assetDir), 'utf8'));
export const brandCtaManifest = manifest;
// Default (and only) CTA: hosted paper-colour photo GIFs. The 1.17-1.18 character CTAs (Flow GIF, inline SVG) are legacy.
export const brandCtaAssets = manifest.assets;
// Earlier versions: no longer shipped, only recognised so old drafts are cleaned on reprocessing.
export const legacyBrandCtaAssets = (manifest.legacy || []).flatMap(entry => Object.values(entry.assets || {}));
const escape = s => String(s).replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;');

export const BRAND_CTA_MARKER = 'v8-photo-gif';

/** Hosted photo GIF as a flat <img>; the pixels already carry the paper background, the portrait and the text. */
export function brandCtaImg(kind) {
  const a = brandCtaAssets[kind];
  if (!a) throw new Error(`unknown brand CTA: ${kind}`);
  return `<img data-wechat-cta-image="${kind}" src="${escape(a.url)}" alt="${escape(a.alt)}" width="${a.width}" height="${a.height}" style="display:block;width:100%;height:auto;margin:0 auto;border:0;" />`;
}

const managedSection = /\n?<section\b[^>]*data-wechat-cta="(?:opening|ending)"[^>]*>[\s\S]*?<\/section>/gi;
const looseSvg = /<svg\b[^>]*data-zhijian-cta="(?:opening|ending)"[^>]*>[\s\S]*?<\/svg>/gi;
// A user/theme opening animation: any animated <svg> that is not one of our own CTA SVGs.
const userSvgOpener = /<svg\b(?![^>]*data-zhijian-cta)[^>]*>(?:(?!<\/svg>)[\s\S])*?<animate(?:Transform|Motion)?\b/i;

/** Remove every managed CTA: v6/v7/v8 sections, loose SVG roots, and GIF <img> tags (by marker, file name or URL). */
export function stripBrandCta(html) {
  let result = html.replace(managedSection, '').replace(looseSvg, '');
  const legacy = [...legacyBrandCtaAssets, ...Object.values(brandCtaAssets)];
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

export function applyBrandCta(html, { mode = 'auto', style = 'gif', cover = false, maxWidth = 640 } = {}) {
  if (style !== 'gif') throw new Error('cta-style must be gif (the character SVG style was removed in 1.19.0; use brand-cta none to opt out)');
  if (!['auto','ending','none'].includes(mode)) throw new Error('brand-cta must be auto, ending, or none');
  // Managed wrappers are deliberately flat, so repeated processing is idempotent.
  let result = stripBrandCta(html);
  if (mode === 'none') return result;
  // An explicit/generated SVG opener takes precedence over the stock greeting.
  const hasSvgOpener = cover || userSvgOpener.test(result);
  // No background-color: the GIF pixels already are the paper colour. The image carries its own paper margins.
  const block = kind => `<section data-wechat-cta="${kind}" data-zhijian-cta="${BRAND_CTA_MARKER}" style="max-width:${Number(maxWidth)}px;margin:${kind === 'opening' ? '0 auto 18px' : '24px auto 0'};padding:${kind === 'opening' ? '24px 0 0' : '0 0 28px'};line-height:0;">${brandCtaImg(kind)}</section>`;
  const opening = mode === 'auto' && !hasSvgOpener ? block('opening') : '';
  if (!/data-wechat-root="article"/.test(result)) throw new Error('CTA insertion requires the article root');
  result = result.replace(/(<section\b[^>]*data-wechat-root="article"[^>]*>)/i, `$1\n${opening}`);
  result = result.replace(/\n?<\/section>\s*<!-- 整体背景容器结束 -->/, `${block('ending')}\n</section>\n<!-- 整体背景容器结束 -->`);
  return result;
}

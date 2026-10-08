import fs from 'node:fs';
const manifest = JSON.parse(fs.readFileSync(new URL('../assets/brand-cta/manifest.json', import.meta.url), 'utf8'));
export const brandCtaAssets = manifest.assets;
const escape = s => String(s).replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;');

export function applyBrandCta(html, { mode = 'auto', cover = false, maxWidth = 640 } = {}) {
  if (!['auto','ending','none'].includes(mode)) throw new Error('brand-cta must be auto, ending, or none');
  // Managed wrappers are deliberately flat, so repeated processing is idempotent.
  let result = html.replace(/<section\b[^>]*data-wechat-cta="(?:opening|ending)"[^>]*>[\s\S]*?<\/section>/gi, '');
  const files = Object.values(brandCtaAssets).map(a => a.file);
  result = result.replace(/<img\b[^>]*\bsrc=["']([^"']+)["'][^>]*>/gi, (tag, src) => {
    return files.some(file => src.split(/[?#]/)[0].endsWith('/'+file) || src === file) ? '' : tag;
  });
  if (mode === 'none') return result;
  // An explicit/generated SVG opener takes precedence over the stock greeting GIF.
  const hasSvgOpener = cover || /<svg\b[\s\S]*?<animate(?:Transform|Motion)?\b/i.test(result);
  const block = kind => {
    const a = brandCtaAssets[kind];
    return `<section data-wechat-cta="${kind}" style="max-width:${Number(maxWidth)}px;margin:${kind === 'opening' ? '0 auto 18px' : '24px auto 0'};padding:0;line-height:0;background-color:#FFFFFF;"><img data-wechat-cta-image="${kind}" src="${escape(a.url)}" alt="${escape(a.alt)}" width="${a.width}" height="${a.height}" style="display:block;width:100%;max-width:100%;height:auto;margin:0;border:0;" /></section>`;
  };
  const opening = mode === 'auto' && !hasSvgOpener ? block('opening') : '';
  if (!/data-wechat-root="article"/.test(result)) throw new Error('CTA insertion requires the article root');
  result = result.replace(/(<section\b[^>]*data-wechat-root="article"[^>]*>)/i, `$1\n${opening}`);
  result = result.replace(/<\/section>\s*<!-- 整体背景容器结束 -->/, `${block('ending')}\n</section>\n<!-- 整体背景容器结束 -->`);
  return result;
}

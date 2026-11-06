import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { applyBrandCta, brandCtaAssets, brandCtaManifest, brandCtaImg, legacyBrandCtaAssets } from '../scripts/brand-cta.mjs';
import { validateHtml } from '../scripts/validate.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const assetDir=path.join(root,'assets/brand-cta');
const shell = '<section data-wechat-root="article"><p>保留正文。</p></section><!-- 整体背景容器结束 -->';
const count=(s,k)=>(s.match(new RegExp(`data-wechat-cta="${k}"`,'g'))||[]).length;
const ctaSections=s=>s.match(/<section\b[^>]*data-wechat-cta="(?:opening|ending)"[^>]*>/g)||[];
const stripCta=s=>s.replace(/<section\b[^>]*data-wechat-cta="(?:opening|ending)"[^>]*>[\s\S]*?<\/section>/g,'');

const GIF_BASE='https://obsidian-1344509300.cos.ap-beijing.myqcloud.com/obsidian/2026/03/';
const GIF={
 opening:{file:'zhijian-cta-opening-photo-674d9c689c38.gif',w:1160,h:498,frames:160,fps:20,bytes:413718,sha:'674d9c689c380168e6082de10a903df244fd87b07e5c1b571c1d5fa64dd91ae7'},
 ending:{file:'zhijian-cta-ending-photo-ad13d9c0b716.gif',w:1160,h:400,frames:160,fps:20,bytes:424209,sha:'ad13d9c0b716e37a82eea17ea105bf37f76198f6aff8b07088b182fe99640517'}
};
const MARK='v8-photo-gif';
const IMG_STYLE='display:block;width:100%;height:auto;margin:0 auto;border:0;';
// Earlier CTA generations, rebuilt by hand now that their assets are no longer generated or shipped.
const FLOW_V7={opening:'zhijian-cta-opening-flow-376b7c890008.gif',ending:'zhijian-cta-ending-flow-5375c80db38d.gif'};
const v6Svg=kind=>`<section data-wechat-cta="${kind}" data-zhijian-cta="v6" style="max-width:640px;margin:0 auto;padding:24px 0 0;line-height:0;"><svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 360 136" data-zhijian-cta="${kind}"><g><path d="M0 0L1 1"/><animate attributeName="opacity" values="1;0.9;1" dur="3s" repeatCount="indefinite"/></g></svg></section>`;
const v7Flow=kind=>`<section data-wechat-cta="${kind}" data-zhijian-cta="v7-flow-gif" style="max-width:640px;margin:0 auto;padding:24px 0 0;line-height:0;"><img data-wechat-cta-image="${kind}" src="${GIF_BASE+FLOW_V7[kind]}" alt="x" width="720" height="272" style="display:block;width:100%;max-width:360px;" /></section>`;

test('manifest: v8 photo GIF default, character SVG and Flow GIFs legacy',()=>{
 assert.equal(brandCtaManifest.version,'2026-11-06-v8-photo-gif');
 assert.deepEqual(fs.readdirSync(assetDir).filter(f=>f.endsWith('.gif')),[],'GIF payload is hosted, not shipped');
 assert.deepEqual(fs.readdirSync(assetDir).filter(f=>f.endsWith('.svg')),[],'character SVG CTAs are removed');
 assert.equal(brandCtaManifest.fallback,undefined);
 for(const kind of ['opening','ending']){
  const a=brandCtaAssets[kind],g=GIF[kind];
  assert.equal(a.format,'gif');assert.equal(a.url,GIF_BASE+g.file);assert.equal(a.file,g.file);assert.equal(a.sha256,g.sha);
  assert.match(g.file,new RegExp(`^zhijian-cta-${kind}-photo-${g.sha.slice(0,12)}\\.gif$`));
  assert.equal(a.width,g.w);assert.equal(a.height,g.h);assert.equal(a.frames,g.frames);assert.equal(a.fps,g.fps);assert.equal(a.bytes,g.bytes);
  assert.equal(a.loop,'forever');
  assert.match(a.alt,/大鹏/);
  assert.doesNotMatch(a.alt,/小蓝/);
 }
 assert.match(brandCtaAssets.opening.alt,/AI 落地专家/);
 assert.match(brandCtaAssets.ending.alt,/有用，就留一份/);
 assert.ok(legacyBrandCtaAssets.length>=4&&legacyBrandCtaAssets.every(a=>a.url&&a.sha256&&a.file.endsWith('.gif')));
 assert.ok(legacyBrandCtaAssets.every(a=>!Object.values(brandCtaAssets).some(n=>n.url===a.url)));
 // The 1.18.1 Flow GIFs are legacy now, so reprocessing removes them.
 for(const f of Object.values(FLOW_V7)) assert.ok(legacyBrandCtaAssets.some(a=>a.file===f),f);
 assert.ok(brandCtaManifest.legacy.some(l=>l.format==='inline-svg'),'v6 SVG generation is recorded');
});

test('default emits v8 photo GIF img, transparent wrapper, unique on reapplication',()=>{
 const a=applyBrandCta(shell);const b=applyBrandCta(a);
 assert.equal(b,a);
 assert.equal(count(b,'opening'),1);assert.equal(count(b,'ending'),1);
 assert.ok(b.indexOf('data-wechat-cta="opening"')<b.indexOf('保留正文'));
 assert.ok(b.indexOf('data-wechat-cta="ending"')>b.indexOf('保留正文'));
 const sections=ctaSections(b);assert.equal(sections.length,2);
 for(const s of sections){assert.match(s,new RegExp(`data-zhijian-cta="${MARK}"`));assert.doesNotMatch(s,/background/i);}
 // Section padding keeps the image off the article card's top and bottom edges (1.18.1).
 assert.match(sections[0],/padding:24px 0 0;/);assert.match(sections[1],/padding:0 0 28px;/);
 assert.doesNotMatch(b,/小蓝|xiaolan|flow/i,'no character in the default CTAs');
 for(const kind of ['opening','ending']){
  const g=GIF[kind];
  const img=b.match(new RegExp(`<img [^>]*data-wechat-cta-image="${kind}"[^>]*>`))[0];
  assert.match(img,new RegExp(`src="${GIF_BASE+g.file}"`));
  assert.match(img,new RegExp(`width="${g.w}" height="${g.h}"`));
  assert.match(img,new RegExp(`alt="${brandCtaAssets[kind].alt}"`));
  assert.match(img,new RegExp(`style="${IMG_STYLE}"`));
  assert.doesNotMatch(img,/max-width/);
  assert.doesNotMatch(img,/background|border:[^0]/i);
 }
 assert.doesNotMatch(b,/<svg\b/);
 assert.equal(brandCtaImg('opening'),b.match(/<img [^>]*data-wechat-cta-image="opening"[^>]*>/)[0]);
 assert.throws(()=>applyBrandCta(shell,{style:'png'}));
});

test('the character SVG style is gone; v6 SVG and v7 Flow CTAs from older drafts are replaced by the photo GIFs',()=>{
 assert.throws(()=>applyBrandCta(shell,{style:'svg'}),/cta-style/);
 const gif=applyBrandCta(shell);
 const v6=shell.replace('<p>',v6Svg('opening')+'<p>').replace('</section><!--',v6Svg('ending')+'</section><!--');
 const v7=shell.replace('<p>',v7Flow('opening')+'<p>').replace('</section><!--',v7Flow('ending')+'</section><!--');
 for(const old of [v6,v7]){
  const out=applyBrandCta(old);
  assert.equal(out,gif);
  assert.doesNotMatch(out,/<svg\b|v6|v7-flow-gif|flow/);
 }
 // Loose v6 SVG roots without their wrapper are removed too.
 const loose=shell.replace('<p>','<svg width="100%" viewBox="0 0 360 136" data-zhijian-cta="opening"><g><animate repeatCount="indefinite"/></g></svg><p>');
 assert.equal(applyBrandCta(loose),gif);
});

test('dedupe across v5 GIF, v6 SVG, v7 Flow GIF and v8 photo GIF existing CTAs',()=>{
 const v5=legacyBrandCtaAssets.find(a=>a.file.includes('-opening-'));
 const v5End=legacyBrandCtaAssets.find(a=>a.file.includes('-ending-'));
 const v5Html=shell.replace('<p>',`<section data-wechat-cta="opening" style="background-color:#FFFFFF;"><img data-wechat-cta-image="opening" src="${v5.url}" alt="x" /></section><p>`).replace('</section><!--',`<img src="${v5End.url}"></section><!--`);
 const v6Html=shell.replace('<p>',v6Svg('opening')+'<p>').replace('</section><!--',v6Svg('ending')+'</section><!--');
 const v7Html=applyBrandCta(shell);
 const v7FlowHtml=shell.replace('<p>',v7Flow('opening')+'<p>').replace('</section><!--',v7Flow('ending')+'</section><!--');
 const loose=shell.replace('<p>',`<img src="${GIF_BASE+GIF.opening.file}?v=1"><img src="https://mmbiz.qpic.cn/x/${GIF.ending.file}"><img src="${GIF_BASE+FLOW_V7.opening}"><p>`);
 for(const input of [v5Html,v6Html,v7Html,v7FlowHtml,loose]){
  for(const style of ['gif']){
   const out=applyBrandCta(input,{style});
   assert.equal(count(out,'opening'),1);assert.equal(count(out,'ending'),1);
   assert.equal((out.match(/<img\b/g)||[]).length,2);
   assert.equal((out.match(/<svg\b/g)||[]).length,0);
   assert.equal(out,applyBrandCta(shell,{style}));
  }
  const none=applyBrandCta(input,{mode:'none'});
  assert.doesNotMatch(none,/data-wechat-cta|<img|<svg/);
 }
});

test('ending order: end-mark, topics, then ending CTA',()=>{
 const full='<section data-wechat-root="article"><p>保留正文。</p><section data-wechat-block="end-mark"></section><section data-wechat-topics="1"></section></section><!-- 整体背景容器结束 -->';
 for(const style of ['gif']){
  const h=applyBrandCta(full,{style});
  const e=h.indexOf('data-wechat-cta="ending"');
  assert.ok(h.indexOf('end-mark')<h.indexOf('data-wechat-topics')&&h.indexOf('data-wechat-topics')<e);
  assert.ok(h.indexOf('data-wechat-cta="opening"')<h.indexOf('保留正文'));
 }
});

test('explicit and existing user SVG opener suppress greeting, retain ending',()=>{
 for(const [h,opts] of [[shell,{cover:true}],[shell.replace('<p>','<svg><animate /></svg><p>'),{}]]){
  const a=applyBrandCta(h,opts);assert.equal(count(a,'opening'),0);assert.equal(count(a,'ending'),1);
 }
 // An animated SVG that still carries our marker (a v6 CTA left in a draft) must not count as a user opener.
 const loose=shell.replace('<p>','<svg data-zhijian-cta="opening"><animate repeatCount="indefinite" /></svg><svg><rect /></svg><p>');
 const a=applyBrandCta(loose);assert.equal(count(a,'opening'),1);assert.equal(count(a,'ending'),1);
 assert.equal((a.match(/<animate/g)||[]).length,0,'the marked v6 SVG is removed');assert.match(a,/<svg><rect \/><\/svg>/,'the user SVG is kept');
});

test('none removes owned assets only; ending option does not add greeting',()=>{
 const a=applyBrandCta(applyBrandCta(shell),{mode:'none'});assert.equal(count(a,'opening'),0);assert.equal(count(a,'ending'),0);assert.match(a,/保留正文/);
 assert.doesNotMatch(a,/data-zhijian-cta/);
 const e=applyBrandCta(shell,{mode:'ending'});assert.equal(count(e,'opening'),0);assert.equal(count(e,'ending'),1);
 assert.throws(()=>applyBrandCta(shell,{mode:'bad'}));
});

test('legacy GIF CTAs from earlier drafts are replaced, unrelated images preserved',()=>{
 const [op,en]=['opening','ending'].map(k=>legacyBrandCtaAssets.find(a=>a.file.includes(`-${k}-`)));
 const legacyWrapped=`<section data-wechat-cta="opening" style="background-color:#FFFFFF;"><img data-wechat-cta-image="opening" src="${op.url}" alt="x" /></section>`;
 const html=shell.replace('<p>',`${legacyWrapped}<img src="${op.url}?v=2"><img src="https://mmbiz.qpic.cn/x/${en.file}"><img data-wechat-cta-image="ending" src="https://mmbiz.qpic.cn/rehosted.gif"><img src="https://example.com/user.png"><p>`);
 const a=applyBrandCta(html);
 for(const l of legacyBrandCtaAssets){assert.ok(!a.includes(l.file));}
 assert.doesNotMatch(a,/rehosted\.gif/);
 assert.equal((a.match(/data-wechat-cta-image/g)||[]).length,2,'only the two fresh CTA images');
 assert.match(a,/example.com\/user.png/);
 assert.equal(count(a,'opening'),1);assert.equal(count(a,'ending'),1);
});

test('real converter default, components, SVG and opt-out routes',()=>{
 for(const [args,opening,ending,svg] of [[[],1,1,false],[['--components'],1,1,false],[['--cover','--cover-template','xiaolan-terminal'],0,1,true],[['--brand-cta','none'],0,0,false],[['--brand-cta','ending'],0,1,false],[['--cta-style','gif'],1,1,false]]){
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'cta-convert-'));
  try{
   fs.writeFileSync(path.join(dir,'article.md'),'---\ntitle: 验收文章\n---\n\n## 正文\n\n正文保留。\n');
   const r=spawnSync(process.execPath,[path.join(root,'scripts/convert.mjs'),path.join(dir,'*.md'),'--no-open',...args],{encoding:'utf8'});
   assert.equal(r.status,0,r.stderr);const h=fs.readFileSync(path.join(dir,'article_wechat.html'),'utf8');
   assert.equal(count(h,'opening'),opening);assert.equal(count(h,'ending'),ending);
   assert.equal(stripCta(h).replace(/<section data-wechat-block="end-mark"[\s\S]*?<\/section>/,'').includes('<svg'),svg);assert.match(h,/正文保留/);
   for(const s of ctaSections(h)) assert.doesNotMatch(s,/background/i);
   if(!args.includes('--cover')&&ending) assert.match(h,new RegExp(`data-zhijian-cta="${MARK}"`));
   assert.equal(validateHtml(h).errors.length,0,JSON.stringify(validateHtml(h).errors));
  }finally{fs.rmSync(dir,{recursive:true,force:true});}
 }
});

test('converter rejects an unknown --cta-style and the removed svg style',()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'cta-bad-'));
 try{
  fs.writeFileSync(path.join(dir,'a.md'),'正文\n');
  for(const style of ['png','svg']){
   const r=spawnSync(process.execPath,[path.join(root,'scripts/convert.mjs'),path.join(dir,'a.md'),'--no-open','--cta-style',style],{encoding:'utf8'});
   assert.notEqual(r.status,0);assert.match(r.stderr,/cta-style/);
  }
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});

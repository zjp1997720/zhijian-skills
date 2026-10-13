import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { applyBrandCta, brandCtaAssets, brandCtaManifest, brandCtaImg, brandCtaSvg, brandCtaSvgAssets, legacyBrandCtaAssets } from '../scripts/brand-cta.mjs';
import { validateHtml } from '../scripts/validate.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const assetDir=path.join(root,'assets/brand-cta');
const shell = '<section data-wechat-root="article"><p>保留正文。</p></section><!-- 整体背景容器结束 -->';
const count=(s,k)=>(s.match(new RegExp(`data-wechat-cta="${k}"`,'g'))||[]).length;
const ctaSections=s=>s.match(/<section\b[^>]*data-wechat-cta="(?:opening|ending)"[^>]*>/g)||[];
const stripCta=s=>s.replace(/<section\b[^>]*data-wechat-cta="(?:opening|ending)"[^>]*>[\s\S]*?<\/section>/g,'');

const GIF_BASE='https://obsidian-1344509300.cos.ap-beijing.myqcloud.com/obsidian/2026/03/';
const GIF={
 opening:{file:'zhijian-cta-opening-flow-376b7c890008.gif',w:720,h:272,frames:48,fps:12,bytes:800024,sha:'376b7c89000817b0d050bb1674578563ba35017846a1f68b029e93e7f0ffa490'},
 ending:{file:'zhijian-cta-ending-flow-5375c80db38d.gif',w:720,h:300,frames:72,fps:10,bytes:1286172,sha:'5375c80db38d67a5c1e11514f1c7bfab50311058aa913f90f9a9ca473c612c88'}
};

test('manifest: v7 Flow GIF default, SVG fallback, old GIFs legacy',()=>{
 assert.equal(brandCtaManifest.version,'2026-10-13-v7.1-flow-gif');
 assert.deepEqual(fs.readdirSync(assetDir).filter(f=>f.endsWith('.gif')),[],'GIF payload is hosted, not shipped');
 for(const kind of ['opening','ending']){
  const a=brandCtaAssets[kind],g=GIF[kind];
  assert.equal(a.format,'gif');assert.equal(a.url,GIF_BASE+g.file);assert.equal(a.sha256,g.sha);
  assert.equal(a.width,g.w);assert.equal(a.height,g.h);assert.equal(a.frames,g.frames);assert.equal(a.fps,g.fps);assert.equal(a.bytes,g.bytes);
  assert.match(a.source,/Google Flow Omni 1\.1 Flash/);
  const f=brandCtaSvgAssets[kind];
  assert.equal(f.format,'inline-svg');assert.equal(f.url,undefined);
  const raw=fs.readFileSync(path.join(assetDir,f.file));
  assert.equal(crypto.createHash('sha256').update(raw).digest('hex'),f.sha256);
  assert.equal(f.viewBox,`0 0 ${f.width} ${f.height}`);
  assert.match(raw.toString('utf8'),new RegExp(`viewBox="${f.viewBox}"`));
 }
 assert.equal(brandCtaManifest.fallback.role,'fallback');
 assert.ok(legacyBrandCtaAssets.length>=2&&legacyBrandCtaAssets.every(a=>a.url&&a.sha256&&a.file.endsWith('.gif')));
 assert.ok(legacyBrandCtaAssets.every(a=>!Object.values(brandCtaAssets).some(n=>n.url===a.url)));
});

test('CTA SVGs avoid markup WeChat strips or rejects',()=>{
 // validate.mjs blanks single-line <svg>…</svg>, so the SVG interior is checked here.
 for(const kind of ['opening','ending']){
  const svg=brandCtaSvg(kind);
  assert.doesNotMatch(svg,/\n/);
  for(const bad of [/\sid=/,/\sclass=/,/<image\b/,/<defs\b/,/<use\b/,/<style\b/,/url\(/,/data:/,/<text\b/,/href=/,/\/Users\//,/rgba/,/<filter\b/,/Gradient/,/<\?xml/])
   assert.doesNotMatch(svg,bad,`${kind} contains ${bad}`);
  assert.match(svg,/^<svg xmlns="http:\/\/www\.w3\.org\/2000\/svg" width="100%" viewBox="[^"]+"/);
  assert.match(svg,/style="display:block;width:100%;height:auto;"/);
  assert.match(svg,new RegExp(`data-alt="${brandCtaSvgAssets[kind].alt}"`));
  assert.match(svg,/<path\b/);assert.match(svg,/<animate(?:Transform)?\b[^>]*repeatCount="indefinite"/);
 }
});

test('default emits v7 Flow GIF img, transparent wrapper, unique on reapplication',()=>{
 const a=applyBrandCta(shell);const b=applyBrandCta(a);
 assert.equal(b,a);
 assert.equal(count(b,'opening'),1);assert.equal(count(b,'ending'),1);
 assert.ok(b.indexOf('data-wechat-cta="opening"')<b.indexOf('保留正文'));
 assert.ok(b.indexOf('data-wechat-cta="ending"')>b.indexOf('保留正文'));
 const sections=ctaSections(b);assert.equal(sections.length,2);
 for(const s of sections){assert.match(s,/data-zhijian-cta="v7-flow-gif"/);assert.doesNotMatch(s,/background/i);}
 // Paper padding keeps the character off the article card's top and bottom edges (1.18.1).
 assert.match(sections[0],/padding:24px 0 0;/);assert.match(sections[1],/padding:0 0 28px;/);
 for(const kind of ['opening','ending']){
  const g=GIF[kind];
  const img=b.match(new RegExp(`<img [^>]*data-wechat-cta-image="${kind}"[^>]*>`))[0];
  assert.match(img,new RegExp(`src="${GIF_BASE+g.file}"`));
  assert.match(img,new RegExp(`width="${g.w}" height="${g.h}"`));
  assert.match(img,new RegExp(`alt="${brandCtaAssets[kind].alt}"`));
  assert.match(img,/style="display:block;width:100%;max-width:360px;height:auto;margin:0 auto;border:0;"/);
  assert.doesNotMatch(img,/background|border:[^0]/i);
 }
 assert.doesNotMatch(b,/<svg\b/);
 assert.equal(brandCtaImg('opening'),b.match(/<img [^>]*data-wechat-cta-image="opening"[^>]*>/)[0]);
 assert.throws(()=>applyBrandCta(shell,{style:'png'}));
});

test('--cta-style svg style emits the 1.17.0 inline SVG; style switches replace, never stack',()=>{
 const svg=applyBrandCta(shell,{style:'svg'});
 for(const s of ctaSections(svg)){assert.match(s,/data-zhijian-cta="v6"/);assert.doesNotMatch(s,/background/i);}
 assert.equal(count(svg,'opening'),1);assert.equal(count(svg,'ending'),1);
 assert.doesNotMatch(svg,/<img\b/);assert.match(svg,/<svg\b[^>]*data-zhijian-cta="ending"/);
 assert.equal(applyBrandCta(svg,{style:'svg'}),svg);
 const gif=applyBrandCta(shell);
 assert.equal(applyBrandCta(svg),gif,'svg -> gif');
 assert.equal(applyBrandCta(gif,{style:'svg'}),svg,'gif -> svg');
});

test('dedupe across v5 GIF, v6 SVG and v7 GIF existing CTAs',()=>{
 const v5=legacyBrandCtaAssets.find(a=>a.file.includes('-opening-'));
 const v5End=legacyBrandCtaAssets.find(a=>a.file.includes('-ending-'));
 const v5Html=shell.replace('<p>',`<section data-wechat-cta="opening" style="background-color:#FFFFFF;"><img data-wechat-cta-image="opening" src="${v5.url}" alt="x" /></section><p>`).replace('</section><!--',`<img src="${v5End.url}"></section><!--`);
 const v6Html=applyBrandCta(shell,{style:'svg'});
 const v7Html=applyBrandCta(shell);
 const loose=shell.replace('<p>',`<img src="${GIF_BASE+GIF.opening.file}?v=1"><img src="https://mmbiz.qpic.cn/x/${GIF.ending.file}"><p>`);
 for(const input of [v5Html,v6Html,v7Html,loose]){
  for(const style of ['gif','svg']){
   const out=applyBrandCta(input,{style});
   assert.equal(count(out,'opening'),1);assert.equal(count(out,'ending'),1);
   assert.equal((out.match(/<img\b/g)||[]).length,style==='gif'?2:0);
   assert.equal((out.match(/<svg\b/g)||[]).length,style==='svg'?2:0);
   assert.equal(out,applyBrandCta(shell,{style}));
  }
  const none=applyBrandCta(input,{mode:'none'});
  assert.doesNotMatch(none,/data-wechat-cta|<img|<svg/);
 }
});

test('ending order: end-mark, topics, then ending CTA, for both styles',()=>{
 const full='<section data-wechat-root="article"><p>保留正文。</p><section data-wechat-block="end-mark"></section><section data-wechat-topics="1"></section></section><!-- 整体背景容器结束 -->';
 for(const style of ['gif','svg']){
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
 // Our own animated CTA SVG, even unwrapped, must not count as a user opener.
 const loose=shell.replace('<p>',brandCtaSvg('opening')+'<svg><rect /></svg><p>');
 const a=applyBrandCta(loose,{style:'svg'});assert.equal(count(a,'opening'),1);assert.equal(count(a,'ending'),1);
 assert.equal((a.match(/data-zhijian-cta="opening"/g)||[]).length,1);
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
 assert.equal((a.match(/data-wechat-cta-image/g)||[]).length,2,'only the two fresh v7 CTA images');
 assert.match(a,/example.com\/user.png/);
 assert.equal(count(a,'opening'),1);assert.equal(count(a,'ending'),1);
});

test('real converter default, components, SVG and opt-out routes',()=>{
 for(const [args,opening,ending,svg] of [[[],1,1,false],[['--components'],1,1,false],[['--cover','--cover-template','xiaolan-terminal'],0,1,true],[['--brand-cta','none'],0,0,false],[['--brand-cta','ending'],0,1,false],[['--cta-style','svg'],1,1,false],[['--cta-style','gif'],1,1,false]]){
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'cta-convert-'));
  try{
   fs.writeFileSync(path.join(dir,'article.md'),'---\ntitle: 验收文章\n---\n\n## 正文\n\n正文保留。\n');
   const r=spawnSync(process.execPath,[path.join(root,'scripts/convert.mjs'),path.join(dir,'*.md'),'--no-open',...args],{encoding:'utf8'});
   assert.equal(r.status,0,r.stderr);const h=fs.readFileSync(path.join(dir,'article_wechat.html'),'utf8');
   assert.equal(count(h,'opening'),opening);assert.equal(count(h,'ending'),ending);
   assert.equal(stripCta(h).replace(/<section data-wechat-block="end-mark"[\s\S]*?<\/section>/,'').includes('<svg'),svg);assert.match(h,/正文保留/);
   for(const s of ctaSections(h)) assert.doesNotMatch(s,/background/i);
   if(!args.includes('svg')&&!args.includes('--cover')&&ending) assert.match(h,/data-zhijian-cta="v7-flow-gif"/);
   if(args.includes('svg')) assert.match(h,/data-zhijian-cta="v6"/);
   assert.equal(validateHtml(h).errors.length,0,JSON.stringify(validateHtml(h).errors));
  }finally{fs.rmSync(dir,{recursive:true,force:true});}
 }
});

test('converter rejects an unknown --cta-style',()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'cta-bad-'));
 try{
  fs.writeFileSync(path.join(dir,'a.md'),'正文\n');
  const r=spawnSync(process.execPath,[path.join(root,'scripts/convert.mjs'),path.join(dir,'a.md'),'--no-open','--cta-style','png'],{encoding:'utf8'});
  assert.notEqual(r.status,0);assert.match(r.stderr,/cta-style/);
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});

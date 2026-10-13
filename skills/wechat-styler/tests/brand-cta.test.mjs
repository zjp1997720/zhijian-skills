import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { applyBrandCta, brandCtaAssets, brandCtaManifest, brandCtaSvg, legacyBrandCtaAssets } from '../scripts/brand-cta.mjs';
import { validateHtml } from '../scripts/validate.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const assetDir=path.join(root,'assets/brand-cta');
const shell = '<section data-wechat-root="article"><p>保留正文。</p></section><!-- 整体背景容器结束 -->';
const count=(s,k)=>(s.match(new RegExp(`data-wechat-cta="${k}"`,'g'))||[]).length;
const ctaSections=s=>s.match(/<section\b[^>]*data-wechat-cta="(?:opening|ending)"[^>]*>/g)||[];
const stripCta=s=>s.replace(/<section\b[^>]*data-wechat-cta="(?:opening|ending)"[^>]*>[\s\S]*?<\/section>/g,'');

test('manifest records inline SVG assets that match the shipped files',()=>{
 assert.equal(brandCtaManifest.version,'2026-10-13-v6-svg');
 assert.deepEqual(fs.readdirSync(assetDir).filter(f=>f.endsWith('.gif')),[],'GIF payload is no longer shipped');
 for(const kind of ['opening','ending']){
  const a=brandCtaAssets[kind];
  assert.equal(a.format,'inline-svg');assert.equal(a.url,undefined);
  const raw=fs.readFileSync(path.join(assetDir,a.file));
  assert.equal(crypto.createHash('sha256').update(raw).digest('hex'),a.sha256);
  assert.equal(a.viewBox,`0 0 ${a.width} ${a.height}`);
  assert.match(raw.toString('utf8'),new RegExp(`viewBox="${a.viewBox}"`));
 }
 assert.ok(legacyBrandCtaAssets.length>=2&&legacyBrandCtaAssets.every(a=>a.url&&a.sha256&&a.file.endsWith('.gif')));
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
  assert.match(svg,new RegExp(`data-alt="${brandCtaAssets[kind].alt}"`));
  assert.match(svg,/<path\b/);assert.match(svg,/<animate(?:Transform)?\b[^>]*repeatCount="indefinite"/);
 }
});

test('default inserts once at both ends, transparent, and reapplication stays unique',()=>{
 const a=applyBrandCta(shell);const b=applyBrandCta(a);
 assert.equal(b,a);
 assert.equal(count(b,'opening'),1);assert.equal(count(b,'ending'),1);
 assert.ok(b.indexOf('data-wechat-cta="opening"')<b.indexOf('保留正文'));
 assert.ok(b.indexOf('data-wechat-cta="ending"')>b.indexOf('保留正文'));
 const sections=ctaSections(b);assert.equal(sections.length,2);
 for(const s of sections){assert.match(s,/data-zhijian-cta="v6"/);assert.doesNotMatch(s,/background/i);}
 assert.doesNotMatch(b,/<img\b/);
});

test('explicit and existing user SVG opener suppress greeting, retain ending',()=>{
 for(const [h,opts] of [[shell,{cover:true}],[shell.replace('<p>','<svg><animate /></svg><p>'),{}]]){
  const a=applyBrandCta(h,opts);assert.equal(count(a,'opening'),0);assert.equal(count(a,'ending'),1);
 }
 // Our own animated CTA SVG, even unwrapped, must not count as a user opener.
 const loose=shell.replace('<p>',brandCtaSvg('opening')+'<svg><rect /></svg><p>');
 const a=applyBrandCta(loose);assert.equal(count(a,'opening'),1);assert.equal(count(a,'ending'),1);
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
 assert.doesNotMatch(a,/\.gif/);assert.doesNotMatch(a,/data-wechat-cta-image/);
 assert.match(a,/example.com\/user.png/);
 assert.equal(count(a,'opening'),1);assert.equal(count(a,'ending'),1);
});

test('real converter default, components, SVG and opt-out routes',()=>{
 for(const [args,opening,ending,svg] of [[[],1,1,false],[['--components'],1,1,false],[['--cover','--cover-template','xiaolan-terminal'],0,1,true],[['--brand-cta','none'],0,0,false],[['--brand-cta','ending'],0,1,false]]){
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'cta-convert-'));
  try{
   fs.writeFileSync(path.join(dir,'article.md'),'---\ntitle: 验收文章\n---\n\n## 正文\n\n正文保留。\n');
   const r=spawnSync(process.execPath,[path.join(root,'scripts/convert.mjs'),path.join(dir,'*.md'),'--no-open',...args],{encoding:'utf8'});
   assert.equal(r.status,0,r.stderr);const h=fs.readFileSync(path.join(dir,'article_wechat.html'),'utf8');
   assert.equal(count(h,'opening'),opening);assert.equal(count(h,'ending'),ending);
   assert.equal(stripCta(h).replace(/<section data-wechat-block="end-mark"[\s\S]*?<\/section>/,'').includes('<svg'),svg);assert.match(h,/正文保留/);
   for(const s of ctaSections(h)) assert.doesNotMatch(s,/background/i);
   assert.equal(validateHtml(h).errors.length,0,JSON.stringify(validateHtml(h).errors));
  }finally{fs.rmSync(dir,{recursive:true,force:true});}
 }
});

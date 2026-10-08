import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { applyBrandCta, brandCtaAssets } from '../scripts/brand-cta.mjs';
const shell = '<section data-wechat-root="article"><p>保留正文。</p></section><!-- 整体背景容器结束 -->';
const count=(s,k)=>(s.match(new RegExp(`data-wechat-cta="${k}"`,'g'))||[]).length;
test('default inserts once at both ends and reapplication stays unique',()=>{
 const a=applyBrandCta(shell);const b=applyBrandCta(a);
 assert.equal(count(b,'opening'),1);assert.equal(count(b,'ending'),1);
 assert.ok(b.indexOf('data-wechat-cta="opening"')<b.indexOf('保留正文'));
 assert.ok(b.indexOf('data-wechat-cta="ending"')>b.indexOf('保留正文'));
});
test('explicit and existing SVG opener suppress greeting, retain ending',()=>{
 for(const [h,opts] of [[shell,{cover:true}],[shell.replace('<p>','<svg><animate /></svg><p>'),{}]]){
  const a=applyBrandCta(h,opts);assert.equal(count(a,'opening'),0);assert.equal(count(a,'ending'),1);
 }
});
test('none removes owned assets only; ending option does not add greeting',()=>{
 const a=applyBrandCta(applyBrandCta(shell),{mode:'none'});assert.equal(count(a,'opening'),0);assert.equal(count(a,'ending'),0);assert.match(a,/保留正文/);
 assert.equal(count(applyBrandCta(shell,{mode:'ending'}),'opening'),0);
 assert.throws(()=>applyBrandCta(shell,{mode:'bad'}));
});
test('raw repeated stock image is normalized, unrelated image is preserved',()=>{
 const a=applyBrandCta(shell.replace('<p>',`<img src="${brandCtaAssets.opening.url}"><img src="https://example.com/user.png"><p>`));
 assert.equal(a.split(brandCtaAssets.opening.url).length-1,1);assert.match(a,/example.com\/user.png/);
});
test('real converter default, components, SVG and opt-out routes',()=>{
 const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
 for(const [args,opening,ending,svg] of [[[],1,1,false],[['--components'],1,1,false],[['--cover','--cover-template','xiaolan-terminal'],0,1,true],[['--brand-cta','none'],0,0,false],[['--brand-cta','ending'],0,1,false]]){
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'cta-convert-'));
  try{
   fs.writeFileSync(path.join(dir,'article.md'),'---\ntitle: 验收文章\n---\n\n## 正文\n\n正文保留。\n');
   const r=spawnSync(process.execPath,[path.join(root,'scripts/convert.mjs'),path.join(dir,'*.md'),...args],{encoding:'utf8'});
   assert.equal(r.status,0,r.stderr);const h=fs.readFileSync(path.join(dir,'article_wechat.html'),'utf8');
   assert.equal(count(h,'opening'),opening);assert.equal(count(h,'ending'),ending);assert.equal(h.includes('<svg'),svg);assert.match(h,/正文保留/);
  }finally{fs.rmSync(dir,{recursive:true,force:true});}
 }
});

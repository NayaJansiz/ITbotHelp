// jsdom smoke test of the picture-binding switch (Part 2D item 1).
// Setup: npm i jsdom ; build a fixture site first (see HANDOFF-BUILD.md fifth-account item-1 log): needs site-dir with packs built with --intake containing proposals for subject 11 (tools/test_oneshot.py does not need this; run_all.sh builds it).
// run: node tools/smoke_pics.js <site-dir> <modules-dir containing node_modules/jsdom>
const root=require('path').resolve(process.argv[2]||'site'), mods=process.argv[3]||'.';
const {JSDOM}=require(require('path').resolve(mods,'node_modules/jsdom')),fs=require('fs'),path=require('path');
const html=fs.readFileSync(root+'/index.html','utf8').replace(/<link[^>]*googleapis[^>]*>/,'');
const dom=new JSDOM(html,{runScripts:'dangerously',url:'http://localhost/',pretendToBeVisual:true,beforeParse(w){
 w.fetch=(u)=>{const f=path.join(root,decodeURIComponent(u));return fs.existsSync(f)?Promise.resolve({ok:true,status:200,text:()=>Promise.resolve(fs.readFileSync(f,'utf8'))}):Promise.resolve({ok:false,status:404})};
 w.TextEncoder=TextEncoder;w.crypto=require('crypto').webcrypto;w.URL.createObjectURL=()=>'blob:x';w.URL.revokeObjectURL=()=>{};}});
const w=dom.window,d=w.document,$=id=>d.getElementById(id),sleep=ms=>new Promise(r=>setTimeout(r,ms));
let bad=0;const ok=(n,c)=>{console.log((c?'PASS  ':'FAIL  ')+n);if(!c)bad++;};
(async()=>{
 await sleep(300);
 $('yearSel').value='3';$('yearSel').onchange();$('subjSel').value='11';$('subjSel').onchange();await sleep(600);
 const sj=JSON.parse(fs.readFileSync(root+'/packs/11/site.json','utf8'));const keys=sj.keys;
 const lec=fs.readFileSync(root+'/packs/11/lectures/par5.md','utf8');
 const line=lec.split('\n').filter(l=>l.split(' ').length>8)[0].replace(/[*#|>_`]/g,' ').split(/\s+/).filter(Boolean).slice(0,15).join(' ');
 const P=Object.keys(sj.p).filter(k=>keys.includes(k)); ok('fixture has >=3 proposals in subject 11',P.length>=3);
 // P[0]: Claude uses_image true; P[1]: uses_image false; P[2]: not stated
 const reply=[{id:P[0],a:'A',src:'LECTURE',q:line,e:'x',uses_image:true},{id:P[1],a:'A',src:'LECTURE',q:line,e:'x',uses_image:false},{id:P[2],a:'A',src:'LECTURE',q:line,e:'x'}].map(JSON.stringify).join('\n');
 $('reply').value=reply;$('btnCheck').click();await sleep(500);
 $('rvFilter').value='all';$('rvFilter').onchange();
 const cs=[...$('cards').children],chk=cs.map(c=>c.querySelector('input[type=checkbox]'));
 ok('3 cards with picture + switch',chk.every(Boolean)&&cs.every(c=>c.querySelector('.pic img')));
 ok('img src points at media/<file>',cs[0].querySelector('.pic img').src.includes('/media/'));
 ok('defaults: true->on, false->off, unstated->off',chk[0].checked&&!chk[1].checked&&!chk[2].checked);
 ok('Claude-ticked default is NOT shown as a student edit',!cs[0].classList.contains('edited'));
 $('rvFilter').value='att';$('rvFilter').onchange();
 ok('filter keeps the card with no uses_image visible, hides the verified default ones',cs[0].hidden&&cs[1].hidden&&!cs[2].hidden);
 chk[2].checked=true;chk[2].onchange();chk[0].checked=false;chk[0].onchange();
 ok('student changes are marked edited',cs[2].classList.contains('edited')&&cs[0].classList.contains('edited'));
 let files={};w.HTMLAnchorElement.prototype.click=function(){files[this.download]=this.href};
 const blobs=[];w.URL.createObjectURL=b=>{blobs.push(b);return 'blob:'+blobs.length};
 $('btnReplyFile').click();await sleep(200);
 const txt=await blobs[blobs.length-1].text();const lines=txt.trim().split('\n').map(JSON.parse);
 const by=Object.fromEntries(lines.map(l=>[l.id,l]));
 ok('reply: ticked card carries img id; unticked has none',by[P[2]].img===sj.p[P[2]]&&!by[P[0]].img&&!by[P[1]].img);
 ok('reply: changes flagged img_edited',by[P[2]].img_edited===true&&by[P[0]].img_edited===true&&!by[P[1]].img_edited);
 $('btnSummary').click();await sleep(200);const sum=await blobs[blobs.length-1].text();
 ok('summary has the pictures section',sum.includes('## ربط الصور')&&sum.includes(P[2])&&sum.includes('الطالب أزال ربط الصورة'));
 // persistence: re-run check with same reply -> saved state restored
 $('btnCheck').click();await sleep(500);const c2=[...$('cards').children].map(c=>c.querySelector('input[type=checkbox]'));
 ok('switch state restored from localStorage',c2[2].checked&&!c2[0].checked);
 console.log(bad?'SMOKE FAILED':'smoke_pics OK');process.exit(bad?1:0);
})().catch(e=>{console.error('ERR',e);process.exit(1)});

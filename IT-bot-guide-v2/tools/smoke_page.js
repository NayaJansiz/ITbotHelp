// jsdom smoke test of site/index.html review screen (lecture picker flow). Setup: npm i jsdom ; run: node tools/smoke_page.js site (needs site/packs built by build_site.py; uses subject 11, every lecture ticked)
const {JSDOM}=require('jsdom'),fs=require('fs'),path=require('path');
const root=require('path').resolve(process.argv[2]||'site');
const html=fs.readFileSync(root+'/index.html','utf8').replace(/<link[^>]*googleapis[^>]*>/,'');
const dom=new JSDOM(html,{runScripts:'dangerously',url:'http://localhost/',pretendToBeVisual:true,beforeParse(w){
 w.fetch=(u)=>{const f=path.join(root,decodeURIComponent(u));return fs.existsSync(f)?Promise.resolve({ok:true,status:200,text:()=>Promise.resolve(fs.readFileSync(f,'utf8'))}):Promise.resolve({ok:false,status:404})};
 w.TextEncoder=TextEncoder;w.crypto=require('crypto').webcrypto;w.URL.createObjectURL=()=>'blob:x';w.URL.revokeObjectURL=()=>{};}});
const w=dom.window,d=w.document,$=id=>d.getElementById(id),sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 await sleep(300);
 $('yearSel').value='3';$('yearSel').onchange();
 $('subjSel').value='11';$('subjSel').onchange();await sleep(600);
 const sj=JSON.parse(fs.readFileSync(root+'/packs/11/site.json','utf8'));const keys=sj.keys;
 const lec=fs.readFileSync(root+'/packs/11/lectures/par5.md','utf8');
 const line=lec.split('\n').filter(l=>l.split(' ').length>8)[0].replace(/[*#|>_`]/g,' ').split(/\s+/).filter(Boolean).slice(0,15).join(' ');
 const reply=[{id:keys[0],a:'A',src:'LECTURE',q:line,e:'شرح'},{id:keys[1],src:'NOT-FOUND'},{id:keys[2],a:'B',src:'INFERRED',e:'x'}].map(JSON.stringify).join('\n');
 $('reply').value=reply;$('btnCheck').click();await sleep(500);
 console.log('cards',$('cards').children.length,'review hidden?',$('review').hidden);
 const cs=$('cards').children;
 console.log('badges',[...cs].map(c=>c.querySelector('.badge').textContent));
 // edit 2nd card: choose A with no quote
 const sel=cs[1].querySelector('select');sel.value='A';sel.onchange();
 const ta=cs[2].querySelector('textarea');ta.value='شرح جديد';ta.oninput();
 console.log('after',[...cs].map(c=>c.querySelector('.badge').textContent));
 console.log('btn',$('btnReplyFile').textContent,$('btnSummary').disabled);
 let saved={};w.HTMLAnchorElement.prototype.click=function(){saved[this.download]=1};
 $('btnSummary').click();await sleep(200);console.log('downloads',Object.keys(saved));
 $('btnReplyFile').click();await sleep(200);console.log('downloads',Object.keys(saved));
 process.exit(0);
})().catch(e=>{console.error('ERR',e);process.exit(1)});

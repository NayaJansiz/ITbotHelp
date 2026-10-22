// jsdom smoke test of the lecture picker + one-run pack (site/index.html).
// Setup: npm i jsdom (in any folder). Run by tools/test_oneshot.py, or by hand:
//   node tools/smoke_oneshot.js <site-dir (index.html + packs/)> <modules-dir containing node_modules/jsdom> <dir with tools/make_packs.py --mode all output for subject 11 (all-1.md ...)>
const path = require('path'), fs = require('fs');
const root = path.resolve(process.argv[2] || 'site'), mods = process.argv[3] || '.', pk11 = process.argv[4];
const { JSDOM, VirtualConsole } = require(path.resolve(mods, 'node_modules/jsdom'));
const html = fs.readFileSync(root + '/index.html', 'utf8').replace(/<link[^>]*googleapis[^>]*>/, '');
const errs = [], saved = [], blobs = new Map(); let nblob = 0;
class FakeBlob { constructor(p, o) { this.text = p.join(''); this.type = (o || {}).type; } }
const vc = new VirtualConsole(); vc.on('jsdomError', e => errs.push(String(e.message || e)));
const dom = new JSDOM(html, { runScripts: 'dangerously', url: 'http://localhost/', pretendToBeVisual: true, virtualConsole: vc, beforeParse(w) {
  w.fetch = (u) => { const f = path.join(root, decodeURIComponent(u)); return fs.existsSync(f) ? Promise.resolve({ ok: true, status: 200, text: () => Promise.resolve(fs.readFileSync(f, 'utf8')) }) : Promise.resolve({ ok: false, status: 404 }); };
  w.TextEncoder = TextEncoder; w.crypto = require('crypto').webcrypto; w.Blob = FakeBlob; w.URL.createObjectURL = (b) => { const u = 'blob:http://localhost/' + (++nblob); blobs.set(u, b); return u; }; w.URL.revokeObjectURL = () => {};
  w.HTMLAnchorElement.prototype.click = function () { saved.push({ name: this.download, text: (blobs.get(this.href) || {}).text }); }; } });
const w = dom.window, d = w.document, $ = id => d.getElementById(id), sleep = ms => new Promise(r => setTimeout(r, ms));
let bad = 0; const ok = (n, c, x) => { console.log((c ? 'PASS  ' : 'FAIL  ') + n + (!c && x !== undefined ? '  ' + x : '')); if (!c) bad++; };
const fire = (el, type) => el.dispatchEvent(new w.Event(type, { bubbles: true }));
const pick = (y, s) => { $('yearSel').value = String(y); fire($('yearSel'), 'change'); $('subjSel').value = String(s); fire($('subjSel'), 'change'); };
const boxes = () => [...$('lecList').querySelectorAll('input')], btns = () => [...$('dlBox').children];
(async () => {
  await sleep(300);
  const sj = JSON.parse(fs.readFileSync(root + '/packs/11/site.json', 'utf8')), lecDir = root + '/packs/11/lectures/';
  pick(3, 11); await sleep(600);
  ok('subject 11: 9 lectures listed, all ticked', boxes().length === 9 && boxes().every(c => c.checked), boxes().length);
  ok('subject 11: 2 download buttons (over MAX_CHARS) and the summary says so', btns().length === 2 && /2 ملفات/.test($('lecSum').textContent), btns().map(b => b.textContent));
  ok('pack card + reply card visible', $('packCard').classList.contains('is-visible') && $('replyCard').classList.contains('is-visible'));
  btns()[0].click(); await sleep(400);
  ok('part 1 downloaded as 11-lectures-part1of2.md', saved.length === 1 && saved[0].name === '11-lectures-part1of2.md', saved.map(s => s.name));
  if (pk11 && saved.length) ok('page-built part 1 is IDENTICAL to make_packs.py --mode all all-1.md', saved[0].text === fs.readFileSync(path.join(pk11, 'all-1.md'), 'utf8'));
  btns()[1].click(); await sleep(400);
  if (pk11 && saved.length > 1) ok('page-built part 2 is IDENTICAL to make_packs.py --mode all all-2.md', saved[1].text === fs.readFileSync(path.join(pk11, 'all-2.md'), 'utf8'));
  $('ghUser').value = 'tester'; fire($('ghUser'), 'input');
  ok('PDF upload button points at the student\'s fork, inbox/<subject id>/', /github\.com\/tester\/IT-bot\/upload\/main\/inbox\/11$/.test($('btnPdf').href) && !$('btnPdf').classList.contains('is-disabled'), $('btnPdf').href);
  // untick -> fewer lectures, one pack
  const keep = ['par5.md', 'par6.md'];
  boxes().forEach(c => { c.checked = keep.includes(c.value); }); fire(boxes()[0], 'change'); await sleep(100);
  ok('2 lectures ticked -> one download button', btns().length === 1 && /ملف واحد/.test($('lecSum').textContent), btns().map(b => b.textContent));
  saved.length = 0; btns()[0].click(); await sleep(400);
  const t = saved[0] ? saved[0].text : '';
  ok('one-run pack has exactly the ticked lectures and ALL questions', (t.match(/\n# LECTURE \(/g) || []).length === 2 && t.includes('# LECTURE (par5.md)') && t.includes('# LECTURE (par6.md)') && !t.includes('# LECTURE (par1.md)') && (t.match(/\n### y3:/g) || []).length === Object.keys(sj.t).length, (t.match(/\n### y3:/g) || []).length + ' vs ' + Object.keys(sj.t).length);
  boxes().forEach(c => { c.checked = false; }); fire(boxes()[0], 'change'); await sleep(100);
  ok('nothing ticked -> cards hidden', !$('packCard').classList.contains('is-visible') && /واحدة/.test($('lecSum').textContent));
  boxes().forEach(c => { c.checked = true; }); fire(boxes()[0], 'change'); await sleep(100);
  // reply: real quotes from two lectures (one with a WRONG "lec" hint, one with none), a NOT-FOUND, a fabricated quote
  const quote = f => { const s = fs.readFileSync(lecDir + f, 'utf8').split('\n').filter(l => !l.startsWith('<!--') && l.split(/\s+/).length > 9)[3]; return s.replace(/[*#|>_`]/g, ' ').split(/\s+/).filter(Boolean).slice(0, 14).join(' '); };
  const K = sj.keys;
  const reply = [{ id: K[0], a: 'A', src: 'LECTURE', lec: 'par5.md', ref: 'x', q: quote('par5.md'), e: 'شرح' }, { id: K[1], a: 'A', src: 'LECTURE', lec: 'par1.md', ref: 'x', q: quote('par7.md'), e: 'شرح' },
    { id: K[2], a: 'B', src: 'LECTURE', ref: 'x', q: quote('par2-sec2.md'), e: 'شرح' }, { id: K[3], src: 'NOT-FOUND' }, { id: K[3], src: 'NOT-FOUND' }, { id: K[4], src: 'NOT-FOUND' }, { id: K[4], a: 'A', src: 'LECTURE', lec: 'par3.md', q: quote('par3.md'), e: 'x' },
    { id: K[5], a: 'A', src: 'LECTURE', lec: 'par5.md', q: 'هذه جملة مخترعة لا وجود لها في أي محاضرة إطلاقاً', e: 'x' }].map(JSON.stringify).join('\n');
  $('reply').value = reply; $('btnCheck').click(); await sleep(900);
  const chips = [...$('sum').children].map(c => c.textContent);
  ok('reply checked: 4 verified (wrong/missing "lec" hints still found), 1 rejected, 1 NOT-FOUND (2 repeated lines -> 1; the NOT-FOUND that also has an answer -> dropped)', chips.includes('✓ موثّق: 4') && chips.includes('✗ مرفوض: 1') && chips.includes('⚠ لم يوجد: 1'), chips);
  ok('missing-answers note lists the questions with no reply line', !$('missing').hidden && /لا يوجد رد على/.test($('missing').textContent));
  ok('review cards built for the non-rejected lines (4 verified + 1 NOT-FOUND)', $('cards').children.length === 5, $('cards').children.length);
  saved.length = 0; $('btnReplyFile').click(); await sleep(400);
  ok('reply file name is all-<sha8>.jsonl and keeps the "lec" field', saved.length === 1 && /^all-[0-9a-f]{8}\.jsonl$/.test(saved[0].name) && saved[0].text.split('\n').filter(Boolean).every(l => JSON.parse(l)) && saved[0].text.includes('"lec":"par5.md"'), saved.map(s => s.name));
  saved.length = 0; $('btnSummary').click(); await sleep(400);
  ok('summary file named all-<sha8>.summary.md and lists the ticked lectures', saved.length === 1 && /^all-[0-9a-f]{8}\.summary\.md$/.test(saved[0].name) && saved[0].text.includes('- المحاضرات: par1.md'), saved.map(s => s.name));
  // a subject WITHOUT lectures keeps one INFERRED file
  const inf = JSON.parse(fs.readFileSync(root + '/packs/index.json', 'utf8')).subjects.find(s => s.inferred); if (inf) pick(inf.year, inf.id);
  if (inf) { await sleep(500); saved.length = 0;
    ok('subject without lectures: no checklist, one INFERRED download', $('lecField').hidden && btns().length === 1 && /ملف الأسئلة/.test(btns()[0].textContent), btns().map(b => b.textContent));
    btns()[0].click(); await sleep(400);
    ok('INFERRED file is the packs/<id>/INFERRED.md', saved.length === 1 && saved[0].text === fs.readFileSync(root + '/packs/' + inf.id + '/INFERRED.md', 'utf8'), saved.map(s => s.name)); }
  ok('no script errors in the page', errs.length === 0, errs);
  process.exit(bad ? 1 : 0);
})().catch(e => { console.error('ERR', e); process.exit(1); });

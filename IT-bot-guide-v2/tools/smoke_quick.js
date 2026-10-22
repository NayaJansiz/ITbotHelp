// jsdom smoke test of the QUICK mode (site/index.html): student uploads a lecture PDF + a Telegram export -> pack -> reply -> zip for the pull request.
// Run by tools/test_quick.py (which builds the inputs and checks the zip afterwards). By hand:
//   node tools/smoke_quick.js <site-dir> <modules-dir with node_modules/jsdom and node_modules/pdfjs-dist> <lecture.pdf> <export-folder> <out-dir> '["D","B","A"]'
const path = require('path'), fs = require('fs');
const root = path.resolve(process.argv[2]), mods = process.argv[3], pdfPath = process.argv[4], tgDir = process.argv[5], out = process.argv[6], stored = JSON.parse(process.argv[7] || '["A","A","A"]');   // stored = the letters already stored for the 3 existing questions, in export order
const { JSDOM, VirtualConsole } = require(path.resolve(mods, 'node_modules/jsdom'));
const pdfjs = require(path.resolve(mods, 'node_modules/pdfjs-dist/legacy/build/pdf.js'));
const html = fs.readFileSync(root + '/index.html', 'utf8').replace(/<link[^>]*googleapis[^>]*>/, '');
const errs = [], saved = [], blobs = new Map(); let nblob = 0;
class FakeBlob { constructor(p, o) { this.buf = Buffer.concat(p.map(x => Buffer.from(typeof x === 'string' ? x : x))); this.type = (o || {}).type; } get text() { return this.buf.toString('utf8'); } }
const vc = new VirtualConsole(); vc.on('jsdomError', e => errs.push(String(e.message || e)));
const dom = new JSDOM(html, { runScripts: 'dangerously', url: 'http://localhost/', pretendToBeVisual: true, virtualConsole: vc, beforeParse(w) {
  w.fetch = (u) => { const f = path.join(root, decodeURIComponent(u)); return fs.existsSync(f) ? Promise.resolve({ ok: true, status: 200, text: () => Promise.resolve(fs.readFileSync(f, 'utf8')) }) : Promise.resolve({ ok: false, status: 404 }); };
  w.TextEncoder = TextEncoder; Object.defineProperty(w, 'crypto', { value: require('crypto').webcrypto, configurable: true }); w.Blob = FakeBlob; w.URL.createObjectURL = (b) => { const u = 'blob:http://localhost/' + (++nblob); blobs.set(u, b); return u; }; w.URL.revokeObjectURL = () => {};
  w.HTMLAnchorElement.prototype.click = function () { const b = blobs.get(this.href) || {}; saved.push({ name: this.download, text: b.text, buf: b.buf }); };
  // the real pdf.js (Node build) stands in for the CDN copy; the Uint8Array is re-created in the Node realm
  w.pdfjsLib = { GlobalWorkerOptions: {}, getDocument: o => pdfjs.getDocument({ data: new Uint8Array(o.data), verbosity: 0, useSystemFonts: true }) };
} });
const w = dom.window, d = w.document, $ = id => d.getElementById(id), sleep = ms => new Promise(r => setTimeout(r, ms));
let bad = 0; const ok = (n, c, x) => { console.log((c ? 'PASS  ' : 'FAIL  ') + n + (!c && x !== undefined ? '  ' + x : '')); if (!c) bad++; };
const setFiles = (el, files) => { Object.defineProperty(el, 'files', { value: files, configurable: true }); el.onchange(); };
const mkFile = (p, type) => new w.File([fs.readFileSync(p)], path.basename(p), { type });
const pick = (y, s) => { $('yearSel').value = String(y); $('yearSel').onchange(); $('subjSel').value = String(s); $('subjSel').onchange(); };
(async () => {
  await sleep(300); pick(3, 11); await sleep(700);
  ok('quick card is shown once a subject is picked', $('quickCard').classList.contains('is-visible') && $('btnQuick').disabled);
  setFiles($('qPdf'), [mkFile(pdfPath, 'application/pdf')]);
  ok('lecture number is guessed from the file name (3)', $('qNum0') && $('qNum0').value === '3', $('qNum0') && $('qNum0').value);
  const tgFiles = fs.readdirSync(tgDir).filter(f => /^messages\d*\.html$/.test(f)).sort().map(f => mkFile(path.join(tgDir, f), 'text/html'));
  setFiles($('qTg'), tgFiles); ok('button enabled after both uploads', !$('btnQuick').disabled);
  $('qNum0').value = ''; $('btnQuick').click(); await sleep(600);
  ok('missing lecture number -> clear error in the report box', /رقم المحاضرة/.test($('qReport').textContent) && $('qReport').className === 'note--bad', $('qReport').textContent);
  $('qNum0').value = '3'; $('btnQuick').click(); await sleep(2500);
  const rep = $('qReport').textContent; fs.writeFileSync(out + '/report.txt', rep);
  ok('report: 1 lecture converted, questions counted (2 new + 3 existing, 1 duplicate dropped), 1 photo warned', /tdm-lecture-3\.md: 4 صفحة/.test(rep) && /جديد 2/.test(rep) && /موجود 3/.test(rep) && /مكرر في التصدير 1/.test(rep) && /1 صورة في التصدير/.test(rep), rep);
  ok('report warns about the page without text', /1 صفحة بلا نص/.test(rep), rep);
  ok('pack card + reply card visible, one download button', $('packCard').classList.contains('is-visible') && $('replyCard').classList.contains('is-visible') && $('dlBox').children.length === 1, $('dlBox').children.length);
  $('dlBox').children[0].click(); await sleep(500);
  const pack = saved.length ? saved[0].text : ''; fs.writeFileSync(out + '/pack.md', pack);
  ok('pack file is named 11-lectures.md and starts with the task instructions', saved.length === 1 && saved[0].name === '11-lectures.md' && pack.startsWith('# TASK'), saved.map(s => s.name));
  ok('pack has the uploaded lecture with page markers, and only that lecture', (pack.match(/\n# LECTURE \(/g) || []).length === 1 && pack.includes('# LECTURE (tdm-lecture-3.md)') && pack.includes('<!-- p1 -->') && pack.includes('<!-- p2 -->') && pack.includes('Time division multiplexing'));
  ok('page numbers (bare digits) were dropped like ingest_pdf.py does', !/\n7\n/.test(pack.split('# QUESTIONS')[0]));
  const keys = [...pack.matchAll(/^### (\S+)$/mg)].map(m => m[1]); fs.writeFileSync(out + '/keys.json', JSON.stringify(keys));
  ok('5 questions in the pack (3 existing y3: keys + 2 new f: keys)', keys.length === 5 && keys.filter(k => k.startsWith('f:')).length === 2 && keys.filter(k => k.startsWith('y3:')).length === 3, keys);
  const fk = keys.filter(k => k.startsWith('f:')), yk = keys.filter(k => k.startsWith('y3:'));
  // reply: a real quote for one existing and one new question, NOT-FOUND for one, an invented quote for another
  const q1 = 'Time division multiplexing gives each source a fixed time slot in every frame';
  const reply = [{ id: fk[0], a: 'A', src: 'LECTURE', lec: 'tdm-lecture-3.md', ref: 'TDM', q: q1, e: 'كل منبع يأخذ فتحة زمنية ثابتة في كل إطار.' },
    { id: yk[0], a: stored[0], src: 'LECTURE', lec: 'tdm-lecture-3.md', ref: 'TDM', q: 'The frame repeats every 125 microseconds so each slot returns at a regular interval', e: 'شرح' },
    { id: fk[1], src: 'NOT-FOUND' }, { id: yk[1], a: 'B', src: 'LECTURE', lec: 'tdm-lecture-3.md', q: 'this sentence was invented and is not in the lecture at all', e: 'x' }, { id: yk[2], src: 'NOT-FOUND' }].map(JSON.stringify).join('\n');
  $('reply').value = reply; $('btnCheck').click(); await sleep(900);
  const chips = [...$('sum').children].map(c => c.textContent);
  ok('reply checked: 2 verified against the UPLOADED lecture, 1 rejected, 2 not found', chips.includes('✓ موثّق: 2') && chips.includes('✗ مرفوض: 1') && chips.includes('⚠ لم يوجد: 2'), chips);
  ok('review/edit cards exist (edit before sending)', $('cards').children.length === 4, $('cards').children.length);
  // the student edits the explanation of the first card
  const ta = $('cards').querySelector('textarea:not(.q)'); ta.value = 'شرح معدَّل بيد الطالب.'; ta.oninput(); await sleep(100);
  ok('zip button visible and enabled after a check', !$('btnZip').hidden && !$('btnZip').disabled);
  $('ghUser').value = 'tester'; $('ghUser').oninput();
  ok('upload link goes to the ROOT of the fork (the zip holds several folders)', /github\.com\/tester\/IT-bot\/upload\/main$/.test($('btnUpload').href), $('btnUpload').href);
  saved.length = 0; $('btnZip').click(); await sleep(900);
  ok('zip downloaded as pr-11-<sha8>.zip', saved.length === 1 && /^pr-11-[0-9a-f]{8}\.zip$/.test(saved[0].name), saved.map(s => s.name));
  if (saved.length) fs.writeFileSync(out + '/pr.zip', saved[0].buf);
  ok('zip holds replies/ (jsonl + summary), intake/ (new questions) and sources/ (lecture text)', w.__lastZip && w.__lastZip.length === 4 && w.__lastZip.some(p => /^replies\/11\/quick-[0-9a-f]{8}\.jsonl$/.test(p)) && w.__lastZip.some(p => /^replies\/11\/quick-[0-9a-f]{8}\.summary\.md$/.test(p)) && w.__lastZip.some(p => /^intake\/11\/\d{4}-\d\d-\d\d-[0-9a-f]{8}\.json$/.test(p)) && w.__lastZip.includes('sources/11/tdm-lecture-3.md'), w.__lastZip);
  // token saving: only new / unsolved questions
  $('qOnlyNew').checked = true; $('btnQuick').click(); await sleep(2500);
  const rep2 = $('qReport').textContent; ok('"only new/unsolved" keeps the 2 new questions and skips solved existing ones', /جديد 2/.test(rep2) && /محلول وتخطيته/.test(rep2), rep2);
  // no export file at all -> every question of the subject
  $('qOnlyNew').checked = false; setFiles($('qTg'), []); $('btnQuick').click(); await sleep(2500);
  const sj = JSON.parse(fs.readFileSync(root + '/packs/11/site.json', 'utf8'));
  ok('no export -> all the subject\'s questions go in', new RegExp('الأسئلة: ' + Object.keys(sj.t).length + ' ').test($('qReport').textContent), $('qReport').textContent);
  ok('no page error', errs.length === 0, errs.slice(0, 3));
  console.log(bad ? 'smoke_quick FAILED' : 'smoke_quick OK'); process.exit(bad ? 1 : 0);
})().catch(e => { console.log('CRASH', e.stack || e); process.exit(2); });

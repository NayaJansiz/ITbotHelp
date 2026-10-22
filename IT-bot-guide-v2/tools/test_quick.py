#!/usr/bin/env python3
"""
test_quick.py - the QUICK mode of site/index.html: a student uploads a lecture PDF + a Telegram export on the page, checks Claude's reply, downloads ONE zip for the pull request.
  python tools/test_quick.py --data data --lectures ../lecture-site-engine --node-modules <dir with node_modules/jsdom and node_modules/pdfjs-dist>
Needs: pymupdf (to make a test PDF), beautifulsoup4 (tools/ingest_polls.py), node + jsdom + pdfjs-dist (3.11.x). Skips (and says so) when one is missing.
What it proves, with a real pdf.js, a real jsdom page and the real Python tools:
  A. the page converts the PDF and the export, builds a one-lecture pack, validates the reply against the UPLOADED lecture, lets the student edit, writes the zip;
  B. the zip is a valid zip, holds only NEW files under replies/ intake/ sources/ (what check_pr_paths.py allows);
  C. the new-question keys/fingerprints the page computes are IDENTICAL to tools/ingest_polls.py on the same export;
  D. after "merging" it (register_sources.py + apply_pending.py = the data-writer Action) the new question is solved, with the lecture marker, and nothing existing is overwritten.
"""
import argparse, glob, json, os, shutil, subprocess, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); sys.path.insert(0, HERE)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--data', default='data'); ap.add_argument('--lectures', required=True); ap.add_argument('--node-modules'); a = ap.parse_args()
    try:
        import pymupdf as fitz
    except ImportError:
        try: import fitz
        except ImportError: print('SKIP  test_quick (pip install pymupdf)'); return
    try: import bs4  # noqa
    except ImportError: print('SKIP  test_quick (pip install beautifulsoup4)'); return
    nm = a.node_modules
    if not (nm and os.path.isdir(os.path.join(nm, 'node_modules', 'jsdom')) and os.path.isdir(os.path.join(nm, 'node_modules', 'pdfjs-dist'))):
        print('SKIP  test_quick (--node-modules must hold node_modules/jsdom and node_modules/pdfjs-dist@3.11.x)'); return
    fails = 0
    def check(n, ok, x=''):
        nonlocal fails; print(('PASS  ' if ok else 'FAIL  ') + n + (('  ' + str(x)[:600]) if x and not ok else '')); fails += (not ok)
    with tempfile.TemporaryDirectory() as td:
        # ---- inputs: a PDF (page 3 has no text) and a Telegram HTML export
        pdf = os.path.join(td, 'TDM lecture 3.pdf'); doc = fitz.open()
        for i, body in enumerate(['Time division multiplexing gives each source a fixed time slot in every frame. A frame carries one slot per source.',
                                  'The frame repeats every 125 microseconds so each slot returns at a regular interval. Synchronisation bits mark the frame start.', '']):
            pg = doc.new_page()
            if body: pg.insert_textbox(fitz.Rect(50, 60, 540, 300), body, fontsize=12); pg.insert_text((300, 800), str(i + 1), fontsize=10)
        pg = doc.new_page(); pg.insert_htmlbox(fitz.Rect(50, 60, 540, 400), '<div dir="rtl" style="font-family: sans-serif; font-size:14pt"><p>تعدد الإرسال بتقسيم الزمن يعطي كل منبع فتحة زمنية ثابتة في كل إطار.</p><p>يتكرر الإطار كل 125 ميكروثانية حتى تعود كل فتحة بانتظام.</p></div>')
        ar_ref = pg.get_text(); doc.save(pdf); doc.close()          # page 4 = Arabic, one glyph per text item in pdf.js: the page must still give real words
        rows = json.load(open(os.path.join(a.data, 'questions', 'subject-11.json'), encoding='utf-8'))[:3]
        exp = os.path.join(td, 'export'); os.makedirs(exp)
        def poll(n, q, opts, fwd=''):
            f = f'<div class="forwarded body"><div class="from_name">{fwd}</div></div>' if fwd else ''
            return (f'<div class="message default clearfix" id="message{n}"><div class="body">{f}<div class="media_wrap clearfix"><div class="media_poll"><div class="question bold">{q}</div>'
                    f'<div class="details">Anonymous poll</div><div class="answers">' + ''.join(f'<div class="answer">- {o}</div>' for o in opts) + '</div><div class="total">0 votes</div></div></div></div></div>\n')
        L = 'ABCDEFGHIJ'; letters = [L[r['correct_index']] for r in rows]; h = '<html><body><div class="history">\n<div class="message service" id="message1"><div class="body details">Group created</div></div>\n'
        for i, r in enumerate(rows):
            opts = list(r['options']); opts[0] = opts[0][:1] + '\u0640' + opts[0][1:] if len(opts[0]) > 1 else opts[0]      # tatweel must not change the identity
            h += poll(10 + i, f'{i + 1}- ' + r['question'], opts, 'Rukaia Al Abrash 07.02.2026 01:57:18' if i == 0 else '')
        newq = [('كم فتحة زمنية يعطيها TDM لكل منبع في الإطار ؟', ['فتحة ثابتة واحدة', 'فتحتان', 'عدد عشوائي', 'كل ما سبق خطأ']), ('ما معنى تكرار الإطار كل 125 ميكروثانية ؟', ['يعود لكل منبع دوره بانتظام', 'يتوقف البث', 'يتغير الترددات', 'ليس أي مما سبق'])]
        h += poll(20, '4- ' + newq[0][0], newq[0][1]) + poll(21, '5_ ' + newq[1][0], newq[1][1]) + poll(22, '9- ' + newq[0][0], newq[0][1])    # last one = duplicate of the first new one
        h += '<div class="message default clearfix" id="message30"><div class="body"><div class="media_wrap"><a class="photo_wrap" href="photos/photo_1@19-10-2026_14-28-31.jpg"><img class="photo" src="photos/photo_1@19-10-2026_14-28-31_thumb.jpg"></a></div></div></div>\n</div></body></html>'
        open(os.path.join(exp, 'messages.html'), 'w', encoding='utf-8').write(h)
        os.makedirs(os.path.join(exp, 'photos')); open(os.path.join(exp, 'photos', 'photo_1@19-10-2026_14-28-31.jpg'), 'wb').write(b'\xff\xd8\xff\xe0 fake picture')   # ingest_polls.py reads the picture file; the page ignores pictures
        # ---- the site (packs) built from the real data + lecture repo
        site = os.path.join(td, 'site'); os.makedirs(site); shutil.copy(os.path.join(ROOT, 'site', 'index.html'), site)
        r = subprocess.run([sys.executable, os.path.join(HERE, 'build_site.py'), '--data', a.data, '--lectures', a.lectures, '--subject', '11', '--out', os.path.join(site, 'packs')], capture_output=True, text=True, encoding='utf-8')
        if r.returncode: print(r.stdout[-500:], r.stderr[-500:]); check('build_site for subject 11', False); sys.exit(1)
        idx = {'subjects': [], 'instr': ''}
        # build_site writes packs/index.json only for a full build: make a one-subject index from what it wrote
        full = subprocess.run([sys.executable, os.path.join(HERE, 'build_site.py'), '--data', a.data, '--lectures', a.lectures, '--out', os.path.join(site, 'packs')], capture_output=True, text=True, encoding='utf-8')
        check('site built (packs/index.json exists)', full.returncode == 0 and os.path.exists(os.path.join(site, 'packs', 'index.json')), full.stdout[-300:] + full.stderr[-300:])
        # ---- A. the page (jsdom + real pdf.js)
        out = os.path.join(td, 'out'); os.makedirs(out)
        nr = subprocess.run(['node', os.path.join(HERE, 'smoke_quick.js'), site, nm, pdf, exp, out, json.dumps(letters)], capture_output=True, text=True, encoding='utf-8')
        print(nr.stdout.rstrip()); fails += (nr.returncode != 0)
        if not os.path.exists(os.path.join(out, 'pr.zip')): print(nr.stderr[-800:]); check('page produced pr.zip', False); sys.exit(1)
        pack = open(os.path.join(out, 'pack.md'), encoding='utf-8').read(); import unicodedata; from lecturelib import flat
        pg4 = pack.split('<!-- p4 -->')[1].split('\n\n# QUESTIONS')[0]
        check('A. Arabic page: pdf.js text == PyMuPDF text (same letters, same order, after NFKC) and words are separated by spaces', flat(pg4) == flat(unicodedata.normalize('NFKC', ar_ref)) and 'كل منبع' in pg4 and 'تعدد' in pg4, (pg4[:120], flat(pg4)[:60], flat(unicodedata.normalize('NFKC', ar_ref))[:60]))
        # ---- B. the zip
        z = zipfile.ZipFile(os.path.join(out, 'pr.zip')); names = z.namelist()
        check('B. zip is valid (CRC of every file)', z.testzip() is None, z.testzip())
        allowed = ('intake/', 'replies/', 'sources/', 'media/', 'inbox/')
        check('B. only new files under intake/ replies/ sources/ (what check_pr_paths.py allows)', all(n.startswith(allowed) for n in names) and len(names) == 4, names)
        # ---- C. identity parity with tools/ingest_polls.py
        ip = subprocess.run([sys.executable, os.path.join(HERE, 'ingest_polls.py'), exp, '--year', '3', '--subject', '11', '--data', a.data, '--media', os.path.join(td, 'm'), '--out', os.path.join(td, 'ipout')], capture_output=True, text=True, encoding='utf-8')
        if ip.returncode: print(ip.stdout[-400:], ip.stderr[-600:])
        pj = json.load(open(glob.glob(os.path.join(td, 'ipout', '11', '*.json'))[0], encoding='utf-8'))
        py_new = {}
        for p in pj['polls']:
            if p['action'] == 'new' and 'duplicate_of_msg' not in p: py_new[p['key']] = p
        py_old = sorted(p['key'] for p in pj['polls'] if p['action'] == 'unchanged')
        page_in = json.loads(z.read([n for n in names if n.startswith('intake/')][0]).decode('utf-8'))
        pg_new = {p['key']: p for p in page_in['polls']}
        check('C. ingest_polls.py found 2 new + 3 known; page found the same 2 new', ip.returncode == 0 and len(py_new) == 2 and len(py_old) == 3 and set(py_new) == set(pg_new), (ip.stderr[-300:], list(py_new), list(pg_new)))
        same = all(all(py_new[k][f] == pg_new[k][f] for f in ('fingerprint', 'question', 'options', 'batch', 'msg', 'action')) for k in py_new if k in pg_new)
        check('C. fingerprint, key, cleaned question, options, msg id identical (Python == page)', same and len(pg_new) == 2, [(k, py_new[k]['question'], pg_new.get(k, {}).get('question')) for k in py_new])
        keys = json.load(open(os.path.join(out, 'keys.json'))); check('C. the 3 known questions in the pack carry the same keys Python matched', sorted(k for k in keys if k.startswith('y3:')) == py_old, (keys, py_old))
        check('C. page intake file: subject 11, year 3, no pictures', page_in['subject'] == 11 and page_in['year'] == 3 and page_in['media'] == {})
        # ---- D. "merge" the pull request: register_sources + apply_pending, like the data-writer Action
        repo = os.path.join(td, 'repo'); os.makedirs(repo); shutil.copytree(a.data, os.path.join(repo, 'data')); shutil.copytree(os.path.join(ROOT, 'config'), os.path.join(repo, 'config')); shutil.copytree(os.path.join(ROOT, 'sources'), os.path.join(repo, 'sources'))
        shutil.rmtree(os.path.join(repo, 'data', 'provenance'), ignore_errors=True)
        for f in ('media.json', 'aliases.json', 'applied.json'):
            if os.path.exists(os.path.join(repo, 'data', f)): os.remove(os.path.join(repo, 'data', f))
        z.extractall(repo)
        rs = subprocess.run([sys.executable, os.path.join(HERE, 'register_sources.py'), '--data', os.path.join(repo, 'data'), '--sources', os.path.join(repo, 'sources'), '--config', os.path.join(repo, 'config')], capture_output=True, text=True, encoding='utf-8')
        check('D. register_sources.py lists the new lecture for subject 11', rs.returncode == 0 and json.load(open(os.path.join(repo, 'config', 'sources.json')))['11'] == ['tdm-lecture-3'], rs.stdout + rs.stderr)
        before = {r['key']: r for r in json.load(open(os.path.join(repo, 'data', 'questions', 'subject-11.json'), encoding='utf-8'))}
        ap_ = subprocess.run([sys.executable, os.path.join(HERE, 'apply_pending.py'), '--data', os.path.join(repo, 'data'), '--root', repo, '--lectures', a.lectures, '--packs', os.path.join(repo, 'nopacks'), '--config', os.path.join(repo, 'config', 'subjects.json'), '--apply'], capture_output=True, text=True, encoding='utf-8')
        after_rows = json.load(open(os.path.join(repo, 'data', 'questions', 'subject-11.json'), encoding='utf-8')); after = {r['key']: r for r in after_rows}
        check('D. apply_pending exit 0 (no structural error)', ap_.returncode == 0, ap_.stdout[-700:] + ap_.stderr[-300:])
        fk = [k for k in keys if k.startswith('f:')]
        solved = after.get(fk[0]); unsolved = after.get(fk[1])
        check('D. the 2 new questions were added (hidden until solved)', solved is not None and unsolved is not None and len(after) == len(before) + 2, len(after))
        check('D. new question 1: answer A applied from the UPLOADED lecture, explanation = the student\'s edit + marker (م3), visible', solved and solved['correct_index'] == 0 and '(م3)' in (solved['explanation'] or '') and solved['excluded'] == 0, solved)
        check('D. new question 2 (NOT-FOUND) stays unsolved', unsolved and unsolved['correct_index'] is None, unsolved)
        check('D. existing answers untouched (a quote-verified SAME answer may only refresh the explanation)', all(after[k]['correct_index'] == before[k]['correct_index'] for k in before), [k for k in before if after[k]['correct_index'] != before[k]['correct_index']])
        check('D. rejected line (invented quote) changed nothing', after[keys[1]]['explanation'] == before[keys[1]]['explanation'], after[keys[1]]['explanation'])
        ap2 = subprocess.run([sys.executable, os.path.join(HERE, 'apply_pending.py'), '--data', os.path.join(repo, 'data'), '--root', repo, '--lectures', a.lectures, '--packs', os.path.join(repo, 'nopacks'), '--config', os.path.join(repo, 'config', 'subjects.json'), '--apply'], capture_output=True, text=True, encoding='utf-8')
        check('D. running it again applies nothing twice', ap2.returncode == 0 and len(json.load(open(os.path.join(repo, 'data', 'questions', 'subject-11.json'), encoding='utf-8'))) == len(after_rows))
    print('\ntest_quick: ' + ('FAILED' if fails else 'OK')); sys.exit(1 if fails else 0)

if __name__ == '__main__': main()

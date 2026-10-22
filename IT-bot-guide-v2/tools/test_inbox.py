#!/usr/bin/env python3
"""
test_inbox.py - student PDF upload path: inbox/<subject>/<lecture>.pdf -> ingest_inbox.py -> sources/ + config/sources.json -> picker + one-run pack.
  python tools/test_inbox.py --data data          (needs PyMuPDF + Pillow: pip install pymupdf pillow; no lecture repo needed)
Everything happens in a temp folder with a REAL PDF made on the fly (2 text pages + 1 figure page). data/ is only read.
"""
import argparse, io, json, os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
from lecturelib import *
import check_pr_paths

def make_pdf(path):
    import pymupdf as fitz
    from PIL import Image
    doc = fitz.open()
    for txt in (["Computer Networks lecture five", "The transport layer provides end to end delivery between processes.", "TCP uses a three way handshake to establish a connection."],
                ["UDP is connectionless and does not guarantee delivery or ordering.", "Flow control prevents a fast sender from overwhelming a slow receiver."]):
        pg = doc.new_page()
        for i, ln in enumerate(txt): pg.insert_text((72, 72 + 20 * i), ln, fontsize=11)
    pg = doc.new_page(); buf = io.BytesIO(); Image.new('RGB', (600, 800), (30, 90, 160)).save(buf, 'PNG')
    pg.insert_image(pg.rect, stream=buf.getvalue()); pg.insert_text((72, 40), "Figure 1: network topology diagram", fontsize=9)
    doc.save(path)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--data', default='data'); a = ap.parse_args(); fails = 0
    def check(n, ok, x=''):
        nonlocal fails; print(('PASS  ' if ok else 'FAIL  ') + n + (('  ' + str(x)[:600]) if x and not ok else '')); fails += (not ok)
    try: import pymupdf  # noqa
    except ImportError: sys.exit('PyMuPDF missing: pip install pymupdf pillow')
    SID = 12; NAME = 'Test Lecture 5'; SLUG = 'test-lecture-5'
    with tempfile.TemporaryDirectory() as td:
        data = os.path.join(td, 'data'); shutil.copytree(a.data, data); os.makedirs(os.path.join(td, 'config')); shutil.copy(os.path.join(ROOT, 'config', 'subjects.json'), os.path.join(td, 'config'))
        inbox = os.path.join(td, 'inbox'); os.makedirs(os.path.join(inbox, str(SID))); make_pdf(os.path.join(inbox, str(SID), NAME + '.pdf'))
        ing = lambda: subprocess.run([sys.executable, os.path.join(HERE, 'ingest_inbox.py'), '--data', data, '--inbox', inbox, '--sources', os.path.join(td, 'sources'), '--config', os.path.join(td, 'config'), '--report', os.path.join(td, 'report.md')], capture_output=True, text=True, encoding='utf-8')
        r = ing(); check('ingest_inbox.py ran on a real PDF (exit 0)', r.returncode == 0, r.stdout + r.stderr)
        md = os.path.join(td, 'sources', str(SID), SLUG + '.md'); txt = open(md, encoding='utf-8').read() if os.path.exists(md) else ''
        check('sources/12/test-lecture-5.md has the text and page markers', 'three way handshake' in txt and '<!-- p1 -->' in txt and '<!-- p2 -->' in txt, txt[:200])
        check('the figure page is kept as an image and marked (<!-- fig: ... -->)', '<!-- fig: figs/test-lecture-5-p3.jpg -->' in txt and os.path.exists(os.path.join(td, 'sources', str(SID), 'figs', 'test-lecture-5-p3.jpg')), txt[-200:])
        cj = os.path.join(td, 'config', 'sources.json')
        check('config/sources.json lists the slug under the folder\'s subject', os.path.exists(cj) and json.load(open(cj)) == {str(SID): [SLUG]}, open(cj).read() if os.path.exists(cj) else 'missing')
        check('hand-edited config/subjects.json untouched', open(os.path.join(td, 'config', 'subjects.json'), encoding='utf-8').read() == open(os.path.join(ROOT, 'config', 'subjects.json'), encoding='utf-8').read())
        check('PDF removed from inbox/ after ingest', not os.listdir(os.path.join(inbox, str(SID))))
        cfg = load_config(os.path.join(td, 'config', 'subjects.json'))
        check('load_config merges sources.json (subject 12 had no config entry)', cfg.get(str(SID), {}).get('sources') == [SLUG] and cfg['11'].get('folder') == 'year-3/digital-communications')
        lec = subject_lectures(cfg, None, os.path.join(td, 'sources'), SID)
        check('subject_lectures finds the PDF lecture (marker (م5) from the name)', [l['file'] for l in lec] == [SLUG + '.md'] and marker(cfg[str(SID)], SLUG + '.md') == '(م5)', [l['file'] for l in lec])
        # a question that talks about the figure page -> the figure is attached (unrelated questions would not attach it: each image costs tokens)
        rows = load_subject(data, SID); rows[0]['question'] = 'network topology diagram figure ' + rows[0]['question']; save_subject(data, SID, rows)
        # the page data + one-run pack for that subject
        packs = os.path.join(td, 'packs')
        r = subprocess.run([sys.executable, os.path.join(HERE, 'build_site.py'), '--data', data, '--sources', os.path.join(td, 'sources'), '--config', os.path.join(td, 'config', 'subjects.json'), '--subject', str(SID), '--out', packs], capture_output=True, text=True, encoding='utf-8')
        check('build_site.py builds subject 12 with the uploaded lecture', r.returncode == 0 and 'subject 12: 1 lectures' in r.stdout, r.stdout + r.stderr)
        ix = json.load(open(os.path.join(packs, 'index.json'), encoding='utf-8'))['subjects'][0]
        check('picker data: subject 12 is no longer INFERRED-only, lists the PDF lecture with origin "sources"', ix['id'] == SID and not ix['inferred'] and ix['lectures'][0]['file'] == SLUG + '.md' and ix['lectures'][0]['origin'] == 'sources' and ix['lectures'][0]['marker'] == '(م5)', ix)
        sj = json.load(open(os.path.join(packs, str(SID), 'site.json'), encoding='utf-8'))
        check('site.json lists the figure page (routed because a question mentions it)', sj['lectures'][SLUG + '.md']['figs'] == {'3': f'sources/{SID}/figs/{SLUG}-p3.jpg'}, sj['lectures'])
        r = subprocess.run([sys.executable, os.path.join(HERE, 'make_packs.py'), '--data', data, '--sources', os.path.join(td, 'sources'), '--config', os.path.join(td, 'config', 'subjects.json'), '--subject', str(SID), '--mode', 'all', '--out', os.path.join(td, 'pk')], capture_output=True, text=True, encoding='utf-8')
        pk = open(os.path.join(td, 'pk', str(SID), 'all.md'), encoding='utf-8').read() if r.returncode == 0 else ''
        check('one-run pack has the PDF lecture, the instructions and the questions', '# LECTURE (test-lecture-5.md)' in pk and 'three way handshake' in pk and '# QUESTIONS' in pk and '"lec"' in pk and '- test-lecture-5.md p3: test-lecture-5-p3.jpg' in pk, r.stdout + r.stderr)
        # same PDF again -> nothing changes
        make_pdf(os.path.join(inbox, str(SID), NAME + '.pdf')); before = open(md, encoding='utf-8').read(); r = ing()
        check('same PDF again: exit 0, config not duplicated', r.returncode == 0 and json.load(open(cj)) == {str(SID): [SLUG]} and before == open(md, encoding='utf-8').read(), r.stdout)
        # unknown subject folder and a broken PDF: exit 1, files stay
        os.makedirs(os.path.join(inbox, '9999')); make_pdf(os.path.join(inbox, '9999', 'x.pdf')); open(os.path.join(inbox, str(SID), 'broken.pdf'), 'wb').write(b'not a pdf')
        r = ing()
        check('unknown subject id and a broken PDF -> exit 1, both reported, files stay in inbox/', r.returncode == 1 and 'unknown subject id 9999' in r.stdout and 'broken.pdf: ingest failed' in r.stdout and os.path.exists(os.path.join(inbox, '9999', 'x.pdf')) and os.path.exists(os.path.join(inbox, str(SID), 'broken.pdf')), r.stdout[-600:])
    check('student PR guard allows NEW files under inbox/', 'inbox/' in check_pr_paths.ALLOWED_ADD and 'data/' not in check_pr_paths.ALLOWED_ADD)
    print('\ntest_inbox ' + ('FAILED' if fails else 'OK')); sys.exit(1 if fails else 0)

if __name__ == '__main__': main()

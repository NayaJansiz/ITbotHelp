#!/usr/bin/env python3
"""
test_sources.py - Part 2A item 7: PDFs ingested by ingest_pdf.py (sources/<id>/*.md) work like repo lectures.
  python tools/test_sources.py --data data            (needs node; uses sources/9/wp-lecture-3.md, no lecture repo)
Runs in a temp folder with its own config: subject 12 gets "sources": ["wp-lecture-3"] (an arbitrary subject, test only).
Checks: pack built from the PDF text; figure pages attached only when routed; a quote spanning a page marker is accepted;
FIGURE replies (valid ref / invalid ref) in merge_answers.py; page JS counters == Python counters.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
from lecturelib import *
from make_packs import fig_pages
import test_site

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--data', default='data'); a = ap.parse_args(); fails = 0
    def check(n, ok, x=''):
        nonlocal fails; print(('PASS  ' if ok else 'FAIL  ') + n + (('  ' + str(x)) if x and not ok else '')); fails += (not ok)
    SID = 12
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, 'sources', str(SID)); shutil.copytree(os.path.join(ROOT, 'sources', '9'), src)
        cfgp = os.path.join(td, 'subjects.json'); json.dump({str(SID): {'sources': ['wp-lecture-3']}}, open(cfgp, 'w'))
        data = os.path.join(td, 'data'); shutil.copytree(a.data, data)
        rows = load_subject(data, SID)
        # make 3 questions that talk about the figure on page 6 (CSS modules) so the figure is routed
        fp = fig_pages(load_sources(os.path.join(td, 'sources'), SID, ['wp-lecture-3'])[0])
        check('figure pages found in the source (6 and 48)', sorted(fp) == [6, 48], sorted(fp))
        words6 = ' '.join(sorted(set(words(fp[6][1]))))
        rows[0]['question'] = 'CSS modules ' + words6; rows[0]['correct_index'] = None; save_subject(data, SID, rows)
        out = os.path.join(td, 'packs')
        r = subprocess.run([sys.executable, os.path.join(HERE, 'make_packs.py'), '--data', data, '--subject', str(SID), '--out', out, '--config', cfgp, '--sources', os.path.join(td, 'sources'), '--all'], capture_output=True, text=True)
        check('make_packs ran on a PDF-only subject', r.returncode == 0, r.stdout + r.stderr)
        man = json.load(open(os.path.join(out, str(SID), 'manifest.json')))
        check('pack named after the source (wp-lecture-3)', list(man) == ['wp-lecture-3'], list(man))
        pk = open(os.path.join(out, str(SID), 'wp-lecture-3.md'), encoding='utf-8').read()
        check('pack holds the PDF text with page markers', '# LECTURE (wp-lecture-3.md)' in pk and '<!-- p12 -->' in pk)
        check('figure page 6 attached because a question is routed to it', 'sources/9/figs/wp-lecture-3-p6.jpg' in man['wp-lecture-3']['images'] or any(i.endswith('-p6.jpg') for i in man['wp-lecture-3']['images']), man['wp-lecture-3']['images'])
        check('FIGURE IMAGES section lists the attached page', '# FIGURE IMAGES' in pk and '- p6:' in pk)
        keys = man['wp-lecture-3']['keys']; byid = {q['key']: q for q in load_subject(data, SID)}
        lec = load_sources(os.path.join(td, 'sources'), SID, ['wp-lecture-3'])[0]['text']
        # a quote that spans a page marker
        lines = lec.split('\n'); qi = next(i for i, l in enumerate(lines) if re.match(r'\s*<!-- p13 -->', l))
        before = [l for l in lines[:qi] if l.strip() and not l.strip().startswith('<!--')][-3:]; after = [l for l in lines[qi:] if l.strip() and not l.strip().startswith('<!--')][:3]
        span = ' '.join(x.strip() for x in before + after)
        L = 'ABCDEFGHIJ'; replies = []
        for i, k in enumerate(keys[:8]):
            n = len(byid[k]['options'])
            if i == 0: replies.append({'id': k, 'a': 'A', 'src': 'LECTURE', 'ref': 'p13', 'q': span, 'e': 'span page'})
            elif i == 1: replies.append({'id': k, 'a': 'A', 'src': 'FIGURE', 'ref': 'p6', 'e': 'figure ok'})
            elif i == 2: replies.append({'id': k, 'a': 'A', 'src': 'FIGURE', 'ref': 'p7', 'e': 'not a figure page'})
            elif i == 3: replies.append({'id': k, 'a': 'A', 'src': 'FIGURE', 'e': 'no ref'})
            elif i == 4: replies.append({'id': k, 'a': 'A', 'src': 'LECTURE', 'ref': 'x', 'q': 'fabricated quote that is not in the pdf at all', 'e': 'x'})
        fr = load_subject(data, SID)
        for q in fr:
            if q['key'] == keys[1]: q['correct_index'] = None      # the FIGURE answer is applied only to an unsolved row (a stored answer would give CONFLICT-EXISTING)
        save_subject(data, SID, fr); byid = {q['key']: q for q in fr}
        body = '\n'.join(json.dumps(x, ensure_ascii=False) for x in replies) + '\n'
        os.makedirs(os.path.join(td, 'replies', str(SID))); open(os.path.join(td, 'replies', str(SID), 'wp-lecture-3.jsonl'), 'w', encoding='utf-8').write(body)
        cp = lambda ap_: subprocess.run([sys.executable, os.path.join(HERE, 'merge_answers.py'), '--data', data, '--sources', os.path.join(td, 'sources'), '--config', cfgp, '--replies', os.path.join(td, 'replies'), '--packs', out] + ap_, capture_output=True, text=True)
        r = cp([]); m = re.search(r'replies -> (\{.*?\})\n', r.stdout); pyc = eval(m.group(1)) if m else {}
        check('python: span-page quote accepted, 1 FIGURE ok, 2 invalid figure refs, 1 quote fail', pyc.get('LECTURE ok') == 1 and pyc.get('FIGURE') == 1 and pyc.get('INVALID figure ref') == 2 and pyc.get('QUOTE-FAIL') == 1, pyc)
        # the harness wants the page numbers found in the lecture text: compute like the page does
        figp = []; page = 0
        for ln in test_site.extractLecture_py(pk).split('\n'):
            mm = re.match(r'\s*<!-- p(\d+) -->', ln)
            if mm: page = int(mm.group(1)); continue
            if re.match(r'\s*<!-- fig: \S+ -->', ln): figp.append(page)
        jr = test_site.node({'mode': 'validate', 'text': body, 'lectureFlat': flat(test_site.extractLecture_py(pk)), 'qinfo': {k: [len(byid[k]['options']), byid[k]['correct_index']] for k in byid}, 'keys': keys, 'figPages': figp})
        jc = {k: v for k, v in jr['counts'].items()}
        check('page JS counters == python counters', jc == pyc, f'js={jc} py={pyc}')
        # apply: FIGURE answer is visible with needs_review=1; provenance has the page
        r = cp(['--apply']); rr = {q['key']: q for q in load_subject(data, SID)}; pv = json.load(open(os.path.join(data, 'provenance', f'subject-{SID}.json')))
        fk = keys[1]
        check('FIGURE applied: needs_review=1, visible, provenance ref p6', rr[fk]['needs_review'] == 1 and rr[fk]['excluded'] == 0 and pv[fk]['src'] == 'FIGURE' and pv[fk]['ref'] == 'p6', (rr[fk], pv.get(fk)))
        lk = keys[0]
        check('span-page LECTURE applied with marker (م3)', rr[lk]['explanation'].endswith('(م3)') and pv[lk]['file'] == 'wp-lecture-3.md', rr[lk]['explanation'])
        # reverify: quote still found; change the source -> stale
        rv = lambda: subprocess.run([sys.executable, os.path.join(HERE, 'reverify.py'), '--data', data, '--sources', os.path.join(td, 'sources'), '--config', cfgp], capture_output=True, text=True)
        check('reverify ok on unchanged source', rv().returncode == 0)
        mdp = os.path.join(td, 'sources', str(SID), 'wp-lecture-3.md'); open(mdp, 'w', encoding='utf-8').write(open(mdp, encoding='utf-8').read().replace(before[-1].strip(), 'REMOVED'))
        check('reverify flags the answer after the PDF text changed', rv().returncode == 1)
        # a subject with sources NOT listed in config must not get the PDF
        json.dump({str(SID): {}}, open(cfgp, 'w')); r2 = subprocess.run([sys.executable, os.path.join(HERE, 'make_packs.py'), '--data', data, '--subject', str(SID), '--out', os.path.join(td, 'p2'), '--config', cfgp, '--sources', os.path.join(td, 'sources')], capture_output=True, text=True)
        check('sources not listed in config are NOT attached to the subject', 'INFERRED' in r2.stdout and 'wp-lecture-3' not in r2.stdout, r2.stdout[-300:])
    print('\ntest_sources ' + ('FAILED' if fails else 'OK')); sys.exit(1 if fails else 0)

if __name__ == '__main__': main()

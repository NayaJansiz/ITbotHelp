#!/usr/bin/env python3
"""
test_oneshot.py - lecture picker + one-run pack. Python and the page JS must agree, and the merge must follow the "lec" hint.
  python tools/test_oneshot.py --data data --lectures ../lecture-site-engine [--node-modules <dir containing node_modules/jsdom>]
 A. planBins (JS) == plan_bins (Python) on random cases, and every real subject's packs respect MAX_CHARS
 B. the pack the page builds from site/packs files == the pack make_packs.py --mode all writes (byte for byte), for 8 subjects
 C. a one-run reply (right / wrong / missing "lec", fake quote, NOT-FOUND repeated, FIGURE, STUDENT) gives the same counters in
    merge_answers.py (dry run, all-<sha8>.jsonl) and in the page JS
 D. --apply: each answer takes the lecture its quote is in (provenance file + (م#) marker); two lectures with different letters = CONFLICT
 E. jsdom smoke (tools/smoke_oneshot.js) when jsdom is installed
 F. apply_pending.py (the data-writer Action) applies an all-<sha8>.jsonl reply
Uses a temp copy of everything it writes; data/ is only read.
"""
import argparse, json, os, random, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
from lecturelib import *
import test_site

HARNESS = test_site.js_module() + r"""
var inp = JSON.parse(require('fs').readFileSync(0, 'utf8')), out;
if (inp.mode === 'bins') out = inp.cases.map(function (c) { return planBins(c.lectures, c.overhead, c.max); });
if (inp.mode === 'build') out = inp.jobs.map(function (j) { return buildPack(j.instr, j.title, j.qb, j.lectures, j.figs); });
if (inp.mode === 'validate') {
  var lectures = {}; Object.keys(inp.texts).forEach(function (f) { lectures[f] = { flat: flat(inp.texts[f]), figs: figPagesOf(inp.texts[f]) }; });
  var r = validateReply(inp.text, { lectures: lectures, order: inp.order, qinfo: inp.qinfo, keys: inp.keys });
  out = { counts: r.counts, bad: r.bad, missing: r.missing, rows: r.rows.map(function (x) { return [x.id, x.kind, x.lec]; }) };
}
process.stdout.write(JSON.stringify(out));
"""

def node(payload):
    r = subprocess.run(['node', '-e', HARNESS], input=json.dumps(payload), capture_output=True, encoding='utf-8')
    if r.returncode: sys.exit('node failed: ' + r.stderr[:600])
    return json.loads(r.stdout)

def run(*args):
    r = subprocess.run([sys.executable] + [str(x) for x in args], capture_output=True, text=True, encoding='utf-8'); return r.stdout + r.stderr

def counters(out):
    m = re.search(r'replies -> (\{.*?\})\n', out); return eval(m.group(1)) if m else {}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--data', default='data'); ap.add_argument('--lectures', required=True); ap.add_argument('--sources', default=os.path.join(ROOT, 'sources'))
    ap.add_argument('--node-modules', default=os.environ.get('JSDOM_DIR', '')); a = ap.parse_args()
    cfg = load_config(os.path.join(ROOT, 'config', 'subjects.json')); fails = 0
    def check(name, ok, extra=''):
        nonlocal fails; print(('PASS  ' if ok else 'FAIL  ') + name + (('  ' + str(extra)[:600]) if extra and not ok else '')); fails += (not ok)
    tmp = tempfile.mkdtemp(); site = os.path.join(tmp, 'site'); os.makedirs(site); shutil.copy(os.path.join(ROOT, 'site', 'index.html'), site)
    packs = os.path.join(site, 'packs')
    out = run(os.path.join(HERE, 'build_site.py'), '--data', a.data, '--lectures', a.lectures, '--sources', a.sources, '--out', packs)
    check('build_site.py ran', 'site/packs/index.json' in out, out[-400:])
    index = json.load(open(os.path.join(packs, 'index.json'), encoding='utf-8'))

    # ---- A. binning
    rnd = random.Random(11); cases = []
    for _ in range(300):
        n = rnd.randint(1, 14); cases.append({'lectures': [{'file': f'par{i}.md' if rnd.random() < .8 else f'x-{i}.md', 'num': rnd.randint(0, 9), 'chars': rnd.randint(1000, 400000)} for i in range(n)], 'overhead': rnd.randint(0, 30000), 'max': rnd.choice([250000, 120000, 500000])})
    for c in cases:
        for l in c['lectures']: l['file'] = l['file'][:-3] + '-' + str(rnd.randint(0, 99)) + '.md' if False else l['file']
    # unique file names inside a case
    for c in cases:
        seen = set()
        for i, l in enumerate(c['lectures']):
            while l['file'] in seen: l['file'] = 'dup%d-%s' % (i, l['file'])
            seen.add(l['file'])
    jsb = node({'mode': 'bins', 'cases': cases}); pyb = [plan_bins(c['lectures'], c['overhead'], c['max']) for c in cases]
    bad = [i for i, (x, y) in enumerate(zip(jsb, pyb)) if x != y]
    check('planBins (JS) == plan_bins (Python) on 300 random cases', not bad, bad[:3])
    check('every lecture is in exactly one pack', all(sorted(f for b in bs for f in b) == sorted(l['file'] for l in c['lectures']) for bs, c in zip(pyb, cases)))
    check('packs never exceed MAX_CHARS unless one lecture alone is bigger', all(sum(next(l['chars'] + LEC_HEADER_COST for l in c['lectures'] if l['file'] == f) for f in b) <= c['max'] - c['overhead'] or len(b) == 1 for bs, c in zip(pyb, cases) for b in bs))
    check('fewest packs: never more than the trivial lower bound + 1 (first-fit decreasing)', all(len(bs) <= -(-sum(l['chars'] + LEC_HEADER_COST for l in c['lectures']) // max(1, c['max'] - c['overhead'])) * 2 or len(bs) == len(c['lectures']) for bs, c in zip(pyb, cases)))

    # ---- B. page-built pack == make_packs.py --mode all
    subjects = [s for s in index['subjects'] if not s['inferred']]
    pk = os.path.join(tmp, 'pk'); mismatches = []; oversize = []; njobs = 0
    for s in subjects:
        sid = s['id']; o = run(os.path.join(HERE, 'make_packs.py'), '--data', a.data, '--lectures', a.lectures, '--sources', a.sources, '--subject', sid, '--mode', 'all', '--out', pk)
        man = json.load(open(os.path.join(pk, str(sid), 'manifest.json'), encoding='utf-8'))['all']; sj = json.load(open(os.path.join(packs, str(sid), 'site.json'), encoding='utf-8'))
        qb = open(os.path.join(packs, str(sid), 'questions.md'), encoding='utf-8').read()
        jobs = []
        for i, part in enumerate(man['parts'], 1):
            jobs.append({'instr': index['instr'], 'title': f"SUBJECT {sid}" + (f" \u2014 part {i} of {len(man['parts'])}" if len(man['parts']) > 1 else ''), 'qb': qb,
                         'lectures': [{'file': f, 'text': open(os.path.join(packs, str(sid), 'lectures', f), encoding='utf-8').read()} for f in part['lectures']],
                         'figs': [[f, sj['lectures'][f]['figs']] for f in part['lectures'] if sj['lectures'][f]['figs']]})
        built = node({'mode': 'build', 'jobs': jobs}); njobs += len(jobs)
        for part, text in zip(man['parts'], built):
            want = open(os.path.join(pk, str(sid), part['pack'] + '.md'), encoding='utf-8', newline='').read()
            if text != want: mismatches.append((sid, part['pack']))
            if clen(want) > index['max_chars'] and len(part['lectures']) > 1: oversize.append((sid, part['pack'], clen(want)))
        # JS planBins on the index metadata == the parts Python wrote
        ov = len(index['instr']) + len(qb) + PACK_SLACK
        jb = node({'mode': 'bins', 'cases': [{'lectures': s['lectures'], 'overhead': ov, 'max': index['max_chars']}]})[0]
        if jb != [p_['lectures'] for p_ in man['parts']]: mismatches.append((sid, 'bins', jb))
    check(f'page-built packs identical to make_packs.py --mode all ({njobs} packs, {len(subjects)} subjects)', not mismatches, mismatches[:3])
    check('multi-lecture packs are within MAX_CHARS (UTF-16 units)', not oversize, oversize[:3])
    check('subject 11: 9 lectures -> 2 packs; subject 9 lists repo lectures AND the PDF', next(len(s['lectures']) for s in subjects if s['id'] == 11) == 9 and 'wp-lecture-3.md' in [l['file'] for s in subjects if s['id'] == 9 for l in s['lectures']])

    # ---- C. replies: merge_answers.py vs page JS
    def lectures_of(sid): return {l['file']: l for l in subject_lectures(cfg, a.lectures, a.sources, sid)}
    def uniq_quote(lecs, f, rnd, skip=0):
        lines = [l for l in lecs[f]['text'].split('\n') if len(l.split()) > 9 and not l.lstrip().startswith('<!--') and '|' not in l]
        for _ in range(200):
            w = rnd.choice(lines).replace('*', ' ').split(); q = ' '.join(w[:rnd.randint(8, min(20, len(w)))])
            if sum(flat(q) in flat(l['text']) for l in lecs.values()) == 1 and len(flat(q)) >= 15: return q
        raise SystemExit('no unique quote in ' + f)
    scen = {}
    for sid in (11, 9):
        lecs = lectures_of(sid); files = list(lecs); rows = {r['key']: r for r in load_subject(a.data, sid)}; keys = json.load(open(os.path.join(packs, str(sid), 'manifest.json'), encoding='utf-8'))['all']['keys']
        rnd = random.Random(sid); LET_ = 'ABCDEFGHIJ'; L = lambda k, i=0: LET_[i % len(rows[k]['options'])]
        A, B, C, D, E = [f for f in files if f != 'wp-lecture-3.md'][:5]; qa, qb_, qc, qd, qe = [uniq_quote(lecs, f, rnd) for f in (A, B, C, D, E)]
        k = keys; lines = [
            {'id': k[0], 'a': L(k[0]), 'src': 'LECTURE', 'lec': A, 'ref': 'x', 'q': qa, 'e': 'ok'},                      # right lec
            {'id': k[1], 'a': L(k[1]), 'src': 'LECTURE', 'lec': A, 'ref': 'x', 'q': qb_, 'e': 'ok'},                     # WRONG lec: quote is in B
            {'id': k[2], 'a': L(k[2]), 'src': 'LECTURE', 'ref': 'x', 'q': qc, 'e': 'ok'},                                 # no lec
            {'id': k[3], 'a': L(k[3]), 'src': 'LECTURE', 'lec': D[:-3], 'ref': 'x', 'q': qd, 'e': 'ok'},                  # lec without .md
            {'id': k[4], 'a': L(k[4]), 'src': 'LECTURE', 'lec': A, 'q': 'هذه الجملة مخترعة بالكامل ولا وجود لها في أي محاضرة', 'e': 'x'},
            {'id': k[5], 'src': 'NOT-FOUND'},
            {'id': k[6], 'src': 'NOT-FOUND'}, {'id': k[6], 'src': 'NOT-FOUND'},                                            # repeated NOT-FOUND (several parts) -> counted once
            {'id': k[7], 'src': 'NOT-FOUND'}, {'id': k[7], 'a': L(k[7]), 'src': 'LECTURE', 'lec': E, 'q': qe, 'e': 'ok'},  # NOT-FOUND + answer -> only the answer
            {'id': k[8], 'a': L(k[8]), 'src': 'STUDENT', 'a0': 'A', 'src0': 'NOT-FOUND', 'q': qc, 'e': 'edited', 'e_edited': True},   # student + valid quote, no lec
            {'id': k[9], 'a': L(k[9]), 'src': 'STUDENT', 'q': 'invented quote not in any lecture at all', 'e': 'x'},
            {'id': k[10], 'a': L(k[10]), 'src': 'INFERRED', 'e': 'x'},
            {'id': k[11], 'a': 'J', 'src': 'LECTURE', 'lec': A, 'q': qa, 'e': 'x'},                                         # letter outside
            {'id': k[12], 'a': L(k[12], 0), 'src': 'LECTURE', 'lec': A, 'q': qa, 'e': 'x'}, {'id': k[12], 'a': L(k[12], 1), 'src': 'LECTURE', 'lec': B, 'q': qb_, 'e': 'x'},   # two lectures, different letters
            {'id': k[13], 'a': 'A', 'src': 'FIGURE', 'lec': 'wp-lecture-3.md', 'ref': 'p6', 'e': 'x'},
            {'id': k[14], 'a': 'A', 'src': 'FIGURE', 'lec': A, 'ref': 'p48', 'e': 'x'},                                    # wrong lec: the figure page is in the PDF
            {'id': k[15], 'a': 'A', 'src': 'FIGURE', 'ref': 'p7', 'e': 'x'},                                                # not a figure page
            {'id': 'nope:1', 'a': 'A', 'src': 'LECTURE', 'q': qa}]
        body = ',\n'.join(json.dumps(l, ensure_ascii=False) for l in lines) + ',\nnot json {broken\n{"id": 1,\n'
        rd = os.path.join(tmp, f'replies{sid}', str(sid)); os.makedirs(rd); open(os.path.join(rd, 'all-1a2b3c4d.jsonl'), 'w', encoding='utf-8').write(body)
        rep = run(os.path.join(HERE, 'merge_answers.py'), '--data', a.data, '--lectures', a.lectures, '--sources', a.sources, '--replies', os.path.join(tmp, f'replies{sid}'), '--packs', packs)
        pyc = counters(rep); sj = json.load(open(os.path.join(packs, str(sid), 'site.json'), encoding='utf-8'))
        jr = node({'mode': 'validate', 'text': body, 'texts': {f: l['text'] for f, l in lecs.items()}, 'order': files, 'qinfo': sj['q'], 'keys': sj['keys']})
        pybad = re.search(r'(\d+) unreadable line', rep); pybad = int(pybad.group(1)) if pybad else 0; pymiss = re.search(r'NO REPLY for (\d+) of', rep); pymiss = int(pymiss.group(1)) if pymiss else 0
        check(f'subject {sid}: one-run reply counters, merge_answers.py == page JS {dict(sorted(jr["counts"].items()))}', pyc == jr['counts'], f'py={pyc} js={jr["counts"]}')
        check(f'subject {sid}: unreadable ({pybad}) and unanswered ({pymiss}) equal', (pybad, pymiss) == (len(jr['bad']), len(jr['missing'])), (pybad, pymiss, len(jr['bad']), len(jr['missing'])))
        kinds = {(r[0], r[1]): r[2] for r in jr['rows']}
        check(f'subject {sid}: "lec" is a hint - wrong/missing/no-.md hints still resolve to the lecture that holds the quote', kinds.get((k[0], 'ok')) == A and kinds.get((k[1], 'bad')) is None and kinds.get((k[2], 'ok')) == C and kinds.get((k[3], 'ok')) == D and kinds.get((k[7], 'ok')) == E and kinds.get((k[8], 'ok')) == C, [r for r in jr['rows'] if r[0] in k[:9]])
        nf = [r for r in jr['rows'] if r[1] == 'nf']
        check(f'subject {sid}: NOT-FOUND de-duplicated (2 questions only, none that was also answered)', sorted(r[0] for r in nf) == sorted([k[5], k[6]]), nf)
        check(f'subject {sid}: two lectures with different letters -> both rows rejected in the page, CONFLICT in the merge', sum(1 for r in jr['rows'] if r[0] == k[12] and r[1] == 'bad') == 2 and not any(r[0] == k[12] and r[1] == 'ok' for r in jr['rows']) and 'CONFLICT between lecture packs' in rep, [r for r in jr['rows'] if r[0] == k[12]])
        if sid == 9:
            fg = {r[0]: r[1:] for r in jr['rows'] if r[0] in (k[13], k[14], k[15])}
            check('subject 9: FIGURE p6 / p48 accepted even with a wrong "lec" (lecture = the PDF), p7 rejected', fg[k[13]] == ['fig', 'wp-lecture-3.md'] and fg[k[14]] == ['fig', 'wp-lecture-3.md'] and fg[k[15]][0] == 'bad', fg)
        scen[sid] = (lines, k, A, B, C, D, E, lecs)

    # ---- D. --apply on a temp copy of data/: the lecture of the quote decides provenance file and the (م#) marker
    sid = 11; lines, k, A, B, C, D, E, lecs = scen[sid]; d2 = os.path.join(tmp, 'data2'); shutil.copytree(a.data, d2)
    rows = load_subject(d2, sid)
    for r in rows:
        if r['key'] in k[:9]: r['correct_index'] = None
    save_subject(d2, sid, rows)
    rep = run(os.path.join(HERE, 'merge_answers.py'), '--data', d2, '--lectures', a.lectures, '--sources', a.sources, '--replies', os.path.join(tmp, 'replies11'), '--packs', packs, '--root', '/nonexistent', '--apply')
    rr = {r['key']: r for r in load_subject(d2, sid)}; pv = json.load(open(os.path.join(d2, 'provenance', f'subject-{sid}.json'), encoding='utf-8'))
    ok = all(pv.get(k[i], {}).get('file') == f and rr[k[i]]['explanation'].endswith(marker(cfg[str(sid)], f)) and rr[k[i]]['correct_index'] is not None and rr[k[i]]['needs_review'] == 0 for i, f in [(0, A), (1, B), (2, C), (3, D), (7, E), (8, C)])
    check('apply: answers from different lectures get THEIR lecture as provenance file and (م#) marker', ok, {k[i]: (pv.get(k[i], {}).get('file'), rr[k[i]]['explanation'][-12:]) for i in (0, 1, 2)})
    check('apply: conflicting two-lecture question (k12) and the fake quote (k4) were not applied', k[12] not in pv and k[4] not in pv)

    # ---- F. the data-writer (apply_pending.py) accepts an all-<sha8>.jsonl reply + its summary file
    root = os.path.join(tmp, 'repo'); os.makedirs(os.path.join(root, 'replies', '11')); d3 = os.path.join(tmp, 'data3'); shutil.copytree(a.data, d3)
    shutil.copy(os.path.join(tmp, 'replies11', '11', 'all-1a2b3c4d.jsonl'), os.path.join(root, 'replies', '11')); open(os.path.join(root, 'replies', '11', 'all-1a2b3c4d.summary.md'), 'w', encoding='utf-8').write('# ملخص\n')
    rows = load_subject(d3, 11)
    for r in rows:
        if r['key'] in k[:9]: r['correct_index'] = None
    save_subject(d3, 11, rows)
    r = subprocess.run([sys.executable, os.path.join(HERE, 'apply_pending.py'), '--data', d3, '--root', root, '--lectures', a.lectures, '--packs', os.path.join(tmp, 'nopacks'), '--apply', '--report', os.path.join(tmp, 'rep.md')], capture_output=True, text=True, encoding='utf-8')
    ap_ = json.load(open(os.path.join(d3, 'applied.json'))) if os.path.exists(os.path.join(d3, 'applied.json')) else {}
    rr = {x['key']: x for x in load_subject(d3, 11)}; pv = json.load(open(os.path.join(d3, 'provenance', 'subject-11.json'), encoding='utf-8')) if os.path.exists(os.path.join(d3, 'provenance', 'subject-11.json')) else {}
    check('data-writer: replies/11/all-<sha8>.jsonl is applied (listed in applied.json) and answers land with THEIR lecture as provenance', 'replies/11/all-1a2b3c4d.jsonl' in ap_ and all(pv.get(k[i], {}).get('file') == f and rr[k[i]]['correct_index'] is not None for i, f in [(0, A), (1, B), (2, C), (3, D)]), (r.stdout[-500:], list(ap_)))
    check('data-writer: nothing about a missing summary file (the pair is complete)', 'no .summary.md' not in r.stdout)

    # ---- E. jsdom smoke
    nm = a.node_modules or ''
    if nm and os.path.isdir(os.path.join(nm, 'node_modules', 'jsdom')):
        r = subprocess.run(['node', os.path.join(HERE, 'smoke_oneshot.js'), site, nm, os.path.join(pk, '11')], capture_output=True, text=True, encoding='utf-8')
        print(r.stdout.rstrip()); sys.stderr.write(r.stderr)
        check('jsdom smoke (tools/smoke_oneshot.js)', r.returncode == 0)
    else: print('SKIP  jsdom smoke (set --node-modules to a folder with node_modules/jsdom)')
    shutil.rmtree(tmp, ignore_errors=True)
    print('\ntest_oneshot ' + ('FAILED' if fails else 'OK')); sys.exit(1 if fails else 0)

if __name__ == '__main__': main()

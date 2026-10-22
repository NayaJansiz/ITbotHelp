#!/usr/bin/env python3
"""
test_site.py - checks that the validation code inside site/index.html behaves exactly like merge_answers.py.
Needs node (any version) + the lecture repo.   python tools/test_site.py --data data --lectures ../lecture-site-engine
The page now builds ONE-RUN packs (see test_oneshot.py); this test still covers the shared validation code on the per-lecture (routed) packs,
which it builds itself in a temp folder with make_packs.py (pass --packs to use an existing folder instead).
 1. every lecture pack: the lecture the page extracts from the .md == the lecture file (same skeleton)
 2. 'flat' fuzz: random mixed Arabic/Latin/markdown strings give the same skeleton in Python and JS
 3. end to end: fabricated/valid/odd replies are run through merge_answers.py (dry run) and through the page JS;
    the per-category counters must be identical.
"""
import argparse, hashlib, json, os, random, re, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
from lecturelib import *

def js_module():
    html = open(os.path.join(ROOT, 'site', 'index.html'), encoding='utf-8').read()
    m = re.search(r'// <validate>(.*?)// </validate>', html, re.S)
    return m.group(1)

HARNESS = js_module() + r"""
var inp = JSON.parse(require('fs').readFileSync(0, 'utf8')), out;
if (inp.mode === 'extract') out = inp.packs.map(function (t) { var l = extractLecture(t); return l == null ? null : flat(l); });
if (inp.mode === 'flat') out = inp.strings.map(flat);
if (inp.mode === 'validate') {
  var ctx = { hasLecture: inp.lectureFlat != null, lectureFlat: inp.lectureFlat, qinfo: inp.qinfo, keys: inp.keys, figPages: inp.figPages || [] };
  var r = validateReply(inp.text, ctx); out = { counts: r.counts, bad: r.bad, missing: r.missing, kinds: r.rows.map(function (x) { return [x.id, x.kind]; }) };
}
process.stdout.write(JSON.stringify(out));
"""

def node(payload):
    r = subprocess.run(['node', '-e', HARNESS], input=json.dumps(payload), capture_output=True, encoding='utf-8')
    if r.returncode: sys.exit('node failed: ' + r.stderr[:500])
    return json.loads(r.stdout)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--data', default='data'); ap.add_argument('--lectures'); ap.add_argument('--sources', default='sources')
    ap.add_argument('--packs')
    a = ap.parse_args(); cfg = load_config(os.path.join(ROOT, 'config', 'subjects.json')); fails = 0
    if not a.packs:
        a.packs = tempfile.mkdtemp()
        for sid in cfg:
            r = subprocess.run([sys.executable, os.path.join(HERE, 'make_packs.py'), '--data', a.data, '--lectures', a.lectures, '--sources', a.sources, '--subject', sid, '--all', '--out', a.packs], capture_output=True, text=True, encoding='utf-8')
            if r.returncode: sys.exit('make_packs failed for subject ' + sid + ': ' + r.stdout + r.stderr)
    def check(name, ok, extra=''):
        nonlocal fails; print(('PASS  ' if ok else 'FAIL  ') + name + (('  ' + extra) if extra and not ok else '')); fails += (not ok)

    # 1. extraction from every lecture pack
    jobs = []
    for sid, c in cfg.items():
        lec = {l['file']: l for l in subject_lectures(cfg, a.lectures, a.sources, int(sid))}
        mp = os.path.join(a.packs, sid, 'manifest.json')
        if not os.path.exists(mp): continue
        for pack in json.load(open(mp, encoding='utf-8')):
            if pack != 'INFERRED': jobs.append((sid, pack, lec[pack + '.md']['text'], open(os.path.join(a.packs, sid, pack + '.md'), encoding='utf-8').read()))
    got = node({'mode': 'extract', 'packs': [j[3] for j in jobs]})
    bad = [(j[0], j[1]) for j, g in zip(jobs, got) if g != flat(j[2])]
    check(f'lecture extracted from {len(jobs)} packs == lecture file', not bad, str(bad[:5]))

    # 2. flat fuzz
    rnd = random.Random(7); alpha = list('abcXYZ019 \n\t.,;:*#|-_()') + ['<b>', '</span>', '<img src=x>', 'ـ', 'َ', 'ّ', 'إ', 'أ', 'آ', 'ى', 'ة', 'ي', 'ك', 'ء', 'ؤ', 'ئ', 'ا', 'ب', 'ت', 'س', 'م', 'ن', '٣', '…', '“', 'é', 'İ']
    strs = [''.join(rnd.choice(alpha) for _ in range(rnd.randint(0, 60))) for _ in range(3000)]
    jsf = node({'mode': 'flat', 'strings': strs}); diff = [s for s, j in zip(strs, jsf) if flat(s) != j]
    check('flat() identical on 3000 random strings', not diff, repr(diff[:2]))

    # 3. end to end on several subjects
    for sid, pack in [('11', 'par5'), ('13', 'par3'), ('14', None), ('9', None)]:
        c = cfg[sid]; lecs = {l['file']: l for l in subject_lectures(cfg, a.lectures, a.sources, int(sid))}
        man = json.load(open(os.path.join(a.packs, sid, 'manifest.json'), encoding='utf-8'))
        pk = pack or sorted(man)[0]; keys = man[pk]['keys']; fname = pk + '.md'; lec = lecs[fname]['text']
        rows = load_subject(a.data, int(sid)); byid = {r['key']: r for r in rows}
        sents = [s.strip() for s in re.split(r'(?<=[.!?؟])\s+|\n+', lec) if len(re.findall(r'\w+', s)) >= 8]
        rnd = random.Random(int(sid)); L = 'ABCDEFGHIJ'; lines = []
        def real(): s = rnd.choice(sents); w = s.split(); return ' '.join(w[:rnd.randint(min(5, len(w)), min(25, len(w)))])
        for i, k in enumerate(keys):
            n = len(byid[k]['options']); ok = L[rnd.randrange(n)]; kind = i % 11
            if kind == 0: lines.append({'id': k, 'a': ok, 'src': 'LECTURE', 'ref': 'x', 'q': real(), 'e': 'ok'})
            elif kind == 1: lines.append({'id': k, 'a': ok, 'src': 'LECTURE', 'ref': 'x', 'q': real() + ' … ' + real(), 'e': 'ok'})
            elif kind == 2: lines.append({'id': k, 'a': ok, 'src': 'LECTURE', 'ref': 'x', 'q': 'this sentence was fabricated by the model entirely', 'e': 'x'})
            elif kind == 3: lines.append({'id': k, 'a': L[n], 'src': 'LECTURE', 'q': real(), 'e': 'x'})          # letter outside
            elif kind == 4: lines.append({'id': k, 'src': 'NOT-FOUND'})
            elif kind == 5: lines.append({'id': k, 'a': ok.lower(), 'src': 'INFERRED', 'e': 'x'})
            elif kind == 6: lines.append({'id': k, 'a': ok, 'src': 'LECTURE', 'q': 'ab', 'e': 'x'})           # too short
            elif kind == 7: lines.append({'id': k, 'a': ok, 'src': 'WHATEVER', 'e': 'x'})
            elif kind == 9: lines.append({'id': k, 'a': ok, 'src': 'STUDENT', 'a0': 'A', 'src0': 'INFERRED', 'q': real(), 'e': 'edited', 'e_edited': True})   # student + valid quote
            elif kind == 10: lines.append({'id': k, 'a': ok, 'src': 'STUDENT', 'q': 'invented quote that is not in the lecture at all', 'e': 'x'})   # student, bad quote
            # kind 8: no reply at all (missing)
        lines.append({'id': 'nope:1', 'a': 'A', 'src': 'LECTURE', 'q': real()})                                 # unknown id
        other = [r['key'] for r in rows if r['key'] not in keys]
        if other: lines.append({'id': other[0], 'a': 'A', 'src': 'LECTURE', 'q': real()})                       # in subject, not in pack
        lines.append({'id': keys[0], 'a': 'A', 'src': 'LECTURE', 'q': 'x'})                                     # numeric/short duplicate
        body = '```json\n' + ',\n'.join(json.dumps(l, ensure_ascii=False) for l in lines) + ',\n```\nnot json {broken\n{"id": 1,\n'
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, 'replies', sid)); open(os.path.join(td, 'replies', sid, pk + '.jsonl'), 'w', encoding='utf-8').write(body)
            r = subprocess.run([sys.executable, os.path.join(HERE, 'merge_answers.py'), '--data', a.data, '--lectures', a.lectures, '--replies', os.path.join(td, 'replies'), '--packs', a.packs], capture_output=True, text=True)
        m = re.search(r'replies -> (\{.*?\})\n', r.stdout); pyc = eval(m.group(1)) if m else {}
        lflat = flat(extractLecture_py(open(os.path.join(a.packs, sid, pk + '.md'), encoding='utf-8').read()))
        qinfo = {r['key']: [len(r['options']), r['correct_index']] for r in rows}
        jr = node({'mode': 'validate', 'text': body, 'lectureFlat': lflat, 'qinfo': qinfo, 'keys': man[pk]['keys']})
        # the page also reports unparseable '{' lines; Python reports them as notes, compare the count
        pybad = re.search(r'(\d+) unreadable line', r.stdout); pybad = int(pybad.group(1)) if pybad else 0
        pymiss = re.search(r'NO REPLY for (\d+) of', r.stdout); pymiss = int(pymiss.group(1)) if pymiss else 0
        check(f'subject {sid} {pk}: counters equal {dict(sorted(jr["counts"].items()))}', pyc == jr['counts'], f'py={pyc} js={jr["counts"]}')
        check(f'subject {sid} {pk}: unreadable lines ({pybad}) and missing ({pymiss}) equal', (pybad, pymiss) == (len(jr['bad']), len(jr['missing'])), f'js bad={jr["bad"]} missing={len(jr["missing"])}')
    print('\ntest_site ' + ('FAILED' if fails else 'OK')); sys.exit(1 if fails else 0)

def extractLecture_py(pack):     # reference: the lecture is what make_packs wrote between its two headers
    i = pack.index('\n# LECTURE ('); start = pack.index('\n', i + 1) + 1; end = pack.rindex('\n# QUESTIONS\n\n'); return pack[start:end]

if __name__ == '__main__': main()

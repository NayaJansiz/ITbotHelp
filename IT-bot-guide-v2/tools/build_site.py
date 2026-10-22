#!/usr/bin/env python3
"""
build_site.py - generate site/packs/ (what site/index.html reads). Python 3.8+, no packages.

  python tools/build_site.py --data data --lectures ../lecture-site-engine            # all subjects
  python tools/build_site.py --data data --lectures ../lecture-site-engine --subject 11 --subject 13

Lecture picker + one-run pack: for a subject WITH lectures (repo folder and/or PDFs in sources/<id>/ listed in config/subjects.json)
the page lists every lecture (all ticked), and builds ONE pack in the browser = the ticked lectures + ALL the subject's questions
(split into the fewest packs only when over MAX_CHARS). So this script writes the pieces, not the packs:
  site/packs/index.json             instructions (INSTR_ALL), MAX_CHARS, subjects with their lecture list (file, num, chars, origin, marker)
  site/packs/<id>/lectures/<file>   the lecture text (LF line endings)
  site/packs/<id>/questions.md      the rendered question block, exactly as it appears in a pack
  site/packs/<id>/site.json         per-subject details for the page: q = [n options, current answer], t = [question, options], keys,
                                    images (question pictures), lectures{file: marker/chars/origin/figs}, p/m = proposed pictures (only with --intake)
  site/packs/<id>/manifest.json     {"all": {keys, lectures, images, parts}} (merge_answers.py --packs reads it)
A subject WITHOUT lectures keeps one INFERRED pack (unsolved questions only): site/packs/<id>/INFERRED.md, "inferred": true.
"""
import argparse, json, os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lecturelib import load_config, load_subject, marker, subject_lectures, lecnum, clen, MAX_CHARS
from make_packs import load_proposals, plan_all, all_manifest, INSTR_ALL, PROPOSED

def wjson(path, obj, **kw):
    with open(path, 'w', encoding='utf-8', newline='\n') as f: json.dump(obj, f, ensure_ascii=False, **kw)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default='data'); ap.add_argument('--lectures'); ap.add_argument('--sources', default='sources')
    ap.add_argument('--subject', type=int, action='append'); ap.add_argument('--intake', help='folder with intake/<subject>/*.json (picture proposals)'); ap.add_argument('--out', default=os.path.join('site', 'packs'))
    ap.add_argument('--max-chars', type=int, default=MAX_CHARS)
    ap.add_argument('--config', default=os.path.join(HERE, '..', 'config', 'subjects.json'))
    a = ap.parse_args()
    cfg = load_config(a.config)
    subs = json.load(open(os.path.join(a.data, 'subjects.json'), encoding='utf-8'))
    if a.subject: subs = [s for s in subs if s['id'] in a.subject]
    if os.path.isdir(a.out) and not a.subject: shutil.rmtree(a.out)
    os.makedirs(a.out, exist_ok=True)
    index = []
    for s in subs:
        sid = s['id']; sdir = os.path.join(a.out, str(sid)); c = cfg.get(str(sid), {})
        if os.path.isdir(sdir): shutil.rmtree(sdir)
        rows = load_subject(a.data, sid); lec = subject_lectures(cfg, a.lectures, a.sources, sid)
        if c.get('folder') and a.lectures and not any(l.get('origin') != 'sources' for l in lec) and not c.get('sources'):
            sys.exit(f"subject {sid}: no par*.md found in {c['folder']} (is --lectures the repo root?)")
        props = load_proposals(a.intake, sid) if a.intake else {}
        PROPOSED.clear(); PROPOSED.update(props)
        os.makedirs(sdir, exist_ok=True)
        if lec:
            qs, qb, bins, figs_all = plan_all(sid, rows, lec, a.max_chars)
            man = all_manifest(qs, lec, bins, figs_all)
            os.makedirs(os.path.join(sdir, 'lectures'))
            for l in lec:
                with open(os.path.join(sdir, 'lectures', l['file']), 'w', encoding='utf-8', newline='\n') as f: f.write(l['text'])
            with open(os.path.join(sdir, 'questions.md'), 'w', encoding='utf-8', newline='\n') as f: f.write(qb)
            lecs = {l['file']: {'marker': marker(c, l['file']), 'chars': clen(l['text']), 'origin': l.get('origin', 'repo'), 'figs': {str(pg): p for pg, p in sorted(figs_all[l['file']].items())}} for l in lec}
            keys = man['all']['keys']; images = sorted(set(man['all']['images']) - {p for d in figs_all.values() for p in d.values()})
            lec_index = [{'file': l['file'], 'num': l['num'], 'chars': lecs[l['file']]['chars'], 'origin': lecs[l['file']]['origin'], 'marker': lecs[l['file']]['marker']} for l in lec]
            inferred = False; npacks = len(bins)
        else:
            cmd = [sys.executable, os.path.join(HERE, 'make_packs.py'), '--data', a.data, '--subject', str(sid), '--out', a.out, '--config', a.config, '--sources', a.sources]
            if a.intake: cmd += ['--intake', a.intake]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0: sys.exit(f'make_packs failed for subject {sid}:\n{r.stdout}{r.stderr}')
            mp = os.path.join(sdir, 'manifest.json')
            if not os.path.exists(mp): shutil.rmtree(sdir); continue                      # nothing to pack
            man = json.load(open(mp, encoding='utf-8')); keys = man['INFERRED']['keys']; images = man['INFERRED']['images']
            lecs = {}; lec_index = []; inferred = True; npacks = 1
        wjson(os.path.join(sdir, 'manifest.json'), man, indent=1)
        pm = {}; media = {}
        if props:
            for fn in sorted(os.listdir(os.path.join(a.intake, str(sid)))):
                if fn.endswith('.json'):
                    for mid, m in json.load(open(os.path.join(a.intake, str(sid), fn), encoding='utf-8')).get('media', {}).items():
                        media[mid] = {'f': os.path.basename(m['file']), 'c': m.get('caption', '')}
            names = {m['f']: mid for mid, m in media.items()}
            pm = {k: names[f] for k, f in props.items() if f in names and k in {r['key'] for r in rows if not r.get('image')}}
        wjson(os.path.join(sdir, 'site.json'), {'p': pm, 'm': {mid: media[mid] for mid in set(pm.values())}, 'q': {r['key']: [len(r['options']), r['correct_index']] for r in rows},
                                                 't': {r['key']: [r['question'], r['options']] for r in rows}, 'keys': keys, 'images': images, 'lectures': lecs, 'inferred': inferred}, separators=(',', ':'))
        index.append({'id': sid, 'year': s['year'], 'semester': s['semester'], 'name': s['name'], 'nq': len(keys), 'inferred': inferred, 'lectures': lec_index})
        print(f"subject {sid}: {len(lec_index)} lectures, {len(keys)} questions -> {npacks} pack(s)" + (' (INFERRED)' if inferred else ''))
    ip = os.path.join(a.out, 'index.json')
    if a.subject:     # partial run: merge into the existing index
        old = json.load(open(ip, encoding='utf-8'))['subjects'] if os.path.exists(ip) else []
        keep = {s['id']: s for s in old}; keep.update({s['id']: s for s in index}); index = list(keep.values())
    index.sort(key=lambda s: (s['year'], s['semester'], s['id']))
    wjson(ip, {'instr': INSTR_ALL, 'max_chars': a.max_chars, 'subjects': index}, separators=(',', ':'))
    print(f"site/packs/index.json: {len(index)} subjects")

if __name__ == '__main__': main()

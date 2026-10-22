#!/usr/bin/env python3
"""register_sources.py - list student-added lecture text files (sources/<subject id>/<slug>.md) in config/sources.json.

  python tools/register_sources.py --data data --sources sources --config config [--report]

A student who uses the quick page uploads a PDF and the page converts it to text IN THE BROWSER, so the pull request carries
sources/<id>/<slug>.md directly (no PDF in inbox/). Merging that pull request is the approval. This tool then adds the slug to
config/sources.json (machine-managed, never hand-edited; subjects.json is never rewritten) so every tool finds the lecture.
The SUBJECT is the folder name the student chose; an unknown subject id is reported and skipped. Idempotent: run it as often as you like.
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lecturelib import load_config

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--data', default='data'); ap.add_argument('--sources', default='sources'); ap.add_argument('--config', default='config')
    a = ap.parse_args()
    subs = {str(s['id']) for s in json.load(open(os.path.join(a.data, 'subjects.json'), encoding='utf-8'))}
    cfg = load_config(os.path.join(a.config, 'subjects.json')); cpath = os.path.join(a.config, 'sources.json')
    extra = json.load(open(cpath, encoding='utf-8')) if os.path.exists(cpath) else {}
    added, errs = [], []
    for sid in sorted(os.listdir(a.sources)) if os.path.isdir(a.sources) else []:
        d = os.path.join(a.sources, sid)
        if not os.path.isdir(d) or not sid.isdigit(): continue
        slugs = sorted(f[:-3] for f in os.listdir(d) if f.endswith('.md'))
        if slugs and sid not in subs: errs.append(f'sources/{sid}/: unknown subject id (see data/subjects.json)'); continue
        known = set(cfg.get(sid, {}).get('sources', []))             # hand-edited list + sources.json, merged by load_config
        for slug in slugs:
            if slug in known: continue
            lst = extra.setdefault(sid, [])
            if slug not in lst: lst.append(slug); lst.sort(); added.append(f'{sid}/{slug}')
    if added:
        os.makedirs(a.config, exist_ok=True)
        with open(cpath, 'w', encoding='utf-8', newline='\n') as f: json.dump(extra, f, ensure_ascii=False, indent=1, sort_keys=True); f.write('\n')
    print(f'registered {len(added)} new lecture file(s): {added or "none"}')
    for e in errs: print('ERROR', e)
    sys.exit(1 if errs else 0)

if __name__ == '__main__': main()

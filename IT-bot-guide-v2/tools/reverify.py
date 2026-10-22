#!/usr/bin/env python3
"""reverify.py - re-check every stored provenance quote against the CURRENT lecture text (0 tokens).
  python tools/reverify.py --data data --lectures ../lecture-site-engine [--sources sources] [--mark]
Quote still found -> stays verified. Missing -> reported as STALE (with --mark: needs_review=1, so it goes into the next pack).
Sources: lecture-site-engine folder (config 'folder') or sources/<subject id>/<file>.md ingested from PDFs. STUDENT/INFERRED entries are skipped."""
import argparse, glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lecturelib import *
from merge_answers import quote_ok

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--data', default='data'); ap.add_argument('--lectures'); ap.add_argument('--sources', default='sources')
    ap.add_argument('--mark', action='store_true')
    ap.add_argument('--config', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config', 'subjects.json'))
    a = ap.parse_args(); cfg = load_config(a.config); tot = {'ok': 0, 'stale': 0, 'skipped': 0}
    for pp in sorted(glob.glob(os.path.join(a.data, 'provenance', 'subject-*.json'))):
        sid = int(os.path.basename(pp)[8:-5]); prov = json.load(open(pp, encoding='utf-8')); rows = load_subject(a.data, sid); byid = {r['key']: r for r in rows}
        texts = {}
        for l in subject_lectures(cfg, a.lectures, a.sources, sid): texts[l['file']] = flat(l['text'])
        for f in glob.glob(os.path.join(a.sources, str(sid), '*.md')): texts.setdefault(os.path.basename(f), flat(open(f, encoding='utf-8', errors='ignore').read()))   # unconfigured sources still count for re-checking old quotes
        stale = []
        for k, v in prov.items():
            if v.get('src') != 'LECTURE' or not v.get('quote'): tot['skipped'] += 1; continue
            t = texts.get(v.get('file'))
            if t is not None and quote_ok(v['quote'], t): tot['ok'] += 1
            else:
                tot['stale'] += 1; stale.append(k)
                if a.mark and k in byid: byid[k]['needs_review'] = 1
        if stale: print(f'subject {sid}: STALE {len(stale)} {stale[:8]}')
        if a.mark and stale: save_subject(a.data, sid, rows)
    print('reverify:', tot)
    sys.exit(1 if tot['stale'] else 0)
if __name__ == '__main__': main()

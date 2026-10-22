#!/usr/bin/env python3
"""
fake_reply.py - a stand-in for Claude, so you can test the whole page flow (paste -> check -> review -> download) without a Claude chat.
  python tools/fake_reply.py --lectures ../lecture-site-engine --subject 11 > reply.txt
For every question of the subject it writes ONE reply line in the one-run format: the answer already stored in data/, a verbatim quote from
the lecture line that best matches the stored explanation, and "lec". On purpose it also writes 1 line with an INVENTED quote (must be rejected),
1 NOT-FOUND, and 1 line whose "lec" names the wrong lecture (must still verify). Paste the output into step 3 of the page.
It does NOT measure Claude's accuracy; it only exercises the machinery.
"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8')
from lecturelib import *
from selftest import best_line

ap = argparse.ArgumentParser(); ap.add_argument('--data', default='data'); ap.add_argument('--lectures'); ap.add_argument('--sources', default='sources'); ap.add_argument('--subject', type=int, required=True)
ap.add_argument('--config', default=os.path.join(HERE, '..', 'config', 'subjects.json')); a = ap.parse_args()
cfg = load_config(a.config); lecs = subject_lectures(cfg, a.lectures, a.sources, a.subject)
if not lecs: sys.exit('this subject has no lectures here (pass --lectures <lecture repo>, or add PDF lectures)')
rows = [r for r in load_subject(a.data, a.subject) if r['correct_index'] is not None and r.get('explanation')]
out = []
for i, r in enumerate(rows):
    score, line, f = max(((*best_line(l['text'], r['explanation']), l['file']) for l in lecs), key=lambda x: x[0])
    letter = 'ABCDEFGHIJ'[r['correct_index']]
    if score < .2: out.append({'id': r['key'], 'src': 'NOT-FOUND'}); continue
    q = ' '.join(line.split()[:20]); lec = f
    if i == 0: q = 'هذه جملة مخترعة بالكامل ولا وجود لها في أي محاضرة من المحاضرات'      # must be rejected
    elif i == 1: out.append({'id': r['key'], 'src': 'NOT-FOUND'}); continue
    elif i == 2 and len(lecs) > 1: lec = next(l['file'] for l in lecs if l['file'] != f)          # wrong lec: the quote is still found elsewhere
    out.append({'id': r['key'], 'a': letter, 'src': 'LECTURE', 'lec': lec, 'ref': 'x', 'q': q, 'e': 'شرح تجريبي'})
print('\n'.join(json.dumps(o, ensure_ascii=False) for o in out))

#!/usr/bin/env python3
"""
merge_answers.py - validate Claude's replies (JSON lines) and merge them into data/ (dry-run unless --apply).

Replies live in  replies/<subject_id>/<pack-name>.jsonl   (pack-name = the pack file name without .md,
e.g. replies/11/par5.jsonl answers packs/11/par5.md ; INFERRED.jsonl answers the INFERRED pack;
all-<sha8>.jsonl answers the ONE-RUN pack of the lecture picker: each LECTURE/FIGURE line names its lecture in "lec" (a hint: the quote is
looked up in every lecture of the subject, the named one first), and a NOT-FOUND line is ignored when another part of the same reply answers that id).

  python tools/merge_answers.py --data data --lectures ../lecture-site-engine --replies replies            # dry run (report)
  python tools/merge_answers.py ... --apply                                                              # write data/ + provenance
  python tools/merge_answers.py ... --leftover packs                                                      # build INFERRED packs for unresolved questions

What is checked (machine, 0 tokens):  valid JSON, known id, letter inside the options, explanation <= 200 chars with the
lecture marker (م#) added, and for src=LECTURE the quote must exist WORD FOR WORD in the lecture file of that pack.
Rules: never overwrites an existing different answer (reported as CONFLICT-EXISTING) unless --overwrite;
STUDENT answers (src=STUDENT, optional a0/src0/e_edited/reason/q) are applied like LECTURE if their quote is found, else tagged STUDENT (visible after merge, listed for approvers).
two LECTURE answers with different letters for one question = CONFLICT (nothing applied).
Image questions are made visible only if the image file exists under --root/media.
"""
import argparse, datetime, glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
from lecturelib import *
from make_packs import pack_text, INSTR_I, fig_pages

LET = 'ABCDEFGHIJ'

def parse_reply(path):
    good, bad = [], []
    for n, line in enumerate(open(path, encoding='utf-8', errors='ignore').read().split('\n'), 1):
        line = line.strip().strip(',')
        if not line.startswith('{'): continue
        try: good.append(json.loads(line))
        except Exception: bad.append(n)
    return good, bad

def fit(e, mk, limit=200):
    e = re.sub(r'\s+', ' ', (e or '').replace('\n', ' ')).strip()
    room = limit - len(mk) - 1
    if len(e) > room: e = e[:room - 1].rstrip() + '…'
    return (e + ' ' + mk).strip()

def quote_ok(quote, lecture_flat):
    parts = [flat(p) for p in re.split(r'…|\.\.\.', quote or '')]
    parts = [p for p in parts if len(p) >= 15]      # ignore fragments too short to prove anything
    return bool(parts) and all(p in lecture_flat for p in parts)

def find_quote(quote, hint, scope, lflat):
    """first lecture of `scope` (the lecture named by the reply line's "lec" first) that holds the quote word for word, else None"""
    for f in lec_order(hint, scope):
        if quote_ok(quote, lflat[f]): return f
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default='data'); ap.add_argument('--lectures'); ap.add_argument('--sources', default='sources')
    ap.add_argument('--replies', default='replies'); ap.add_argument('--packs', default='packs'); ap.add_argument('--root', default='.')
    ap.add_argument('--apply', action='store_true'); ap.add_argument('--overwrite', action='store_true')
    ap.add_argument('--approved-lecture-overwrites', action='store_true',
                    help='After a reviewed PR is merged, allow verified LECTURE answers to replace a different stored answer; inferred answers are never covered by this flag.')
    ap.add_argument('--hide-inferred', action='store_true'); ap.add_argument('--leftover')
    ap.add_argument('--config', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config', 'subjects.json'))
    a = ap.parse_args()
    cfg = load_config(a.config); today = datetime.date.today().isoformat()
    for sdir in sorted(glob.glob(os.path.join(a.replies, '*'))):
        if not os.path.isdir(sdir): continue
        sid = int(os.path.basename(sdir)); rows = load_subject(a.data, sid); byid = {r['key']: r for r in rows}
        c = cfg.get(str(sid), {}); lec = {l['file']: l for l in subject_lectures(cfg, a.lectures, a.sources, sid)}
        lflat = {f: flat(l['text']) for f, l in lec.items()}
        cand = collections.defaultdict(list); rep = collections.Counter(); notes = []
        for rp in sorted(glob.glob(os.path.join(sdir, '*.jsonl')) + glob.glob(os.path.join(sdir, '*.txt'))):
            pack = re.sub(r'-[0-9a-f]{8}$', '', os.path.splitext(os.path.basename(rp))[0]); fname = pack + '.md'
            is_all = bool(re.fullmatch(r'(all|quick)(-\d+)?', pack))      # one-run pack (lecture picker): the quote may be in ANY lecture, "lec" is only a hint
            scope = list(lec) if is_all else ([fname] if fname in lec else [])
            items, bad = parse_reply(rp)
            mp = os.path.join(a.packs, str(sid), 'manifest.json')
            if os.path.exists(mp) and not pack.startswith('quick'):   # 'quick' = student uploaded PDF + export: only a part of the subject was asked, so no NO-REPLY check
                want = json.load(open(mp, encoding='utf-8')).get('all' if is_all else pack, {}).get('keys', []); got = {i.get('id') for i in items}
                miss = [k for k in want if k not in got]
                if miss: notes.append(f"{pack}: NO REPLY for {len(miss)} of {len(want)} questions {miss[:6]} (ask Claude to continue, or paste the rest)")
            if bad: notes.append(f"{pack}: {len(bad)} unreadable line(s) {bad[:5]} (not valid JSON)")
            answered = {i.get('id') for i in items if not (i.get('src') == 'NOT-FOUND' or not i.get('a'))}; seen_nf = set()   # several parts pasted together: a NOT-FOUND never hides an answer
            for it in items:
                k = it.get('id'); q = byid.get(k)
                if q is None: rep['INVALID unknown id'] += 1; notes.append(f"{pack}: unknown id {k}"); continue
                src = it.get('src')
                if src == 'NOT-FOUND' or not it.get('a'):
                    if k not in answered and k not in seen_nf: seen_nf.add(k); rep['NOT-FOUND'] += 1
                    continue
                L = str(it['a']).strip().upper()[:1]
                if L not in LET[:len(q['options'])]: rep['INVALID letter'] += 1; notes.append(f"{k}: letter {it.get('a')!r} outside options"); continue
                if src == 'LECTURE':
                    if not scope: rep['INVALID no lecture file'] += 1; notes.append(f"{k}: pack {pack} has no lecture file"); continue
                    hit = find_quote(it.get('q'), it.get('lec'), scope, lflat)
                    if not hit: rep['QUOTE-FAIL'] += 1; notes.append(f"{k}: quote not found word-for-word in {', '.join(scope) if len(scope) < 4 else str(len(scope)) + ' lectures'}: {str(it.get('q'))[:70]!r}"); continue
                    if it.get('lec') and norm_lec(it.get('lec'), scope) not in (None, hit): notes.append(f"{k}: reply said lec={it.get('lec')} but the quote is in {hit} (used {hit})")
                    cand[k].append(('LECTURE', LET.index(L), it, hit)); rep['LECTURE ok'] += 1
                elif src == 'STUDENT':      # Part 2D: a human picked/edited the answer; a pasted quote that is found upgrades it to LECTURE
                    hit = find_quote(it.get('q'), it.get('lec'), scope, lflat) if it.get('q') and scope else None
                    if hit: cand[k].append(('LECTURE', LET.index(L), it, hit)); rep['STUDENT+quote verified'] += 1
                    else: cand[k].append(('STUDENT', LET.index(L), it, None)); rep['STUDENT (no verified quote)'] += 1
                elif src == 'FIGURE':       # answer read from a figure page: cannot be machine-verified -> visible, needs_review=1
                    m = re.fullmatch(r'p(\d+)', str(it.get('ref') or '').strip()); hit = None
                    if m:
                        for f in lec_order(it.get('lec'), scope):
                            if int(m.group(1)) in fig_pages(lec[f]): hit = f; break
                    if not hit: rep['INVALID figure ref'] += 1; notes.append(f"{k}: FIGURE ref {it.get('ref')!r} is not a figure page of {', '.join(scope) if len(scope) < 4 else str(len(scope)) + ' lectures'}"); continue
                    cand[k].append(('FIGURE', LET.index(L), it, hit)); rep['FIGURE'] += 1
                elif src == 'INFERRED': cand[k].append(('INFERRED', LET.index(L), it, None)); rep['INFERRED'] += 1
                else: rep[f'INVALID src {src}'] += 1
        res = collections.Counter(); prov_path = os.path.join(a.data, 'provenance', f'subject-{sid}.json')
        prov = json.load(open(prov_path, encoding='utf-8')) if os.path.exists(prov_path) else {}
        for k, cs in cand.items():
            q = byid[k]; lc = [x for x in cs if x[0] == 'LECTURE']
            if len({x[1] for x in lc}) > 1: res['CONFLICT between lecture packs'] += 1; notes.append(f"{k}: lecture packs disagree {[LET[x[1]] for x in lc]} -> nothing applied"); continue
            kind, idx, it, fname = lc[0] if lc else cs[0]
            if q['correct_index'] is not None and q['correct_index'] != idx and not a.overwrite:
                if a.approved_lecture_overwrites and kind == 'LECTURE':
                    res['approved LECTURE overwrite'] += 1
                    notes.append(f"{k}: verified lecture answer {LET[idx]} replaces existing {LET[q['correct_index']]} after PR approval ({fname})")
                else:
                    res['CONFLICT-EXISTING (needs review)'] += 1; notes.append(f"{k}: existing answer {LET[q['correct_index']]} but {kind} says {LET[idx]} ({fname or 'general knowledge'}) -> kept existing"); continue
            if kind == 'FIGURE': notes.append(f"{k}: FIGURE answer {LET[idx]} from {fname} {it.get('ref')} (not machine-verified, needs_review=1) -> approver please look at the picture")
            if q['correct_index'] == idx and not a.overwrite and kind == 'LECTURE' and q.get('needs_review') == 0:
                # The answer is already correct, but still record its verified
                # lecture marker so students see (م#) at the end of the explanation.
                mk = marker(c, fname)
                old_e = (q.get('explanation') or '').strip()
                base_e = old_e
                marker_start = base_e.rfind('(م')
                if marker_start >= 0 and base_e.endswith(')') and base_e[marker_start + 2:-1].isdigit():
                    base_e = base_e[:marker_start].rstrip()
                new_e = fit(base_e, mk)
                if new_e != old_e:
                    q['explanation'] = new_e
                    res['lecture marker added/updated'] += 1
                else:
                    res['already same'] += 1
                entry = prov.get(k, {})
                entry.update({
                    'src': 'LECTURE',
                    'ref': it.get('ref'),
                    'file': fname,
                    'quote': it.get('q'),
                    'date': today,
                })
                prov[k] = entry
                continue
            if kind == 'LECTURE': e = fit(it.get('e'), marker(c, fname)); nr = 0
            elif kind == 'STUDENT': e = fit(it.get('e'), ''); nr = 0      # owner decision: approval = merge, so visible once merged
            elif kind == 'FIGURE': e = fit(it.get('e'), ''); nr = 1
            else: e = fit(it.get('e'), '(استنتاج)'); nr = 1
            img_ok = (not q.get('image')) or os.path.exists(os.path.join(a.root, q['image'])) or os.path.exists(os.path.join(a.root, os.path.basename(q['image'])))
            vis = img_ok and not (kind == 'INFERRED' and a.hide_inferred)
            if not img_ok: notes.append(f"{k}: image file missing ({q['image']}) -> answered but stays hidden")
            res[f'{kind} applied' + ('' if vis else ' (kept hidden)')] += 1
            q['correct_index'] = idx; q['explanation'] = e; q['needs_review'] = nr; q['excluded'] = 0 if vis else 1
            prov[k] = {'src': kind, 'ref': it.get('ref') if kind in ('LECTURE', 'FIGURE') else None, 'file': fname, 'quote': it.get('q') if kind == 'LECTURE' else None, 'date': today}
            if it.get('img') or it.get('uses_image') is not None:   # picture binding PROPOSED by the student/Claude; the single-writer Action applies it after approval (Part 2C)
                prov[k]['img'] = it.get('img') or None; prov[k]['uses_image'] = it.get('uses_image'); prov[k]['img_edited'] = bool(it.get('img_edited'))
                if it.get('img_edited'): notes.append(f"{k}: student changed the picture binding (img={it.get('img') or 'removed'}) -> approver please check")
            if it.get('src') == 'STUDENT' or it.get('e_edited') or it.get('a0'):
                prov[k].update({'student': True, 'a0': it.get('a0'), 'src0': it.get('src0'), 'e_edited': bool(it.get('e_edited')), 'reason': it.get('reason')})
                if kind == 'STUDENT': prov[k]['src'] = 'STUDENT'
                notes.append(f"{k}: STUDENT edit ({'quote verified' if kind == 'LECTURE' else 'no verified quote'}; a0={it.get('a0')}, explanation edited={bool(it.get('e_edited'))}) -> approver please check")
        print(f"\n=== subject {sid}: replies -> {dict(rep)}\n    merge -> {dict(res)}")
        for n in notes[:40]: print('    -', n)
        if len(notes) > 40: print(f'    ... {len(notes)-40} more')
        if a.apply:
            save_subject(a.data, sid, rows); os.makedirs(os.path.dirname(prov_path), exist_ok=True)
            json.dump(prov, open(prov_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, sort_keys=True); print('    data/ updated')
        if a.leftover:
            left = [r for r in rows if r['correct_index'] is None]
            if left:
                od = os.path.join(a.leftover, str(sid)); os.makedirs(od, exist_ok=True)
                open(os.path.join(od, 'INFERRED.md'), 'w', encoding='utf-8').write(pack_text(INSTR_I, f"SUBJECT {sid} — leftovers (not found in lectures)", left))
                print(f"    leftover: {len(left)} unresolved -> {od}/INFERRED.md")
    if not a.apply: print('\n(dry run: nothing written. Add --apply to write data/.)')

if __name__ == '__main__': main()

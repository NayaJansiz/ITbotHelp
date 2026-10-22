#!/usr/bin/env python3
"""
make_packs.py - build one ready-to-drop "pack" per lecture file (instructions + lecture + its questions).

  python tools/make_packs.py --data data --lectures ../lecture-site-engine --subject 11
  python tools/make_packs.py --data data --lectures ../lecture-site-engine --subject 11 --all     # re-verify solved questions too
  python tools/make_packs.py --data data --status                                                   # coverage per subject

By default only UNSOLVED questions (correct_index is null) are packed. Each question is routed to its top-K
lecture files (keyword ranking, measured: right lecture inside top-3 for ~91% of questions), so a question can
appear in up to K packs; merge_answers.py keeps the answer that has a verified quote.
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
from lecturelib import *

INSTR_L = """# TASK (do not repeat this text)
Solve the multiple-choice questions below for university students using ONLY the LECTURE in this file.
Reply with ONE JSON object per line, one line per question id, same order, nothing else (no prose, no code fences):
{"id":"<id>","a":"<letter>","src":"LECTURE","ref":"<nearest heading>","q":"<verbatim quote>","e":"<explanation>"}
RULES
1. Pick the option the lecture supports. Never use outside knowledge. If the lecture does not settle it, reply {"id":"<id>","src":"NOT-FOUND"}.
2. Letters follow the order shown (A, B, C...). Never reorder, edit or merge options.
3. "q" = 5-25 words copied EXACTLY from the lecture (same language, same spelling, not translated). It is machine-checked.
4. "e" = Arabic, max 150 characters, why the answer is right, using the lecture's terms. Do not mention these rules.
5. A question marked IMAGE: the image is attached to this chat; read it. If it is missing reply NOT-FOUND.
6. A question marked IMAGE?: the named image MAY belong to it (it is only a proposal). Add "uses_image":true or "uses_image":false to that question's JSON line.
7. If the answer rests ONLY on a figure page (a <!-- fig: ... --> marker in the lecture; that page image is attached, see FIGURE IMAGES at the end), reply {"id":"<id>","a":"<letter>","src":"FIGURE","ref":"p<N>","e":"<explanation>"} without "q". If the image is not attached reply NOT-FOUND.
"""
INSTR_I = """# TASK (do not repeat this text)
These questions were NOT found in the lectures. Solve them from general knowledge of the subject.
Reply with ONE JSON object per line, one line per question id, same order, nothing else (no prose, no code fences):
{"id":"<id>","a":"<letter>","src":"INFERRED","e":"<explanation>"}
RULES
1. Letters follow the order shown (A, B, C...). Never reorder, edit or merge options.
2. "e" = Arabic, max 150 characters. If you are not sure, reply {"id":"<id>","src":"NOT-FOUND"} instead of guessing.
3. A question marked IMAGE: the image is attached to this chat; read it. If it is missing reply NOT-FOUND.
4. A question marked IMAGE?: the named image MAY belong to it (it is only a proposal). Add "uses_image":true or "uses_image":false to that question's JSON line.
"""

INSTR_ALL = """# TASK (do not repeat this text)
Solve the multiple-choice questions below for university students using ONLY the LECTURES in this file. Each lecture starts with a line "# LECTURE (<file name>)".
Reply with ONE JSON object per line, one line per question id, same order, nothing else (no prose, no code fences):
{"id":"<id>","a":"<letter>","src":"LECTURE","lec":"<file name>","ref":"<nearest heading>","q":"<verbatim quote>","e":"<explanation>"}
RULES
1. Pick the option the lectures support. Never use outside knowledge. If none of the lectures settles it, reply {"id":"<id>","src":"NOT-FOUND"}. Every question needs a line, in order.
2. Letters follow the order shown (A, B, C...). Never reorder, edit or merge options.
3. "lec" = the file name from the header of the lecture the quote comes from, exactly as written (for example par5.md).
4. "q" = 5-25 words copied EXACTLY from that lecture (same language, same spelling, not translated). It is machine-checked.
5. "e" = Arabic, max 150 characters, why the answer is right, using the lecture's terms. Do not mention these rules.
6. A question marked IMAGE: the image is attached to this chat; read it. If it is missing reply NOT-FOUND.
7. A question marked IMAGE?: the named image MAY belong to it (it is only a proposal). Add "uses_image":true or "uses_image":false to that question's JSON line.
8. If the answer rests ONLY on a figure page (a <!-- fig: ... --> marker in a lecture; that page image is attached, see FIGURE IMAGES at the end), reply {"id":"<id>","a":"<letter>","src":"FIGURE","lec":"<file name>","ref":"p<N>","e":"<explanation>"} without "q". If the image is not attached reply NOT-FOUND.
"""

PROPOSED = {}     # question key -> image file name (picture PROPOSED by ingest_polls.py, not yet confirmed by a student)

def load_proposals(intake, sid):
    """{key: file name} from intake/<sid>/*.json (polls[].proposed_media -> media[id].file)."""
    out = {}; d = os.path.join(intake, str(sid)) if intake else None
    if not d or not os.path.isdir(d): return out
    for fn in sorted(os.listdir(d)):
        if not fn.endswith('.json'): continue
        j = json.load(open(os.path.join(d, fn), encoding='utf-8'))
        for p in j.get('polls', []):
            m = p.get('proposed_media')
            if m and p.get('key') and m in j.get('media', {}): out[p['key']] = os.path.basename(j['media'][m]['file'])
    return out

def render_q(q):
    L = 'ABCDEFGHIJ'
    s = f"### {q['key']}\n"
    if q.get('pre_text'): s += "```\n" + q['pre_text'] + "\n```\n"
    s += q['question'].strip() + "\n"
    s += "\n".join(f"{L[i]}) {o}" for i, o in enumerate(q['options'])) + "\n"
    if q.get('image'): s += f"IMAGE: {os.path.basename(q['image'])}\n"
    elif q['key'] in PROPOSED: s += f"IMAGE?: {PROPOSED[q['key']]}\n"
    return s

def imgs_of(plist):
    return sorted({os.path.basename(q['image']) for q in plist if q.get('image')} | {PROPOSED[q['key']] for q in plist if not q.get('image') and q['key'] in PROPOSED})

def fig_pages(lecture):
    """{page number: (repo-relative image path, page text)} for the FIGURE pages of a sources/ lecture (markers written by ingest_pdf.py)"""
    out = {}; page = 0; buf = collections.defaultdict(list)
    for ln in lecture['text'].split('\n'):
        m = re.match(r'\s*<!-- p(\d+) -->', ln)
        if m: page = int(m.group(1)); continue
        m = re.match(r'\s*<!-- fig: (\S+) -->', ln)
        if m and lecture.get('dir'): out[page] = ['sources/' + os.path.basename(lecture['dir']) + '/' + m.group(1), '']; continue
        buf[page].append(ln)
    for pg in out: out[pg][1] = '\n'.join(buf[pg])
    return out

def figs_for(lecture, plist, minwords=2):
    """figure pages worth attaching to this pack: page text shares >= minwords words with some question (a figure image costs ~1,200 tokens)"""
    if not lecture or not lecture.get('dir'): return {}
    fp = fig_pages(lecture); pick = {}
    for pg, (path, txt) in fp.items():
        pw = set(words(txt))
        if any(len(pw & set(words(qtext(q)))) >= minwords for q in plist): pick[pg] = path
    return pick

def pack_text(instr, title, qs, lecture=None, figs=None):
    s = instr + f"\n# {title}\n"
    if lecture: s += f"\n# LECTURE ({lecture['file']})\n\n" + lecture['text'] + "\n"
    s += "\n# QUESTIONS\n\n" + "\n".join(render_q(q) for q in qs)
    if figs: s += "\n# FIGURE IMAGES (attached to this chat)\n" + "\n".join(f"- p{pg}: {os.path.basename(p)}" for pg, p in sorted(figs.items())) + "\n"
    return s

def qblock(qs):
    return "\n".join(render_q(q) for q in qs)

def fig_lines(figs):
    """figs = {lecture file: {page: repo path}} (insertion order = order of the lectures in the pack)"""
    return [f"- {f} p{pg}: {os.path.basename(p)}" for f, d in figs.items() for pg, p in sorted(d.items())]

def pack_text_all(instr, title, qb, lectures, figs=None):
    """one-run pack: several lectures + all questions. site/index.html builds the same text in JS (tools/test_oneshot.py compares them)."""
    s = instr + f"\n# {title}\n"
    for l in lectures: s += f"\n# LECTURE ({l['file']})\n\n" + l['text'] + "\n"
    s += "\n# QUESTIONS\n\n" + qb
    fl = fig_lines(figs or {})
    if fl: s += "\n# FIGURE IMAGES (attached to this chat)\n" + "\n".join(fl) + "\n"
    return s

def plan_all(sid, rows, lec, max_chars=MAX_CHARS):
    """-> (questions sorted by id, rendered question block, [[lecture file, ...] per pack], {lecture file: {page: figure path}})"""
    qs = sorted(rows, key=lambda q: q['id']); qb = qblock(qs)
    overhead = clen(INSTR_ALL) + clen(qb) + PACK_SLACK
    bins = plan_bins([{'file': l['file'], 'num': l['num'], 'chars': clen(l['text'])} for l in lec], overhead, max_chars)
    return qs, qb, bins, {l['file']: figs_for(l, qs) for l in lec}

def all_manifest(qs, lec, bins, figs_all):
    allfigs = {p for d in figs_all.values() for p in d.values()}
    return {'all': {'lecture': None, 'lectures': [l['file'] for l in lec], 'keys': [q['key'] for q in qs], 'images': sorted(set(imgs_of(qs)) | allfigs),
                    'parts': [{'pack': 'all' if len(bins) == 1 else f'all-{i}', 'lectures': files} for i, files in enumerate(bins, 1)]}}

def write_all(sid, rows, lec, outdir, max_chars=MAX_CHARS):
    """one-run packs for a subject: every lecture + every question; split into the fewest packs only when over max_chars"""
    qs, qb, bins, figs_all = plan_all(sid, rows, lec, max_chars); byfile = {l['file']: l for l in lec}
    man = all_manifest(qs, lec, bins, figs_all)
    for i, (files, part) in enumerate(zip(bins, man['all']['parts']), 1):
        figs = {f: figs_all[f] for f in files if figs_all[f]}
        title = f"SUBJECT {sid}" + (f" — part {i} of {len(bins)}" if len(bins) > 1 else '')
        path = os.path.join(outdir, part['pack'] + '.md')
        open(path, 'w', encoding='utf-8', newline='\n').write(pack_text_all(INSTR_ALL, title, qb, [byfile[f] for f in files], figs))
        part['chars'] = os.path.getsize(path)
    return man

def status(data):
    subs = json.load(open(os.path.join(data, 'subjects.json'), encoding='utf-8'))
    print(f"{'id':>3} {'yr':>2} {'sem':>3}  {'subject':<24} total solved visible unsolved excluded needs_review")
    T = [0] * 6
    for s in subs:
        rows = load_subject(data, s['id'])
        tot = len(rows); sol = sum(r['correct_index'] is not None for r in rows)
        vis = sum(r['correct_index'] is not None and not r['excluded'] for r in rows)
        uns = tot - sol; exc = sum(bool(r['excluded']) for r in rows)
        nr = sum(r['correct_index'] is not None and not r['excluded'] and bool(r['needs_review']) for r in rows)
        for i, v in enumerate((tot, sol, vis, uns, exc, nr)): T[i] += v
        print(f"{s['id']:>3} {s['year']:>2} {s['semester']:>3}  {s['name']:<24} {tot:>5} {sol:>6} {vis:>7} {uns:>8} {exc:>8} {nr:>12}")
    print(f"{'ALL':<36} {T[0]:>5} {T[1]:>6} {T[2]:>7} {T[3]:>8} {T[4]:>8} {T[5]:>12}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default='data'); ap.add_argument('--lectures'); ap.add_argument('--sources', default='sources', help='folder written by ingest_pdf.py')
    ap.add_argument('--subject', type=int, action='append'); ap.add_argument('--all', action='store_true')
    ap.add_argument('--k', type=int, default=3); ap.add_argument('--out', default='packs')
    ap.add_argument('--config', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config', 'subjects.json'))
    ap.add_argument('--mode', choices=['routed', 'all'], default='routed', help='routed = one pack per lecture, questions routed to the best K (old); all = ONE run: every lecture + every question, split only over MAX_CHARS')
    ap.add_argument('--max-chars', type=int, default=MAX_CHARS)
    ap.add_argument('--status', action='store_true'); ap.add_argument('--intake', help='folder with intake/<subject>/*.json (adds proposed pictures to the packs)')
    a = ap.parse_args()
    if a.status: return status(a.data)
    if not a.subject: ap.error('--subject is required')
    cfg = load_config(a.config)
    for sid in a.subject:
        rows = load_subject(a.data, sid)
        PROPOSED.clear(); PROPOSED.update(load_proposals(a.intake, sid))
        qs = [q for q in rows if a.all or q['correct_index'] is None]
        outdir = os.path.join(a.out, str(sid)); os.makedirs(outdir, exist_ok=True)
        if a.mode == 'all':
            c = cfg.get(str(sid), {}); lec = subject_lectures(cfg, a.lectures, a.sources, sid)
            if c.get('folder') and not a.lectures and not c.get('sources'): sys.exit(f"subject {sid}: --lectures is required (config folder {c['folder']})")
            if c.get('folder') and a.lectures and not lec: sys.exit(f"subject {sid}: no par*.md found in {c['folder']} (is --lectures the repo root?)")
            if lec:
                manifest = write_all(sid, rows, lec, outdir, a.max_chars)
                json.dump(manifest, open(os.path.join(outdir, 'manifest.json'), 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1)
                m = manifest['all']; print(f"subject {sid}: {len(rows)} questions, {len(lec)} lectures -> {len(m['parts'])} pack(s) in {outdir}/")
                for pt in m['parts']: print(f"   {pt['pack']:<8} {len(pt['lectures']):>3} lectures  {pt['chars']//1000:>4} KB")
                continue
        if not qs: print(f"subject {sid}: nothing to pack (no unsolved questions)"); continue
        c = cfg.get(str(sid), {})
        sources = c.get('sources', [])
        manifest = {}; packs = collections.defaultdict(list); byfile = {}
        lec = subject_lectures(cfg, a.lectures, a.sources, sid)
        if sources:
            # sources-first (PDF lectures listed in config): only those files; ONE pack per source file, every question, no routing
            lec = [l for l in lec if l.get('origin') == 'sources' and l['file'][:-3] in sources]
            if not lec: print(f"subject {sid}: no source files found in {a.sources}/{sid}/ matching {sources}"); continue
            byfile = {l['file']: l for l in lec}
            for l in lec: packs[l['file']] = list(qs)
        else:
            if c.get('folder') and not a.lectures: sys.exit(f"subject {sid}: --lectures is required (config folder {c['folder']})")
            if c.get('folder') and not lec: sys.exit(f"subject {sid}: no par*.md found in {c['folder']} (is --lectures the repo root?)")
            if lec:
                bm = BM25([l['text'] for l in lec]); byfile = {l['file']: l for l in lec}
                for q in qs:
                    for i in bm.rank(qtext(q))[:a.k]: packs[lec[i]['file']].append(q)
        for f, plist in sorted(packs.items(), key=lambda x: (byfile[x[0]]['num'], x[0])):
            plist.sort(key=lambda q: q['id'])
            name = f[:-3]
            figs = figs_for(byfile[f], plist)
            open(os.path.join(outdir, name + '.md'), 'w', encoding='utf-8').write(
                pack_text(INSTR_L, f"SUBJECT {sid} — lecture file {f}", plist, byfile[f], figs))
            manifest[name] = {'lecture': f, 'keys': [q['key'] for q in plist],
                              'images': sorted(set(imgs_of(plist)) | set(figs.values()))}
        if not lec:   # no lecture source: everything goes to the INFERRED pack
            open(os.path.join(outdir, 'INFERRED.md'), 'w', encoding='utf-8').write(pack_text(INSTR_I, f"SUBJECT {sid} — no lecture folder configured", qs))
            manifest['INFERRED'] = {'lecture': None, 'keys': [q['key'] for q in qs], 'images': imgs_of(qs)}
        json.dump(manifest, open(os.path.join(outdir, 'manifest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f"subject {sid}: {len(qs)} questions -> {len(manifest)} packs in {outdir}/")
        for n, m in manifest.items():
            sz = os.path.getsize(os.path.join(outdir, n + '.md'))
            print(f"   {n:<10} {len(m['keys']):>3} questions  {sz//1000:>4} KB  images: {len(m['images'])}")

if __name__ == '__main__': main()

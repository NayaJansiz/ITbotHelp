#!/usr/bin/env python3
"""
apply_pending.py - the SINGLE WRITER of data/ (Part 2C/3). Python 3.8+, no packages.

Students only ADD uniquely named files in a pull request:
  intake/<subject>/<date>-<sha8>.json      polls from a Telegram export (tools/ingest_polls.py)
  replies/<subject>/<pack>-<sha8>.jsonl    Claude's answers after the student's review (+ <pack>-<sha8>.summary.md)
  sources/ , media/                        lecture text, figure pages and pictures (content-hash names)
This tool applies every file that is not yet listed in data/applied.json, ONE AT A TIME, in the order the files were
added to git (fallback: path), with the same machine checks as merge_answers.py, and writes a report.

  python tools/apply_pending.py --data data --lectures ../lecture-site-engine            # dry run: report only, nothing written
  python tools/apply_pending.py --data data --lectures ../lecture-site-engine --apply --report report.md

What it does per file
  intake : media entries are merged into data/media.json (the file must exist under media/ and match its sha256);
           poll 'update'  -> question/options changed, correct_index re-mapped by option TEXT (done by ingest_polls),
                             hide_for_review -> answer cleared + needs_review=1 (re-solved by the pack workflow);
           poll 'new'     -> new row with key f:<hash12> (unsolved, hidden); a fingerprint that already exists under another
                             key is recorded in data/aliases.json instead of creating a duplicate;
           'unchanged'    -> nothing. Existing pictures are never replaced; rows absent from an export are never deleted.
           Proposed pictures (proposed_media) are only proposals and change nothing here.
  replies: merge_answers.py logic (LECTURE / STUDENT / FIGURE / INFERRED, CONFLICT-EXISTING keeps the stored answer), then
           picture bindings the student CONFIRMED (reply field `img`, `img_edited`) are written to data/media.json used_by.
Exit code 1 = structural ERROR (changed/immutable file, missing or altered picture, unknown subject, merge failure).
The report also lists NEEDS DECISION items (conflicts, STUDENT edits, FIGURE answers, rejected lines): approvers decide, no error.
"""
import argparse, collections, hashlib, json, os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from lecturelib import load_subject, save_subject, fp_parts, strip_num, flatn
from merge_answers import parse_reply

def sha_file(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def jload(p, default):
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else default
def jsave(p, obj):
    json.dump(obj, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, sort_keys=True)

def git_added_time(root, rel):
    try:
        r = subprocess.run(['git', '-C', root, 'log', '--diff-filter=A', '--format=%ct', '--', rel], capture_output=True, text=True)
        ts = [int(x) for x in r.stdout.split() if x.strip().isdigit()]
        return min(ts) if ts else None
    except Exception:
        return None

def find_pending(root, applied):
    """-> (pending [(rel path, sha)], errors). A listed file whose content changed is an ERROR (files are immutable)."""
    files = []
    for kind, pats in (('intake', ('.json',)), ('replies', ('.jsonl', '.txt'))):
        base = os.path.join(root, kind)
        if not os.path.isdir(base): continue
        for sdir in sorted(os.listdir(base)):
            d = os.path.join(base, sdir)
            if not os.path.isdir(d) or not sdir.isdigit(): continue
            for fn in sorted(os.listdir(d)):
                if fn.endswith(pats): files.append(f'{kind}/{sdir}/{fn}')
    pend, errs = [], []
    for rel in files:
        h = sha_file(os.path.join(root, rel))
        if rel in applied:
            if applied[rel] != h: errs.append(f'{rel}: already applied but its content changed (files are immutable: add a NEW file instead)')
        else: pend.append((rel, h))
    pend.sort(key=lambda x: (git_added_time(root, x[0]) or 0, x[0]))
    return pend, errs

class Ctx:
    def __init__(self, a, work):
        self.a, self.work = a, work
        self.media = jload(os.path.join(work, 'media.json'), {})
        self.aliases = jload(os.path.join(work, 'aliases.json'), {})
        self.subs = {s['id']: s for s in json.load(open(os.path.join(work, 'subjects.json'), encoding='utf-8'))}
        self.next_id = 1 + max([r['id'] for f in os.listdir(os.path.join(work, 'questions')) for r in json.load(open(os.path.join(work, 'questions', f), encoding='utf-8'))] or [0])
        self.errors, self.decide, self.lines = [], [], []
    def rows(self, sid): return load_subject(self.work, sid)

def apply_intake(ctx, rel, root):
    j = json.load(open(os.path.join(root, rel), encoding='utf-8')); sid = int(j['subject']); c = collections.Counter()
    if sid not in ctx.subs: ctx.errors.append(f'{rel}: unknown subject {sid}'); return
    if int(os.path.basename(os.path.dirname(rel))) != sid: ctx.errors.append(f'{rel}: file is in folder {os.path.dirname(rel)} but says subject {sid}'); return
    for mid, m in (j.get('media') or {}).items():             # pictures first: a missing/altered picture rejects the whole file
        p = os.path.join(root, m['file'])
        if not os.path.exists(p): ctx.errors.append(f'{rel}: picture {m["file"]} is missing from media/'); return
        if sha_file(p) != m.get('sha256'): ctx.errors.append(f'{rel}: picture {m["file"]} does not match its sha256'); return
    for mid, m in (j.get('media') or {}).items():
        e = ctx.media.setdefault(mid, {'file': m['file'], 'sha256': m['sha256'], 'original_names': [], 'caption': '', 'used_by': []})
        e['original_names'] = sorted(set(e.get('original_names', [])) | set(m.get('original_names', [])))
        if m.get('caption') and not e.get('caption'): e['caption'] = m['caption']
        c['pictures'] += 1
    rows = ctx.rows(sid); byk = {r['key']: r for r in rows}; byfp = {fp_parts(r['question'], r['options'])[2]: r for r in rows}
    for p in j.get('polls', []):
        act, key = p.get('action'), p.get('key')
        if act == 'unchanged': c['unchanged'] += 1; continue
        if act == 'update':
            r = byk.get(key)
            if r is None: ctx.errors.append(f'{rel}: update for unknown key {key}'); continue
            old_q = r['question']; num = re.match(r'^\s*\d+\s*[-_ـ.)\]:]+\s*', old_q)
            new_q = (num.group(0) if num else '') + p['question']
            if new_q != old_q: r['question'] = new_q
            if p['options'] != r['options']:
                was_solved = r['correct_index'] is not None
                r['options'] = p['options']; r['correct_index'] = p.get('correct_index')
                if was_solved and r['correct_index'] is None:         # the old correct option text no longer exists
                    r['needs_review'] = 1; r['excluded'] = 1
                    ctx.decide.append(f'{key}: options changed and the old correct option no longer exists -> answer cleared, hidden until re-solved')
            c['update'] += 1
        elif act == 'new':
            fp = p['fingerprint']; hit = byfp.get(fp)
            if hit is not None or key in byk:
                keys = sorted(set(ctx.aliases.get(fp, [])) | {key} | ({hit['key']} if hit else set()))
                if len(keys) > 1: ctx.aliases[fp] = keys
                c['alias (already known)'] += 1; continue
            row = {'id': ctx.next_id, 'key': key, 'subject_id': sid, 'question': p['question'], 'options': p['options'], 'correct_index': None,
                   'explanation': None, 'needs_review': 0, 'answer_source': 0, 'image': None, 'long_question': 0, 'excluded': 1, 'pre_text': None}
            ctx.next_id += 1; rows.append(row); byk[key] = row; byfp[fp] = row; c['new'] += 1
        else: ctx.errors.append(f'{rel}: poll with unknown action {act!r}')
    save_subject(ctx.work, sid, rows)
    ctx.lines.append(f'- `{rel}`: ' + ', '.join(f'{k} {v}' for k, v in c.items()))

def apply_reply(ctx, rel, root):
    sid = int(os.path.basename(os.path.dirname(rel))); a = ctx.a
    if sid not in ctx.subs: ctx.errors.append(f'{rel}: unknown subject {sid}'); return
    with tempfile.TemporaryDirectory() as td:
        d = os.path.join(td, 'replies', str(sid)); os.makedirs(d); shutil.copy(os.path.join(root, rel), d)
        cmd = [sys.executable, os.path.join(HERE, 'merge_answers.py'), '--data', ctx.work, '--replies', os.path.join(td, 'replies'), '--root', root,
               '--sources', os.path.join(root, 'sources'), '--apply']
        if a.approved_lecture_overwrites: cmd += ['--approved-lecture-overwrites']
        if a.lectures: cmd += ['--lectures', a.lectures]
        if a.packs and os.path.isdir(a.packs): cmd += ['--packs', a.packs]
        if a.config: cmd += ['--config', a.config]
        r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0: ctx.errors.append(f'{rel}: merge_answers failed: {(r.stdout + r.stderr)[-400:]}'); return
    out = [l for l in r.stdout.split('\n') if l.strip() and 'dry run' not in l]
    ctx.lines.append(f'- `{rel}`'); ctx.lines += ['  ' + l for l in out]
    for l in out:                                                    # items that need a human decision
        if re.search(r'CONFLICT|STUDENT edit|FIGURE|picture binding|lecture packs disagree|NO REPLY|unreadable|quote not found|letter .* outside', l): ctx.decide.append(f'{rel}: {l.strip()}')
    # picture bindings the student confirmed on the review screen
    items, _ = parse_reply(os.path.join(root, rel)); rows = {r['key'] for r in ctx.rows(sid)}; nb = 0
    for it in items:
        k = it.get('id')
        if k not in rows or ('img' not in it and not it.get('img_edited')): continue
        img = it.get('img')
        if img:
            if img not in ctx.media: ctx.errors.append(f'{rel}: {k} binds unknown picture id {img}'); continue
            if k not in ctx.media[img]['used_by']: ctx.media[img]['used_by'] = sorted(ctx.media[img]['used_by'] + [k]); nb += 1
        elif it.get('img_edited'):                                   # student removed a binding that existed
            for m in ctx.media.values():
                if k in m.get('used_by', []): m['used_by'] = [x for x in m['used_by'] if x != k]; nb += 1
    if nb: ctx.lines.append(f'  picture bindings changed: {nb}')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default='data'); ap.add_argument('--root', default='.', help='repo root (intake/, replies/, media/, sources/)')
    ap.add_argument('--lectures'); ap.add_argument('--packs', default=os.path.join('site', 'packs'))
    ap.add_argument('--config', default=os.path.join(HERE, '..', 'config', 'subjects.json'))
    ap.add_argument('--apply', action='store_true', help='write data/ (default: dry run, report only)')
    ap.add_argument('--approved-lecture-overwrites', action='store_true',
                    help='After a reviewed PR is merged, allow verified lecture answers to replace existing answers; inferred answers remain protected.')
    ap.add_argument('--report', help='write the Markdown report here')
    ap.add_argument('--only', help='apply only this one pending file (relative path)')
    a = ap.parse_args()
    root = a.root; applied = jload(os.path.join(a.data, 'applied.json'), {})
    pend, errs = find_pending(root, applied)
    if a.only: pend = [p for p in pend if p[0] == a.only]
    with tempfile.TemporaryDirectory() as td:
        work = os.path.join(td, 'data'); shutil.copytree(a.data, work)       # all changes happen on a copy
        ctx = Ctx(a, work); ctx.errors += errs; done = {}
        for rel, h in pend:
            n_err = len(ctx.errors)
            try:
                (apply_intake if rel.startswith('intake/') else apply_reply)(ctx, rel, root)
            except Exception as e:                                          # a broken file must not stop the others
                ctx.errors.append(f'{rel}: could not be processed ({type(e).__name__}: {e})')
            if len(ctx.errors) == n_err: done[rel] = h
            else: ctx.lines.append(f'  !! `{rel}` NOT applied (see errors)')
        # note replies without their summary file (approvers rely on it)
        for rel in done:
            if rel.startswith('replies/') and not os.path.exists(os.path.join(root, os.path.splitext(rel)[0] + '.summary.md')):
                ctx.decide.append(f'{rel}: no .summary.md next to the reply file')
        md = ['# Pending changes report', '', f'- files pending: {len(pend)} | applied: {len(done)} | errors: {len(ctx.errors)} | needs decision: {len(ctx.decide)}', '']
        md += ['## ERRORS (block the merge)'] + (['- ' + e for e in ctx.errors] or ['none']) + ['', '## NEEDS DECISION (approvers)'] + (['- ' + d for d in ctx.decide] or ['none']) + ['', '## Applied files'] + (ctx.lines or ['nothing pending'])
        report = '\n'.join(md) + '\n'; print(report)
        if a.report: open(a.report, 'w', encoding='utf-8').write(report)
        if a.apply and done:
            jsave(os.path.join(work, 'media.json'), ctx.media)
            if ctx.aliases: jsave(os.path.join(work, 'aliases.json'), ctx.aliases)
            applied.update(done); jsave(os.path.join(work, 'applied.json'), applied)
            for dp, _, fns in os.walk(work):                              # copy the result back
                for fn in fns:
                    dst = os.path.join(a.data, os.path.relpath(os.path.join(dp, fn), work)); os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(os.path.join(dp, fn), dst)
            print(f'data/ updated: {len(done)} file(s) recorded in data/applied.json')
        elif not a.apply: print('(dry run: nothing written. Add --apply to write data/.)')
    sys.exit(1 if ctx.errors else 0)

if __name__ == '__main__': main()

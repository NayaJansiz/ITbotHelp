#!/usr/bin/env python3
"""
test_apply.py - tools/apply_pending.py (single writer of data/).  python tools/test_apply.py --data data --lectures ../lecture-site-engine
Runs in a temp copy of the repo layout; uses tests/fixtures/intake/2/*.json + tests/fixtures/media/ (real sample) and subject 11 par5.
"""
import argparse, copy, glob, hashlib, json, os, random, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); sys.path.insert(0, HERE)
from lecturelib import *

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--data', default='data'); ap.add_argument('--lectures', required=True); a = ap.parse_args(); fails = 0
    def check(n, ok, x=''):
        nonlocal fails; print(('PASS  ' if ok else 'FAIL  ') + n + (('  ' + str(x)[:500]) if x and not ok else '')); fails += (not ok)
    with tempfile.TemporaryDirectory() as td:
        data = os.path.join(td, 'data'); shutil.copytree(a.data, data); shutil.rmtree(os.path.join(data, 'provenance'), ignore_errors=True)
        for f in ('media.json', 'aliases.json', 'applied.json'):
            if os.path.exists(os.path.join(data, f)): os.remove(os.path.join(data, f))
        os.makedirs(os.path.join(td, 'media')); os.makedirs(os.path.join(td, 'intake', '2')); os.makedirs(os.path.join(td, 'replies', '11'))
        src_int = glob.glob(os.path.join(ROOT, 'tests', 'fixtures', 'intake', '2', '*.json'))[0]
        run = lambda *args: subprocess.run([sys.executable, os.path.join(HERE, 'apply_pending.py'), '--data', data, '--root', td, '--lectures', a.lectures, '--packs', os.path.join(td, 'nopacks')] + list(args), capture_output=True, text=True)
        applied = lambda: json.load(open(os.path.join(data, 'applied.json'))) if os.path.exists(os.path.join(data, 'applied.json')) else {}
        # 1. picture missing -> error, file not applied
        shutil.copy(src_int, os.path.join(td, 'intake', '2', 'a.json'))
        r = run('--apply'); check('missing picture -> exit 1, nothing applied', r.returncode == 1 and 'is missing from media/' in r.stdout and not applied(), r.stdout[-400:])
        # 2. with pictures: applied, media.json merged with EMPTY used_by (proposals are not bindings)
        for f in glob.glob(os.path.join(ROOT, 'tests', 'fixtures', 'media', '*.jpg')): shutil.copy(f, os.path.join(td, 'media'))
        before = json.load(open(os.path.join(data, 'questions', 'subject-2.json'), encoding='utf-8'))
        r = run('--apply'); mj = json.load(open(os.path.join(data, 'media.json')))
        check('intake applied (exit 0), 3 pictures in media.json, used_by empty', r.returncode == 0 and len(mj) == 3 and all(m['used_by'] == [] for m in mj.values()) and 'intake/2/a.json' in applied(), r.stdout[-500:])
        after = json.load(open(os.path.join(data, 'questions', 'subject-2.json'), encoding='utf-8'))
        check('31 unchanged polls change no row', before == after)
        r = run('--apply'); check('second run: nothing pending, data untouched', 'files pending: 0' in r.stdout and r.returncode == 0)
        # 3. immutable
        t = json.load(open(os.path.join(td, 'intake', '2', 'a.json'))); t['date'] = 'x'; json.dump(t, open(os.path.join(td, 'intake', '2', 'a.json'), 'w'))
        r = run(); check('changed already-applied file -> ERROR', r.returncode == 1 and 'content changed' in r.stdout, r.stdout[-300:])
        shutil.copy(src_int, os.path.join(td, 'intake', '2', 'a.json'))
        # 4. update / hide / new / alias in a second intake file
        j = json.load(open(src_int)); polls = j['polls']; byk = {r_['key']: r_ for r_ in after}
        u1 = next(p for p in polls if p['key'] == 'y1:p43'); u1.update(action='update', match='text-changed', question='التيار الكهربائي هو :')
        u2 = next(p for p in polls if p['key'] == 'y1:p44'); old = byk['y1:p44']
        u2.update(action='update', match='options-changed', options=['خيار جديد 1', 'خيار جديد 2'], correct_index=None, hide_for_review=True)
        n1 = dict(fingerprint='f' * 64, question='سؤال جديد كلياً ؟', options=['نعم', 'لا'], key='f:' + 'f' * 12, match=None, action='new', batch='x', msg='m1')
        n2 = dict(n1, msg='m2')                                           # same fingerprint again (second student) -> alias, not a duplicate
        j['polls'] = [u1, u2, n1, n2]; j['date'] = '2026-10-20'
        json.dump(j, open(os.path.join(td, 'intake', '2', 'b.json'), 'w'), ensure_ascii=False)
        r = run('--apply'); rows = {x['key']: x for x in json.load(open(os.path.join(data, 'questions', 'subject-2.json'), encoding='utf-8'))}
        check('text update keeps the "N- " numbering of the old text', rows['y1:p43']['question'] == '1- التيار الكهربائي هو :' and rows['y1:p43']['correct_index'] == byk['y1:p43']['correct_index'], rows['y1:p43']['question'])
        check('options change with lost correct option -> answer cleared, needs_review, hidden', rows['y1:p44']['correct_index'] is None and rows['y1:p44']['needs_review'] == 1 and rows['y1:p44']['excluded'] == 1 and rows['y1:p44']['options'] == ['خيار جديد 1', 'خيار جديد 2'], rows['y1:p44'])
        newrows = [x for x in rows.values() if x['key'] == 'f:' + 'f' * 12]
        allids = [x['id'] for f in glob.glob(os.path.join(data, 'questions', '*.json')) for x in json.load(open(f, encoding='utf-8'))]
        check('new question created once (hidden, unsolved, unique id), no duplicate', len(newrows) == 1 and newrows[0]['correct_index'] is None and newrows[0]['excluded'] == 1 and len(allids) == len(set(allids)), newrows)
        check('hide event listed for the approvers', 'y1:p44' in r.stdout and 'NEEDS DECISION' in r.stdout)
        # 5. replies: LECTURE answer + picture bindings
        lec = {l['file']: l for l in load_lectures(a.lectures, json.load(open(os.path.join(ROOT, 'config', 'subjects.json')))['11']['folder'])}['par5.md']['text']
        sents = [s.strip() for s in re.split(r'(?<=[.!?؟])\s+|\n+', lec) if len(re.findall(r'\w+', s)) >= 10]; quote = ' '.join(random.Random(1).choice(sents).split()[:14])
        s11 = json.load(open(os.path.join(data, 'questions', 'subject-11.json'), encoding='utf-8')); k1, k2, k3 = [x['key'] for x in s11 if x['correct_index'] is not None][:3]
        for x in s11:
            if x['key'] == k1: x['correct_index'] = None
        save_subject(data, 11, s11)
        mid = sorted(mj)[0]
        lines = [{'id': k1, 'a': 'A', 'src': 'LECTURE', 'ref': 'x', 'q': quote, 'e': 'e', 'uses_image': True, 'img': mid},
                 {'id': k2, 'a': 'A', 'src': 'NOT-FOUND', 'uses_image': True, 'img': mid, 'img_edited': True}]
        open(os.path.join(td, 'replies', '11', 'par5-aaaaaaaa.jsonl'), 'w', encoding='utf-8').write('\n'.join(json.dumps(x, ensure_ascii=False) for x in lines) + '\n')
        r = run('--apply'); mj = json.load(open(os.path.join(data, 'media.json'))); s11 = {x['key']: x for x in json.load(open(os.path.join(data, 'questions', 'subject-11.json'), encoding='utf-8'))}
        check('reply applied through merge_answers (LECTURE ok, marker added)', r.returncode == 0 and s11[k1]['correct_index'] == 0 and s11[k1]['explanation'].endswith('(م5)'), r.stdout[-500:])
        check('confirmed picture bindings written to media.json used_by', sorted(mj[mid]['used_by']) == sorted([k1, k2]), mj[mid]['used_by'])
        check('missing .summary.md is flagged for the approvers', 'no .summary.md' in r.stdout)
        # 6. a student removes a binding
        open(os.path.join(td, 'replies', '11', 'par5-bbbbbbbb.jsonl'), 'w', encoding='utf-8').write(json.dumps({'id': k2, 'src': 'NOT-FOUND', 'img_edited': True}) + '\n')
        r = run('--apply'); mj = json.load(open(os.path.join(data, 'media.json')))
        check('binding removed when the student unticks it (img_edited without img)', mj[mid]['used_by'] == [k1], mj[mid]['used_by'])
        # 7. build the bot db with the confirmed binding
        db = os.path.join(td, 'bot.db'); os.makedirs(os.path.join(td, 'media'), exist_ok=True)
        rr = subprocess.run([sys.executable, os.path.join(HERE, 'bot_db_tool.py'), 'build', data, db, '--force', '--media-dir', os.path.join(td, 'media')], capture_output=True, text=True)
        import sqlite3
        _c = sqlite3.connect(db)
        try:
            img = _c.execute('SELECT image FROM questions WHERE key=?', (k1,)).fetchone()[0]
        finally:
            _c.close()  # Windows: the temp folder cannot be removed while a connection is open
        check('bot_db_tool build gives the bound question its picture', rr.returncode == 0 and img == mj[mid]['file'], rr.stdout + rr.stderr)
    # 8. student PR path guard (temp git repo)
    with tempfile.TemporaryDirectory() as g:
        sh = lambda *c: subprocess.run(list(c), cwd=g, capture_output=True, text=True)
        sh('git', 'init', '-q', '-b', 'main'); sh('git', 'config', 'user.email', 'a@b'); sh('git', 'config', 'user.name', 't')
        os.makedirs(os.path.join(g, 'data')); open(os.path.join(g, 'data', 'x'), 'w').write('1'); sh('git', 'add', '-A'); sh('git', 'commit', '-qm', 'base'); sh('git', 'checkout', '-qb', 'pr')
        os.makedirs(os.path.join(g, 'replies', '9')); open(os.path.join(g, 'replies', '9', 'a.jsonl'), 'w').write('{}'); os.makedirs(os.path.join(g, 'media')); open(os.path.join(g, 'media', 'aaa.jpg'), 'w').write('p')
        sh('git', 'add', '-A'); sh('git', 'commit', '-qm', 'ok')
        guard = lambda: subprocess.run([sys.executable, os.path.join(HERE, 'check_pr_paths.py'), '--base', 'main'], cwd=g, capture_output=True, text=True)
        r = guard(); check('PR path guard: only new files in allowed folders -> OK', r.returncode == 0, r.stdout + r.stderr)
        open(os.path.join(g, 'data', 'x'), 'w').write('2'); sh('git', 'commit', '-qam', 'edit data')
        r = guard(); check('PR path guard: editing data/ -> violation listed', r.returncode == 1 and 'M  data/x' in r.stdout, r.stdout + r.stderr)
    print('\ntest_apply ' + ('FAILED' if fails else 'OK')); sys.exit(1 if fails else 0)
if __name__ == '__main__': main()

#!/usr/bin/env python3
"""
selftest.py - mechanical test of make_packs.py + merge_answers.py (it does NOT test Claude's accuracy).
It makes packs for subject 11, fakes Claude's replies from the answers already in data/, injects 4 faults
(fabricated quote, wrong letter vs existing answer, unreadable line, too-long explanation) and checks they are caught.

  python tools/selftest.py --data data --lectures ../lecture-site-engine
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from lecturelib import *
from merge_answers import fit

def run(*a):
    r = subprocess.run([sys.executable] + list(a), capture_output=True, text=True, encoding='utf-8'); return r.stdout + r.stderr

def best_line(text, expl):
    et = set(words(expl)); best = (0, '')
    for ln in text.split('\n'):
        t = re.sub(r'\s+', ' ', re.sub(r'[*_`#>|]+', ' ', ln)).strip()
        if len(t) < 25: continue
        s = len(et & set(words(t))) / max(1, len(et))
        if s > best[0]: best = (s, t)
    return best

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--data', default='data'); ap.add_argument('--lectures', required=True)
    a = ap.parse_args(); cfg = load_config(os.path.join(HERE, '..', 'config', 'subjects.json'))
    sid = 11; tmp = tempfile.mkdtemp(); data = os.path.join(tmp, 'data'); shutil.copytree(a.data, data)
    out = run(os.path.join(HERE, 'make_packs.py'), '--data', data, '--lectures', a.lectures, '--subject', str(sid), '--all', '--out', os.path.join(tmp, 'packs'))
    assert 'packs in' in out, out
    man = json.load(open(os.path.join(tmp, 'packs', str(sid), 'manifest.json'), encoding='utf-8'))
    lec = {l['file']: l for l in load_lectures(a.lectures, cfg[str(sid)]['folder'])}
    rows = {r['key']: r for r in load_subject(data, sid)}
    oracle = {k: max((best_line(l['text'], r['explanation'] or '')[0], f) for f, l in lec.items())[1] for k, r in rows.items()}
    rd = os.path.join(tmp, 'replies', str(sid)); os.makedirs(rd); n_ok = 0; fab = conf = None
    for pack, m in man.items():
        lines = []
        for k in m['keys']:
            r = rows[k]; f = m['lecture']
            if oracle[k] != f: lines.append(json.dumps({'id': k, 'src': 'NOT-FOUND'})); continue
            q = ' '.join(best_line(lec[f]['text'], r['explanation'] or '')[1].split()[:20]); letter = 'ABCDEFGHIJ'[r['correct_index']]
            if fab is None: fab = k; q = 'هذه الجملة مخترعة بالكامل ولا وجود لها في أي محاضرة من المحاضرات'
            elif conf is None: conf = k; letter = 'ABCDEFGHIJ'[(r['correct_index'] + 1) % len(r['options'])]
            else: n_ok += 1
            lines.append(json.dumps({'id': k, 'a': letter, 'src': 'LECTURE', 'ref': 'x', 'q': q, 'e': 'شرح'}, ensure_ascii=False))
        if not lines: continue
        lines = lines[:-2] if len(lines) > 6 else lines; dropped = m['keys'][len(lines):]
        lines.append('{"id": broken'); open(os.path.join(rd, pack + '.jsonl'), 'w', encoding='utf-8').write('```json\n' + '\n'.join(lines) + '\n```')
        break   # one pack is enough
    rep = run(os.path.join(HERE, 'merge_answers.py'), '--data', data, '--lectures', a.lectures, '--replies', os.path.join(tmp, 'replies'), '--packs', os.path.join(tmp, 'packs'), '--root', '/nonexistent')
    # --- Part 2A item 7: lecture text that comes from a PDF (sources/9/wp-lecture-3.md), checked on the temp data copy
    SRC = os.path.abspath(os.path.join(HERE, '..', 'sources')); sid9 = 9
    out9 = run(os.path.join(HERE, 'make_packs.py'), '--data', data, '--subject', str(sid9), '--all', '--out', os.path.join(tmp, 'packs9'), '--sources', SRC)
    assert 'packs in' in out9, out9
    man9 = json.load(open(os.path.join(tmp, 'packs9', str(sid9), 'manifest.json'), encoding='utf-8')); pk9 = 'wp-lecture-3'; assert pk9 in man9, list(man9)
    src_text = load_sources(SRC, sid9, [pk9])[0]['text']; k9 = man9[pk9]['keys']
    real9 = ' '.join(max((l for l in src_text.split('\n') if len(l.split()) > 8 and not l.lstrip().startswith('<!--')), key=len).split()[:15])
    lines9 = [{'id': k9[0], 'a': 'A', 'src': 'LECTURE', 'ref': 'x', 'q': real9, 'e': 'شرح'},
              {'id': k9[1], 'a': 'A', 'src': 'LECTURE', 'ref': 'x', 'q': 'هذه الجملة مخترعة بالكامل ولا وجود لها في ملف المصدر على الإطلاق', 'e': 'شرح'},
              {'id': k9[2], 'a': 'A', 'src': 'FIGURE', 'ref': 'p6', 'e': 'شرح'},
              {'id': k9[3], 'a': 'A', 'src': 'FIGURE', 'ref': 'p99', 'e': 'شرح'}]
    rd9 = os.path.join(tmp, 'replies9', str(sid9)); os.makedirs(rd9)
    open(os.path.join(rd9, pk9 + '.jsonl'), 'w', encoding='utf-8').write('\n'.join(json.dumps(x, ensure_ascii=False) for x in lines9) + '\n')
    rep9 = run(os.path.join(HERE, 'merge_answers.py'), '--data', data, '--sources', SRC, '--replies', os.path.join(tmp, 'replies9'), '--packs', os.path.join(tmp, 'packs9'), '--root', '/nonexistent')
    m9 = re.search(r'replies -> (\{.*?\})\n', rep9); c9 = eval(m9.group(1)) if m9 else {}
    checks = {'valid quotes accepted': 'LECTURE ok' in rep, 'fabricated quote rejected': 'QUOTE-FAIL' in rep and fab in rep,
              'wrong letter vs existing kept out': 'CONFLICT-EXISTING' in rep, 'unreadable line reported': 'unreadable' in rep, 'missing replies reported': 'NO REPLY' in rep,
              'long explanation fitted to 200': len(fit('x' * 500, '(م1)')) <= 200 and fit('x' * 500, '(م1)').endswith('(م1)'),
              'valid quote from sources/9/wp-lecture-3.md accepted': c9.get('LECTURE ok') == 1,
              'fabricated quote rejected against sources': c9.get('QUOTE-FAIL') == 1 and k9[1] in rep9,
              'FIGURE page 6 accepted': c9.get('FIGURE') == 1 and k9[2] in rep9,
              'FIGURE page 99 rejected': c9.get('INVALID figure ref') == 1 and k9[3] in rep9}
    # --- Part 2D: STUDENT edits (applied on a copy with --apply)
    d2 = os.path.join(tmp, 'data2'); shutil.copytree(data, d2); rows2 = load_subject(d2, sid); r2 = {r['key']: r for r in rows2}
    pk = next(iter(man)); ks = man[pk]['keys']; f = man[pk]['lecture']; kq, kn, kc = ks[0], ks[1], ks[2]
    for k in (kq, kn): r2[k]['correct_index'] = None
    save_subject(d2, sid, rows2)
    q = ' '.join(max((l for l in lec[f]['text'].split('\n') if len(l.split()) > 8), key=len).split()[:15]); cur = r2[kc]['correct_index']
    L = lambda i: 'ABCDEFGHIJ'[i % len(r2[kc]['options'])]
    items = [{'id': kq, 'a': 'A', 'src': 'STUDENT', 'a0': None, 'src0': 'NOT-FOUND', 'q': q, 'e': 'شرح معدّل', 'e_edited': True, 'reason': 'r'},
             {'id': kn, 'a': 'A', 'src': 'STUDENT', 'q': '', 'e': 'بلا اقتباس'},
             {'id': kc, 'a': L(cur + 1), 'src': 'STUDENT', 'a0': L(cur), 'src0': 'LECTURE', 'q': '', 'e': 'x'}]
    rd2 = os.path.join(tmp, 'replies2', str(sid)); os.makedirs(rd2)
    open(os.path.join(rd2, pk + '-1a2b3c4d.jsonl'), 'w', encoding='utf-8').write('\n'.join(json.dumps(i, ensure_ascii=False) for i in items))
    rep2 = run(os.path.join(HERE, 'merge_answers.py'), '--data', d2, '--lectures', a.lectures, '--replies', os.path.join(tmp, 'replies2'), '--packs', os.path.join(tmp, 'packs'), '--root', '/nonexistent', '--apply')
    rr = {r['key']: r for r in load_subject(d2, sid)}; pv = json.load(open(os.path.join(d2, 'provenance', f'subject-{sid}.json'), encoding='utf-8'))
    checks.update({'student+valid quote -> LECTURE verified with marker': pv.get(kq, {}).get('src') == 'LECTURE' and rr[kq]['explanation'].endswith(marker(cfg[str(sid)], f)) and pv[kq].get('e_edited') is True,
                   'student without quote -> STUDENT, visible, no marker': pv.get(kn, {}).get('src') == 'STUDENT' and rr[kn]['needs_review'] == 0 and rr[kn]['excluded'] == 0,
                   'student edit vs stored answer -> CONFLICT-EXISTING, unchanged': 'CONFLICT-EXISTING' in rep2 and rr[kc]['correct_index'] == cur,
                   'reply file name suffix -sha8 accepted': 'no lecture file' not in rep2 and 'LECTURE applied' in rep2})
    for k, v in checks.items(): print(('PASS  ' if v else 'FAIL  ') + k)
    if not all(checks.values()): print(rep); print(rep9); print(locals().get('rep2', '')); sys.exit(1)
    print('selftest OK (mechanical checks only)'); shutil.rmtree(tmp)

if __name__ == '__main__': main()

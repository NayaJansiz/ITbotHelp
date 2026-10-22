#!/usr/bin/env python3
"""
run_all.py - run EVERY test of the project in the right order and print the raw output of each.
  python tools/run_all.py --lectures ../lecture-site-engine
Optional: --node-modules <folder containing node_modules/jsdom>  (or set JSDOM_DIR; without it the browser-like page tests are SKIPPED)
Needs: Python 3.8+, node. Optional: pip install pymupdf pillow (PDF + picture tests are SKIPPED without them; test_inbox/test_media).
Exit code 0 only if nothing FAILED. Skipped tests are listed at the end so you never mistake "skipped" for "passed".
"""
import argparse, importlib.util, json, os, shutil, subprocess, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))

def have(mod): return importlib.util.find_spec(mod) is not None

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--lectures', required=True, help='folder of the lecture repo (git clone https://github.com/homs-uni/lecture-site-engine)')
    ap.add_argument('--data', default='data'); ap.add_argument('--node-modules', default=os.environ.get('JSDOM_DIR', '')); a = ap.parse_args()
    os.chdir(ROOT); L = a.lectures; D = a.data; nm = a.node_modules; jsdom = bool(nm) and os.path.isdir(os.path.join(nm, 'node_modules', 'jsdom'))
    if not os.path.isdir(os.path.join(L, 'subjects')): sys.exit(f'{L}/subjects not found: clone the lecture repo first (git clone https://github.com/homs-uni/lecture-site-engine {L})')
    T = lambda name, *args: ['python', os.path.join('tools', name)] + list(args)
    steps = [('selftest', T('selftest.py', '--data', D, '--lectures', L), None),
             ('build_site', T('build_site.py', '--data', D, '--lectures', L, '--intake', 'intake'), None),
             ('test_site', T('test_site.py', '--data', D, '--lectures', L), None),
             ('test_sources', T('test_sources.py', '--data', D), None),
             ('test_inbox', T('test_inbox.py', '--data', D), None if have('pymupdf') and have('PIL') else 'pip install pymupdf pillow'),
             ('test_apply', T('test_apply.py', '--data', D, '--lectures', L), None),
             ('test_media', T('test_media.py', '--data', D), None if have('PIL') else 'pip install pillow'),
             ('test_oneshot', T('test_oneshot.py', '--data', D, '--lectures', L) + (['--node-modules', nm] if jsdom else []), None),
             ('test_tools', T('test_tools.py', '--data', D, '--lectures', L), None),
             ('test_quick', T('test_quick.py', '--data', D, '--lectures', L, '--node-modules', nm), None if (jsdom and os.path.isdir(os.path.join(nm, 'node_modules', 'pdfjs-dist')) and have('pymupdf') and have('bs4')) else 'npm install jsdom pdfjs-dist@3.11.174 (in --node-modules folder) and pip install pymupdf beautifulsoup4')]
    if jsdom:
        steps.append(('smoke_page.js', ['node', os.path.join('tools', 'smoke_page.js'), 'site'], None))
    else:
        steps.append(('smoke_page.js', None, 'npm install jsdom (in any folder) and pass --node-modules <that folder>'))
    fix = None
    if jsdom:      # fixture for the picture-binding smoke: 3 picture proposals for subject 11 (the recipe from HANDOFF-BUILD.md)
        sys.path.insert(0, HERE); from lecturelib import load_subject
        fix = tempfile.mkdtemp(); os.makedirs(os.path.join(fix, 'intake', '11')); os.makedirs(os.path.join(fix, 'site'))
        rows = [r for r in load_subject(D, 11) if not r.get('image')][:3]
        json.dump({'subject': 11, 'year': 3, 'polls': [{'key': r['key'], 'proposed_media': 'aaa111bbb222'} for r in rows], 'media': {'aaa111bbb222': {'file': 'media/aaa111bbb222.jpg', 'caption': 'x'}}}, open(os.path.join(fix, 'intake', '11', 't.json'), 'w'))
        if subprocess.run([sys.executable, os.path.join('tools', 'build_site.py'), '--data', D, '--lectures', L, '--intake', os.path.join(fix, 'intake'), '--out', os.path.join(fix, 'site', 'packs')], capture_output=True).returncode == 0:
            shutil.copy(os.path.join('site', 'index.html'), os.path.join(fix, 'site'))
            steps.append(('smoke_pics.js', ['node', os.path.join('tools', 'smoke_pics.js'), os.path.join(fix, 'site'), nm], None))
        else: steps.append(('smoke_pics.js', None, 'fixture build failed'))
    results = []; env = dict(os.environ); env['PYTHONIOENCODING'] = 'utf-8'
    if jsdom: env['NODE_PATH'] = os.path.join(os.path.abspath(nm), 'node_modules')
    for name, cmd, skip in steps:
        print(f'\n################ {name}', flush=True)
        if skip or cmd is None: print(f'SKIPPED ({skip})'); results.append((name, 'SKIPPED', 0, skip)); continue
        cmd = [sys.executable if c == 'python' else c for c in cmd]; t = time.time()
        r = subprocess.run(cmd, env=env); results.append((name, 'ok' if r.returncode == 0 else 'FAILED', time.time() - t, ''))
        print(f'[exit code {r.returncode}]', flush=True)
    print('\n================ summary')
    for name, st, secs, why in results: print(f'{st:<8} {name:<14} {secs:5.0f}s  {why}')
    if fix: shutil.rmtree(fix, ignore_errors=True)
    bad = [n for n, st, _, _ in results if st == 'FAILED']
    print('\nALL TESTS PASSED' + (' (some skipped, see above)' if any(st == 'SKIPPED' for _, st, _, _ in results) else '') if not bad else '\nFAILED: ' + ', '.join(bad))
    sys.exit(1 if bad else 0)

if __name__ == '__main__': main()

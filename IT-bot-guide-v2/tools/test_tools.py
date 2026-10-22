#!/usr/bin/env python3
"""
test_tools.py - the local-testing helpers: fake_reply.py (stand-in for Claude), set_repo.py, dev_site.py (build + serve).
  python tools/test_tools.py --data data --lectures ../lecture-site-engine
"""
import argparse, json, os, re, shutil, socket, subprocess, sys, tempfile, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--data', default='data'); ap.add_argument('--lectures', required=True); a = ap.parse_args(); fails = 0
    def check(n, ok, x=''):
        nonlocal fails; print(('PASS  ' if ok else 'FAIL  ') + n + (('  ' + str(x)[:500]) if x and not ok else '')); fails += (not ok)
    py = lambda *args, **kw: subprocess.run([sys.executable] + [str(x) for x in args], capture_output=True, text=True, encoding='utf-8', **kw)
    with tempfile.TemporaryDirectory() as td:
        # fake_reply -> merge_answers (dry run): the machinery accepts real quotes, rejects the invented one, de-duplicates nothing it should not
        r = py(os.path.join(HERE, 'fake_reply.py'), '--data', a.data, '--lectures', a.lectures, '--subject', 11)
        check('fake_reply.py writes a reply (exit 0, one line per solved question)', r.returncode == 0 and len(r.stdout.strip().split('\n')) >= 30, r.stderr[-300:])
        os.makedirs(os.path.join(td, 'replies', '11')); open(os.path.join(td, 'replies', '11', 'all-1a2b3c4d.jsonl'), 'w', encoding='utf-8').write(r.stdout)
        m = py(os.path.join(HERE, 'merge_answers.py'), '--data', a.data, '--lectures', a.lectures, '--replies', os.path.join(td, 'replies'))
        c = eval(re.search(r'replies -> (\{.*?\})\n', m.stdout).group(1))
        check('merge_answers.py on the fake reply: many LECTURE ok, exactly 1 QUOTE-FAIL (the invented quote), 1 NOT-FOUND, nothing INVALID', c.get('LECTURE ok', 0) >= 25 and c.get('QUOTE-FAIL') == 1 and c.get('NOT-FOUND') == 1 and not any(k.startswith('INVALID') for k in c), c)
        # set_repo
        page = os.path.join(td, 'index.html'); shutil.copy(os.path.join(ROOT, 'site', 'index.html'), page); orig = open(page, encoding='utf-8').read()
        r = py(os.path.join(HERE, 'set_repo.py'), 'someone/my-repo', '--branch', 'dev', '--page', page); s = open(page, encoding='utf-8').read()
        check('set_repo.py rewrites only the REPO/BRANCH line', r.returncode == 0 and "var REPO = 'someone/my-repo', BRANCH = 'dev'" in s and re.sub(r"var REPO = '[^']*', BRANCH = '[^']*'", 'X', s) == re.sub(r"var REPO = '[^']*', BRANCH = '[^']*'", 'X', orig), r.stdout + r.stderr)
        check('set_repo.py refuses a bad repo name', py(os.path.join(HERE, 'set_repo.py'), 'not a repo', '--page', page).returncode != 0)
        # dev_site: build + serve, fetch the page and the data over HTTP
        with socket.socket() as so: so.bind(('127.0.0.1', 0)); port = so.getsockname()[1]
        p = subprocess.Popen([sys.executable, os.path.join(HERE, 'dev_site.py'), '--data', a.data, '--lectures', a.lectures, '--port', str(port)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
        got = {}
        try:
            for _ in range(120):
                try:
                    got['index'] = urllib.request.urlopen(f'http://127.0.0.1:{port}/', timeout=2).read().decode('utf-8')
                    got['packs'] = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{port}/packs/index.json', timeout=2).read().decode('utf-8'))
                    got['lec'] = urllib.request.urlopen(f'http://127.0.0.1:{port}/packs/11/lectures/par5.md', timeout=2).read().decode('utf-8')
                    break
                except Exception: time.sleep(1)
        finally: p.terminate(); p.wait(timeout=10)
        check('dev_site.py builds and serves: page, packs/index.json and a lecture file load over HTTP', 'index' in got and 'packs' in got and len(got.get('packs', {}).get('subjects', [])) >= 20 and len(got.get('lec', '')) > 1000, list(got))
    print('\ntest_tools ' + ('FAILED' if fails else 'OK')); sys.exit(1 if fails else 0)

if __name__ == '__main__': main()

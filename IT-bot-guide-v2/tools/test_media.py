#!/usr/bin/env python3
"""
test_media.py - Part 2B/3 item 4: data/media.json carried by bot_db_tool.py (check-media, build expansion, verify) and
check_bot.py image rules (picture lost = ERROR, sha256 mismatch = ERROR).   python tools/test_media.py --data data   (needs Pillow)
"""
import argparse, hashlib, json, os, shutil, sqlite3, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
PY = sys.executable
def run(*args): return subprocess.run([PY] + [str(x) for x in args], capture_output=True, text=True)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--data', default='data'); a = ap.parse_args(); fails = 0
    from PIL import Image
    def check(n, ok, x=''):
        nonlocal fails; print(('PASS  ' if ok else 'FAIL  ') + n + (('  ' + str(x)[:300]) if x and not ok else '')); fails += (not ok)
    with tempfile.TemporaryDirectory() as td:
        data = os.path.join(td, 'data'); shutil.copytree(a.data, data)
        for d in ('provenance',): shutil.rmtree(os.path.join(data, d), ignore_errors=True)
        out = os.path.join(td, 'out'); os.makedirs(os.path.join(out, 'media'))
        # pictures: two new (by content hash) + one legacy picture the first row already has
        def pic(name, color, size):
            p = os.path.join(out, 'media', name); Image.new('RGB', size, color).save(p, 'JPEG'); return p
        pic('aaaaaaaaaaaa.jpg', 'red', (400, 200)); pic('bbbbbbbbbbbb.jpg', 'blue', (300, 300)); pic('legacy_old.jpg', 'green', (500, 100))
        sha = lambda n: hashlib.sha256(open(os.path.join(out, 'media', n), 'rb').read()).hexdigest()
        # choose rows from subject 2 (year 1): r1 no picture, r2 no picture, r3 has legacy picture
        rows = json.load(open(os.path.join(data, 'questions', 'subject-2.json'), encoding='utf-8'))
        vis = [r for r in rows if r['correct_index'] is not None and not r['excluded'] and not r['image']]
        r1, r2, r3 = vis[0], vis[1], vis[2]; r3['image'] = 'media/legacy_old.jpg'
        json.dump(rows, open(os.path.join(data, 'questions', 'subject-2.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        # OLD db = rows as they are (r3 already has its legacy picture)
        old = os.path.join(out, 'old.db'); r = run(os.path.join(HERE, 'bot_db_tool.py'), 'build', data, old, '--force', '--no-media'); check('build without media', r.returncode == 0, r.stdout + r.stderr)
        media = {'aaaaaaaaaaaa': {'file': 'media/aaaaaaaaaaaa.jpg', 'sha256': sha('aaaaaaaaaaaa.jpg'), 'original_names': ['photo_2.jpg'], 'caption': 'x', 'used_by': [r1['key'], r2['key'], r3['key']]},
                 'bbbbbbbbbbbb': {'file': 'media/bbbbbbbbbbbb.jpg', 'sha256': sha('bbbbbbbbbbbb.jpg'), 'original_names': ['photo_3.jpg'], 'caption': '', 'used_by': [r1['key']]}}
        json.dump(media, open(os.path.join(data, 'media.json'), 'w'), indent=1); json.dump({'abc': [r1['key']]}, open(os.path.join(data, 'aliases.json'), 'w'))
        r = run(os.path.join(HERE, 'bot_db_tool.py'), 'check-media', data, os.path.join(out, 'media')); check('check-media OK', r.returncode == 0 and 'OK' in r.stdout, r.stdout)
        new = os.path.join(out, 'new.db'); r = run(os.path.join(HERE, 'bot_db_tool.py'), 'build', data, new, '--force', '--media-dir', os.path.join(out, 'media')); check('build with media', r.returncode == 0, r.stdout + r.stderr)
        c = sqlite3.connect(new); img = dict(c.execute('SELECT key, image FROM questions WHERE key IN (?,?,?)', (r1['key'], r2['key'], r3['key'])).fetchall()); c.close()
        check('one picture -> that file', img[r2['key']] == 'media/aaaaaaaaaaaa.jpg', img)
        check('two pictures -> one stitched image that exists', img[r1['key']].startswith('media/stitched-') and os.path.exists(os.path.join(out, img[r1['key']])), img)
        check('legacy picture + new picture -> stitched (nothing dropped)', img[r3['key']].startswith('media/stitched-') and img[r3['key']] != img[r1['key']], img)
        st = Image.open(os.path.join(out, img[r3['key']])); check('stitched height = sum of the pictures (width scaled to the widest)', st.width == 500 and st.height == 100 + round(200 * 500 / 400), (st.width, st.height))
        r = run(os.path.join(HERE, 'bot_db_tool.py'), 'verify', old, data); check('verify (round trip) unaffected by media.json', r.returncode == 0, r.stdout + r.stderr)
        # check_bot: no picture lost, hashes ok
        r = run(os.path.join(HERE, 'check_bot.py'), new, '--compare', old, '--media-json', os.path.join(data, 'media.json'), '--strict'); check('check_bot --compare: nothing lost, hashes match, (exit code ignored: the live data has other known ERRORs)', 'had a picture and now have none' not in r.stdout and 'image-hash-mismatch' not in r.stdout and 'COMPARISON' in r.stdout, r.stdout[-600:])
        # a build that drops the legacy picture of r3 must fail
        c = sqlite3.connect(new); c.execute('UPDATE questions SET image=NULL WHERE key=?', (r3['key'],)); c.commit(); c.close()
        r = run(os.path.join(HERE, 'check_bot.py'), new, '--compare', old, '--strict'); check('picture lost -> ERROR printed and exit 1', r.returncode == 1 and 'had a picture and now have none' in r.stdout, r.stdout[-400:])
        # hash mismatch
        open(os.path.join(out, 'media', 'aaaaaaaaaaaa.jpg'), 'ab').write(b'x')
        r = run(os.path.join(HERE, 'bot_db_tool.py'), 'check-media', data, os.path.join(out, 'media')); check('check-media flags a changed file', r.returncode == 1 and 'HASH MISMATCH' in r.stdout, r.stdout)
        r = run(os.path.join(HERE, 'check_bot.py'), new, '--media-json', os.path.join(data, 'media.json'), '--strict'); check('check_bot flags image-hash-mismatch', r.returncode == 1 and 'image-hash-mismatch' in r.stdout, r.stdout[-300:])
        # unknown key
        media['bbbbbbbbbbbb']['used_by'].append('y9:nope'); json.dump(media, open(os.path.join(data, 'media.json'), 'w'))
        r = run(os.path.join(HERE, 'bot_db_tool.py'), 'check-media', data, os.path.join(out, 'media')); check('check-media flags an unknown question key', 'UNKNOWN question key y9:nope' in r.stdout, r.stdout)
    print('\ntest_media ' + ('FAILED' if fails else 'OK')); sys.exit(1 if fails else 0)
if __name__ == '__main__': main()

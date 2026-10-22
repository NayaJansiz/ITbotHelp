#!/usr/bin/env python3
"""
check_pr_paths.py - a STUDENT pull request may only ADD new files under intake/, replies/, sources/, media/, inbox/.
  python tools/check_pr_paths.py --base origin/main [--head HEAD]
Allowed exception: sources/manifest.json may be modified. Deleting or modifying any other existing file is a violation.
"""
import argparse, os, subprocess, sys

ALLOWED_ADD = ('intake/', 'replies/', 'sources/', 'media/', 'inbox/')
ALLOWED_MODIFY = ('sources/manifest.json',)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', required=True)
    ap.add_argument('--head', default='HEAD')
    a = ap.parse_args()

    top = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True)
    if top.returncode:
        sys.exit('git rev-parse failed: ' + top.stderr[-300:])
    repo_root = top.stdout.strip()

    # In ITbotHelp the app is a subfolder; in standalone tests the app is the repo root.
    app_prefix = 'IT-bot-guide-v2/' if os.path.isdir(os.path.join(repo_root, 'IT-bot-guide-v2')) else ''
    r = subprocess.run(
        ['git', 'diff', '--name-status', '--no-renames', f'{a.base}...{a.head}'],
        cwd=repo_root, capture_output=True, text=True
    )
    if r.returncode:
        sys.exit('git diff failed: ' + r.stderr[-300:])

    bad = []
    for ln in r.stdout.splitlines():
        if not ln.strip():
            continue
        fields = ln.split('\t', 1)
        if len(fields) != 2:
            bad.append('unparseable git diff line: ' + ln)
            continue
        st, path = fields
        if app_prefix:
            if not path.startswith(app_prefix):
                bad.append(f'{st}  {path} (outside {app_prefix})')
                continue
            rel = path[len(app_prefix):]
        else:
            rel = path
        if st == 'A' and rel.startswith(ALLOWED_ADD):
            continue
        if st == 'M' and rel in ALLOWED_MODIFY:
            continue
        bad.append(f'{st}  {path}')

    if bad:
        print('This pull request touches files a student PR may not touch (only NEW files under intake/, replies/, sources/, media/, inbox/):')
        print('\n'.join('  ' + item for item in bad))
        sys.exit(1)
    print('OK: only new files under intake/, replies/, sources/, media/, inbox/')

if __name__ == '__main__':
    main()

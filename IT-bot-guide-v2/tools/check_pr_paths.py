#!/usr/bin/env python3
"""
check_pr_paths.py - a STUDENT pull request may only ADD new files under intake/, replies/, sources/, media/, inbox/ (Part 2C item 1; inbox/<subject>/<lecture>.pdf = a new lecture PDF).
  python tools/check_pr_paths.py --base origin/main [--head HEAD]        exit 1 + list when something else is touched
Allowed exceptions: sources/manifest.json may be modified (ingest_pdf.py updates it; two students can still conflict there,
Git then shows it). Deleting or modifying any other existing file, or touching data/, tools/, site/, config/, .github/ -> violation.
Approvers' own pull requests are not checked (the workflow skips authors that are owner/member/collaborator).
"""
import argparse, subprocess, sys
# This repository stores the application under IT-bot-guide-v2/ rather than at repo root.
APP_PREFIX = 'IT-bot-guide-v2/'
ALLOWED_ADD = ('intake/', 'replies/', 'sources/', 'media/', 'inbox/')
ALLOWED_MODIFY = ('sources/manifest.json',)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--base', required=True); ap.add_argument('--head', default='HEAD'); a = ap.parse_args()
    r = subprocess.run(['git', 'diff', '--name-status', '--no-renames', f'{a.base}...{a.head}'], capture_output=True, text=True)
    if r.returncode: sys.exit('git diff failed: ' + r.stderr[-300:])
    bad = []
    for ln in r.stdout.strip().split('\\n'):
        if not ln.strip(): continue
        st, path = ln.split('\\t', 1)
        if not path.startswith(APP_PREFIX):
            bad.append(f'{st}  {path} (outside {APP_PREFIX})'); continue
        rel = path[len(APP_PREFIX):]
        if st == 'A' and rel.startswith(ALLOWED_ADD): continue
        if st == 'M' and rel in ALLOWED_MODIFY: continue
        bad.append(f'{st}  {path}')
    if bad:
        print('This pull request touches files a student PR may not touch (only NEW files under intake/, replies/, sources/, media/, inbox/):')
        print('\n'.join('  ' + b for b in bad)); sys.exit(1)
    print('OK: only new files under intake/, replies/, sources/, media/, inbox/')
if __name__ == '__main__': main()

#!/usr/bin/env python3
"""
set_repo.py - point site/index.html at YOUR GitHub repo (fork / upload / pull-request / picture links).
  python tools/set_repo.py <owner>/<repo> [--branch main]
Edits only the line  var REPO = '...', BRANCH = '...'  in site/index.html. Run it once after you create the repo.
"""
import argparse, os, re, sys
ap = argparse.ArgumentParser(); ap.add_argument('repo', help='owner/name'); ap.add_argument('--branch', default='main'); ap.add_argument('--page', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'site', 'index.html')); a = ap.parse_args()
if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]{1,100}', a.repo): sys.exit('repo must look like owner/name')
s = open(a.page, encoding='utf-8').read()
new, n = re.subn(r"var REPO = '[^']*', BRANCH = '[^']*'", f"var REPO = '{a.repo}', BRANCH = '{a.branch}'", s, count=1)
if n != 1: sys.exit('could not find the "var REPO = ..., BRANCH = ..." line in ' + a.page)
open(a.page, 'w', encoding='utf-8', newline='\n').write(new); print(f'site/index.html now uses {a.repo} ({a.branch})')

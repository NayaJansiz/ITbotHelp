#!/usr/bin/env python3
"""
dev_site.py - build the page data and serve it on your machine so you can click through it.
  python tools/dev_site.py --lectures ../lecture-site-engine [--port 8000] [--no-build]
Then open http://localhost:8000 . (Opening site/index.html by double click does NOT work: the page loads its data with fetch().)
Without --lectures only the PDF lectures in sources/ and the INFERRED subjects appear.
"""
import argparse, functools, http.server, os, subprocess, sys, webbrowser
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
ap = argparse.ArgumentParser(); ap.add_argument('--lectures'); ap.add_argument('--data', default='data'); ap.add_argument('--port', type=int, default=8000)
ap.add_argument('--no-build', action='store_true'); ap.add_argument('--open', action='store_true'); a = ap.parse_args()
os.chdir(ROOT)
if not a.no_build:
    cmd = [sys.executable, os.path.join(HERE, 'build_site.py'), '--data', a.data] + (['--lectures', a.lectures] if a.lectures else []) + (['--intake', 'intake'] if os.path.isdir('intake') else [])
    if subprocess.run(cmd).returncode: sys.exit('build_site.py failed')
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=os.path.join(ROOT, 'site'))
with http.server.ThreadingHTTPServer(('127.0.0.1', a.port), handler) as srv:
    url = f'http://localhost:{a.port}/'; print(f'\nServing site/ at {url}   (Ctrl+C to stop)')
    if a.open: webbrowser.open(url)
    try: srv.serve_forever()
    except KeyboardInterrupt: print('\nstopped')

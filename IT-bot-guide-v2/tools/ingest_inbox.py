#!/usr/bin/env python3
"""
ingest_inbox.py - turn the lecture PDFs students added under inbox/<subject id>/ into sources/ (what the ingest-pdf Action runs after a merge).

  python tools/ingest_inbox.py --data data --inbox inbox --sources sources --config config [--keep-pdf] [--report report.md]

For every inbox/<id>/<name>.pdf:  tools/ingest_pdf.py (text + figure pages -> sources/<id>/<slug>.md, figs/, manifest.json), then the slug is
added to config/sources.json under that subject, then the PDF is deleted (--keep-pdf keeps it). The SUBJECT is the folder name the student chose
and the maintainer approved by merging: it is never guessed. A failing PDF stays in inbox/ and the exit code is 1.
Needs PyMuPDF (pip install pymupdf). Same PDF again = UNCHANGED (nothing happens).
"""
import argparse, json, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8'); sys.stderr.reconfigure(encoding='utf-8')

def slugify(s):      # same rule as ingest_pdf.py (not imported: that module needs PyMuPDF at import time)
    s = re.sub(r'[^\w]+', '-', s.strip().lower(), flags=re.U).strip('-')
    return s or 'lecture'

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--data', default='data'); ap.add_argument('--inbox', default='inbox'); ap.add_argument('--sources', default='sources')
    ap.add_argument('--config', default='config'); ap.add_argument('--keep-pdf', action='store_true'); ap.add_argument('--report'); a = ap.parse_args()
    subs = {str(s['id']) for s in json.load(open(os.path.join(a.data, 'subjects.json'), encoding='utf-8'))}
    cpath = os.path.join(a.config, 'sources.json')
    extra = json.load(open(cpath, encoding='utf-8')) if os.path.exists(cpath) else {}
    lines, errors, done = [], [], 0
    for sid in sorted(os.listdir(a.inbox)) if os.path.isdir(a.inbox) else []:
        d = os.path.join(a.inbox, sid)
        if not os.path.isdir(d): continue
        pdfs = sorted(f for f in os.listdir(d) if f.lower().endswith('.pdf'))
        if pdfs and sid not in subs: errors.append(f'inbox/{sid}/: unknown subject id {sid} (see data/subjects.json); files left in place'); continue
        for fn in pdfs:
            name = os.path.splitext(fn)[0]; rel = f'inbox/{sid}/{fn}'
            r = subprocess.run([sys.executable, os.path.join(HERE, 'ingest_pdf.py'), os.path.join(d, fn), '--subject', sid, '--name', name, '--out', a.sources], capture_output=True, text=True, encoding='utf-8')
            if r.returncode != 0: errors.append(f'{rel}: ingest failed: {(r.stdout + r.stderr)[-400:]}'); continue
            slug = slugify(name); lst = extra.setdefault(sid, [])
            if slug not in lst: lst.append(slug); lst.sort()
            lines.append(f'- `{rel}` -> `sources/{sid}/{slug}.md`\n' + ''.join('    ' + l + '\n' for l in r.stdout.strip().split('\n')))
            if not a.keep_pdf: os.remove(os.path.join(d, fn))
            done += 1
    if done:
        os.makedirs(a.config, exist_ok=True)
        json.dump(extra, open(cpath, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1, sort_keys=True); open(cpath, 'a', newline='\n').write('\n')
    out = f'# Inbox ingest\n\n- PDFs ingested: {done} | errors: {len(errors)}\n\n' + ('## ERRORS\n' + ''.join(f'- {e}\n' for e in errors) + '\n' if errors else '') + ('## Ingested\n' + ''.join(lines) if lines else 'nothing in inbox/\n')
    print(out)
    if a.report: open(a.report, 'w', encoding='utf-8').write(out)
    sys.exit(1 if errors else 0)

if __name__ == '__main__': main()

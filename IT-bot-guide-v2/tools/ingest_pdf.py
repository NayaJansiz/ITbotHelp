#!/usr/bin/env python3
"""Part 2A: convert a lecture PDF to text ONCE (0 tokens). Needs PyMuPDF (pip install pymupdf).
  python tools/ingest_pdf.py lecture.pdf --subject 9 --name "WP lecture 3" [--out sources]
Output: sources/<subject>/<slug>.md  (page markers <!-- pN -->, figure markers <!-- fig: figs/... -->)
        sources/<subject>/figs/<slug>-pN.jpg  (only FIGURE pages, ~110 dpi)
        sources/<subject>/<slug>.pages.json   (per-page status: text | fig | needs-OCR)
        sources/manifest.json                 (sha256, pages, chars, per-page sha256, date, version)
Same sha256 -> nothing happens. Different sha256 -> changed pages are listed, file rewritten."""
import argparse, datetime, hashlib, json, os, re, sys
try:
    import pymupdf as fitz
except ImportError:
    try: import fitz
    except ImportError: sys.exit('PyMuPDF missing: pip install pymupdf')

FIG_AREA, FIG_MAXCHARS, OCR_MAXCHARS, DPI = 0.25, 200, 20, 110

def sha(b): return hashlib.sha256(b).hexdigest()
def slugify(s):
    s = re.sub(r'[^\w]+', '-', s.strip().lower(), flags=re.U).strip('-')
    return s or 'lecture'

def clean(t):
    out = []
    for ln in t.replace('\r', '').split('\n'):
        ln = ln.rstrip()
        if not ln.strip() or re.fullmatch(r'\s*\d{1,3}\s*', ln): continue   # blank / bare page number ONLY
        out.append(ln)
    return '\n'.join(out)

def biggest_image_fraction(page):
    area = page.rect.width * page.rect.height; best = 0.0
    for info in page.get_image_info():
        r = fitz.Rect(info['bbox']) & page.rect
        if not r.is_empty: best = max(best, r.width * r.height / area)
    return best

def classify(text, frac):
    n = len(re.sub(r'\s', '', text))
    if n < OCR_MAXCHARS and frac > 0: return 'needs-OCR'
    if frac >= FIG_AREA and n < FIG_MAXCHARS: return 'fig'
    return 'text'

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('pdf'); ap.add_argument('--subject', required=True)
    ap.add_argument('--name', required=True); ap.add_argument('--out', default='sources')
    ap.add_argument('--force', action='store_true'); a = ap.parse_args()
    raw = open(a.pdf, 'rb').read(); h = sha(raw); slug = slugify(a.name)
    sdir = os.path.join(a.out, str(a.subject)); os.makedirs(os.path.join(sdir, 'figs'), exist_ok=True)
    mpath = os.path.join(a.out, 'manifest.json')
    man = json.load(open(mpath, encoding='utf-8')) if os.path.exists(mpath) else {}
    key = f'{a.subject}/{slug}'; old = man.get(key)
    if old and old['sha256'] == h and not a.force:
        print(f'UNCHANGED: same PDF already ingested as {key} (v{old["version"]}). Nothing done.'); return
    doc = fitz.open(a.pdf); parts, pstat, phash, chars = [], {}, [], 0
    for i, page in enumerate(doc, 1):
        text = clean(page.get_text()); st = classify(text, biggest_image_fraction(page))
        pstat[i] = st; phash.append(sha(text.encode())); chars += len(text)
        parts.append(f'<!-- p{i} -->')
        if st != 'text':
            fp = f'figs/{slug}-p{i}.jpg'
            page.get_pixmap(dpi=DPI).save(os.path.join(sdir, fp), jpg_quality=75)
            parts.append(f'<!-- {"fig" if st == "fig" else "needs-OCR"}: {fp} -->')
        if text: parts.append(text)
    open(os.path.join(sdir, slug + '.md'), 'w', encoding='utf-8').write('\n'.join(parts) + '\n')
    json.dump(pstat, open(os.path.join(sdir, slug + '.pages.json'), 'w'), indent=1)
    changed = ([i + 1 for i, x in enumerate(phash) if i >= len(old['page_sha256']) or x != old['page_sha256'][i]]
               if old else [])
    man[key] = {'sha256': h, 'pages': len(doc), 'chars': chars, 'page_sha256': phash, 'name': a.name,
                'ingested': datetime.date.today().isoformat(), 'version': (old['version'] + 1) if old else 1}
    json.dump(man, open(mpath, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    figs = [i for i, s in pstat.items() if s == 'fig']; ocr = [i for i, s in pstat.items() if s == 'needs-OCR']
    print(f'OK {key}: {len(doc)} pages, {chars} chars (~{chars // 4} tokens est.)')
    print(f'  FIGURE pages (image kept, answers tagged FIGURE): {figs or "none"}')
    print(f'  needs-OCR pages: {ocr or "none"}')
    if old: print(f'  UPDATE v{old["version"]}->v{man[key]["version"]}: changed pages {changed or "none"}; run reverify.py')
if __name__ == '__main__': main()

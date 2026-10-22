#!/usr/bin/env python3
"""Part 2B: read a Telegram Desktop HTML export (messages.html + photos/) and prepare an intake file.
  python tools/ingest_polls.py <export-folder> --year 1 --subject 2 [--data data] [--media media] [--out intake] [--cap 12]
Identity = fingerprint (normalised question + options, order-independent), never message ids.
Writes ONLY new files (Part 2C): intake/<subject>/<date>-<sha8>.json (its `media` section carries the picture entries) and media/<sha12>.<ext>.
Never touches data/ (data/media.json is only READ, to reuse known pictures; the single-writer Action merges the intake file into it).
`used_by` stays EMPTY here: a picture next to polls is only a PROPOSAL (`proposed_media` on the poll); a binding is created only when a student confirms it in the review screen. Needs: pip install beautifulsoup4"""
import argparse, datetime, hashlib, json, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lecturelib import norm, flatn, strip_num, fp_parts
from bs4 import BeautifulSoup

def strip_opt(o): return re.sub(r'^\s*-\s?', '', o.strip(), count=1)
def sha_file(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()

def parse(folder):
    soup = BeautifulSoup(open(os.path.join(folder, 'messages.html'), encoding='utf-8').read(), 'html.parser')
    items, skipped = [], 0
    for m in soup.select('div.message.default'):                 # service messages (group icon) are ignored
        mid = m.get('id', ''); fw = m.select_one('div.forwarded.body .from_name')
        batch = re.sub(r'\s+', ' ', fw.get_text(' ', strip=True)) if fw else ''
        poll = m.select_one('div.media_poll')
        if poll:
            q = poll.select_one('div.question').get_text(' ', strip=True)
            opts = [strip_opt(x.get_text(' ', strip=True)) for x in poll.select('div.answer')]
            items.append({'t': 'poll', 'msg': mid, 'q': q, 'options': opts, 'batch': batch}); continue
        ph = m.select_one('a.photo_wrap')
        if ph and ph.get('href') and not ph['href'].endswith('_thumb.jpg'):
            cap = m.select_one('div.text')
            items.append({'t': 'photo', 'msg': mid, 'href': ph['href'], 'caption': cap.get_text(' ', strip=True) if cap else ''})
        else: skipped += 1
    return items, skipped

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('folder'); ap.add_argument('--year', type=int, required=True)
    ap.add_argument('--subject', type=int, required=True); ap.add_argument('--data', default='data')
    ap.add_argument('--media', default='media'); ap.add_argument('--out', default='intake')
    ap.add_argument('--cap', type=int, default=12, help='max polls a photo can be proposed to'); a = ap.parse_args()
    subs = {s['id']: s for s in json.load(open(os.path.join(a.data, 'subjects.json'), encoding='utf-8'))}
    if a.subject not in subs or subs[a.subject]['year'] != a.year:
        sys.exit(f'subject {a.subject} is not in year {a.year} ({subs.get(a.subject)})')
    existing = json.load(open(os.path.join(a.data, 'questions', f'subject-{a.subject}.json'), encoding='utf-8'))
    by_fp, by_opts, by_q = {}, {}, {}
    for r in existing:
        fq, fo, h = fp_parts(r['question'], r['options']); by_fp[h] = r
        by_opts.setdefault(fo, []).append(r); by_q.setdefault(fq, []).append(r)
    items, skipped = parse(a.folder)
    mpath = os.path.join(a.data, 'media.json')
    mj = json.load(open(mpath, encoding='utf-8')) if os.path.exists(mpath) else {}
    os.makedirs(a.media, exist_ok=True)
    photos = {}                                                     # msg -> media id (stored once, by content)
    for it in items:
        if it['t'] != 'photo': continue
        src = os.path.join(a.folder, it['href']); h = sha_file(src); mid = h[:12]
        ext = os.path.splitext(src)[1].lower(); dst = os.path.join(a.media, mid + ext)
        if not os.path.exists(dst): shutil.copy2(src, dst)
        e = mj.setdefault(mid, {'file': f'media/{mid}{ext}', 'sha256': h, 'original_names': [], 'caption': it['caption'], 'used_by': []})
        nm = os.path.basename(it['href'])
        if nm not in e['original_names']: e['original_names'].append(nm)
        if it['caption'] and not e.get('caption'): e['caption'] = it['caption']
        photos[it['msg']] = mid
    rep = {'unchanged': 0, 'update': 0, 'new': 0, 'ambiguous': 0}; recs, last_photo, run = [], None, 0
    seen_fp = {}
    for it in items:
        if it['t'] == 'photo': last_photo, run = photos[it['msg']], 0; continue
        fq, fo, h = fp_parts(it['q'], it['options'])
        r = by_fp.get(h); how = 'exact'
        if not r and len(by_opts.get(fo, [])) == 1: r, how = by_opts[fo][0], 'text-changed'
        elif not r and len(by_q.get(fq, [])) == 1: r, how = by_q[fq][0], 'options-changed'
        rec = {'fingerprint': h, 'question': strip_num(it['q']), 'options': it['options'], 'batch': it['batch'], 'msg': it['msg']}
        if h in seen_fp: rec['duplicate_of_msg'] = seen_fp[h]; rep['ambiguous'] += 1
        seen_fp.setdefault(h, it['msg'])
        if r:
            rec['key'] = r['key']; rec['match'] = how
            if how == 'exact': rec['action'] = 'unchanged'
            else:
                rec['action'] = 'update'
                old_txt = r['options'][r['correct_index']] if r.get('correct_index') is not None and r['correct_index'] < len(r['options']) else None
                new_i = next((i for i, o in enumerate(it['options']) if old_txt and flatn(o) == flatn(old_txt)), None)
                rec['correct_index'] = new_i                      # re-mapped by option TEXT, not position
                if how == 'options-changed' and new_i is None: rec['hide_for_review'] = True
            if r.get('image'): rec['image_kept'] = r['image']       # existing picture is never replaced
        else:
            rec['key'] = 'f:' + h[:12]; rec['action'] = 'new'
        rep[rec['action']] += 1
        if last_photo and not (r and r.get('image')) and run < a.cap:
            rec['proposed_media'] = last_photo                      # only PROPOSED; student confirms (Part 2D)
        run += 1; recs.append(rec)
    keys_present = {r['key'] for r in recs if 'key' in r}
    absent = [r['key'] for r in existing if r['key'] not in keys_present]
    body = {'subject': a.subject, 'year': a.year, 'date': datetime.date.today().isoformat(), 'polls': recs,
            'media': {k: mj[k] for k in set(photos.values())}}
    blob = json.dumps(body, ensure_ascii=False, sort_keys=True); sh8 = hashlib.sha256(blob.encode()).hexdigest()[:8]
    od = os.path.join(a.out, str(a.subject)); os.makedirs(od, exist_ok=True)
    path = os.path.join(od, f'{body["date"]}-{sh8}.json'); json.dump(body, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'polls {len(recs)} | photos {len(photos)} | non-question messages skipped {skipped}')
    print(f'unchanged {rep["unchanged"]} | update {rep["update"]} | new {rep["new"]} | duplicate-in-export {rep["ambiguous"]}')
    print(f'pictures proposed for {sum(1 for r in recs if r.get("proposed_media"))} polls (need student confirmation), kept existing on {sum(1 for r in recs if r.get("image_kept"))}')
    print(f'hidden for review {sum(1 for r in recs if r.get("hide_for_review"))} | absent from export (not deleted) {len(absent)}')
    print('wrote', path)
    return recs, existing
if __name__ == '__main__': main()

"""Shared helpers for make_packs.py and merge_answers.py (Python 3.8+, no packages)."""
import collections, glob, json, math, os, re

_DIAC = re.compile(r'[\u064B-\u0652\u0640]')
STOP = set('هو هي من في علي الي عن ان لان ثم او لا كل بين عند هذا هذه التي الذي ما كما قد لكن مع '
           'the and for with that this are is of to in a an which what'.split())

def norm(s):
    s = _DIAC.sub('', s.lower()); s = re.sub('[إأآ]', 'ا', s)
    return s.replace('ى', 'ي').replace('ة', 'ه')

def flat(s):
    """skeleton for verbatim-quote matching: letters and digits only (markdown, tables, punctuation,
    diacritics, spacing and line-wrapping are ignored on both sides)"""
    s = re.sub(r'<!--.*?-->', ' ', s, flags=re.S)         # page / figure markers of sources/ files are not lecture text
    return re.sub(r'[^a-z0-9\u0621-\u064A]+', '', norm(re.sub(r'</?[a-zA-Z][^>\n]{0,100}>', ' ', s)))

def words(s):
    out = []
    for w in re.findall(r'[a-z0-9_]{2,}|[\u0621-\u064A]{3,}', norm(s)):
        if w.startswith('ال') and len(w) > 4: w = w[2:]
        if w not in STOP: out.append(w)
    return out

# --- question identity (Part 2B): fingerprint = normalised question (numbering and tatweel removed) + options (order-independent)
def flatn(s): return re.sub(r'[^a-z0-9\u0621-\u064A]+', '', norm(s))          # norm() drops tatweel + diacritics
def strip_num(q): return re.sub(r'^\s*\d+\s*[-_\u0640.)\]:]+\s*', '', q.strip())
def fp_parts(q, opts):
    import hashlib
    fq = flatn(strip_num(q)); fo = sorted(flatn(o) for o in opts)
    return fq, '|'.join(fo), hashlib.sha256((fq + '#' + '|'.join(fo)).encode()).hexdigest()

def load_config(path):
    """config/subjects.json (hand-edited) + config/sources.json (written by tools/ingest_inbox.py: {"<subject>": [slug, ...]}, merged into each subject's "sources")"""
    cfg = {k: v for k, v in json.load(open(path, encoding='utf-8')).items() if not k.startswith('_')}
    extra = os.path.join(os.path.dirname(os.path.abspath(path)), 'sources.json')
    if os.path.exists(extra):
        for sid, slugs in json.load(open(extra, encoding='utf-8')).items():
            if sid.startswith('_'): continue
            c = cfg.setdefault(str(sid), {}); have = list(c.get('sources', []))
            c['sources'] = have + [x for x in slugs if x not in have]
    return cfg

def load_lectures(root, folder):
    out = []
    for p in glob.glob(os.path.join(root, 'subjects', folder, 'lectures', 'par*.md')):
        name = os.path.basename(p); m = re.match(r'par(\d+)', name)
        out.append({'file': name, 'num': int(m.group(1)) if m else 0,
                    'text': open(p, encoding='utf-8', errors='ignore').read().replace('\r', '')})
    out.sort(key=lambda d: (d['num'], d['file']))
    return out

def lecnum(fname):
    """lecture number of a file name: parN.md, or the LAST number in a sources/ slug (wp-lecture-3.md -> 3); 0 if none"""
    m = re.match(r'par(\d+)', fname) or re.search(r'(\d+)(?=\D*$)', os.path.splitext(fname)[0])
    return int(m.group(1)) if m else 0

def marker(cfg, fname):
    n = (cfg.get('marker_map') or {}).get(fname)
    if n is None: n = lecnum(fname) or '?'
    return f'(م{n})'

def load_sources(sources_root, sid, only=None):
    """lecture files made by ingest_pdf.py: sources/<sid>/<slug>.md (same dict shape as load_lectures). `only` = optional list of slugs."""
    out = []
    for p in sorted(glob.glob(os.path.join(sources_root or 'sources', str(sid), '*.md'))):
        name = os.path.basename(p)
        if only and name[:-3] not in only: continue
        out.append({'file': name, 'num': lecnum(name), 'text': open(p, encoding='utf-8', errors='ignore').read().replace('\r', ''),
                    'origin': 'sources', 'dir': os.path.dirname(p)})
    return out

def subject_lectures(cfg, lectures_root, sources_root, sid):
    """all lecture files of a subject: repo folder (config 'folder', needs lectures_root) + ingested PDFs (sources/<sid>/*.md,
    listed in config 'sources': [slugs]). A repo file wins when a name clashes."""
    c = cfg.get(str(sid), {}); out = []
    if c.get('folder') and lectures_root: out = load_lectures(lectures_root, c['folder'])
    have = {l['file'] for l in out}
    if c.get('sources'):      # EXPLICIT per subject: a PDF folder is never attached to a subject by guessing
        out += [l for l in load_sources(sources_root, sid, c['sources']) if l['file'] not in have]
    out.sort(key=lambda d: (d['num'], d['file']))
    return out

def load_subject(data, sid):
    return json.load(open(os.path.join(data, 'questions', f'subject-{sid}.json'), encoding='utf-8'))

def save_subject(data, sid, rows):
    json.dump(rows, open(os.path.join(data, 'questions', f'subject-{sid}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

def qtext(q):
    return q['question'] + ' ' + ' '.join(q['options'] if 'options' in q else [])

class BM25:
    def __init__(self, docs):
        self.tf = [collections.Counter(words(d)) for d in docs]
        self.len = [max(1, sum(c.values())) for c in self.tf]
        self.N = len(docs); self.avg = sum(self.len) / self.N
        self.df = collections.Counter(t for c in self.tf for t in c)
    def rank(self, text):
        q = set(words(text)); sc = []
        for i in range(self.N):
            v = 0
            for t in q:
                f = self.tf[i].get(t, 0)
                if f: v += math.log(1 + (self.N - self.df[t] + .5) / (self.df[t] + .5)) * f * 2.4 / (f + 1.4 * (.25 + .75 * self.len[i] / self.avg))
            sc.append((v, i))
        return [i for v, i in sorted(sc, reverse=True)]

# --- one-run pack (lecture picker): ALL ticked lectures of a subject + ALL its questions, split only if over MAX_CHARS.
# Everything below has a twin in site/index.html (<validate> block); tools/test_oneshot.py checks they agree.
MAX_CHARS = 250000          # one pack never exceeds ~this many characters (UTF-16 units, as JS counts them)
LEC_HEADER_COST = 40        # "\n# LECTURE (<file>)\n\n" + trailing newline, rounded up
PACK_SLACK = 200            # title line, FIGURE IMAGES list, spare

def clen(s):
    """length in UTF-16 code units (what JavaScript's .length counts), so Python and the page plan identically"""
    return len(s.encode('utf-16-le')) // 2

def plan_bins(lectures, overhead, max_chars=MAX_CHARS):
    """Split lectures into the fewest packs (first-fit decreasing). lectures = [{'file','num','chars'}].
    A lecture bigger than the budget gets a pack of its own. Returns [[file, ...], ...]: files of a pack in
    lecture order (num, file); packs ordered by their first lecture."""
    budget = max_chars - overhead
    items = sorted(lectures, key=lambda l: (-(l['chars'] + LEC_HEADER_COST), l['file']))
    bins = []                                   # [used, [lecture, ...]]
    for l in items:
        cost = l['chars'] + LEC_HEADER_COST
        for b in bins:
            if b[0] + cost <= budget: b[0] += cost; b[1].append(l); break
        else: bins.append([cost, [l]])
    out = [sorted(b[1], key=lambda l: (l['num'], l['file'])) for b in bins]
    out.sort(key=lambda b: (b[0]['num'], b[0]['file']))
    return [[l['file'] for l in b] for b in out]

def norm_lec(hint, order):
    """the lecture file a reply line's \"lec\" field names ('par5.md', 'par5', or a path ending in it), or None"""
    if hint is None or hint == '': return None
    h = str(hint).strip().replace('\\', '/').split('/')[-1]
    for c in (h, h + '.md'):
        if c in order: return c
    return None

def lec_order(hint, order):
    """lecture files to try for a quote / figure page: the named one first, then the others in lecture order"""
    h = norm_lec(hint, order)
    return ([h] if h else []) + [f for f in order if f != h]

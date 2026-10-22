#!/usr/bin/env python3
"""
bot_db_tool.py - keep the questions as TEXT (JSON) and build bot.db from them.   (Python 3.8+, no packages)

Why: bot.db is a binary file, so git cannot merge it or show what changed. The JSON files can be reviewed
in a Pull Request, merged, and rolled back. bot.db stays what bot.py reads; it just becomes a build output.

Commands
  export  <bot.db> <data_dir>            write data_dir/schema.sql, subjects.json, questions/subject-<id>.json
  build   <data_dir> <out.db> [--force]   create a new bot.db from the JSON files (same schema, same row ids)
  verify  <bot.db> <data_dir>             rebuild into a temp file and compare every row/column with <bot.db>
                                          (exit 1 if anything differs). Media bindings are NOT expanded here, so the
                                          check stays a pure lossless-round-trip test of the exported rows.
  check-media <data_dir> <media_dir>      data/media.json vs the files: every file exists and matches its sha256, every
                                          used_by key exists, orphan files/ids are listed (exit 1 on missing/mismatch/unknown key)

Pictures (Part 2B): data/media.json = {id: {file, sha256, original_names, caption, used_by:[question keys]}} and
data/aliases.json = {fingerprint: [keys]} are carried as they are (export never touches them). `build` expands the
bindings into the single `image` column the bot reads: one picture -> its file; two or more (or one plus a legacy
picture the row already had) -> ONE stitched image media/stitched-<hash>.jpg written next to the output db
(needs Pillow). A row that had a picture never ends up without one. Use --no-media to skip the expansion.

Notes
 - Rows keep their original `id`, so display order (ORDER BY id) is unchanged.
 - `options` is stored as a real JSON list when the original string is exactly json.dumps(list, ensure_ascii=False);
   otherwise the original string is kept untouched in `options_raw`, so the round trip is always lossless.
 - The result is logically identical to the source, not necessarily byte-identical (SQLite file layout can differ),
   so compare with `verify` or `check_bot.py --compare`, not with md5.
"""
import json, os, re, sqlite3, sys, tempfile

def die(msg):
    sys.exit(msg)

def export(db, out):
    if not os.path.exists(db):
        die(f"File not found: {db}")
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    os.makedirs(os.path.join(out, "questions"), exist_ok=True)
    schema = [r[0] for r in c.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY CASE type WHEN 'table' THEN 0 ELSE 1 END, name")]
    open(os.path.join(out, "schema.sql"), "w", encoding="utf-8").write(";\n\n".join(schema) + ";\n")
    subjects = [dict(r) for r in c.execute("SELECT * FROM subjects ORDER BY id")]
    json.dump(subjects, open(os.path.join(out, "subjects.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n = 0
    for s in subjects:
        rows = []
        for r in c.execute("SELECT * FROM questions WHERE subject_id=? ORDER BY id", (s["id"],)):
            d = dict(r)
            raw = d["options"]
            try:
                lst = json.loads(raw)
                ok = json.dumps(lst, ensure_ascii=False) == raw
            except Exception:
                ok = False
            if ok:
                d["options"] = lst
            else:
                d["options_raw"] = raw
                del d["options"]
            rows.append(d)
        n += len(rows)
        json.dump(rows, open(os.path.join(out, "questions", f"subject-{s['id']}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    orphan = c.execute("SELECT COUNT(*) FROM questions WHERE subject_id NOT IN (SELECT id FROM subjects)").fetchone()[0]
    if orphan:
        die(f"{orphan} questions point to a subject_id that is not in subjects; fix the source db first.")
    print(f"Exported {len(subjects)} subjects and {n} questions to {out}")

def load(data):
    schema = open(os.path.join(data, "schema.sql"), encoding="utf-8").read()
    subjects = json.load(open(os.path.join(data, "subjects.json"), encoding="utf-8"))
    questions = []
    qdir = os.path.join(data, "questions")
    for f in sorted(os.listdir(qdir), key=lambda x: int(x.split("-")[1].split(".")[0])):
        questions += json.load(open(os.path.join(qdir, f), encoding="utf-8"))
    questions.sort(key=lambda d: d["id"])
    return schema, subjects, questions

def load_media(data):
    p = os.path.join(data, "media.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}

def stitch(files, dest):
    """vertically stack pictures (same width, white background) into one jpeg"""
    try:
        from PIL import Image
    except ImportError:
        die("Pillow is needed to stitch 2+ pictures of one question: pip install pillow")
    ims = [Image.open(f).convert("RGB") for f in files]
    w = max(i.width for i in ims)
    ims = [i if i.width == w else i.resize((w, round(i.height * w / i.width))) for i in ims]
    canvas = Image.new("RGB", (w, sum(i.height for i in ims)), "white")
    y = 0
    for i in ims:
        canvas.paste(i, (0, y)); y += i.height
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    canvas.save(dest, "JPEG", quality=88)

def expand_media(questions, media, media_dir, out_dir):
    """sets q['image'] from the media bindings (see module doc); returns the number of rows changed"""
    import hashlib
    by_key = {}
    for mid in sorted(media):
        for k in media[mid].get("used_by", []):
            by_key.setdefault(k, []).append(mid)
    n = 0
    for q in questions:
        ids = by_key.get(q["key"])
        if not ids:
            continue
        files = [media[m]["file"] for m in ids]
        old = q.get("image")
        if old and os.path.basename(old) not in {os.path.basename(f) for f in files}:
            files = [old] + files                       # keep the legacy picture, never drop it
        if len(files) == 1:
            q["image"] = files[0]
        else:
            paths = []
            for f in files:
                p = os.path.join(media_dir, f) if os.path.exists(os.path.join(media_dir, f)) else os.path.join(media_dir, os.path.basename(f))
                if not os.path.exists(p):
                    die(f"{q['key']}: picture file missing for stitching: {f}")
                paths.append(p)
            tag = hashlib.sha256("|".join(os.path.basename(f) for f in files).encode()).hexdigest()[:12]
            name = f"media/stitched-{tag}.jpg"
            stitch(paths, os.path.join(out_dir, name))
            q["image"] = name
        n += 1
    return n

def check_media(data, media_dir):
    import hashlib
    media = load_media(data); bad = 0
    keys = set()
    for f in os.listdir(os.path.join(data, "questions")):
        keys |= {r["key"] for r in json.load(open(os.path.join(data, "questions", f), encoding="utf-8"))}
    for mid, m in sorted(media.items()):
        p = os.path.join(media_dir, os.path.basename(m["file"]))
        if not os.path.exists(p):
            print(f"MISSING file for {mid}: {m['file']}"); bad += 1; continue
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        if m.get("sha256") and h != m["sha256"]:
            print(f"HASH MISMATCH {mid}: {m['file']}"); bad += 1
        for k in m.get("used_by", []):
            if k not in keys:
                print(f"UNKNOWN question key {k} used by {mid}"); bad += 1
        if not m.get("used_by"):
            print(f"note: {mid} is not used by any question (orphan, kept)")
    used = {os.path.basename(m["file"]) for m in media.values()}
    if os.path.isdir(media_dir):
        extra = [f for f in os.listdir(media_dir) if f not in used and re.fullmatch(r"[0-9a-f]{12}\.\w+", f)]
        for f in extra:
            print(f"note: {f} is in the media folder but not in media.json")
    print(f"check-media: {len(media)} ids, {'PROBLEMS: ' + str(bad) if bad else 'OK'}")
    return bad

def build(data, out, force=False, media_dir=None, no_media=False):
    if os.path.exists(out):
        if not force:
            die(f"{out} already exists (use --force to overwrite)")
        os.remove(out)
    schema, subjects, questions = load(data)
    media = {} if no_media else load_media(data)
    if media:
        n = expand_media(questions, media, media_dir or os.path.join(os.path.dirname(os.path.abspath(out)), "media"), os.path.dirname(os.path.abspath(out)))
        print(f"media: {n} question(s) got their picture from data/media.json")
    c = sqlite3.connect(out)
    c.executescript(schema)
    def ins(table, d):
        cols = list(d)
        c.execute(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?'*len(cols))})", [d[k] for k in cols])
    for s in subjects:
        ins("subjects", s)
    for q in questions:
        q = dict(q)
        if "options_raw" in q:
            q["options"] = q.pop("options_raw")
        else:
            q["options"] = json.dumps(q["options"], ensure_ascii=False)
        ins("questions", q)
    c.commit()
    bad = c.execute("PRAGMA integrity_check").fetchone()[0]
    c.close()
    if bad != "ok":
        die(f"integrity_check failed: {bad}")
    print(f"Built {out}: {len(subjects)} subjects, {len(questions)} questions, integrity_check ok")

def dump(path):
    c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = {t: [tuple(r) for r in c.execute(f"SELECT * FROM {t} ORDER BY id")] for t in ("subjects", "questions")}
        cols = {t: [r[1] for r in c.execute(f"PRAGMA table_info({t})")] for t in ("subjects", "questions")}
    finally:
        c.close()  # Windows keeps the file locked otherwise; verify() could not delete its temp copy
    return rows, cols

def verify(db, data):
    with tempfile.TemporaryDirectory() as td:
        tmp = os.path.join(td, "rebuilt.db")
        build(data, tmp, no_media=True)
        a, ca = dump(db)
        b, cb = dump(tmp)
    if ca != cb:
        die(f"Different columns: {ca} vs {cb}")
    ok = True
    for t in ("subjects", "questions"):
        if a[t] != b[t]:
            ok = False
            ids = {r[0] for r in a[t]} ^ {r[0] for r in b[t]}
            diff = [x for x, y in zip(a[t], b[t]) if x != y]
            print(f"DIFFERENT in {t}: rows only on one side={len(ids)}, differing rows={len(diff)}")
    if not ok:
        sys.exit(1)
    print("VERIFY OK: every row and column is identical to the source db.")

if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) >= 3 and a[0] == "export": export(a[1], a[2])
    elif len(a) >= 3 and a[0] == "build":
        md = a[a.index("--media-dir") + 1] if "--media-dir" in a else None
        build(a[1], a[2], "--force" in a, md, "--no-media" in a)
    elif len(a) >= 3 and a[0] == "check-media": sys.exit(1 if check_media(a[1], a[2]) else 0)
    elif len(a) >= 3 and a[0] == "verify": verify(a[1], a[2])
    else: print(__doc__)

#!/usr/bin/env python3
"""
check_bot.py - pre-publish check for IT-bot's bot.db  (no third-party packages, Python 3.8+)

It simulates what bot.py (current main, verified 2026-10-16) does when it sends a question,
and reports what Telegram would reject or what would reach students broken.

Usage:
  python check_bot.py bot.db                          # check only
  python check_bot.py bot.db --snapshot SNAPSHOT.md   # also (re)generate the state snapshot
  python check_bot.py bot.db --compare old_bot.db     # field-by-field comparison of two copies
  python check_bot.py bot.db --strict                 # exit code 1 if any ERROR (for CI / before push)
  python check_bot.py bot.db --fail-on-warnings       # exit code 1 on warnings too

Image files are looked up exactly like bot.py: <folder of bot.db>/<image path>, then
<folder of bot.db>/<basename of image path>.

ERROR   = the student gets a broken/missing question (Telegram rejects the poll, or an image is missing).
WARNING = the question works but is clipped by bot.py or is doubtful (see codes below).
"""
import argparse, collections, datetime, hashlib, json, os, sqlite3, sys

# limits copied from bot.py (clip(..., 100) options, clip(..., 300) title, clip(..., 200) explanation, [:10] options)
OPT_MAX, TITLE_MAX, EXPL_MAX, MAX_OPTS = 100, 300, 200, 10
VISIBLE = "correct_index IS NOT NULL AND excluded = 0"
FILLER = {"-", "لا نتذكر"}  # options that the guide says must be removed

def clip(s, n):  # same behaviour as bot.py clip()
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"

def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def connect(path):
    if not os.path.exists(path):
        sys.exit(f"File not found: {path}")
    c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c

def md5sha(path):
    import hashlib
    return hashlib.sha256(open(path, "rb").read()).hexdigest()

def image_exists(base, image):
    p = os.path.join(base, image)
    return os.path.exists(p) or os.path.exists(os.path.join(base, os.path.basename(image)))

def run_checks(conn, base, media_json=None):
    """returns list of (level, key, code, detail)"""
    issues = []
    rows = conn.execute(
        f"SELECT q.key, q.question, q.options, q.correct_index, q.explanation, q.needs_review, q.image, "
        f"s.year, s.name FROM questions q JOIN subjects s ON s.id=q.subject_id WHERE {VISIBLE.replace('correct_index','q.correct_index').replace('excluded','q.excluded')} "
        f"ORDER BY q.id").fetchall()
    for r in rows:
        k = r["key"]
        def add(level, code, detail=""):
            issues.append((level, k, code, detail))
        try:
            opts = json.loads(r["options"])
            assert isinstance(opts, list)
        except Exception:
            add("ERROR", "options-not-json-list"); continue
        if not (r["question"] or "").strip():
            add("ERROR", "empty-question")
        shown = [clip(str(o), OPT_MAX) for o in opts][:MAX_OPTS]
        if len(opts) < 2:
            add("ERROR", "less-than-2-options", f"{len(opts)} options")
        if len(opts) > MAX_OPTS:
            add("WARNING", "more-than-10-options", f"{len(opts)} options, bot.py keeps the first 10")
        if any(not str(o).strip() for o in opts):
            add("ERROR", "empty-option")
        if len(set(shown)) != len(shown):
            add("ERROR", "duplicate-options", "after clipping to 100 chars, as sent to Telegram")
        ci = r["correct_index"]
        if ci < 0 or ci >= len(shown):
            add("ERROR", "correct_index-out-of-range", f"correct_index={ci}, options sent={len(shown)}")
        if r["explanation"] and "\n" in r["explanation"]:
            add("ERROR", "newline-in-explanation", "guide rule: no line breaks (section 13, item 8)")
        if r["image"] and not image_exists(base, r["image"]):
            add("ERROR", "image-file-missing", r["image"])
        elif r["image"] and media_json:
            bn = os.path.basename(r["image"]); want = media_json.get(bn)
            if want:
                p = os.path.join(base, r["image"]) if os.path.exists(os.path.join(base, r["image"])) else os.path.join(base, bn)
                if md5sha(p) != want:
                    add("ERROR", "image-hash-mismatch", f"{bn} differs from data/media.json")
        for i, o in enumerate(opts):
            if len(str(o)) > OPT_MAX:
                add("WARNING", "option-clipped", f"option {i+1} has {len(str(o))} chars (limit {OPT_MAX})")
            if str(o).strip() in FILLER:
                add("WARNING", "filler-option", f"option {i+1} = {str(o).strip()!r}")
        if len((r["question"] or "").strip()) > TITLE_MAX - 6:
            add("WARNING", "question-may-be-clipped", f"{len((r['question'] or '').strip())} chars (limit {TITLE_MAX} incl. numbering)")
        ex = r["explanation"] or ""
        if not ex.strip():
            add("WARNING", "no-explanation")
        elif len(ex) > EXPL_MAX:
            add("WARNING", "explanation-clipped", f"{len(ex)} chars (limit {EXPL_MAX})")
        elif len(ex) < 40:
            add("WARNING", "explanation-very-short", f"{len(ex)} chars")
        if r["needs_review"]:
            add("WARNING", "needs-review-but-visible")
    return issues

def stats(conn, base):
    q = lambda sql, *a: conn.execute(sql, a).fetchone()[0]
    s = {}
    s["total"] = q("SELECT COUNT(*) FROM questions")
    s["visible"] = q(f"SELECT COUNT(*) FROM questions WHERE {VISIBLE}")
    s["hidden"] = s["total"] - s["visible"]
    s["a_keys"] = q("SELECT COUNT(*) FROM questions WHERE key GLOB 'y[0-9]:a[0-9]*'")
    s["img_total"] = q("SELECT COUNT(*) FROM questions WHERE image IS NOT NULL AND image!=''")
    s["img_visible"] = q(f"SELECT COUNT(*) FROM questions WHERE image IS NOT NULL AND image!='' AND {VISIBLE}")
    s["media_files"] = len(os.listdir(os.path.join(base, "media"))) if os.path.isdir(os.path.join(base, "media")) else 0
    s["by_year"] = [tuple(r) for r in conn.execute(
        f"SELECT s.year, COUNT(*), SUM(q.correct_index IS NOT NULL AND q.excluded=0) FROM questions q JOIN subjects s ON s.id=q.subject_id GROUP BY s.year ORDER BY s.year")]
    s["subjects"] = [tuple(r) for r in conn.execute(
        "SELECT s.id, s.year, s.semester, s.name, s.track, COUNT(q.id), SUM(q.correct_index IS NOT NULL AND q.excluded=0), "
        "SUM(q.correct_index IS NOT NULL AND q.excluded=0 AND q.needs_review=1) "
        "FROM subjects s LEFT JOIN questions q ON q.subject_id=s.id GROUP BY s.id ORDER BY s.year, s.semester, s.id")]
    return s

def print_report(issues, st, path):
    err = [i for i in issues if i[0] == "ERROR"]
    warn = [i for i in issues if i[0] == "WARNING"]
    print(f"File: {path}")
    print(f"Questions: total={st['total']}  visible={st['visible']}  hidden={st['hidden']}")
    print(f"Images: {st['img_total']} questions have an image, {st['media_files']} files in media/")
    print(f"\nERRORS: {len(err)}   WARNINGS: {len(warn)}")
    for lvl, group in (("ERROR", err), ("WARNING", warn)):
        by = collections.defaultdict(list)
        for _, k, code, d in group:
            by[code].append((k, d))
        for code, items in sorted(by.items(), key=lambda x: -len(x[1])):
            print(f"\n[{lvl}] {code}: {len(items)}")
            for k, d in items[:12]:
                print(f"   {k}  {d}")
            if len(items) > 12:
                print(f"   ... and {len(items)-12} more")

def write_snapshot(path, dbpath, st, issues):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    err = collections.Counter(c for l, _, c, _ in issues if l == "ERROR")
    warn = collections.Counter(c for l, _, c, _ in issues if l == "WARNING")
    miss = collections.defaultdict(list)
    for l, k, c, d in issues:
        if c == "image-file-missing":
            miss[d].append(k)
    L = []
    L.append("# لقطة حالة bot.db (مولَّدة تلقائياً)")
    L.append("")
    L.append("> لا تعدّل هذا الملف يدوياً. يُولَّد بالأمر: `python tools/check_bot.py bot.db --snapshot SNAPSHOT.md`")
    L.append("> هذه أرقام لحظية؛ مرجعها الدائم هو bot.db نفسه.")
    L.append("")
    L.append(f"- وقت التوليد: {now}")
    L.append(f"- الملف: `{os.path.basename(dbpath)}` | الحجم: {os.path.getsize(dbpath)} بايت | md5: `{md5(dbpath)}`")
    L.append(f"- الأسئلة: الكلي **{st['total']}** | الظاهر **{st['visible']}** | المخفي **{st['hidden']}**")
    L.append(f"- أسئلة مفاتيحها من نوع `y?:a…` (أنشأتها الإدارة): {st['a_keys']}")
    L.append(f"- أسئلة لها صورة: {st['img_total']} (الظاهر منها {st['img_visible']}) | ملفات في media/: {st['media_files']}")
    L.append("")
    L.append("## حسب السنة")
    L.append("")
    L.append("| السنة | الكلي | الظاهر |")
    L.append("|---|---|---|")
    for y, t, v in st["by_year"]:
        L.append(f"| {y} | {t} | {v} |")
    L.append("")
    L.append("## نتيجة الفحص")
    L.append("")
    L.append(f"- أخطاء (ERROR): **{sum(err.values())}**" + ("" if not err else " — " + "، ".join(f"{c}: {n}" for c, n in err.items())))
    L.append(f"- تحذيرات (WARNING): **{sum(warn.values())}**" + ("" if not warn else " — " + "، ".join(f"{c}: {n}" for c, n in warn.items())))
    if miss:
        L.append("")
        L.append("### ملفات صور ناقصة (يجب رفعها إلى media/ بنفس الاسم بالضبط)")
        L.append("")
        for img, keys in sorted(miss.items()):
            L.append(f"- `{img}` — {len(keys)} سؤالاً: {keys[0]} … {keys[-1]}")
    L.append("")
    L.append("## مواد البوت (من جدول subjects)")
    L.append("")
    L.append("| id | السنة | الفصل | المادة | الاختصاص | الكلي | الظاهر | ظاهر ومعلّم للمراجعة |")
    L.append("|---|---|---|---|---|---|---|---|")
    for sid, y, se, name, tr, t, v, nr in st["subjects"]:
        L.append(f"| {sid} | {y} | {se} | {name} | {tr} | {t} | {v or 0} | {nr or 0} |")
    L.append("")
    open(path, "w", encoding="utf-8").write("\n".join(L))
    print(f"\nSnapshot written: {path}")

def compare(new_path, old_path):
    a, b = connect(old_path), connect(new_path)
    cols = ["subject_id", "question", "options", "correct_index", "explanation", "needs_review", "answer_source", "image", "long_question", "excluded"]
    def load(c):
        return {r["key"]: r for r in c.execute("SELECT * FROM questions")}
    A, B = load(a), load(b)
    for tag, p in (("OLD", old_path), ("NEW", new_path)):
        c = a if tag == "OLD" else b
        st = c.execute(f"SELECT COUNT(*), SUM({VISIBLE}) FROM questions").fetchone()
        print(f"{tag}: {p}  size={os.path.getsize(p)}  md5={md5(p)}  total={st[0]}  visible={st[1]}")
    added = sorted(set(B) - set(A)); removed = sorted(set(A) - set(B))
    print(f"\nKeys added: {len(added)}   removed: {len(removed)}")
    if added: print("  added  :", ", ".join(added[:20]), "..." if len(added) > 20 else "")
    if removed: print("  removed:", ", ".join(removed[:20]), "..." if len(removed) > 20 else "")
    changed = collections.defaultdict(list)
    for k in set(A) & set(B):
        for col in cols:
            if col in A[k].keys() and A[k][col] != B[k][col]:
                changed[col].append(k)
    print("\nChanged fields on common keys:")
    if not changed: print("  (none)")
    for col, ks in sorted(changed.items(), key=lambda x: -len(x[1])):
        print(f"  {col}: {len(ks)}   e.g. {', '.join(sorted(ks)[:6])}")
    if changed.get("correct_index"):
        print("\n  !! correct_index changed on existing questions: review each one before publishing.")
    if changed.get("options"):
        print("  !! options changed on existing questions: allowed only via new_options in a patch.")
    lost = sorted(k for k in set(A) & set(B) if (A[k]["image"] or "") and not (B[k]["image"] or ""))
    if lost:
        print(f"\n  !! ERROR: {len(lost)} question(s) had a picture and now have none: {', '.join(lost[:10])}")
    return lost

def main():
    ap = argparse.ArgumentParser(description="IT-bot pre-publish check")
    ap.add_argument("db")
    ap.add_argument("--snapshot", metavar="FILE")
    ap.add_argument("--compare", metavar="OLD_DB")
    ap.add_argument("--strict", action="store_true", help="exit 1 if any ERROR")
    ap.add_argument("--fail-on-warnings", action="store_true")
    ap.add_argument("--media-json", metavar="FILE", help="data/media.json: check the sha256 of every visible question's picture")
    a = ap.parse_args()
    base = os.path.dirname(os.path.abspath(a.db))
    conn = connect(a.db)
    st = stats(conn, base)
    mj = None
    if a.media_json:
        mj = {os.path.basename(m["file"]): m["sha256"] for m in json.load(open(a.media_json, encoding="utf-8")).values() if m.get("sha256")}
    issues = run_checks(conn, base, mj)
    print_report(issues, st, a.db)
    if a.compare:
        print("\n" + "=" * 60 + "\nCOMPARISON\n" + "=" * 60)
        lost = compare(a.db, a.compare)
        if lost:
            issues.append(("ERROR", lost[0], "picture-lost", f"{len(lost)} question(s) lost their picture"))
    if a.snapshot:
        write_snapshot(a.snapshot, a.db, st, issues)
    n_err = sum(1 for i in issues if i[0] == "ERROR")
    n_warn = sum(1 for i in issues if i[0] == "WARNING")
    if (a.strict and n_err) or (a.fail_on_warnings and (n_err or n_warn)):
        sys.exit(1)

if __name__ == "__main__":
    main()

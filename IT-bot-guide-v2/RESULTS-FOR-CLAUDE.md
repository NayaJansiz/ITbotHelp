# IT-bot — verified results and change proposals (2026-10-21)

Purpose of this file: give a second opinion (e.g. Claude) the **facts as measured**, then the **list of things that could change**, so the owner can decide what to change next. Everything below was run on this machine today; nothing was deployed or pushed.

Repo layout used here:
- Guide/tooling: `C:\Users\nayaj\Desktop\IT-bot-guide-v2\` (source of truth = `data/`, `bot.db` is a build output)
- Live bot clone (read-only): `C:\Users\nayaj\Desktop\IT-bot\` (`bot.py`, `bot.db`, `media/`)
- Lecture text (old local clone, the only one that still has `par*.md`): `C:\Users\nayaj\Desktop\IT-bot-guide-v2(1)\lecture-site-engine\subjects\year-3\digital-communications\lectures\par5.md`

---

## 1. State of the database

| Check | Command | Result |
|---|---|---|
| Data ↔ DB round trip | `bot_db_tool.py verify bot.db.new data` | **VERIFY OK** (every row/column) |
| Pre-publish check | `check_bot.py bot.db.new --strict` | **0 ERROR, 316 WARNING**, exit 0 |
| Diff vs the live DB | `check_bot.py bot.db.new --compare IT-bot\bot.db` | keys added/removed **0**; changed fields = `options` on **3** keys only; no picture lost |
| Self-test | `selftest.py` | 10 PASS |
| Apply/patch test | `test_apply.py` | 16 PASS |
| Sources/PDF test | `test_sources.py` | 13 PASS |
| Student page test | `test_site.py` | OK |
| Media bindings | `bot_db_tool.py check-media data media` | OK (0 bindings in `data/media.json`) |

Artifact: `C:\Users\nayaj\Desktop\IT-bot\bot.db.new`, 487424 bytes, md5 `129128fcb8d9c3fa3c71ba7d2aee32d1`. **Not deployed** (owner decision).

Warnings (316) are pre-existing: 257 questions visible-but-flagged `needs_review`, 58 very short explanations, 1 with no explanation.

Not run: `test_media.py`, `smoke_page.js`, `smoke_pics.js` (Pillow / PyMuPDF / bs4 / jsdom cannot be installed on this machine's msys2 Python). Nothing on GitHub or Render was executed.

## 2. The three data changes (options only)

| Key | Problem | Change | Answer |
|---|---|---|---|
| `y3:p116` (subject 13) | two identical options; Telegram silently skipped the poll | duplicate removed, 4 → 3 options | unchanged (A) |
| `y4:m224` (subject 27) | options 1–3 were 141/139/139 chars, Telegram clips at 100 | 96/94/94, same meaning | unchanged (A) |
| `y4:net12` (subject 31) | option 3 was 121 chars | 95 chars, same meaning | unchanged (B) |

Process note: `check_bot --compare` warns "options changed on existing questions: allowed only via `new_options` in a patch". These three were edited directly in `data/` as maintenance (option text only, answer untouched). Future option edits should go through `new_options`.

## 3. Pilot: real Claude run on pack `par5` (subject 11)

Design: one pack (`pilot/packs/11/par5.md`, 12 questions, 60 KB) built with `--all` so every question already has a stored answer; owner pasted it into a normal claude.ai chat with the standard first message; reply saved to `pilot/replies/11/par5.txt`; merged with `merge_answers.py` (dry run).

| Metric | Value |
|---|---|
| Lines returned / expected | **12 / 12** (correct order and format) |
| `LECTURE` (quote found verbatim in lecture by machine check) | **2** |
| `NOT-FOUND` | **10** |
| Agreement with stored answers | **0** |
| `CONFLICT-EXISTING` (stored answer kept) | **2** |
| Writes to `data/` | **0** |

There was no invented quote: both `q` strings exist verbatim in `par5.md`.

Per-question detail (stored letter = what students see today):

| Key | Question (short) | Stored | Claude | Verdict |
|---|---|---|---|---|
| `y3:p4` | التعديل الافضل هو | D | NOT-FOUND | question is not in par5 |
| `y3:p5` | تعديل PCM | D | NOT-FOUND | not in par5 (PCM only named as a prerequisite) |
| `y3:p6` | الشروط التي حددتها نظرية شانون | C | NOT-FOUND | not in par5 |
| `y3:p8` | في التعديل يتم نقل المعلومات عبر | A | NOT-FOUND | not in par5 |
| `y3:p13` | استخلاص المعلومات من الإشارة المستمرة | A | NOT-FOUND | not in par5 |
| `y3:p16` | انتشار الشعاع الليزري في الليف الضوئي | B | NOT-FOUND | not in par5 |
| `y3:p17` | ليس من مزايا النقل الرقمي | A | NOT-FOUND | not in par5 |
| `y3:p21` | التعديل المطالي يعدل | B | NOT-FOUND | not in par5 |
| `y3:p26` | ترددات المجموعة الكبيرة الأساسية تحسب ب | A (`372-48n`) | D (ليس أي مما سبق) | **real conflict — see §4** |
| `y3:p29` | زمن تخزين العينة في مكثف دارة أخذ العينات | B | NOT-FOUND | not in par5 |
| `y3:p32` | FPM تقسيم التردد على المجال الترددي نفسه… | A (صح) | B (خطأ) | **real conflict — see §4** |
| `y3:p33` | التابع الصناعي المتزامن زمن دورانه | A | NOT-FOUND | not in par5 |

### Why 10 × NOT-FOUND (verified, not Claude's fault)

`par5` is about multiplexing (FDM/TDM/T₁). The ten questions are about sampling, PCM, Shannon, optical fibre, AM, satellites — different lectures. They are in the par5 pack only because routing attaches each question to its **best 3 lectures**:

| Key | Lectures that also contain it |
|---|---|
| `y3:p4` | par3, par4 |
| `y3:p5`, `p13`, `p29` | par2-sec1, par4 |
| `y3:p6` | par2-sec2, par4 |
| `y3:p8` | par3, par6 |
| `y3:p16` | par1, par8 |
| `y3:p17` | par1, par4 |
| `y3:p21` | par3, par4 |
| `y3:p26` | par4, par7 |
| `y3:p32` | par7, par8 |
| `y3:p33` | par1, par6 |

Consequence for the student page: opening the par5 pack shows **12 questions, 10 of which cannot be answered from that lecture**. A student sees "not found in this lecture" ten times. (Answering still works overall, because the same question also appears in another pack.)

To measure real accuracy for these 12, packs `par4` + `par1` + `par3` would cover all ten misses. That run was stopped by the owner ("enough testing").

## 4. The two conflicts, with the exact text

### `y3:p26` — the options contradict the lecture

- Question: **ترددات المجموعة الكبيرة الأساسية تحسب ب**
- Options: `A) 372-48n` `B) 172-48n` `C) 272-48n` `D) كل ما سبق خاطئ`
- Stored: **A**, explanation "…372 - 48n كيلوهرتز", `needs_review = 1`
- Lecture, `par5.md` line 50 (verbatim): `❌ استخدام معادلة FDM الخاصة بالقنوات (112−4n) عوضاً عن معادلة المجموعات (372+48n) أو العكس`
- Claude quoted: `يحدد تردد الموجة الحاملة من العلاقة: Fc = 372 + 48n` (exists verbatim in the lecture) and answered **D**, i.e. "none of the above".

Interpretation: the lecture gives the group formula with a **plus**; every option is written with a **minus**. As printed, no option is the lecture's formula, so D is defensible. Exam intent is clearly `372+48n`.

Possible changes (owner decision):
1. Fix option A to `372+48n` and keep answer A (smallest, keeps the exam's intent). Risk: option text changes for students; still needs `new_options` discipline.
2. Leave as-is and keep the review flag. Risk: students see a wrong option as "correct".
3. Hide the question. Not recommended (loses a valid teaching point).

### `y3:p32` — a garbled true/false sentence

- Question (verbatim): **FPM تقسيم التردد على المجال الترددي نفسه الذي يشكل منابع متعددة الى مجال ترددي نفسه و ترسل في ان واحد على الوسط نفسه**
- Options: `صح` / `خطأ`; stored: **صح**, `needs_review = 1`
- Stored explanation: "تقسيم التردد يوزع المجال الترددي بين عدة منابع تُرسل معاً على الوسط نفسه."
- Lecture, `par5.md` line 133 (verbatim): `يُحوِّل في التنضيد بتقسيم التردد كل مصدر من المجال الترددي نفسه الذي تشغله إلى مجال ترددي مختلف، وترسل جميعها في آنٍ واحد على وسط الاتصال نفسه.`
- Claude answered **B (خطأ)** with that quote.

Interpretation: the question says "**إلى مجال ترددي نفسه**" (to the *same* band), while the lecture says "إلى مجال ترددي **مختلف**" (to a *different* band). The sentence also starts with "**FPM**" instead of FDM. So the sentence as written is false on its key clause, but the second half (same medium, simultaneously) is true. The stored explanation only justifies the second half.

Possible changes (owner decision):
1. Switch the stored answer to **خطأ** (A → B) and rewrite the explanation.
2. Keep **صح** and treat the intended reading as "sources share the same medium at the same time".
3. Fix the question text (remove `FPM`, write "إلى مجال ترددي مختلف") and keep **صح**. Biggest change, but makes the sentence unambiguous and lecture-aligned.

## 5. Student page, tested end-to-end

Local server: `python -m http.server 8765 --directory site` → `http://127.0.0.1:8765/`.

Flow tested with the real par5 reply: pick السنة 3 → اتصالات رقمية → par5 → paste reply → تحقّق.

- Result shown: **✓ موثّق: 2 · ⚠ لم يوجد: 10**, reply file offered as **12 lines** — identical to the Python merge numbers.
- Cards show the question, options, answer selector, explanation box with 200-char counter, and a "conflict with current answer (A), will be reviewed" note on the two answered ones.
- **Bug found and fixed during the test:** packs rebuilt on Windows had CRLF line endings; `extractLecture()` searched for `\n# QUESTIONS\n\n` and failed, so `lectureFlat` became null and **both valid answers were rejected** ("✗ مرفوض: 2"). Fix: normalise `\r\n` in `loadPack()` in `site/index.html`, plus all `site/packs/**` rewritten to LF. `test_site` still OK. This would have hit the first student on a Windows-built page.
- Packs: 89 packs / 27 subjects, rebuilt from current `data/`; content diff vs the previously shipped packs (line endings ignored) = only the 3 fixed questions' files. `site/packs/` is git-ignored and rebuilt on Linux by `pages.yml`, so this is a local artifact only.

## 6. Other facts worth knowing before proposing changes

- Explanation budget mismatch: pack rule 4 tells Claude "max **150** characters"; the bot/validator limit is **200** including the marker `(م#)`. Not a failure (all pilot explanations passed), but two different numbers.
- `bot.db` on Render is still a committed binary; building it from `data/` on Render is not implemented, so merged answers do **not** reach students by themselves. Owner publishes `bot.db` manually.
- A fresh clone of `homs-uni/lecture-site-engine` contains only `lectures/manifest.json` — the `par*.md` files are gone. All builds/tests here used the older local clone. `pages.yml` clones that repo, so the Pages build (packs + `test_site`) would fail or produce empty packs until the lecture files are back.
- `bot.py` does not validate the `key` format; the DB has `key TEXT UNIQUE`, so new keys like `f:<hash12>` are safe at DB level (not verified in a live poll).
- The 2 jsdom browser tests and the media test cannot run on this machine (missing Pillow/PyMuPDF/bs4/jsdom).

## 7. Proposal list (for discussion — not applied)

Priority order, with the reason each exists:

1. **Decide `y3:p26`** (§4). Without it, a visible question keeps an option that contradicts the lecture.
2. **Decide `y3:p32`** (§4). Same class: the sentence and the answer disagree.
3. **Routing: stop putting a question in a pack where it cannot be answered.** Currently best-3. Options: (a) best-1 only; (b) best-3 but drop entries below a similarity floor; (c) keep best-3 and label weak entries in the pack ("may be answered in another lecture") so students are not surprised. Trade-off: fewer packs per question = fewer chances Claude finds it, but far fewer "not found" lines. Needs a measured similarity threshold, not a guess.
4. **Measure accuracy properly**: run `par4` + `par1` + `par3` for subject 11 (covers all 12 questions from the pilot). Without it, "0 agreement" is a 2-question sample.
5. **Unify the explanation limit** (150 in the pack rules vs 200 in the bot/validator).
6. **Deploy** `bot.db.new` (owner only). Otherwise the three fixes never reach students.
7. **Restore or replace the lecture source for the Pages workflow** (`par*.md` missing from the lecture repo). Without it, `pages.yml` cannot build packs.
8. **Subject ↔ lecture-folder mapping** for the 32 subjects still unmapped (owner only; never guessed).
9. **Optional cosmetic**: visible `(شكل)` label on FIGURE answers (owner said "later").

## 8. Questions to answer in the discussion

1. For `y3:p26`, which option is better: fix the option text to `372+48n`, or leave the question and accept "none of the above"? Any third path?
2. For `y3:p32`, is the intended exam meaning "صح" (shares the medium at the same time) or "خطأ" (FDM never puts sources in the same band)? Should the question text itself be repaired?
3. Is dropping a question from a pack where it has no support (routing change #3) worth the loss of a second/third chance to answer it? Which variant (a/b/c)?
4. Is "0 agreement on 2 answered questions" enough evidence to keep going, or should accuracy be measured on the 3 extra packs first?
5. Anything in §2 (the 3 option fixes) that should have gone through `new_options` instead of a direct edit, and needs redoing that way?
6. Any risk in the page's rule "a LECTURE answer that disagrees with the stored answer is kept but flagged" — should a student's verified quote ever be allowed to override a stored answer automatically? (Currently: never.)

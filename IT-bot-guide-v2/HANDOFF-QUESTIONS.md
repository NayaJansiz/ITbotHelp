# Brief for Claude — instructions for the next session (2026-10-21)

Purpose of this file: give Claude everything it needs to write **instructions for the OpenCode agent** on how to continue.
Facts below were verified today on the real files; anything not verified is marked *(unverified)*.

---

## 0. Context to paste to Claude

- **Project folder:** `C:\Users\nayaj\Desktop\IT-bot-guide-v2` (docs + `data/` + `tools/` + `site/` + workflows). Not a git repo.
- **Live bot repo:** `github.com/nadeembrijawy/IT-bot` (public), cloned today at `C:\Users\nayaj\Desktop\IT-bot` (bot.py, bot.db, media/, stats.py). Any commit to it redeploys the student bot on Render.
- **Lecture repo:** `homs-uni/lecture-site-engine`. A fresh clone at `Documents\GitHub\lecture-site-engine` **has no `par*.md`** (each `lectures/` has `manifest.json` only). An older clone with the files is at `Desktop\IT-bot-guide-v2(1)\lecture-site-engine`.
- **Build state:** Parts 1, 2, 2A, 2B, 2C/3, 2D (items 1 and part 2), and item 4 are built and locally tested. Open: Render/live wiring, Part 4 (docs), Part 5 (pilot), Part 6 (subject↔folder mappings).
- **Runtime here:** Windows, msys2 Python 3.12 (ucrt64), Node 24. No Pillow / PyMuPDF / bs4 (they cannot be installed: PyPI wheels don't match this Python; `pacman` conflicts with an existing pip `packaging`).

## 1. Verified today

| Check | Result |
|---|---|
| `check_bot.py --strict` on a db built from `data/` | **0 ERROR, 316 WARNING** (was 1 / 320) |
| `check_bot.py --compare` vs live `bot.db` | keys added/removed **0**; changed fields = `options` on exactly `y3:p116`, `y4:m224`, `y4:net12`; no picture lost |
| `bot_db_tool.py verify` | VERIFY OK |
| `selftest.py` | 10 PASS |
| `test_site.py` | OK |
| `test_sources.py` | 13 PASS |
| `test_apply.py` | 17 PASS |
| `test_media.py`, `smoke_page.js`, `smoke_pics.js` | **not run** (missing Pillow / jsdom) |

Artifact ready but not deployed: `Desktop\IT-bot\bot.db.new` — 487,424 bytes, md5 `129128fcb8d9c3fa3c71ba7d2aee32d1`.

## 2. Facts I established myself (no need to ask)

1. **`bot.py` does not validate question keys.** `data/schema.sql` has `key TEXT UNIQUE`; `stats.py` stores `question_key TEXT`. So new-style `f:<hash12>` keys look safe — *(unverified in a live poll)*.
2. **The 3 data fixes change no key, no image, no answer** — options text only.
3. **`data/` still matches the live `bot.db`** except those 3 rows, so the export is current.
4. **The Windows crashes in `verify` / `test_apply` / `test_media` were sqlite connections left open**, now fixed; nothing else changed.

## 3. Decisions only the owner can make

Answer format used below: **why it matters → options → my recommendation**.

**Q1 — Where does lecture text live now?** *(blocks Part 5, Part 6, and rebuilding packs)*
The public lecture repo no longer ships `par*.md`; the whole workflow needs that text to build packs and to verify quotes.
Options: (a) restore the files in the repo; (b) keep them private and ingest PDFs with `ingest_pdf.py` into `sources/`; (c) use the older local clone as the master copy.
→ **Recommend (b)** if the files were removed on purpose: PDFs are the real source, and `sources/` already works.

**Q2 — Who owns Render, and can the build command change?** *(blocks every answer reaching students)*
Today `bot.db` is a committed binary written by the admin bot; `data/` changes never reach the bot.
Options: (a) change Render's build to `python tools/bot_db_tool.py build data bot.db --force --media-dir media` (then stop committing `bot.db`); (b) keep committing `bot.db` and have the Actions workflow commit the rebuilt binary.
→ **Recommend (a)**; (b) is the fallback if Render access is unavailable.

**Q3 — Do we deploy today's 3 fixes now?**
Options: (a) push `bot.db.new` as `bot.db` (redeploys the bot, fixes a broken question immediately); (b) wait until the Render build from `data/` exists.
→ **Recommend (a)** — small, verified, reversible.

**Q4 — Is `sources/9/wp-lecture-3` really subject 9 (برمجة الويب)?** One yes/no; without it, that PDF is not attached to any subject (`config/subjects.json`).
→ Needs your confirmation only; I will not guess.

**Q5 — Folder mapping for the remaining subjects (Part 6).** Only 8 subjects are confirmed. For each of the others I need: subject id → folder name in `subjects/year-N/...`, or "no lectures". Years 1, 4 and 5 are entirely unconfirmed.
→ Give me whatever part you know; the rest stays INFERRED.

**Q6 — The pilot (Part 5).** Real accuracy is still untested, and there is no API key, so the Claude chat must be run by a human.
Options: (a) you run one pack (I prepare it, subject 11 `par5`), paste the reply back, I merge and compare; (b) skip the pilot.
→ **Recommend (a)** — it is the only honest accuracy number we would have.

**Q7 — GitHub settings I cannot check from here:** is Pages set to "GitHub Actions"? are Actions permissions "Read and write"? branch protection on `main`? PR comments for fork PRs (`pull_request_target`)?
→ Tell me the current state; I will not assume.

**Q8 — Should FIGURE answers show a visible label to students?** Today they are visible with `needs_review=1` and no label in the explanation.
→ **Recommend a short label** such as `(شكل)` so the student knows the answer came from a diagram.

**Q9 — OCR for image-only PDF pages:** not needed for the one sample (2 of 48 pages). Decide after the next PDF.

**Q10 — Handwritten/circuit questions** (e.g. the Thevenin photos): the machine can never verify them. Confirm that "student review + owner approval" is the accepted check for these.

**Q11 — May I install the missing Python deps on this machine?** Options: MSYS2 packages via `pacman -S --overwrite ...` (works but overwrites a pip-installed `packaging`), or leave them out and keep skipping `test_media` + the jsdom smokes.
→ **Recommend leaving them out** unless you want those two tests run here.

**Q12 — Working copy:** should the guide folder become its own git repo (safe history, diffs for you to review), or stay a plain folder?

## 4. Files / inputs I still need

| # | Input | Needed for |
|---|---|---|
| I1 | A **second real lecture PDF**, and an updated version of the same PDF | `ingest_pdf.py` thresholds (figure pages, `minwords=2`) and the PDF-update path — both untested |
| I2 | A **Telegram export (HTML + photos)** for a subject that *has* lectures (the existing sample is subject 2, which has none) | end-to-end picture binding on a real pack |
| I3 | Screenshot (no secrets) of the Render service: build command, auto-deploy, path filter | Q2, and whether a `data/` commit triggers a deploy |
| I4 | The answers to Q1–Q12 | everything below |

## 5. What I can start with no new input (proposed order)

1. **Deploy package for the 3 fixes** — exact commands, before/after hashes, and the post-push check list for you. *(needs Q3)*
2. **Pilot kit (Q6)** — build the `par5` pack, write the exact 3-step script for your Claude chat, plus how to send the reply back. *(needs Q1 + Q6)*
3. **Part 4 remainder** — regenerate `SNAPSHOT.md` after deploy, update `04-STATE-AND-OPEN-ISSUES.md`, add the "new flow" line to `00-INDEX.md`. *(no blockers)*
4. **Rebuild `site/packs/`** from the fixed `data/` and re-run `test_site`. *(needs Q1)*
5. **Part 6 config** — fill `config/subjects.json` only with mappings you confirm. *(needs Q5)*
6. **CI hardening** — make the PR workflow run `selftest`/`test_sources`/`test_apply` on Linux so Windows-only bugs stay out of the way. *(no blockers; untested on GitHub by definition)*

## 6. What Claude's instructions should contain

Ask Claude to return, for each task: the exact files it may change, the acceptance check (a command and its expected output), the stop condition, and what must **not** be touched. Order matters: 1 and 3 first, then 4, then 2, 5, 6.

## 7. Rules I already follow (no need to restate)

See `AGENTS.md` in the project root: no tokens, no `git push`, no Render changes, `data/` only through the tools, never overwrite a verified answer, never invent a quote, explanations ≤ 200 chars including `(م#)`, never delete a question or a picture, Arabic for students, answer the owner in her language.

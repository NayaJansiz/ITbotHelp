# OWNER-DECISIONS.md — answers that gate the agent's tasks

Fill the **Answer** column (or write "your call" where the agent may decide). Leave it empty to keep the task blocked.
Last updated: 2026-10-21

## Gating questions

| Id | Question | Gates | Answer (owner) |
|---|---|---|---|
| Q3 | Deploy `bot.db.new` as `bot.db` in the live repo now? | T1 | **Not now** (2026-10-21): keep working, leave the file undeployed. Still open for later. |
| Q1 | Where does the lecture text live now: restore `par*.md` in `homs-uni/lecture-site-engine`, ingest PDFs into `sources/`, or use the older local clone? | T4, T2 | **Use the older local clone for now** (agent, 2026-10-21). Long-term source still undecided — only matters for the GitHub workflow. |
| Q6 | Run the pilot on pack `par5` (subject 11)? | T2 | **Done** (2026-10-21): one pack only, result in `pilot/RESULT-par5.md`. Owner stopped further testing ("enough testing"). |
| Q4 | Is `sources/9/wp-lecture-3` really subject 9 (برمجة الويب)? | T5 | |
| Q5 | Subject id → lecture folder mapping for the subjects still unconfirmed | T5 | |
| Q8 | Add a visible `(شكل)` label to FIGURE answers (data change to explanations)? | any explanation change | |

## From the par5 pilot (2026-10-21) — two exam answers that a real lecture quote contradicts

| Id | Question | Effect if you say yes | Answer (owner) |
|---|---|---|---|
| Q13 | `y3:p26` — the lecture says `Fc = 372 + 48n` (plus) but every option is written with minus. Change option A to `372+48n` and keep answer A? | one option's text changes; the stored answer stays A; the question stops contradicting the lecture | |
| Q14 | `y3:p32` — "FDM puts several sources in the same band" — we store صح, Claude said خطأ with a real quote (FDM gives each source a different band). Keep صح or switch to خطأ? | the student-facing answer changes (A ↔ B), or it stays and is flagged | |

If both stay empty, nothing changes: the questions remain as students see them today.

## Recorded only (not agent tasks)

| Id | Question | Status |
|---|---|---|
| Q2 | Who owns Render and can its build command become `python tools/bot_db_tool.py build data bot.db --force --media-dir media`? | open |
| Q7 | GitHub settings: Pages source = "GitHub Actions"? Actions permissions "Read and write"? branch protection on `main`? PR comments for fork PRs? | open |
| Q9 | OCR for image-only PDF pages | deferred (only 2 of 48 pages in the one sample) |
| Q10 | Accept "student review + owner approval" as the only check for handwritten/circuit questions? | open |
| Q11 | May the agent install Pillow / PyMuPDF / bs4 (MSYS2 `pacman`, overwrites a pip `packaging`) so `test_media` and the jsdom smokes can run here? | open |
| Q12 | Should the guide folder become its own git repo? | open |

## Q5 detail — what is needed per subject

Fill only what you know; anything blank stays INFERRED (no guessing). Folder names are the ones under `subjects/year-N/<folder>/` in the lecture repo.

| Subject id | Subject name | Year | Folder (or "none") |
|---|---|---|---|
| 1 | برمجة 1 | 1 | |
| 2 | دارات 1 | 1 | |
| 3 | رياضيات 2 | 1 | |
| 4 | دارات 2 | 1 | |
| 5 | برمجة 2 | 1 | |
| 6 | مبادئ 2 | 1 | |
| 7 | انكليزي 2 | 1 | |
| 8 | خوارزميات 1 | 2 | |
| 9 | برمجة الويب | 2 | (Q4) |
| 10 | احتمالات و احصاء | 2 | |
| 17 | بنيان 2 | 3 | |
| 18 | هندسة البرمجيات 1 | 3 | |
| 19 | اتومات | 3 | |
| 11 | اتصالات رقمية | 3 | digital-communications (confirmed) |
| 12 | بحوث العمليات 2 | 3 | operations-research-2 (confirmed) |
| 13 | لغة انكليزي تخصصية 1 | 3 | (confirmed, see config) |
| 14 | برمجة متقدمة 2 | 3 | advanced-programming-2 (confirmed) |
| 15 | ذكاء صنعي | 3 | 2-ai-theory (confirmed) |
| 16 | مترجمات | 3 | 1-compiler-principles (confirmed) |
| 20 | نمذجة و محاكاة | 4 | |
| 21 | نظم وسائط متعددة | 4 | |
| 22 | رسم و حاسب | 4 | |
| 23 | قواعد معطيات 2 | 4 | |
| 24 | نظم معلومات | 4 | |
| 25 | لغات برمجة | 4 | |
| 26 | منطق عائم | 4 | |
| 27 | برمجة منطقية | 4 | |
| 28 | برمجية تفرعية | 4 | |
| 29 | لغة انكليزي تخصصية 2 | 4 | |
| 30 | نظم تشغيل 2 | 4 | |
| 31 | تحليل و تصميم | 4 | |
| 32 | تجارة و تسويق | 5 | |
| 33 | نظم الزمن | 5 | |
| 40 | لغة انكليزي تخصصية 3 | 5 | |
| 34 | هندسة نظم المعلومات | 5 | |
| 35 | امن الشبكات | 5 | |
| 36 | امن المعلومات | 5 | |
| 37 | ادارة المشاريع | 5 | |
| 38 | نظم و تطبيقات موزعة | 5 | |
| 39 | قواعد معطيات معرفية | 5 | |

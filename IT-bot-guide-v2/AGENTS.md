# AGENTS.md — IT-bot-guide-v2

Put this file in the project root (next to `00-INDEX.md`). OpenCode reads it at the start of every session.

## What this project is
Workflow and tooling for the IT-bot exam question bank (Telegram quiz polls, Information Engineering, Homs University). Students' questions are answered **from the lectures**, with machine-checked quotes, and merged into text files that build `bot.db`.

- `data/` = source of truth (JSON per subject). `bot.db` is a build output.
- `tools/` = Python scripts (the older ones use no packages; `ingest_pdf.py` uses PyMuPDF).
- `sources/` = lecture text converted from PDFs. `site/` = student page. `.github/workflows/` = automation.
- `../lecture-site-engine` = separate Node project (lecture sources). Do not edit it unless asked.

## Read first (in this order)
1. `00-INDEX.md` (map of the files)
2. `HANDOFF-BUILD.md` (what is built, what is only designed, decisions already made by the owner)
3. `02-AI-INSTRUCTIONS.md` (hard rules and answer-quality rules, in Arabic)
4. `04-STATE-AND-OPEN-ISSUES.md` (known problems)

The docs and the code can disagree. If they do, **the code and the data are right**. Tell the owner about the difference.

## Hard rules
- Never ask for, print, or write any token or secret (BOT_TOKEN, GITHUB_TOKEN, Cloudflare/wrangler files). They live only in Render/GitHub secrets.
- Never run `git push`, `git push --force`, or change anything on Render. Prepare changes and commits; the owner pushes.
- Any commit on the live bot repo redeploys the bot for students. Do not touch the live repo.
- Do not edit `bot.db` by hand. Change `data/` through the tools, then rebuild and verify.
- Never invent lecture quotes or sources. If the lecture does not cover a question, mark it NOT-FOUND / INFERRED, as `HANDOFF-BUILD.md` describes.
- Never overwrite an existing verified answer. Report it as a conflict.
- Explanations are at most 200 characters, including the lecture marker `(م#)`.
- Do not delete questions or pictures. A question that had a picture must still have one.
- Student-facing text stays simple and in Arabic. Reply to the owner in the language she writes in.

## Commands
```
python tools/check_bot.py bot.db --strict                 # pre-publish check (must have 0 ERROR)
python tools/bot_db_tool.py verify bot.db data            # JSON matches bot.db exactly
python tools/selftest.py --data data --lectures ../lecture-site-engine
python tools/make_packs.py --data data --status           # coverage per subject
python tools/run_all.py --lectures ../lecture-site-engine --node-modules .   # EVERY test, raw output (run before saying anything works)
python tools/dev_site.py --lectures ../lecture-site-engine                  # build + serve the page on localhost:8000
```
The `tools/test_*.py` scripts are the other tests. Read each script's top comment for how to run it before running it.

## How to work
1. Plan first. For any task, list the files you will touch and the checks you will run. Wait for approval on anything that changes `data/`.
2. One small task at a time. Do not refactor across many files in one go.
3. After each change run the relevant tests and the checks above, and paste the real output. Do not say "done" without it.
4. If a command fails twice, stop and report the exact error. Do not keep guessing.
5. Finish each task with: files changed, commands run with results, anything unverified.

## Not tested yet (do not claim these work)
GitHub Actions on GitHub itself, any Render change, real accuracy of Claude's answers with the packs.

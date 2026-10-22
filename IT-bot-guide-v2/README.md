# IT-bot — question bank pipeline (v2.1)

Students answer the exam questions **from the lectures**, with Claude, and an answer is accepted only if its **quote exists word for word** in the lecture text. Everything is checked by scripts (no tokens, no secrets). Accepted answers become text files in `data/`, and `bot.db` is built from them.

بالعربية: الطالب يفتح الصفحة، يختار المادة، ينزّل ملفاً واحداً فيه كل محاضراتها وأسئلتها، يعطيه لـ Claude، يلصق الرد، تتحقق الصفحة من كل اقتباس، ثم يرسل النتيجة في Pull Request. المشرف يدمج، وGitHub Actions تكتب `data/`.

```
site/index.html      the student page (static; GitHub Pages)          .github/workflows/  pages · pr-check · data-writer · ingest-pdf · check-bot
data/                source of truth (JSON per subject)                tools/              all scripts + all tests (tools/test_*.py, smoke_*.js)
sources/  inbox/     lecture text made from PDFs / PDFs waiting       config/             subjects.json (hand-edited) + sources.json (written by the Action)
intake/ replies/ media/   student files (add-only)                    01-RUNBOOK.md …     the guide (Arabic); start with 00-INDEX.md
```

## Quick mode (student uploads a PDF + the Telegram export)

On the page the student picks year and subject, uploads lecture PDF(s) and the Telegram `messages.html` export, and the page converts both **in the browser** (pdf.js from cdnjs for the PDF; DOMParser for the export). It builds one pack for Claude, validates the pasted reply against the **uploaded** lecture, lets the student edit, and downloads ONE zip for the pull request: `replies/<id>/quick-<sha8>.jsonl` + `.summary.md`, `intake/<id>/<date>-<sha8>.json` (new questions only, keys `f:<hash12>` identical to `tools/ingest_polls.py`), `sources/<id>/<slug>.md` (lecture text). After the merge `data-writer.yml` runs `tools/register_sources.py` then `tools/apply_pending.py`. Tested by `tools/test_quick.py` (real pdf.js + jsdom + the real Python tools, English and Arabic PDF pages). Not covered: pictures/figures, scanned PDFs, a real browser.

## Test it on your machine

Needs Python 3.8+ and Node. Once:

```
git clone https://github.com/homs-uni/lecture-site-engine ../lecture-site-engine
pip install pymupdf pillow
npm install jsdom pdfjs-dist@3.11.174
```

**1. Run every test** (about 30 seconds; prints the raw output of each, ends with `ALL TESTS PASSED`; skipped tests are listed, never hidden):

```
python tools/run_all.py --lectures ../lecture-site-engine --node-modules .
```

**2. Click through the page** (do not double-click `index.html`: it loads its data with `fetch`):

```
python tools/dev_site.py --lectures ../lecture-site-engine --open      # http://localhost:8000
```

Pick year 3 → *Digital Communications* → the lecture list appears (all ticked) → download. Subject 11 gives 2 files because its lectures are over 250,000 characters.

**3. Test the paste → check → review → download flow without Claude:**

```
python tools/fake_reply.py --lectures ../lecture-site-engine --subject 11 > reply.txt
```

Paste `reply.txt` into step ③ and press *check*. You should see many ✓ verified, one ✗ rejected (an invented quote on purpose) and one ⚠ not found. It only exercises the machinery; it does not measure Claude's accuracy.

**4. Test a student PDF upload:** copy any PDF to `inbox/12/My lecture 3.pdf`, run `python tools/ingest_inbox.py --keep-pdf`, then `dev_site.py`: subject 12 now lists the lecture. Undo (only these files): `git restore sources/manifest.json`, then delete `sources/12/` and `config/sources.json`.

## Put it on GitHub

1. **Decide the repo.** Use a **new** repo, not the live bot repo: the Render question (how Render builds `bot.db` from `data/`) is still open, and every commit on the live repo redeploys the bot. Students fork it, so it has to be **public**; that also publishes `sources/` (lecture text from student PDFs) — check you are allowed to.
2. Point the page at it, then push:
   ```
   python tools/set_repo.py <owner>/<repo>
   git init -b main && git add -A && git commit -m "IT-bot question pipeline v2.1"
   git remote add origin https://github.com/<owner>/<repo>.git && git push -u origin main
   ```
3. **Settings → Pages → Source = GitHub Actions.** The page appears at `https://<owner>.github.io/<repo>/` after the `pages` workflow finishes.
4. **Settings → Actions → General → Workflow permissions = Read and write** (`data-writer` and `ingest-pdf` commit back to `main`), and *Fork pull request workflows → Require approval for first-time contributors*. If you protect `main`, allow `github-actions[bot]` to push.
5. No secrets are needed. `lecture-site-engine` must stay public (the workflows check it out).
6. Put the 3 fixed questions in `data/` (see `HANDOFF-BUILD.md`) before relying on `check-bot.yml --strict`; `media/` must also hold the pictures for that check to run strictly.

## Never tested yet

A real browser (only jsdom), a real Claude conversation with a 360,000-character pack, and all the GitHub Actions on GitHub itself. The first PR from a fork is the real test: watch the *Summary* tab of the `pr-check` run.

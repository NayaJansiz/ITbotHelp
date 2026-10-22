# GitHub Actions workflow locations

GitHub only discovers executable workflow files in the repository-root `.github/workflows/` folder. The application lives in `IT-bot-guide-v2/`, so the active, path-adjusted workflows are at the repository root:

- `.github/workflows/pages.yml` — build, test, publish the student website.
- `.github/workflows/pr-check.yml` — validate student submissions in pull requests.
- `.github/workflows/data-writer.yml` — process only files that reach `main` after review, update this repository's text data and rebuild the Pages output.
- `.github/workflows/ingest-pdf.yml` — turn approved `inbox/` PDFs into lecture text after merge.

The YAML files in this directory are retained as implementation-root templates/reference copies; they are not executed directly by GitHub Actions. These workflows operate on ITbotHelp only and do not deploy, push to, or modify the separate Render-hosted `nadeembrijawy/IT-bot` bot/database.

Student PRs must be reviewed and merged by a maintainer. The automated writer starts only after approved files reach `main`; unresolved answer conflicts and inferred/figure/student answers remain flagged for review.

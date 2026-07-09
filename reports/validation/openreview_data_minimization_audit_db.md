# OpenReview Data Minimization Audit

- Created: `2026-07-08T19:38:25+00:00`
- Status: `passed`
- Normalized files: `25`
- Batch files: `789`
- Papers seen: `35397`
- Reviews seen: `160517`
- Batch requests: `683620`
- Database checked: `True`
- Database status: `ok`
- Raw checked: `True`
- Raw status: `requires_cleanup`
- Raw size GB: `1.769`
- Fail on raw: `False`

## Policy

- Normalized: title, abstract, decision metadata, official review fields, ratings/confidence, and timestamps only; no PDF pointer/body and no author response/rebuttal text
- AI scoring: title, abstract, rating/confidence, and compacted public review text only
- Forbidden normalized keys: `body, body_text, full_text, paper_text, paragraphs, pdf_text, pdf_url, rebuttals, sections`
- Forbidden batch markers: `pdf_url, full_text, paper_text, pdf_text, body_text`

## Issues

- None

## Raw Snapshot Retention

- Status: `requires_cleanup`
- Files: `284`
- Raw note pages: `265`
- Size GB: `1.769`
- Recommendation: delete or archive raw OpenReview API snapshots after explicit approval; normalized, batch, and database artifacts are sufficient for production

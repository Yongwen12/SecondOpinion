# OpenReview Data Minimization Audit

- Created: `2026-07-08T19:01:37+00:00`
- Status: `passed`
- Normalized files: `1`
- Batch files: `1`
- Papers seen: `418`
- Reviews seen: `1586`
- Batch requests: `1569`
- Database checked: `True`
- Database status: `ok`

## Policy

- Normalized: title, abstract, decision metadata, official review fields, ratings/confidence, and timestamps only; no PDF pointer/body and no author response/rebuttal text
- AI scoring: title, abstract, rating/confidence, and compacted public review text only
- Forbidden normalized keys: `body, body_text, full_text, paper_text, paragraphs, pdf_text, pdf_url, rebuttals, sections`
- Forbidden batch markers: `pdf_url, full_text, paper_text, pdf_text, body_text`

## Issues

- None

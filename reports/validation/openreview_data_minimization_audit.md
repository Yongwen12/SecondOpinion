# OpenReview Data Minimization Audit

- Created: `2026-07-07T10:34:33+00:00`
- Status: `passed`
- Normalized files: `19`
- Batch files: `120`
- Papers seen: `25007`
- Reviews seen: `98903`
- Batch requests: `182480`

## Policy

- Normalized: title, abstract, decisions, public review fields, ratings/confidence, timestamps, and optional pdf_url pointer metadata
- AI scoring: title, abstract, rating/confidence, and compacted public review text only
- Forbidden normalized keys: `body, body_text, full_text, paper_text, paragraphs, pdf_text, sections`
- Forbidden batch markers: `pdf_url, full_text, paper_text, pdf_text, body_text`

## Issues

- None

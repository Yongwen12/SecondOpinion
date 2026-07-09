# Priority 2 Minimal OpenReview Probe Runbook

Goal: pull only title, abstract, decision metadata, and official review fields. Do not keep PDF pointers, paper full text, author rebuttals, revision notices, or admin/meta comments. Batch scoring applies a second author/admin noise filter before any OpenAI request is written.

Current blocker: `data/validation/openreview_auth_check.json` reports `TokenExpiredError`; refresh `data/secrets/openreview.cookie` from a logged-in OpenReview browser session, then rerun the probes below.

## Refresh Cookie

```powershell
python -m secondopinion.tools.openreview_auth_setup --cookie-file path	oresh-openreview-cookies.txt --out-cookie data/secrets/openreview.cookie --env .env --out data/validation/openreview_auth_setup.json
python -m secondopinion.tools.openreview_auth_check --invitation AISTATS.cc/2025/Conference/-/Submission --sample-limit 1 --out data/validation/openreview_auth_check.json
```

## Probe Candidates

These commands run safe local stages only: pull, year/filter where applicable, quality, ingest, build batch, split batch. They do not submit OpenAI Batch jobs.

```powershell
python -m secondopinion.tools.openreview_safe_pipeline --venues data/config/openreview_venues_2025.json --venue AISTATS --pull-limit 50 --execute-safe --max-submit-cost-usd 25.0 --batch-cost-limit-usd 25.0
python -m secondopinion.tools.openreview_safe_pipeline --venues data/config/openreview_venues_2025.json --venue COLM --pull-limit 50 --execute-safe --max-submit-cost-usd 25.0 --batch-cost-limit-usd 25.0
python -m secondopinion.tools.openreview_safe_pipeline --venues data/config/openreview_venues_2025.json --venue CORL --pull-limit 50 --execute-safe --max-submit-cost-usd 25.0 --batch-cost-limit-usd 25.0
python -m secondopinion.tools.openreview_safe_pipeline --venues data/config/openreview_venues_2025.json --venue UAI --pull-limit 50 --execute-safe --max-submit-cost-usd 25.0 --batch-cost-limit-usd 25.0
```

## Gates Before Scoring

```powershell
python -m secondopinion.tools.openreview_data_minimization_audit --normalized data/normalized/*_2025*.json --batch data/batch/**/*_batch.jsonl --out data/validation/openreview_data_minimization_audit.json --markdown reports/validation/openreview_data_minimization_audit.md
python -m secondopinion.tools.batch_cost_review --manifest data/batch/**/*_manifest.json --out data/validation/batch_cost_review.json --markdown reports/validation/batch_cost_review.md --max-total-cost-usd 25.0
```

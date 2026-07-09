# OpenReview 2025 Execution Runbook

- Created: `2026-07-06T21:01:07+00:00`
- Model: `gpt-5.4-nano`
- Pilot sample limit: `50`
- Core priority 1: `ICLR, ICML, NEURIPS, TMLR`
- Probe priority 2: `AISTATS, COLM, CORL, UAI`
- Excluded: `JAIR, JMLR, MLJ`

## install_cookie_and_probe_inventory

Install a browser-verified OpenReview cookie, then confirm which 2025 venues expose public reviews.

- Venues: `-`
- Success gate: openreview_resolved_inventory.ready_to_pull_and_score contains venues confirmed by candidate-level public-review probes
- Resume note: pull commands include `--resume`; if a network/API error interrupts a crawl, inspect the raw snapshot `manifest.json` for `failed`, `error`, and `next_offset`, then rerun the same command.

```powershell
python -m secondopinion.tools.openreview_challenge_resume --cookie-file path\to\browser-cookies.txt --execute-probe --skip-existing --pull-limit 50
python -m secondopinion.tools.openreview_secret_check --out data/validation/openreview_secret_check.json
python -m secondopinion.tools.openreview_local_refresh --max-total-cost-usd 25.0
```

## priority1_pilots

Run safe pull/build stages for core 2025 venues with a small paper limit before any full crawl.

- Venues: `ICLR, ICML, NEURIPS, TMLR`
- Success gate: openreview_pilot_readiness returns ready_for_full_pull for each selected venue; interrupted pulls leave manifest.failed=true and can be rerun with --resume
- Resume note: pull commands include `--resume`; if a network/API error interrupts a crawl, inspect the raw snapshot `manifest.json` for `failed`, `error`, and `next_offset`, then rerun the same command.

```powershell
python -m secondopinion.tools.openreview_safe_pipeline --venues data/config/openreview_venues_2025.json --venue ICLR --pull-limit 50 --cookie-file path\to\browser-cookies.txt --execute-safe --max-submit-cost-usd 25.0 --batch-cost-limit-usd 25.0
python -m secondopinion.tools.openreview_safe_pipeline --venues data/config/openreview_venues_2025.json --venue ICML --pull-limit 50 --cookie-file path\to\browser-cookies.txt --execute-safe --max-submit-cost-usd 25.0 --batch-cost-limit-usd 25.0
python -m secondopinion.tools.openreview_safe_pipeline --venues data/config/openreview_venues_2025.json --venue NEURIPS --pull-limit 50 --cookie-file path\to\browser-cookies.txt --execute-safe --max-submit-cost-usd 25.0 --batch-cost-limit-usd 25.0
python -m secondopinion.tools.openreview_safe_pipeline --venues data/config/openreview_venues_2025.json --venue TMLR --pull-limit 50 --cookie-file path\to\browser-cookies.txt --execute-safe --max-submit-cost-usd 25.0 --batch-cost-limit-usd 25.0
```

## priority1_full_pull_and_batch_build

Promote core venues to full safe pull/build only after their pilots pass readiness checks.

- Venues: `ICLR, ICML, NEURIPS, TMLR`
- Success gate: batch_cost_review is under budget and no submit_batch has been run; interrupted pulls leave manifest.next_offset for --resume
- Resume note: pull commands include `--resume`; if a network/API error interrupts a crawl, inspect the raw snapshot `manifest.json` for `failed`, `error`, and `next_offset`, then rerun the same command.

```powershell
python -m secondopinion.tools.openreview_safe_pipeline --venues data/config/openreview_venues_2025.json --venue ICLR --cookie-file path\to\browser-cookies.txt --execute-safe --max-submit-cost-usd 25.0 --batch-cost-limit-usd 25.0
python -m secondopinion.tools.openreview_safe_pipeline --venues data/config/openreview_venues_2025.json --venue ICML --cookie-file path\to\browser-cookies.txt --execute-safe --max-submit-cost-usd 25.0 --batch-cost-limit-usd 25.0
python -m secondopinion.tools.openreview_safe_pipeline --venues data/config/openreview_venues_2025.json --venue NEURIPS --cookie-file path\to\browser-cookies.txt --execute-safe --max-submit-cost-usd 25.0 --batch-cost-limit-usd 25.0
python -m secondopinion.tools.openreview_safe_pipeline --venues data/config/openreview_venues_2025.json --venue TMLR --cookie-file path\to\browser-cookies.txt --execute-safe --max-submit-cost-usd 25.0 --batch-cost-limit-usd 25.0
```

## priority2_public_review_probe

Only pull and score candidate venues after inventory confirms public official-review coverage.

- Venues: `AISTATS, COLM, CORL, UAI`
- Success gate: score only venues whose sample quality shows non-empty public reviews
- Resume note: pull commands include `--resume`; if a network/API error interrupts a crawl, inspect the raw snapshot `manifest.json` for `failed`, `error`, and `next_offset`, then rerun the same command.

```powershell
python -m secondopinion.tools.openreview_safe_pipeline --venues data/config/openreview_venues_2025.json --venue AISTATS --pull-limit 50 --cookie-file path\to\browser-cookies.txt --execute-safe --max-submit-cost-usd 25.0 --batch-cost-limit-usd 25.0
python -m secondopinion.tools.openreview_safe_pipeline --venues data/config/openreview_venues_2025.json --venue COLM --pull-limit 50 --cookie-file path\to\browser-cookies.txt --execute-safe --max-submit-cost-usd 25.0 --batch-cost-limit-usd 25.0
python -m secondopinion.tools.openreview_safe_pipeline --venues data/config/openreview_venues_2025.json --venue CORL --pull-limit 50 --cookie-file path\to\browser-cookies.txt --execute-safe --max-submit-cost-usd 25.0 --batch-cost-limit-usd 25.0
python -m secondopinion.tools.openreview_safe_pipeline --venues data/config/openreview_venues_2025.json --venue UAI --pull-limit 50 --cookie-file path\to\browser-cookies.txt --execute-safe --max-submit-cost-usd 25.0 --batch-cost-limit-usd 25.0
```

## batch_submit_after_cost_review

Submit OpenAI Batch jobs only after manifests exist and total estimated cost is acceptable.

- Venues: `-`
- Success gate: human approval for OpenAI spend; submit_batch is intentionally separate from safe pipeline
- Resume note: pull commands include `--resume`; if a network/API error interrupts a crawl, inspect the raw snapshot `manifest.json` for `failed`, `error`, and `next_offset`, then rerun the same command.

```powershell
python -m secondopinion.tools.batch_cost_review --manifest data/batch/**/*_manifest.json --out data/validation/batch_cost_review.json --markdown reports/validation/batch_cost_review.md --max-total-cost-usd 25.0
python -m secondopinion.tools.openreview_plan_runner --plan data/validation/openreview_ingestion_plan_2025.json --include-costly --stage submit_batch --max-submit-cost-usd 25.0
```

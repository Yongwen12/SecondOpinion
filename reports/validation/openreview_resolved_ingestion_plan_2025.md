# OpenReview 2025 Ingestion Plan

- Created: `2026-07-09T19:42:43+00:00`
- Source inventory: `2026-07-09T19:42:43+00:00`
- Batch scoring model: `gpt-5.4-nano`
- Pull limit: `50`

## Summary

| Readiness | Venues |
| --- | ---: |
| ready | 1 |

## Queue

| Venue | Status | Readiness | Invitation | Normalized output |
| --- | --- | --- | --- | --- |
| ICLR | open_reviews_available | ready | `ICLR.cc/2025/Conference/-/Submission` | `data/normalized/iclr_2025_sample50.json` |

## Auth Gate

If venues are `blocked_openreview_auth`, verify OpenReview in a browser and set one local-only value:

```powershell
$env:OPENREVIEW_COOKIE_FILE = "data/secrets/openreview.cookie"
# The file may contain either a raw Cookie header or a Netscape cookie jar export.
# or, for a short value:
$env:OPENREVIEW_COOKIE = "..."
```
Then verify auth and rerun inventory before executing venue pull commands:

First inspect local secret wiring without printing secret values, then run the network gate:

```powershell
python -m secondopinion.tools.openreview_secret_check --out data/validation/openreview_secret_check.json
python -m secondopinion.tools.openreview_pipeline_gate --venues data/config/openreview_venues_2025.json --out data/validation/openreview_pipeline_gate.json
python -m secondopinion.tools.openreview_auth_check --out data/validation/openreview_auth_check.json
python -m secondopinion.tools.openreview_venue_inventory --venues data/config/openreview_venues_2025.json --sample-limit 50 --out data/validation/openreview_venue_inventory_2025.json --markdown reports/validation/openreview_venue_inventory_2025.md
python -m secondopinion.tools.openreview_ingestion_plan --inventory data/validation/openreview_venue_inventory_2025.json --out data/validation/openreview_ingestion_plan_2025.json --markdown reports/validation/openreview_ingestion_plan_2025.md
python -m secondopinion.tools.openreview_plan_runner --plan data/validation/openreview_ingestion_plan_2025.json --out data/validation/openreview_plan_runner_last.json
```

## Commands

### ICLR


```powershell
python -m secondopinion.tools.openreview_pull --venue ICLR --year 2025 --invitation ICLR.cc/2025/Conference/-/Submission --output data/normalized/iclr_2025_sample50.json --details replies --page-size 100 --polite-delay 0.2 --snapshot iclr_2025_sample50 --limit 50
python -m secondopinion.tools.data_quality_report --input data/normalized/iclr_2025_sample50.json --json-out data/validation/iclr_2025_sample50_quality.json --markdown-out reports/validation/iclr_2025_sample50_quality.md
python -m secondopinion.tools.ingest_normalized --input data/normalized/iclr_2025_sample50.json
python -m secondopinion.tools.build_scoring_batch --input data/normalized/iclr_2025_sample50.json --output data/batch/iclr_2025_sample50_batch.jsonl --manifest data/batch/iclr_2025_sample50_batch_manifest.json --model gpt-5.4-nano
python -m secondopinion.tools.split_scoring_batch --input data/batch/iclr_2025_sample50_batch.jsonl --manifest data/batch/iclr_2025_sample50_batch_manifest.json --output-dir data/batch/iclr_2025_sample50_parts --prefix iclr_2025 --max-estimated-input-tokens 1600000
python -m secondopinion.tools.submit_scoring_batch --input data/batch/iclr_2025_sample50_batch.jsonl --manifest data/batch/iclr_2025_sample50_batch_manifest.json --output data/batch/iclr_2025_sample50_batch_submission.json --dry-run
python -m secondopinion.tools.submit_scoring_batch --input data/batch/iclr_2025_sample50_batch.jsonl --manifest data/batch/iclr_2025_sample50_batch_manifest.json --output data/batch/iclr_2025_sample50_batch_submission.json
python -m secondopinion.tools.retrieve_scoring_batch --batch-id YOUR_BATCH_ID --output data/batch/iclr_2025_sample50_batch_output.jsonl --status-out data/batch/iclr_2025_sample50_batch_status.json --error-output data/batch/iclr_2025_sample50_batch_errors.jsonl
python -m secondopinion.tools.import_scoring_batch_results --input data/batch/iclr_2025_sample50_batch_output.jsonl --manifest data/batch/iclr_2025_sample50_batch_manifest.json
```

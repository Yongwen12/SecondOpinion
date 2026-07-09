# OpenReview 2025 Ingestion Plan

- Created: `2026-07-07T10:17:52+00:00`
- Source inventory: `2026-07-07T10:16:59+00:00`
- Batch scoring model: `gpt-5.4-nano`
- Pull limit: `None`

## Summary

| Readiness | Venues |
| --- | ---: |
| excluded_not_scored | 3 |
| needs_manual_inspection | 5 |
| ready | 3 |

## Queue

| Venue | Status | Readiness | Invitation | Normalized output |
| --- | --- | --- | --- | --- |
| ICLR | open_reviews_available | ready | `ICLR.cc/2025/Conference/-/Submission` | `data/normalized/iclr_2025_full.json` |
| ICML | open_reviews_available | ready | `ICML.cc/2025/Conference/-/Submission` | `data/normalized/icml_2025_full.json` |
| NEURIPS | open_reviews_available | ready | `NeurIPS.cc/2025/Conference/-/Submission` | `data/normalized/neurips_2025_full.json` |
| TMLR | no_public_reviews | needs_manual_inspection | `TMLR/-/Submission` | `data/normalized/tmlr_2025_full.json` |
| COLM | no_public_reviews | needs_manual_inspection | `colmweb.org/2025/Conference/-/Submission` | `data/normalized/colm_2025_full.json` |
| AISTATS | no_public_reviews | needs_manual_inspection | `AISTATS.cc/2025/Conference/-/Submission` | `data/normalized/aistats_2025_full.json` |
| UAI | no_public_reviews | needs_manual_inspection | `auai.org/UAI/2025/Conference/-/Submission` | `data/normalized/uai_2025_full.json` |
| CORL | no_public_reviews | needs_manual_inspection | `robot-learning.org/CoRL/2025/Conference/-/Submission` | `data/normalized/corl_2025_full.json` |
| JMLR | excluded_no_public_reviews | excluded_not_scored | `` | `data/normalized/jmlr_2025_full.json` |
| JAIR | excluded_no_public_reviews | excluded_not_scored | `` | `data/normalized/jair_2025_full.json` |
| MLJ | excluded_no_public_reviews | excluded_not_scored | `` | `data/normalized/mlj_2025_full.json` |

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
python -m secondopinion.tools.openreview_pull --venue ICLR --year 2025 --invitation ICLR.cc/2025/Conference/-/Submission --output data/normalized/iclr_2025_full.json --raw-root data/raw --details replies --page-size 100 --polite-delay 0.2 --snapshot iclr_2025_full --resume
python -m secondopinion.tools.data_quality_report --input data/normalized/iclr_2025_full.json --json-out data/validation/iclr_2025_full_quality.json --markdown-out reports/validation/iclr_2025_full_quality.md
python -m secondopinion.tools.ingest_normalized --input data/normalized/iclr_2025_full.json
python -m secondopinion.tools.build_scoring_batch --input data/normalized/iclr_2025_full.json --output data/batch/iclr_2025_full_batch.jsonl --manifest data/batch/iclr_2025_full_batch_manifest.json --model gpt-5.4-nano
python -m secondopinion.tools.split_scoring_batch --input data/batch/iclr_2025_full_batch.jsonl --manifest data/batch/iclr_2025_full_batch_manifest.json --output-dir data/batch/iclr_2025_full_parts --prefix iclr_2025 --max-estimated-input-tokens 1600000
python -m secondopinion.tools.submit_scoring_batch --input data/batch/iclr_2025_full_batch.jsonl --manifest data/batch/iclr_2025_full_batch_manifest.json --output data/batch/iclr_2025_full_batch_submission.json --dry-run
python -m secondopinion.tools.submit_scoring_batch --input data/batch/iclr_2025_full_batch.jsonl --manifest data/batch/iclr_2025_full_batch_manifest.json --output data/batch/iclr_2025_full_batch_submission.json
python -m secondopinion.tools.retrieve_scoring_batch --batch-id YOUR_BATCH_ID --output data/batch/iclr_2025_full_batch_output.jsonl --status-out data/batch/iclr_2025_full_batch_status.json --error-output data/batch/iclr_2025_full_batch_errors.jsonl
python -m secondopinion.tools.import_scoring_batch_results --input data/batch/iclr_2025_full_batch_output.jsonl --manifest data/batch/iclr_2025_full_batch_manifest.json
```

### ICML


```powershell
python -m secondopinion.tools.openreview_pull --venue ICML --year 2025 --invitation ICML.cc/2025/Conference/-/Submission --output data/normalized/icml_2025_full.json --raw-root data/raw --details replies --page-size 100 --polite-delay 0.2 --snapshot icml_2025_full --resume
python -m secondopinion.tools.data_quality_report --input data/normalized/icml_2025_full.json --json-out data/validation/icml_2025_full_quality.json --markdown-out reports/validation/icml_2025_full_quality.md
python -m secondopinion.tools.ingest_normalized --input data/normalized/icml_2025_full.json
python -m secondopinion.tools.build_scoring_batch --input data/normalized/icml_2025_full.json --output data/batch/icml_2025_full_batch.jsonl --manifest data/batch/icml_2025_full_batch_manifest.json --model gpt-5.4-nano
python -m secondopinion.tools.split_scoring_batch --input data/batch/icml_2025_full_batch.jsonl --manifest data/batch/icml_2025_full_batch_manifest.json --output-dir data/batch/icml_2025_full_parts --prefix icml_2025 --max-estimated-input-tokens 1600000
python -m secondopinion.tools.submit_scoring_batch --input data/batch/icml_2025_full_batch.jsonl --manifest data/batch/icml_2025_full_batch_manifest.json --output data/batch/icml_2025_full_batch_submission.json --dry-run
python -m secondopinion.tools.submit_scoring_batch --input data/batch/icml_2025_full_batch.jsonl --manifest data/batch/icml_2025_full_batch_manifest.json --output data/batch/icml_2025_full_batch_submission.json
python -m secondopinion.tools.retrieve_scoring_batch --batch-id YOUR_BATCH_ID --output data/batch/icml_2025_full_batch_output.jsonl --status-out data/batch/icml_2025_full_batch_status.json --error-output data/batch/icml_2025_full_batch_errors.jsonl
python -m secondopinion.tools.import_scoring_batch_results --input data/batch/icml_2025_full_batch_output.jsonl --manifest data/batch/icml_2025_full_batch_manifest.json
```

### NEURIPS


```powershell
python -m secondopinion.tools.openreview_pull --venue NEURIPS --year 2025 --invitation NeurIPS.cc/2025/Conference/-/Submission --output data/normalized/neurips_2025_full.json --raw-root data/raw --details replies --page-size 100 --polite-delay 0.2 --snapshot neurips_2025_full --resume
python -m secondopinion.tools.data_quality_report --input data/normalized/neurips_2025_full.json --json-out data/validation/neurips_2025_full_quality.json --markdown-out reports/validation/neurips_2025_full_quality.md
python -m secondopinion.tools.ingest_normalized --input data/normalized/neurips_2025_full.json
python -m secondopinion.tools.build_scoring_batch --input data/normalized/neurips_2025_full.json --output data/batch/neurips_2025_full_batch.jsonl --manifest data/batch/neurips_2025_full_batch_manifest.json --model gpt-5.4-nano
python -m secondopinion.tools.split_scoring_batch --input data/batch/neurips_2025_full_batch.jsonl --manifest data/batch/neurips_2025_full_batch_manifest.json --output-dir data/batch/neurips_2025_full_parts --prefix neurips_2025 --max-estimated-input-tokens 1600000
python -m secondopinion.tools.submit_scoring_batch --input data/batch/neurips_2025_full_batch.jsonl --manifest data/batch/neurips_2025_full_batch_manifest.json --output data/batch/neurips_2025_full_batch_submission.json --dry-run
python -m secondopinion.tools.submit_scoring_batch --input data/batch/neurips_2025_full_batch.jsonl --manifest data/batch/neurips_2025_full_batch_manifest.json --output data/batch/neurips_2025_full_batch_submission.json
python -m secondopinion.tools.retrieve_scoring_batch --batch-id YOUR_BATCH_ID --output data/batch/neurips_2025_full_batch_output.jsonl --status-out data/batch/neurips_2025_full_batch_status.json --error-output data/batch/neurips_2025_full_batch_errors.jsonl
python -m secondopinion.tools.import_scoring_batch_results --input data/batch/neurips_2025_full_batch_output.jsonl --manifest data/batch/neurips_2025_full_batch_manifest.json
```

### TMLR

- Blocked: inventory status is no_public_reviews
- Rolling venue: `decision_or_activity_year` is applied before quality checks, ingest, and scoring.
- Commands are recorded for handoff but should wait until readiness is `ready`.

```powershell
python -m secondopinion.tools.openreview_pull --venue TMLR --year 2025 --invitation TMLR/-/Submission --output data/normalized/tmlr_2025_full_unfiltered.json --raw-root data/raw --details replies --page-size 100 --polite-delay 0.2 --snapshot tmlr_2025_full --resume
python -m secondopinion.tools.filter_normalized --input data/normalized/tmlr_2025_full_unfiltered.json --out data/normalized/tmlr_2025_full.json --year 2025 --mode decision_or_activity_year
python -m secondopinion.tools.data_quality_report --input data/normalized/tmlr_2025_full.json --json-out data/validation/tmlr_2025_full_quality.json --markdown-out reports/validation/tmlr_2025_full_quality.md
python -m secondopinion.tools.ingest_normalized --input data/normalized/tmlr_2025_full.json
python -m secondopinion.tools.build_scoring_batch --input data/normalized/tmlr_2025_full.json --output data/batch/tmlr_2025_full_batch.jsonl --manifest data/batch/tmlr_2025_full_batch_manifest.json --model gpt-5.4-nano
python -m secondopinion.tools.split_scoring_batch --input data/batch/tmlr_2025_full_batch.jsonl --manifest data/batch/tmlr_2025_full_batch_manifest.json --output-dir data/batch/tmlr_2025_full_parts --prefix tmlr_2025 --max-estimated-input-tokens 1600000
python -m secondopinion.tools.submit_scoring_batch --input data/batch/tmlr_2025_full_batch.jsonl --manifest data/batch/tmlr_2025_full_batch_manifest.json --output data/batch/tmlr_2025_full_batch_submission.json --dry-run
python -m secondopinion.tools.submit_scoring_batch --input data/batch/tmlr_2025_full_batch.jsonl --manifest data/batch/tmlr_2025_full_batch_manifest.json --output data/batch/tmlr_2025_full_batch_submission.json
python -m secondopinion.tools.retrieve_scoring_batch --batch-id YOUR_BATCH_ID --output data/batch/tmlr_2025_full_batch_output.jsonl --status-out data/batch/tmlr_2025_full_batch_status.json --error-output data/batch/tmlr_2025_full_batch_errors.jsonl
python -m secondopinion.tools.import_scoring_batch_results --input data/batch/tmlr_2025_full_batch_output.jsonl --manifest data/batch/tmlr_2025_full_batch_manifest.json
```

### COLM

- Blocked: inventory status is no_public_reviews
- Commands are recorded for handoff but should wait until readiness is `ready`.

```powershell
python -m secondopinion.tools.openreview_pull --venue COLM --year 2025 --invitation colmweb.org/2025/Conference/-/Submission --output data/normalized/colm_2025_full.json --raw-root data/raw --details replies --page-size 100 --polite-delay 0.2 --snapshot colm_2025_full --resume
python -m secondopinion.tools.data_quality_report --input data/normalized/colm_2025_full.json --json-out data/validation/colm_2025_full_quality.json --markdown-out reports/validation/colm_2025_full_quality.md
python -m secondopinion.tools.ingest_normalized --input data/normalized/colm_2025_full.json
python -m secondopinion.tools.build_scoring_batch --input data/normalized/colm_2025_full.json --output data/batch/colm_2025_full_batch.jsonl --manifest data/batch/colm_2025_full_batch_manifest.json --model gpt-5.4-nano
python -m secondopinion.tools.split_scoring_batch --input data/batch/colm_2025_full_batch.jsonl --manifest data/batch/colm_2025_full_batch_manifest.json --output-dir data/batch/colm_2025_full_parts --prefix colm_2025 --max-estimated-input-tokens 1600000
python -m secondopinion.tools.submit_scoring_batch --input data/batch/colm_2025_full_batch.jsonl --manifest data/batch/colm_2025_full_batch_manifest.json --output data/batch/colm_2025_full_batch_submission.json --dry-run
python -m secondopinion.tools.submit_scoring_batch --input data/batch/colm_2025_full_batch.jsonl --manifest data/batch/colm_2025_full_batch_manifest.json --output data/batch/colm_2025_full_batch_submission.json
python -m secondopinion.tools.retrieve_scoring_batch --batch-id YOUR_BATCH_ID --output data/batch/colm_2025_full_batch_output.jsonl --status-out data/batch/colm_2025_full_batch_status.json --error-output data/batch/colm_2025_full_batch_errors.jsonl
python -m secondopinion.tools.import_scoring_batch_results --input data/batch/colm_2025_full_batch_output.jsonl --manifest data/batch/colm_2025_full_batch_manifest.json
```

### AISTATS

- Blocked: inventory status is no_public_reviews
- Commands are recorded for handoff but should wait until readiness is `ready`.

```powershell
python -m secondopinion.tools.openreview_pull --venue AISTATS --year 2025 --invitation AISTATS.cc/2025/Conference/-/Submission --output data/normalized/aistats_2025_full.json --raw-root data/raw --details replies --page-size 100 --polite-delay 0.2 --snapshot aistats_2025_full --resume
python -m secondopinion.tools.data_quality_report --input data/normalized/aistats_2025_full.json --json-out data/validation/aistats_2025_full_quality.json --markdown-out reports/validation/aistats_2025_full_quality.md
python -m secondopinion.tools.ingest_normalized --input data/normalized/aistats_2025_full.json
python -m secondopinion.tools.build_scoring_batch --input data/normalized/aistats_2025_full.json --output data/batch/aistats_2025_full_batch.jsonl --manifest data/batch/aistats_2025_full_batch_manifest.json --model gpt-5.4-nano
python -m secondopinion.tools.split_scoring_batch --input data/batch/aistats_2025_full_batch.jsonl --manifest data/batch/aistats_2025_full_batch_manifest.json --output-dir data/batch/aistats_2025_full_parts --prefix aistats_2025 --max-estimated-input-tokens 1600000
python -m secondopinion.tools.submit_scoring_batch --input data/batch/aistats_2025_full_batch.jsonl --manifest data/batch/aistats_2025_full_batch_manifest.json --output data/batch/aistats_2025_full_batch_submission.json --dry-run
python -m secondopinion.tools.submit_scoring_batch --input data/batch/aistats_2025_full_batch.jsonl --manifest data/batch/aistats_2025_full_batch_manifest.json --output data/batch/aistats_2025_full_batch_submission.json
python -m secondopinion.tools.retrieve_scoring_batch --batch-id YOUR_BATCH_ID --output data/batch/aistats_2025_full_batch_output.jsonl --status-out data/batch/aistats_2025_full_batch_status.json --error-output data/batch/aistats_2025_full_batch_errors.jsonl
python -m secondopinion.tools.import_scoring_batch_results --input data/batch/aistats_2025_full_batch_output.jsonl --manifest data/batch/aistats_2025_full_batch_manifest.json
```

### UAI

- Blocked: inventory status is no_public_reviews
- Commands are recorded for handoff but should wait until readiness is `ready`.

```powershell
python -m secondopinion.tools.openreview_pull --venue UAI --year 2025 --invitation auai.org/UAI/2025/Conference/-/Submission --output data/normalized/uai_2025_full.json --raw-root data/raw --details replies --page-size 100 --polite-delay 0.2 --snapshot uai_2025_full --resume
python -m secondopinion.tools.data_quality_report --input data/normalized/uai_2025_full.json --json-out data/validation/uai_2025_full_quality.json --markdown-out reports/validation/uai_2025_full_quality.md
python -m secondopinion.tools.ingest_normalized --input data/normalized/uai_2025_full.json
python -m secondopinion.tools.build_scoring_batch --input data/normalized/uai_2025_full.json --output data/batch/uai_2025_full_batch.jsonl --manifest data/batch/uai_2025_full_batch_manifest.json --model gpt-5.4-nano
python -m secondopinion.tools.split_scoring_batch --input data/batch/uai_2025_full_batch.jsonl --manifest data/batch/uai_2025_full_batch_manifest.json --output-dir data/batch/uai_2025_full_parts --prefix uai_2025 --max-estimated-input-tokens 1600000
python -m secondopinion.tools.submit_scoring_batch --input data/batch/uai_2025_full_batch.jsonl --manifest data/batch/uai_2025_full_batch_manifest.json --output data/batch/uai_2025_full_batch_submission.json --dry-run
python -m secondopinion.tools.submit_scoring_batch --input data/batch/uai_2025_full_batch.jsonl --manifest data/batch/uai_2025_full_batch_manifest.json --output data/batch/uai_2025_full_batch_submission.json
python -m secondopinion.tools.retrieve_scoring_batch --batch-id YOUR_BATCH_ID --output data/batch/uai_2025_full_batch_output.jsonl --status-out data/batch/uai_2025_full_batch_status.json --error-output data/batch/uai_2025_full_batch_errors.jsonl
python -m secondopinion.tools.import_scoring_batch_results --input data/batch/uai_2025_full_batch_output.jsonl --manifest data/batch/uai_2025_full_batch_manifest.json
```

### CORL

- Blocked: inventory status is no_public_reviews
- Commands are recorded for handoff but should wait until readiness is `ready`.

```powershell
python -m secondopinion.tools.openreview_pull --venue CORL --year 2025 --invitation robot-learning.org/CoRL/2025/Conference/-/Submission --output data/normalized/corl_2025_full.json --raw-root data/raw --details replies --page-size 100 --polite-delay 0.2 --snapshot corl_2025_full --resume
python -m secondopinion.tools.data_quality_report --input data/normalized/corl_2025_full.json --json-out data/validation/corl_2025_full_quality.json --markdown-out reports/validation/corl_2025_full_quality.md
python -m secondopinion.tools.ingest_normalized --input data/normalized/corl_2025_full.json
python -m secondopinion.tools.build_scoring_batch --input data/normalized/corl_2025_full.json --output data/batch/corl_2025_full_batch.jsonl --manifest data/batch/corl_2025_full_batch_manifest.json --model gpt-5.4-nano
python -m secondopinion.tools.split_scoring_batch --input data/batch/corl_2025_full_batch.jsonl --manifest data/batch/corl_2025_full_batch_manifest.json --output-dir data/batch/corl_2025_full_parts --prefix corl_2025 --max-estimated-input-tokens 1600000
python -m secondopinion.tools.submit_scoring_batch --input data/batch/corl_2025_full_batch.jsonl --manifest data/batch/corl_2025_full_batch_manifest.json --output data/batch/corl_2025_full_batch_submission.json --dry-run
python -m secondopinion.tools.submit_scoring_batch --input data/batch/corl_2025_full_batch.jsonl --manifest data/batch/corl_2025_full_batch_manifest.json --output data/batch/corl_2025_full_batch_submission.json
python -m secondopinion.tools.retrieve_scoring_batch --batch-id YOUR_BATCH_ID --output data/batch/corl_2025_full_batch_output.jsonl --status-out data/batch/corl_2025_full_batch_status.json --error-output data/batch/corl_2025_full_batch_errors.jsonl
python -m secondopinion.tools.import_scoring_batch_results --input data/batch/corl_2025_full_batch_output.jsonl --manifest data/batch/corl_2025_full_batch_manifest.json
```

### JMLR

- Blocked: No public OpenReview review corpus expected
- Commands are recorded for handoff but should wait until readiness is `ready`.

```powershell
```

### JAIR

- Blocked: No public OpenReview review corpus expected
- Commands are recorded for handoff but should wait until readiness is `ready`.

```powershell
```

### MLJ

- Blocked: No public OpenReview review corpus expected
- Commands are recorded for handoff but should wait until readiness is `ready`.

```powershell
```

# OpenReview Raw Cleanup Runbook

## Current state

- Production data minimization audit: normalized, batch, and database are clean.
- Strict audit is still expected to fail until historical raw snapshots are removed.
- Historical raw root: `data/raw/openreview`
- Current dry-run evidence: `data/validation/openreview_raw_cleanup_dry_run.json`
- Current strict audit evidence: `data/validation/openreview_data_minimization_audit_strict.json`

## Why cleanup is needed

The product only needs minimized normalized data, scoring batches, score summaries, and the database. Historical raw OpenReview API pages may include author responses, admin comments, author metadata, and non-core discussion text. They are not needed for the public homepage or scoring results.

## Pre-cleanup dry-run

```powershell
python -m secondopinion.tools.openreview_raw_cleanup --out data/validation/openreview_raw_cleanup_dry_run.json
```

Expected before deletion:

- `status`: `dry_run`
- `deleted`: `false`
- `before.raw_note_page_count`: greater than `0`

## Required authorization

Deletion is destructive. Execute cleanup only after explicit user approval to delete `data/raw/openreview`.

## Cleanup command

```powershell
python -m secondopinion.tools.openreview_raw_cleanup --execute --confirm delete-raw-openreview --out data/validation/openreview_raw_cleanup.json
```

The cleanup tool refuses unexpected paths and requires the exact confirmation token above.

## Post-cleanup strict audit

```powershell
python -m secondopinion.tools.openreview_data_minimization_audit --include-database --raw-root data/raw/openreview --fail-on-raw --out data/validation/openreview_data_minimization_audit_strict.json --markdown reports/validation/openreview_data_minimization_audit_strict.md
```

Expected after deletion:

- `status`: `passed`
- `database_status`: `ok`
- `raw_status`: `ok`
- `raw_total_gb`: `0` or near `0`

## Regression tests

```powershell
python -m pytest -p no:cacheprovider tests/test_openreview_raw_cleanup.py tests/test_openreview_data_minimization_audit.py tests/test_openreview_pull_snapshot_id.py tests/test_openreview_ingestion_plan_resume.py -q
```

Expected: all tests pass.

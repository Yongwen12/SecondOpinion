# OpenReview Pipeline Gate

- Created: `2026-07-08T19:04:34+00:00`
- Status: `ready_for_safe_runner_execute`
- Recommendation: Run the generated plan runner through pull/quality/ingest/build/split first; submit OpenAI batch only after cost review.
- Max submit cost USD: `25.0`
- Pull limit: `50`

## Current Gate

| Check | Status | Detail |
| --- | --- | --- |
| Local secret | `True` | `run_openreview_pipeline_gate` |
| OpenReview auth | `ok` | `run_inventory` |
| Inventory ran | `True` | Ready: `ICLR, ICML, NEURIPS, COLM, MIDL` |
| Runner dry-run | `True` | Counts: `{'skipped_existing': 22, 'dry_run': 13, 'skipped': 12, 'blocked_missing_input': 5}` |
| Scope matrix | `ICLR, ICML, NEURIPS, TMLR, COLM, AISTATS, UAI, CORL, MIDL` | Excluded: `JMLR, JAIR, MLJ` |
| Scope audit | `passed` | Errors: `0`, warnings: `0` |

## Secret

- Cookie source: `OPENREVIEW_COOKIE_FILE`
- Cookie format: `raw_header`
- Cookie names: `_ga, GCILB, openreview.refreshToken, openreview.accessToken, openreview.user, _ga_GTB25PBMVL`
- Token source: `-`

## Venue Summaries

- Inventory ready: `ICLR, ICML, NEURIPS, COLM, MIDL`
- Needs OpenReview auth: `-`
- Plan ready: `ICLR, ICML, NEURIPS, COLM, MIDL`
- Plan blocked auth: `-`

## Next Commands

```powershell
python -m secondopinion.tools.openreview_safe_pipeline --venues data/config/openreview_venues_2025.json --venue ICLR --execute-safe --max-submit-cost-usd 25.0 --batch-cost-limit-usd 25.0
python -m secondopinion.tools.openreview_safe_pipeline --venues data/config/openreview_venues_2025.json --execute-safe --max-submit-cost-usd 25.0 --batch-cost-limit-usd 25.0
python -m secondopinion.tools.openreview_scope_matrix --venues data/config/openreview_venues_2025.json --inventory data/validation/openreview_venue_inventory_2025.json --out data/validation/openreview_scope_matrix_2025.json --markdown reports/validation/openreview_scope_matrix_2025.md
python -m secondopinion.tools.batch_cost_review --manifest data/batch/**/*_manifest.json --out data/validation/batch_cost_review.json --markdown reports/validation/batch_cost_review.md --max-total-cost-usd 25.0
```

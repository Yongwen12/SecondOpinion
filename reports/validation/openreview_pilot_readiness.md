# OpenReview Pilot Readiness

- Created: `2026-07-08T19:04:36+00:00`
- Status: `not_ready`
- Venue: `AISTATS`
- Dataset: `aistats_2025_sample50`
- Pull limit: `50`
- Papers: `0`
- Reviews: `0`
- Empty core review rate: `0.00%`
- Batch requests: `0`
- Estimated batch cost USD: `0.0000`
- Recommendation: `fix_pilot_outputs`

## Next Commands

- None

## Remediation Commands

```powershell
python -m secondopinion.tools.openreview_safe_pipeline --venues data/config/openreview_venues_2025.json --venue AISTATS --pull-limit 50 --execute-safe
```

## Issues

- ERROR: missing_normalized_dataset
- ERROR: missing_quality_report
- ERROR: missing_batch_manifest

# OpenReview Batch Submit Preflight

- Created: `2026-07-07T10:38:30+00:00`
- Status: `ready_for_submit`
- OpenAI submit used: `False`
- Consistency status: `ok`
- Batch cost status: `ready_for_cost_review`
- Request count: `82219`
- Manifest count: `92`
- Estimated batch cost USD: `19.8083`
- Max total cost USD: `25.0`
- Allow submit: `True`

## Issues

- none

## Next Commands

- `python -m secondopinion.tools.openreview_report_consistency`
- `python -m secondopinion.tools.batch_cost_review --max-total-cost-usd 25`
- `python -m secondopinion.tools.openreview_plan_runner --plan data/validation/openreview_ingestion_plan.json --include-costly --stage submit_batch --execute --max-submit-cost-usd 25`

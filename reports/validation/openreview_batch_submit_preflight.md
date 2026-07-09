# OpenReview Batch Submit Preflight

- Created: `2026-07-07T10:34:34+00:00`
- Status: `blocked_explicit_approval_required`
- OpenAI submit used: `False`
- Consistency status: `ok`
- Batch cost status: `ready_for_cost_review`
- Request count: `91240`
- Manifest count: `104`
- Estimated batch cost USD: `21.9817`
- Max total cost USD: `25.0`
- Allow submit: `False`

## Issues

- `explicit_approval_required`

## Next Commands

- `python -m secondopinion.tools.openreview_report_consistency`
- `python -m secondopinion.tools.batch_cost_review --max-total-cost-usd 25`
- `python -m secondopinion.tools.openreview_batch_submit_preflight --allow-submit --max-total-cost-usd 25`

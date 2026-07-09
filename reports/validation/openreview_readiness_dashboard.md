# OpenReview Readiness Dashboard

- Created: `2026-07-08T19:16:41+00:00`
- Status: `run_priority1_pilot`
- Recommendation: Run safe 50-paper pilots for ready venues, then check pilot readiness.

## Current State

- Auth ok: `True`
- Auth recommendation: `run_openreview_pipeline_gate`
- Cookie names: `_ga, GCILB, openreview.refreshToken, openreview.accessToken, openreview.user, _ga_GTB25PBMVL`
- Cookie warnings: `missing_cf_clearance_cookie`
- OpenReview API auth ok: `True`
- OpenReview API auth status: `ok`
- Gate status: `ready_for_safe_runner_execute`
- Challenge resume: `ready_for_safe_execute`
- Challenge resume recommendation: `inspect_resolved_inventory_then_run_execute_safe`
- Auth diagnosis: `auth_ok`
- Cookie handoff: `auth_ready`
- Cookie handoff warnings: `missing_cf_clearance_cookie`
- Cookie preflight: `ready_for_auth_check`
- Cookie preflight blocking warnings: `-`
- Scope audit: `passed` targets=6 excluded=6
- Scope priority 1 core: `ICLR, ICML, NEURIPS, TMLR`
- Scope priority 2 probe: `COLM, MIDL`
- Scope excluded top journals: `JAIR, JMLR, MLJ`
- Data minimization: `passed` batch_requests=182480
- Inventory ran: `True`
- Ready to pull: `ICLR, ICML, NEURIPS, COLM, MIDL`
- Blocked auth venues: `-`
- Invitation audit attention: `-`
- Invitation probe queue: `11` candidates
- Probe queue runner: `execute=True counts={success: 11}`
- Probe results selected: `ICLR, ICML, NEURIPS`
- Probe results missing: `-`
- Probe results need larger sample: `-`
- Resolved ready to pull: `ICLR, ICML, NEURIPS`
- Resolved needs probe: `MIDL`
- Resolved needs larger probe: `-`
- Resolved pipeline: `dry_run_safe_stages`
- Pilot readiness: `ICLR=ready_for_full_pull, ICML=ready_for_full_pull, NEURIPS=ready_for_full_pull`
- Snapshot recoverable: `0`
- Existing batch estimated cost USD: `76.9724`
- Scale estimate status: `blocked_missing_inventory_sample`
- Scale estimate blocked venues: `AISTATS`
- Scale estimated batch cost USD: `0.2355`
- Batch submit preflight: `blocked_explicit_approval_required`
- Core priority 1: `ICLR, ICML, NEURIPS, TMLR`
- Probe priority 2: `AISTATS, COLM, CORL, UAI`

## Freshness

- Source: `auth_check` `2026-07-08T19:04:23+00:00`
- Stale reports: `-`
- Missing reports: `-`

## Next Commands

```powershell
python -m secondopinion.tools.openreview_safe_pipeline --venues data/config/openreview_venues_2025.json --venue COLM --venue MIDL --pull-limit 50 --execute-safe
```

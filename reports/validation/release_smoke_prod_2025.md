# SecondOpinion Release Smoke

- Created: `2026-07-09T16:08:53+00:00`
- Status: `passed`
- Frontend: `https://yongwen12.github.io/SecondOpinion/`
- API: `https://secondopinion.smartselling.work`

## Checks

| Check | OK | Message |
| --- | ---: | --- |
| `frontend_status` | `True` | Frontend returned HTTP 200 |
| `frontend_coverage_copy` | `True` | Frontend contains 2025 V1 coverage copy |
| `frontend_api_default` | `True` | Frontend default API base is production API |
| `api_health` | `True` | API health returned HTTP 200 |
| `api_home_static` | `True` | Home returned HTTP 200 source=static_home_2025 |
| `api_home_stats` | `True` | Home stats match 2025 V1 release counts |
| `api_home_boards` | `True` | Home leaderboards include publishable rows |
| `api_global_search` | `True` | Global search returned 1 items for 'CrossSpectra' |
| `api_scorecard` | `True` | Scorecard Ni4jNyroJZ returned 4 reviewers and 4 comments |

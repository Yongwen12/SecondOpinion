# SecondOpinion Release Smoke

- Created: `2026-07-09T15:47:21+00:00`
- Status: `failed`
- Frontend: `https://yongwen12.github.io/SecondOpinion/`
- API: `https://secondopinion.smartselling.work`

## Checks

| Check | OK | Message |
| --- | ---: | --- |
| `frontend_status` | `True` | Frontend returned HTTP 200 |
| `frontend_coverage_copy` | `False` | Frontend contains 2025 V1 coverage copy |
| `frontend_api_default` | `True` | Frontend default API base is production API |
| `api_health` | `True` | API health returned HTTP 200 |
| `api_home_static` | `False` | Home returned HTTP 200 source=None |
| `api_home_stats` | `False` | Home stats match 2025 V1 release counts |
| `api_home_boards` | `False` | Home leaderboards include publishable rows |
| `api_global_search` | `False` | Global search returned 0 items for 'CrossSpectra' |
| `api_scorecard` | `False` | Scorecard Ni4jNyroJZ returned 0 reviewers and 0 comments |

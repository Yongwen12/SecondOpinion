# SecondOpinion Release Smoke

- Created: `2026-07-09T15:43:12+00:00`
- Status: `passed`
- Frontend: `http://127.0.0.1:8766/index.html?api=http%3A%2F%2F127.0.0.1%3A8765`
- API: `http://127.0.0.1:8765`

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

# Frontend/API Release QA - 2025 V1

Date: 2026-07-09

## Scope

This QA pass covers the publish-critical homepage paths for the 2025 public OpenReview V1 dataset:

- Homepage payload
- Global paper search
- Paper scorecard detail fetch
- Static homepage data size
- Leaderboard noise filtering regression tests

## Current Dataset Surface

- Papers: 26,749
- Reviews/comments: 128,723
- Scored official reviews: 99,671
- Frontend static home payload: 53,073 bytes / 51.8 KiB
- Static API source: `static_home_2025`

## Real-DB Smoke Timings

Measured against `data/server/secondopinion.db` via FastAPI TestClient.

| Path | Status | Time | Notes |
| --- | ---: | ---: | --- |
| `/api/home?year=2025&limit=12` | 200 | 0.020s | Serves `frontend/data/home_2025.json` snapshot |
| `/api/papers?query=Learning Multimodal Energy-Based Model&year=2025&limit=8` | 200 | 0.232s | Finds TMLR paper |
| `/api/papers/Ni4jNyroJZ/scorecard` | 200 | 0.016s | Returns 4 reviewers / 4 comments |

## Fixes From This Pass

- Global home API now serves the release static homepage snapshot for `year=2025` instead of rebuilding leaderboards from 99,671 scored rows on every request.
- Kept conference-scoped `/api/home?conference=...` dynamic for compatibility.
- Homepage API now respects `limit` for `latest_papers` when serving the static snapshot.
- Existing frontend/API tests cover static homepage source, global search, data-scope copy, empty states, HTML escaping, and leaderboard noise filtering.

## Verification

Command:

```powershell
python -m pytest tests/test_server_api.py tests/test_frontend_api_wiring.py tests/test_batch_review_scoring.py::test_new_leaderboards_read_batch_dimensions tests/test_batch_review_scoring.py::test_leaderboards_filter_obvious_author_and_admin_noise
```

Result: 9 passed, 1 upstream FastAPI/httpx deprecation warning.


## Mobile Layout Guardrails

Added and verified narrow-screen CSS protections for the first release:

- `@media (max-width: 420px)` rules for both the detail view and the homepage leaderboard.
- Homepage leaderboard rows switch from a compressed three-column layout to a safer two-row mobile layout.
- Detail-page comment vote controls move onto their own full-width row on very narrow screens.
- Long review/comment strings use `overflow-wrap: anywhere` so raw public review text cannot force horizontal overflow.
- Regression coverage lives in `test_frontend_has_mobile_overflow_guards`.

Verification command:

```powershell
python -m pytest tests/test_frontend_api_wiring.py tests/test_server_api.py tests/test_batch_review_scoring.py::test_leaderboards_filter_obvious_author_and_admin_noise
```

Result: 9 passed, 1 upstream FastAPI/httpx deprecation warning.


## Error And Empty States

Added and verified release-copy guardrails for user-facing failure states:

- Search no-result copy now names the current 2025 public official-review coverage instead of giving generic OpenReview-only advice.
- API-unavailable copy tells users static leaderboards are still available.
- Scorecard 404 now distinguishes `paper_not_found` from `scorecard_not_ready` at the API layer.
- Frontend reads the 404 detail payload with `safeJson(response)` and does not enqueue scoring jobs for papers outside current coverage.
- Topbar/landing unavailable messages no longer use stale `ICLR 2022-2025 sample papers` or generic `Paper is not indexed yet` copy.

Real-DB smoke:

| Path | Status | Detail code |
| --- | ---: | --- |
| `/api/papers/not-a-real-paper/scorecard` | 404 | `paper_not_found` |
| `/api/papers/not-a-real-paper/scoring-jobs` | 404 | `paper_not_found` |

Verification command:

```powershell
python -m pytest tests/test_frontend_api_wiring.py tests/test_server_api.py tests/test_batch_review_scoring.py::test_leaderboards_filter_obvious_author_and_admin_noise
```

Result: 10 passed, 1 upstream FastAPI/httpx deprecation warning.


## Release Gate Refresh

Gate refresh run after frontend/API, mobile, error-state, and data-minimization fixes.

### Data Minimization

Command:

```powershell
python -m secondopinion.tools.openreview_data_minimization_audit --include-database --raw-root data/raw/openreview --fail-on-raw --out data/validation/openreview_data_minimization_audit_strict.json --markdown reports/validation/openreview_data_minimization_audit_strict.md
```

Result:

- status: `passed`
- database_status: `ok`
- raw_status: `ok`
- raw_total_gb: `0.0`
- normalized_failed_count: `0`
- batch_failed_count: `0`

### Static Home Consistency

- `frontend/data/home_2025.json`: 51.8 KiB
- stats: 26,749 papers / 128,723 reviews-comments / 99,671 scored official reviews
- leaderboards: overall=20, toxic=20, helpful=20, red=20, black=20
- noise phrase hits in release boards: 0

### Real-DB API Smoke

| Path | Status | Time | Notes |
| --- | ---: | ---: | --- |
| `/api/home?year=2025&limit=12` | 200 | 0.035s | `source=static_home_2025` |
| `/api/papers?query=CrossSpectra&year=2025&limit=3` | 200 | 0.290s | global search |
| `/api/papers/Ni4jNyroJZ/scorecard` | 200 | 0.019s | detail scorecard |

### Test Gate

Command:

```powershell
python -m pytest tests/test_frontend_api_wiring.py tests/test_server_api.py tests/test_batch_review_scoring.py::test_new_leaderboards_read_batch_dimensions tests/test_batch_review_scoring.py::test_leaderboards_filter_obvious_author_and_admin_noise tests/test_openreview_data_minimization_audit.py tests/test_openreview_raw_cleanup.py tests/test_openreview_pull_snapshot_id.py tests/test_openreview_ingestion_plan_resume.py
```

Result: 25 passed, 1 upstream FastAPI/httpx deprecation warning.

Syntax check:

```powershell
python -m compileall -q src/secondopinion tests
```

Result: passed.


## Browser Deep-Link And Mobile Visual QA

Local services:

- API: `http://127.0.0.1:8765`
- Static frontend: `http://127.0.0.1:8766`
- API override: `?api=http://127.0.0.1:8765`

### Findings Fixed

- Cross-origin local/staging API override failed because frontend always used `credentials: include`; now `apiFetch` uses credentials only for same-origin API bases and `omit` for cross-origin QA/staging bases.
- Direct deep-link detail pages loaded the scorecard but did not refresh paper stats because `renderAll()` did not call `renderPaperInfo()`; now stats reflect actual rendered reviewer/comment counts.
- Mobile detail view had page-level horizontal overflow at 390px due max-content grid sizing; `content-stack`, score containers, reviewer grid, and long paper titles now have explicit min/max width guards.

### Browser Checks

Desktop detail deep link:

- URL: `/index.html?api=http://127.0.0.1:8765&paper=Ni4jNyroJZ`
- body class: `is-resolved`
- paper title rendered: yes
- paper stats: `4 reviewers / 4 comments / ICLR 2025`
- empty Themes state rendered for `topics=0`
- console errors/warnings: none
- page-level horizontal overflow: false

Mobile detail, 390x844 viewport:

- body class: `is-resolved`
- reviewer cards: 4
- comments: 4
- paper stats: `4 reviewers / 4 comments / ICLR 2025`
- console errors/warnings: none
- page-level horizontal overflow: false

Mobile homepage, 390x844 viewport:

- body class: `is-idle`
- board rows: 8
- board tabs: 3
- 2025 coverage copy rendered: yes
- console errors/warnings: none
- page-level horizontal overflow: false

Verification command:

```powershell
python -m pytest tests/test_frontend_api_wiring.py tests/test_server_api.py tests/test_batch_review_scoring.py::test_leaderboards_filter_obvious_author_and_admin_noise
```

Result: 10 passed, 1 upstream FastAPI/httpx deprecation warning.


## Deployment Configuration Check

Deployment-oriented checks added after local browser QA:

- GitHub Pages workflow uploads the full `frontend/` directory, so `frontend/data/home_2025.json` is included in the static artifact.
- API home snapshot path is now configurable with `SECONDOPINION_HOME_SNAPSHOT`; default remains `frontend/data/home_2025.json`.
- `.env.example` documents `SECONDOPINION_HOME_SNAPSHOT=frontend/data/home_2025.json`.
- Added `docs/release_checklist_2025_v1.md` as the canonical 2025 V1 release checklist.
- Left legacy README untouched because it contains historical mojibake/old MVP content and should be replaced in a separate documentation cleanup.

Smoke:

```text
GET /api/home?year=2025&limit=2 -> 200 source=static_home_2025 latest_papers=2
```

Verification command:

```powershell
python -m pytest tests/test_server_api.py tests/test_frontend_api_wiring.py tests/test_batch_review_scoring.py::test_leaderboards_filter_obvious_author_and_admin_noise
```

Result: 10 passed, 1 upstream FastAPI/httpx deprecation warning.


## Release Smoke Tool

Added reusable deployed-domain smoke tooling:

```powershell
python -m secondopinion.tools.release_smoke --frontend-url https://<pages-domain>/ --api-url https://secondopinion.smartselling.work --out data/validation/release_smoke_2025.json --markdown reports/validation/release_smoke_2025.md
```

The smoke checks:

- frontend HTTP 200
- 2025 V1 coverage copy present
- frontend default API points at production API
- API `/health`
- `/api/home?year=2025&limit=12` serves `source=static_home_2025` and expected 2025 counts
- global search returns results
- reference scorecard returns reviewers and comments

Unit coverage: `tests/test_release_smoke.py`.


### Release Smoke Tool Verification

Implemented `secondopinion.tools.release_smoke` for deployed-domain release validation.

Command after deployment:

```powershell
python -m secondopinion.tools.release_smoke --frontend-url https://<pages-domain>/ --api-url https://secondopinion.smartselling.work --out data/validation/release_smoke_2025.json --markdown reports/validation/release_smoke_2025.md
```

Validated locally with fake HTTP responses and the existing product gate:

```powershell
python -m pytest tests/test_release_smoke.py tests/test_frontend_api_wiring.py tests/test_server_api.py tests/test_batch_review_scoring.py::test_leaderboards_filter_obvious_author_and_admin_noise
python -m compileall -q src/secondopinion tests
```

Result: 12 passed, 1 upstream FastAPI/httpx deprecation warning; compileall passed.


### Local HTTP Release Smoke Run

Ran the release smoke tool against real local HTTP services:

```powershell
python -m secondopinion.tools.release_smoke --frontend-url "http://127.0.0.1:8766/index.html?api=http%3A%2F%2F127.0.0.1%3A8765" --api-url http://127.0.0.1:8765 --out data/validation/release_smoke_local_2025.json --markdown reports/validation/release_smoke_local_2025.md
```

Result: `passed`, 9 checks, 0 failures.

Artifacts:

- `data/validation/release_smoke_local_2025.json`
- `reports/validation/release_smoke_local_2025.md`

Key timings:

- frontend status: 125ms
- API health: 12ms
- static home: 6ms
- global search: 219ms
- reference scorecard: 11ms


### Production-Domain Release Smoke Run

Ran the release smoke tool against the expected production URLs:

```powershell
python -m secondopinion.tools.release_smoke --frontend-url https://yongwen12.github.io/SecondOpinion/ --api-url https://secondopinion.smartselling.work --out data/validation/release_smoke_prod_2025.json --markdown reports/validation/release_smoke_prod_2025.md
```

Result: `failed`, 9 checks, 6 failures.

Artifacts:

- `data/validation/release_smoke_prod_2025.json`
- `reports/validation/release_smoke_prod_2025.md`

Passing production checks:

- frontend HTTP 200
- frontend default API base points at `https://secondopinion.smartselling.work`
- API `/health` HTTP 200

Failing production checks:

- frontend does not yet contain the 2025 V1 coverage copy
- `/api/home?year=2025&limit=12` does not return `source=static_home_2025`
- production home stats do not match the 2025 V1 release counts
- production home leaderboards do not yet include the expected publishable rows
- global search returns 0 items for the reference query
- reference scorecard `Ni4jNyroJZ` returns 0 reviewers and 0 comments

Interpretation: the current production domain is reachable, but it has not yet been updated with the 2025 V1 frontend, static home snapshot, API changes, and scored dataset. The release remains pending production deployment and a passing production-domain smoke run.

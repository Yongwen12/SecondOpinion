# SecondOpinion 2025 V1 Release Checklist

Date: 2026-07-09

## Release Scope

This release publishes the first productized 2025 public-review dataset.

Included venues:

- ICLR 2025
- ICML 2025
- NeurIPS 2025
- TMLR 2025
- COLM 2025
- MIDL 2025

Current public counts:

- Papers: 26,749
- Reviews/comments in database: 128,723
- Scored official reviews: 99,671

Public product scope:

- Use title, abstract, decision, public official reviews, and scoring results.
- Do not expose PDF full text, raw OpenReview snapshots, author rebuttals, admin comments, private reviewer identities, scoring internals, or model prompts.
- Historical raw OpenReview API pages are archived under `data/archive/` and are not needed for the public product path.

## Frontend Deployment

GitHub Pages deploys the complete `frontend/` directory through `.github/workflows/deploy-pages.yml`.

Required static release assets:

- `frontend/index.html`
- `frontend/data/home_2025.json`

`frontend/data/home_2025.json` is intentionally small enough for static first paint: about 51.8 KiB.

The frontend connects to the production API by default:

```text
https://secondopinion.smartselling.work
```

For staging/local QA, override the API base with:

```text
?api=https://<api-domain>
```

The frontend uses credentials only for same-origin API bases. Cross-origin staging/local API overrides use `credentials=omit`, so CORS with explicit allowed origins is enough.

## API Deployment

Required API environment:

```text
SECONDOPINION_DATABASE_URL=sqlite:///data/server/secondopinion.db
SECONDOPINION_HOME_SNAPSHOT=frontend/data/home_2025.json
SECONDOPINION_CORS_ORIGINS=https://<pages-domain>
SECONDOPINION_ENABLE_LLM_SCORER=0
```

`SECONDOPINION_HOME_SNAPSHOT` may be an absolute path in production if the API working directory differs from the repo root.

The global homepage endpoint should serve the static release snapshot:

```text
GET /api/home?year=2025&limit=12
```

Expected response properties:

- `source=static_home_2025`
- 12 `latest_papers`
- 20 rows each for `overall`, `toxic`, `helpful`, `red`, and `black`

Conference-scoped home endpoints remain dynamic for compatibility:

```text
GET /api/home?conference=ICLR&year=2025
```

## Release Gates

Run strict data minimization:

```powershell
python -m secondopinion.tools.openreview_data_minimization_audit --include-database --raw-root data/raw/openreview --fail-on-raw --out data/validation/openreview_data_minimization_audit_strict.json --markdown reports/validation/openreview_data_minimization_audit_strict.md
```

Expected:

- `status=passed`
- `database_status=ok`
- `raw_status=ok`
- `raw_total_gb=0.0`

Run core product tests:

```powershell
python -m pytest tests/test_frontend_api_wiring.py tests/test_server_api.py tests/test_batch_review_scoring.py::test_new_leaderboards_read_batch_dimensions tests/test_batch_review_scoring.py::test_leaderboards_filter_obvious_author_and_admin_noise tests/test_openreview_data_minimization_audit.py tests/test_openreview_raw_cleanup.py tests/test_openreview_pull_snapshot_id.py tests/test_openreview_ingestion_plan_resume.py
```

Run syntax check:

```powershell
python -m compileall -q src/secondopinion tests
```

Run deployed-domain release smoke after deployment:

```powershell
python -m secondopinion.tools.release_smoke --frontend-url https://<pages-domain>/ --api-url https://secondopinion.smartselling.work --out data/validation/release_smoke_2025.json --markdown reports/validation/release_smoke_2025.md
```

Expected:

- `status=passed`
- frontend coverage copy present
- `/health` ok
- `/api/home?year=2025&limit=12` returns `source=static_home_2025`
- global search returns at least one result
- reference scorecard `Ni4jNyroJZ` returns reviewers and comments

Run real-DB API smoke:

```powershell
python - <<'PY'
from pathlib import Path
from time import perf_counter
from fastapi.testclient import TestClient
from secondopinion.server.api import create_app
from secondopinion.server.config import ServerSettings
from secondopinion.server.database import make_engine, make_session_factory
settings = ServerSettings(
    database_url='sqlite:///data/server/secondopinion.db',
    artifact_root=Path('data/server/artifacts'),
    scoring_memory_path=Path('data/server/memory.jsonl'),
    home_snapshot_path=Path('frontend/data/home_2025.json'),
)
client = TestClient(create_app(settings=settings, session_factory=make_session_factory(make_engine(settings.database_url))))
for label, path, params in [
    ('home', '/api/home', {'year': 2025, 'limit': 12}),
    ('search', '/api/papers', {'query': 'CrossSpectra', 'year': 2025, 'limit': 3}),
    ('scorecard', '/api/papers/Ni4jNyroJZ/scorecard', {}),
]:
    start = perf_counter()
    response = client.get(path, params=params)
    print(label, response.status_code, f'{perf_counter() - start:.3f}s')
PY
```

Expected current timings are approximately:

- home: 0.02-0.04s
- global search: about 0.3s
- scorecard: about 0.02s

## Browser QA Evidence

Latest local browser QA is recorded in:

- `reports/validation/frontend_api_release_qa_2025.md`

Covered browser checks:

- desktop detail deep link
- mobile detail view at 390x844
- mobile homepage at 390x844
- no page-level horizontal overflow
- no console errors/warnings
- current 2025 coverage copy visible
- detail stats match rendered reviewer/comment counts

## Known Follow-Ups

These are not blockers for the 2025 V1 release, but should be addressed soon:

- Replace the old mojibake README with a concise product README.
- Add automated browser screenshots in CI if a browser runner becomes available.
- Decide whether to keep legacy `frontend/app.js` and `frontend/demos/` in the Pages artifact or move old demo surfaces under a separate archive path.
- Run final production-domain smoke after deployment.

## Production Deployment Runbook

Current production check on 2026-07-09:

- API domain is reachable: `https://secondopinion.smartselling.work`
- Frontend domain is reachable: `https://yongwen12.github.io/SecondOpinion/`
- Production API code is still old: `/opt/secondopinion` at `6e77255`
- Production environment currently has no `SECONDOPINION_HOME_SNAPSHOT`
- Production Postgres still contains the old small dataset: about 4,001 papers, 15,340 reviews, and 401 scorecards
- Local V1 SQLite contains 26,749 papers, 128,723 reviews/comments, 25,214 scorecards, and 99,671 reviewer scores

Deploy order:

1. Commit and push the V1 frontend/API/static-data changes to `main`.
2. Wait for GitHub Pages to deploy `frontend/`, including `frontend/data/home_2025.json`.
3. Create a fresh production backup before replacing data:

```bash
mkdir -p /srv/secondopinion/backups
pg_dump -Fc -d secondopinion -f /srv/secondopinion/backups/secondopinion-pre-2025-v1-$(date -u +%Y%m%dT%H%M%SZ).dump
cp /etc/secondopinion/secondopinion.env /srv/secondopinion/backups/secondopinion-env-pre-2025-v1-$(date -u +%Y%m%dT%H%M%SZ).env
```

4. Copy the local V1 SQLite database to the server, for example:

```powershell
scp data/server/secondopinion.db root@47.253.217.98:/srv/secondopinion/secondopinion-v1-2025.db
```

5. Update production code:

```bash
cd /opt/secondopinion
git fetch origin main
git checkout main
git pull --ff-only origin main
```

6. Install/update package dependencies if the service virtualenv is not editable against `/opt/secondopinion`.

7. Add the home snapshot path to `/etc/secondopinion/secondopinion.env`:

```text
SECONDOPINION_HOME_SNAPSHOT=/opt/secondopinion/frontend/data/home_2025.json
```

8. Replace production Postgres from the V1 SQLite snapshot:

```bash
cd /opt/secondopinion
sudo -u secondopinion python scripts/migrate_sqlite_to_postgres.py --sqlite-url sqlite:////srv/secondopinion/secondopinion-v1-2025.db --postgres-url postgresql+psycopg:///secondopinion --replace --batch-size 1000
```

Expected final target counts:

- `papers: 26749`
- `reviews: 128723`
- `scorecards: 25214`
- `reviewer_scores: 99671`

9. Restart API:

```bash
systemctl restart secondopinion-api
systemctl status secondopinion-api --no-pager
```

The worker can remain disabled for this release because V1 uses precomputed scorecards and `SECONDOPINION_ENABLE_LLM_SCORER=0`.

10. Run production smoke from the local workstation:

```powershell
python -m secondopinion.tools.release_smoke --frontend-url https://yongwen12.github.io/SecondOpinion/ --api-url https://secondopinion.smartselling.work --out data/validation/release_smoke_prod_2025.json --markdown reports/validation/release_smoke_prod_2025.md
```

Release can be considered production-ready only after this production-domain smoke returns `status=passed`.

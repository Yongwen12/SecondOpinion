# SecondOpinion Server API Rollout v0.1

Date: 2026-06-21

This document records the first server-backed version of SecondOpinion. The frontend still consumes only public scorecard JSON; raw OpenReview snapshots, normalized datasets, scoring memory, hybrid scores, and retrieval internals remain server-side.

## Architecture

```text
GitHub Pages frontend
  -> FastAPI API
  -> PostgreSQL / SQLite
  -> DB-backed scoring_jobs queue
  -> worker
  -> external scoring memory JSONL
  -> public reviewer scorecard JSON
```

## Core API

```text
GET  /health
GET  /api/conferences
GET  /api/conferences/{conference_id}/papers?query=&year=&cursor=&limit=
GET  /api/papers/{paper_id}
GET  /api/papers/{paper_id}/scorecard
POST /api/papers/{paper_id}/scoring-jobs
GET  /api/scoring-jobs/{job_id}
POST /api/papers/{paper_id}/reviewers/{reviewer_key}/votes
GET  /api/leaderboards?conference=ICLR&year=2025
```

Public scorecard responses use `reviewer-public-scorecard-v0.1` and must not expose `hybrid_scores`, `memory_prior`, `mapped_score`, raw reviewer identity, or retrieved examples.

## Local Smoke

```bash
python -m pip install -e .
python -m secondopinion server-init-db
python -m secondopinion server-ingest-normalized \
  data/normalized/iclr_2022_sample_1000.json \
  data/normalized/iclr_2023_sample_1000.json \
  data/normalized/iclr_2024_sample_1000.json \
  data/normalized/iclr_2025_sample_1000.json
python -m secondopinion server-import-demo-scorecard
python -m secondopinion server-register-memory-index
uvicorn secondopinion.server.api:app --host 0.0.0.0 --port 8000
python -m secondopinion server-run-worker
```

Frontend API wiring is opt-in so GitHub Pages keeps working without a server:

```text
https://<pages-url>/?api=https://<api-domain>
```

If the API is unreachable, the frontend falls back to `frontend/demos/reviewer_public_scorecard_v0.1.json`.

## Docker Compose

```bash
docker compose up -d db
docker compose --profile bootstrap up bootstrap
docker compose up -d api worker
```

Expected data mount:

```text
./data -> /srv/secondopinion/data:ro
```

Expected writable artifact mount:

```text
secondopinion-artifacts -> /srv/secondopinion/artifacts
```

Production should set:

```text
SECONDOPINION_DATABASE_URL=postgresql+psycopg://...
SECONDOPINION_CORS_ORIGINS=https://yongwen12.github.io
SECONDOPINION_SCORING_MEMORY=/srv/secondopinion/data/normalized/scoring_memory_external_full_lite_v0.1.jsonl
SECONDOPINION_SERVER_ARTIFACT_ROOT=/srv/secondopinion/artifacts
```

## Current Limits

- The v0.1 worker defaults to a local heuristic score provider plus external scoring memory, so the server path is operational without LLM calls. Set `SECONDOPINION_ENABLE_LLM_SCORER=1` and `SECONDOPINION_SCORER_MODEL=gpt-5-nano` to use the optional structured LLM scorer; failures fall back to the local provider.
- The queue is database-backed polling; Redis/Celery is intentionally deferred.
- The first rollout imports normalized ICLR samples and uses raw snapshots as server-side artifacts only.

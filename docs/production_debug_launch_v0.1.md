# SecondOpinion Production Debug Launch v0.1

Date: 2026-06-21

This runbook records the current production-debug deployment of SecondOpinion on the smartselling server. The deployment is intentionally isolated so it can be moved to a dedicated server later.

## Runtime Shape

- Public API: `https://secondopinion.smartselling.work`
- Local bind: `127.0.0.1:18280`
- Runtime user: `secondopinion`
- Code: `/opt/secondopinion`
- Data and artifacts: `/srv/secondopinion`
- Environment: `/etc/secondopinion/secondopinion.env`
- API service: `secondopinion-api`
- Worker service: `secondopinion-worker`
- Backup timer: `secondopinion-backup.timer`

The frontend should connect with:

```text
https://yongwen12.github.io/SecondOpinion/?api=https://secondopinion.smartselling.work
```

## Production Defaults

- Database: SQLite at `/srv/secondopinion/secondopinion.db`
- LLM scorer: disabled with `SECONDOPINION_ENABLE_LLM_SCORER=0`
- Scoring memory: `/srv/secondopinion/data/normalized/scoring_memory_external_full_lite_v0.1.jsonl`
- CORS origin: `https://yongwen12.github.io`
- Scoring mode: on-demand jobs, not full pre-scoring

## Verification Commands

```bash
curl -sS https://secondopinion.smartselling.work/health
curl -sS https://secondopinion.smartselling.work/api/conferences
curl -sS "https://secondopinion.smartselling.work/api/conferences/ICLR/papers?year=2025&query=baseline&limit=3"
systemctl status secondopinion-api
systemctl status secondopinion-worker
journalctl -u secondopinion-api -n 100 --no-pager
journalctl -u secondopinion-worker -n 100 --no-pager
systemctl list-timers secondopinion-backup.timer --no-pager
```

## Backup And Migration

Daily backups are generated under:

```text
/srv/secondopinion/backups/
```

Each backup includes the SQLite database, artifacts, and the server env file. Backups are retained for 14 days.

To migrate this deployment, copy:

```text
/opt/secondopinion
/srv/secondopinion
/etc/secondopinion
/etc/systemd/system/secondopinion-api.service
/etc/systemd/system/secondopinion-worker.service
/etc/systemd/system/secondopinion-backup.service
/etc/systemd/system/secondopinion-backup.timer
/etc/nginx/sites-available/secondopinion.conf
```

Then restore the DNS record for `secondopinion.smartselling.work` or point a new API domain at the target server.

## Launch Smoke Result

The production-debug launch was validated with three real ICLR 2025 papers:

- `P8FS9byr1c`
- `QqziJAdev9`
- `q6CM6UdP3K`

All three scoring jobs completed successfully, wrote public scorecards, and passed the public contract check: no `hybrid_scores`, `memory_prior`, `mapped_score`, retrieved examples, or raw reviewer identity appeared in public responses.
## Batch Scoring Operations

Use these commands to expand from demo papers to the full imported ICLR corpus without blocking the frontend.

```bash
python -m secondopinion server-scoring-status --conference ICLR --year 2025
python -m secondopinion server-enqueue-scoring --conference ICLR --year 2025 --limit 10 --dry-run
python -m secondopinion server-enqueue-scoring --conference ICLR --year 2025 --limit 10
python -m secondopinion server-retry-failed-scoring --conference ICLR --year 2025 --limit 20
```

Recommended rollout order:

```text
ICLR 2025: 10 -> 100 -> 1000
ICLR 2024: 100 -> 1000
ICLR 2023: 100 -> 1000
ICLR 2022: 100 -> 1000
```

The enqueue command defaults to missing-only behavior. Papers that already have a scorecard for the active scorer and memory index are skipped, and queued/running jobs are not duplicated.

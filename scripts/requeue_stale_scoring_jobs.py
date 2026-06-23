from __future__ import annotations

import argparse
import datetime as dt
import os

from sqlalchemy import select

from secondopinion.server.database import make_engine, make_session_factory
from secondopinion.server.models import ScoringJob, utcnow


def main() -> None:
    parser = argparse.ArgumentParser(description="Requeue stale SecondOpinion scoring jobs.")
    parser.add_argument("--database-url", default=os.environ.get("SECONDOPINION_DATABASE_URL", ""))
    parser.add_argument("--older-than-minutes", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("--database-url or SECONDOPINION_DATABASE_URL is required")

    cutoff = utcnow() - dt.timedelta(minutes=args.older_than_minutes)
    engine = make_engine(args.database_url)
    factory = make_session_factory(engine)
    with factory() as session:
        jobs = list(
            session.execute(
                select(ScoringJob)
                .where(ScoringJob.status == "running", ScoringJob.updated_at < cutoff)
                .order_by(ScoringJob.updated_at.asc())
            ).scalars()
        )
        print(f"stale_running: {len(jobs)}")
        for job in jobs:
            print(f"{job.job_id} {job.paper_id} updated_at={job.updated_at}")
            if not args.dry_run:
                job.status = "queued"
                job.error = ""
                job.completed_at = None
                job.updated_at = utcnow()
        if not args.dry_run:
            session.commit()


if __name__ == "__main__":
    main()

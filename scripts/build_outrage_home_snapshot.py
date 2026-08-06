from __future__ import annotations

import argparse
import json
from pathlib import Path

from secondopinion.server.database import make_engine, make_session_factory
from secondopinion.server.repository import build_outrage_leaderboards


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the static outrage-community home boards.")
    parser.add_argument(
        "--database-url",
        default="sqlite:///data/server/secondopinion.db",
        help="SQLAlchemy database URL used as the leaderboard source.",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=Path("frontend/data/home_2025.json"),
        help="Existing home snapshot to update.",
    )
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--limit", type=int, default=12)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.snapshot.exists():
        raise SystemExit(f"Home snapshot does not exist: {args.snapshot}")

    payload = json.loads(args.snapshot.read_text(encoding="utf-8"))
    engine = make_engine(args.database_url)
    factory = make_session_factory(engine)
    try:
        with factory() as session:
            boards = build_outrage_leaderboards(
                session,
                year=args.year,
                limit=max(1, min(50, args.limit)),
            )
    finally:
        engine.dispose()

    payload["leaderboards"] = boards
    payload.pop("source", None)
    args.snapshot.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(
        "Updated",
        args.snapshot,
        {name: len(rows) for name, rows in boards.items()},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

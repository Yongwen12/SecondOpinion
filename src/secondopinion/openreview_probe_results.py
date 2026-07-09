from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
from pathlib import Path
from typing import Any


PROBE_RESULTS_SCHEMA_VERSION = "openreview-probe-results-v0.1"
OPEN_STATUSES = {"success"}
AUTH_STATUSES = {"challenge_required", "auth_required"}
DEFAULT_MIN_REVIEW_COVERAGE = 0.5


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: str | Path, text: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


def discover_probe_paths(patterns: list[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        paths.extend(Path(path) for path in glob.glob(pattern, recursive=True))
    return sorted(set(paths))


def resolve_probe_results(
    *,
    patterns: list[str],
    queue: dict[str, Any] | None = None,
    min_review_coverage: float = DEFAULT_MIN_REVIEW_COVERAGE,
) -> dict[str, Any]:
    records = [probe_record(path) for path in discover_probe_paths(patterns)]
    by_venue: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_venue.setdefault(record["venue_id"], []).append(record)
    queued_by_venue = queued_candidates_by_venue(queue or {})
    venue_rows = []
    all_venues = sorted(set(by_venue) | set(queued_by_venue))
    for venue_id in all_venues:
        venue_rows.append(
            resolve_venue(
                venue_id,
                by_venue.get(venue_id, []),
                queued_by_venue.get(venue_id, []),
                min_review_coverage=min_review_coverage,
            )
        )
    status_counts: dict[str, int] = {}
    for row in venue_rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
    return {
        "schema_version": PROBE_RESULTS_SCHEMA_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "summary": {
            "probe_result_count": len(records),
            "venue_count": len(venue_rows),
            "status_counts": dict(sorted(status_counts.items())),
            "selected_for_scoring": [row["venue_id"] for row in venue_rows if row["status"] == "selected_public_reviews"],
            "blocked_auth": [row["venue_id"] for row in venue_rows if row["status"] == "blocked_auth"],
            "missing_results": [row["venue_id"] for row in venue_rows if row["status"] == "missing_probe_results"],
            "no_public_reviews": [row["venue_id"] for row in venue_rows if row["status"] == "no_public_reviews"],
            "needs_larger_probe": [row["venue_id"] for row in venue_rows if row["status"] == "needs_larger_probe"],
        },
        "venues": venue_rows,
    }


def probe_record(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    stats = payload.get("sample_stats") or {}
    return {
        "path": str(path),
        "venue_id": str(payload.get("venue_id") or "").upper(),
        "invitation": str(payload.get("invitation") or ""),
        "status": str(payload.get("status") or "unknown"),
        "recommendation": str(payload.get("recommendation") or ""),
        "paper_count": int(stats.get("paper_count") or 0),
        "review_count": int(stats.get("review_count") or 0),
        "review_coverage_rate": float(stats.get("review_coverage_rate") or 0.0),
        "mean_reviews_per_paper": float(stats.get("mean_reviews_per_paper") or 0.0),
    }


def queued_candidates_by_venue(queue: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for item in queue.get("items", []) if isinstance(queue, dict) else []:
        venue_id = str(item.get("venue_id") or "").upper()
        if venue_id:
            result.setdefault(venue_id, []).append(dict(item))
    return result


def resolve_venue(
    venue_id: str,
    records: list[dict[str, Any]],
    queued: list[dict[str, Any]],
    *,
    min_review_coverage: float = DEFAULT_MIN_REVIEW_COVERAGE,
) -> dict[str, Any]:
    records = sorted(records, key=lambda item: (-item["review_count"], -item["review_coverage_rate"], item["invitation"]))
    candidates_with_reviews = [record for record in records if record["status"] == "success" and record["review_count"] > 0]
    if candidates_with_reviews:
        selected = candidates_with_reviews[0]
        if float(selected.get("review_coverage_rate") or 0.0) >= min_review_coverage:
            status = "selected_public_reviews"
            recommendation = "use_selected_invitation_for_pull_and_score"
        else:
            status = "needs_larger_probe"
            recommendation = "rerun_candidate_with_larger_sample_before_full_pull"
    elif records and all(record["status"] in AUTH_STATUSES for record in records):
        selected = None
        status = "blocked_auth"
        recommendation = "rerun_probe_after_browser_cookie"
    elif records and any(record["status"] == "success" for record in records):
        selected = None
        status = "no_public_reviews"
        recommendation = "skip_or_inspect_larger_sample"
    elif records:
        selected = None
        status = "needs_manual_inspection"
        recommendation = "inspect_probe_errors_or_try_remaining_candidates"
    else:
        selected = None
        status = "missing_probe_results"
        recommendation = "run_probe_queue_commands"
    return {
        "venue_id": venue_id,
        "status": status,
        "recommendation": recommendation,
        "selected_invitation": selected["invitation"] if selected else "",
        "selected_probe_path": selected["path"] if selected else "",
        "min_review_coverage": min_review_coverage,
        "selected_review_coverage_rate": float(selected.get("review_coverage_rate") or 0.0) if selected else 0.0,
        "queued_candidate_count": len(queued),
        "probe_result_count": len(records),
        "candidates": records,
    }


def render_probe_results_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# OpenReview Probe Results",
        "",
        f"- Created: `{report.get('created_at', '')}`",
        f"- Probe results: `{summary.get('probe_result_count', 0)}`",
        f"- Venues: `{summary.get('venue_count', 0)}`",
        f"- Selected for scoring: `{', '.join(summary.get('selected_for_scoring') or []) or '-'}`",
        f"- Blocked auth: `{', '.join(summary.get('blocked_auth') or []) or '-'}`",
        f"- Missing results: `{', '.join(summary.get('missing_results') or []) or '-'}`",
        f"- Needs larger probe: `{', '.join(summary.get('needs_larger_probe') or []) or '-'}`",
        "",
        "## Venues",
        "",
        "| Venue | Status | Selected invitation | Coverage | Probe results | Queued candidates | Recommendation |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in report.get("venues", []):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("venue_id", "")),
                    str(row.get("status", "")),
                    f"`{row.get('selected_invitation', '')}`",
                    str(row.get("selected_review_coverage_rate", 0.0)),
                    str(row.get("probe_result_count", 0)),
                    str(row.get("queued_candidate_count", 0)),
                    str(row.get("recommendation", "")),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resolve OpenReview invitation probe results into selected venue candidates.")
    parser.add_argument("--probe", action="append", default=[], help="Probe result JSON glob. Repeatable.")
    parser.add_argument("--queue", default="data/validation/openreview_probe_queue_2025.json")
    parser.add_argument("--min-review-coverage", type=float, default=DEFAULT_MIN_REVIEW_COVERAGE)
    parser.add_argument("--out", default="data/validation/openreview_probe_results_2025.json")
    parser.add_argument("--markdown", default="reports/validation/openreview_probe_results_2025.md")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    queue = read_json(args.queue) if args.queue and Path(args.queue).exists() else {}
    report = resolve_probe_results(
        patterns=args.probe or ["data/validation/openreview_probe_*_c*_*.json"],
        queue=queue,
        min_review_coverage=args.min_review_coverage,
    )
    write_json(args.out, report)
    write_markdown(args.markdown, render_probe_results_markdown(report))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

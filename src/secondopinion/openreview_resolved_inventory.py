from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from .openreview_venue_inventory import empty_sample_stats


RESOLVED_INVENTORY_SCHEMA_VERSION = "openreview-resolved-inventory-v0.1"


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


def load_venue_specs(path: str | Path) -> list[dict[str, Any]]:
    payload = read_json(path)
    venues = payload.get("venues", []) if isinstance(payload, dict) else payload
    return [dict(item) for item in venues if isinstance(item, dict)]


def build_resolved_inventory(*, venue_specs: list[dict[str, Any]], probe_results: dict[str, Any]) -> dict[str, Any]:
    probe_by_id = {str(row.get("venue_id") or "").upper(): row for row in probe_results.get("venues", [])}
    venues = [resolved_venue(spec, probe_by_id.get(str(spec.get("venue_id") or "").upper())) for spec in venue_specs]
    counts: dict[str, int] = {}
    for venue in venues:
        counts[venue["status"]] = counts.get(venue["status"], 0) + 1
    return {
        "schema_version": RESOLVED_INVENTORY_SCHEMA_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "source_probe_results_created_at": probe_results.get("created_at", ""),
        "summary": {
            "venue_count": len(venues),
            "status_counts": dict(sorted(counts.items())),
            "ready_to_pull_and_score": [venue["venue_id"] for venue in venues if venue["recommendation"] == "pull_and_score"],
            "needs_probe_results": [venue["venue_id"] for venue in venues if venue["status"] == "missing_probe_results"],
            "needs_larger_probe": [venue["venue_id"] for venue in venues if venue["status"] == "needs_larger_probe"],
            "blocked_openreview_auth": [venue["venue_id"] for venue in venues if venue["status"] in {"challenge_required", "auth_required"}],
            "skipped_not_open_review": [venue["venue_id"] for venue in venues if venue["status"].startswith("excluded_")],
        },
        "venues": venues,
    }


def resolved_venue(spec: dict[str, Any], probe_row: dict[str, Any] | None) -> dict[str, Any]:
    venue_id = str(spec.get("venue_id") or "").upper()
    base = {
        "venue_id": venue_id,
        "name": str(spec.get("name") or venue_id),
        "year": int(spec.get("year") or 2025),
        "category": str(spec.get("category") or ""),
        "priority": int(spec.get("priority") or 99),
        "rolling_venue": bool(spec.get("rolling_venue")),
        "year_filter": str(spec.get("year_filter") or ""),
        "scope": str(spec.get("scope") or ""),
        "review_policy": str(spec.get("review_policy") or ""),
        "source_notes": list(spec.get("source_notes") or []),
        "invitation_candidates": list(spec.get("invitation_candidates") or []),
        "review_invitation_counts": {},
    }
    if spec.get("include_in_inventory") is False or str(spec.get("scope_decision") or "").startswith("exclude_"):
        return {
            **base,
            "status": str(spec.get("manual_status") or "excluded_no_public_reviews"),
            "recommendation": str(spec.get("manual_recommendation") or "skip_no_public_reviews"),
            "selected_invitation": "",
            "attempts": [],
            "sample_stats": empty_sample_stats(),
            "notes": [*base["source_notes"], "Excluded from scoring queue: no public OpenReview review corpus is expected for this venue."],
        }
    if not probe_row:
        return unresolved(base, status="missing_probe_results", recommendation="run_probe_queue_commands")
    status = str(probe_row.get("status") or "")
    if status == "selected_public_reviews":
        selected = str(probe_row.get("selected_invitation") or "")
        selected_record = selected_candidate_record(probe_row, selected)
        return {
            **base,
            "status": "open_reviews_available",
            "recommendation": "pull_and_score",
            "selected_invitation": selected,
            "attempts": [{"invitation": selected, "probe_status": "success", "api_note_count": selected_record.get("paper_count", 0)}],
            "sample_stats": sample_stats_from_candidate(selected_record),
            "notes": [*base["source_notes"], "Resolved from candidate-level probe results."],
        }
    if status == "needs_larger_probe":
        selected = str(probe_row.get("selected_invitation") or "")
        selected_record = selected_candidate_record(probe_row, selected)
        return {
            **base,
            "status": "needs_larger_probe",
            "recommendation": "rerun_larger_probe_before_full_pull",
            "selected_invitation": selected,
            "attempts": [{"invitation": selected, "probe_status": "success_low_coverage", "api_note_count": selected_record.get("paper_count", 0)}],
            "sample_stats": sample_stats_from_candidate(selected_record),
            "notes": [*base["source_notes"], "Probe found public reviews, but coverage is below the full-pull threshold."],
        }
    if status == "blocked_auth":
        return unresolved(base, status="challenge_required", recommendation="retry_with_openreview_cookie")
    if status == "no_public_reviews":
        return unresolved(base, status="no_public_reviews", recommendation="skip_scoring")
    if status == "missing_probe_results":
        return unresolved(base, status="missing_probe_results", recommendation="run_probe_queue_commands")
    return unresolved(base, status="needs_manual_inspection", recommendation="inspect_probe_results")


def selected_candidate_record(probe_row: dict[str, Any], selected_invitation: str) -> dict[str, Any]:
    for candidate in probe_row.get("candidates", []):
        if candidate.get("invitation") == selected_invitation:
            return dict(candidate)
    return {}


def sample_stats_from_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    paper_count = int(candidate.get("paper_count") or 0)
    review_count = int(candidate.get("review_count") or 0)
    coverage = float(candidate.get("review_coverage_rate") or 0.0)
    mean_reviews = float(candidate.get("mean_reviews_per_paper") or 0.0)
    return {
        **empty_sample_stats(),
        "paper_count": paper_count,
        "review_count": review_count,
        "papers_with_reviews": round(coverage * paper_count),
        "review_coverage_rate": round(coverage, 4),
        "mean_reviews_per_paper": round(mean_reviews, 3),
    }


def unresolved(base: dict[str, Any], *, status: str, recommendation: str) -> dict[str, Any]:
    return {
        **base,
        "status": status,
        "recommendation": recommendation,
        "selected_invitation": "",
        "attempts": [],
        "sample_stats": empty_sample_stats(),
        "notes": base["source_notes"],
    }


def render_resolved_inventory_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# OpenReview Resolved Inventory",
        "",
        f"- Created: `{report.get('created_at', '')}`",
        f"- Ready to pull and score: `{', '.join(summary.get('ready_to_pull_and_score') or []) or '-'}`",
        f"- Needs probe results: `{', '.join(summary.get('needs_probe_results') or []) or '-'}`",
        f"- Needs larger probe: `{', '.join(summary.get('needs_larger_probe') or []) or '-'}`",
        f"- Blocked auth: `{', '.join(summary.get('blocked_openreview_auth') or []) or '-'}`",
        "",
        "## Venues",
        "",
        "| Venue | Status | Recommendation | Selected invitation | Papers | Reviews |",
        "| --- | --- | --- | --- | ---: | ---: |",
    ]
    for venue in sorted(report.get("venues", []), key=lambda item: (int(item.get("priority") or 99), item.get("venue_id", ""))):
        stats = venue.get("sample_stats") or {}
        lines.append(
            "| "
            + " | ".join(
                [
                    str(venue.get("venue_id", "")),
                    str(venue.get("status", "")),
                    str(venue.get("recommendation", "")),
                    f"`{venue.get('selected_invitation', '')}`",
                    str(stats.get("paper_count", 0)),
                    str(stats.get("review_count", 0)),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build ingestion-ready inventory from venue specs and resolved probe results.")
    parser.add_argument("--venues", default="data/config/openreview_venues_2025.json")
    parser.add_argument("--probe-results", default="data/validation/openreview_probe_results_2025.json")
    parser.add_argument("--out", default="data/validation/openreview_resolved_inventory_2025.json")
    parser.add_argument("--markdown", default="reports/validation/openreview_resolved_inventory_2025.md")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    report = build_resolved_inventory(venue_specs=load_venue_specs(args.venues), probe_results=read_json(args.probe_results))
    write_json(args.out, report)
    write_markdown(args.markdown, render_resolved_inventory_markdown(report))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

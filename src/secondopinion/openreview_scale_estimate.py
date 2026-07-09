from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

SCALE_ESTIMATE_SCHEMA_VERSION = "openreview-scale-estimate-v0.1"
DEFAULT_STORAGE_BYTES_PER_PAPER = 24_000
DEFAULT_STORAGE_BYTES_PER_REVIEW = 8_000
DEFAULT_OUTPUT_TOKENS_PER_REVIEW = 100


def read_json_if_exists(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def included_cost_baseline(batch_cost: dict[str, Any]) -> dict[str, Any]:
    summary = batch_cost.get("summary") or {}
    request_count = int(summary.get("request_count") or 0)
    cost = float(summary.get("estimated_batch_cost_usd") or 0.0)
    input_tokens = int(summary.get("estimated_input_tokens") or 0)
    output_tokens = int(summary.get("estimated_output_tokens") or 0)
    return {
        "source": "batch_cost_review",
        "request_count": request_count,
        "estimated_batch_cost_usd": round(cost, 4),
        "cost_per_review_usd": round(cost / request_count, 6) if request_count else 0.0,
        "input_tokens_per_review": round(input_tokens / request_count, 1) if request_count else 0.0,
        "output_tokens_per_review": round(output_tokens / request_count, 1) if request_count else 0.0,
    }


def target_or_probe_venues(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for venue in inventory.get("venues", []) or []:
        if not isinstance(venue, dict):
            continue
        if venue.get("include_in_inventory") is False or str(venue.get("status") or "").startswith("excluded_"):
            continue
        rows.append(venue)
    return rows


def estimate_venue(
    venue: dict[str, Any],
    *,
    baseline: dict[str, Any],
    assumed_full_paper_count: int | None = None,
    storage_bytes_per_paper: int = DEFAULT_STORAGE_BYTES_PER_PAPER,
    storage_bytes_per_review: int = DEFAULT_STORAGE_BYTES_PER_REVIEW,
) -> dict[str, Any]:
    stats = venue.get("sample_stats") or {}
    sample_papers = int(stats.get("paper_count") or 0)
    sample_reviews = int(stats.get("review_count") or 0)
    mean_reviews = float(stats.get("mean_reviews_per_paper") or 0.0)
    if not assumed_full_paper_count and sample_papers <= 0:
        return {
            "venue_id": str(venue.get("venue_id") or ""),
            "status": str(venue.get("status") or ""),
            "estimate_status": "blocked_missing_inventory_sample",
            "reason": "Inventory probe has no sample paper/review counts yet, usually because OpenReview auth is blocked.",
            "sample_paper_count": sample_papers,
            "sample_review_count": sample_reviews,
        }
    full_papers = int(assumed_full_paper_count or sample_papers)
    reviews = int(round(full_papers * mean_reviews)) if mean_reviews else sample_reviews
    cost = reviews * float(baseline.get("cost_per_review_usd") or 0.0)
    storage_bytes = full_papers * storage_bytes_per_paper + reviews * storage_bytes_per_review
    return {
        "venue_id": str(venue.get("venue_id") or ""),
        "status": str(venue.get("status") or ""),
        "estimate_status": "estimated",
        "sample_paper_count": sample_papers,
        "sample_review_count": sample_reviews,
        "mean_reviews_per_paper": mean_reviews,
        "assumed_full_paper_count": full_papers,
        "estimated_review_count": reviews,
        "estimated_batch_cost_usd": round(cost, 4),
        "estimated_storage_mb": round(storage_bytes / 1_000_000, 2),
    }


def build_openreview_scale_estimate(
    *,
    inventory: dict[str, Any],
    batch_cost: dict[str, Any],
    max_total_cost_usd: float = 25.0,
) -> dict[str, Any]:
    baseline = included_cost_baseline(batch_cost)
    venues = [estimate_venue(venue, baseline=baseline) for venue in target_or_probe_venues(inventory)]
    estimated = [venue for venue in venues if venue.get("estimate_status") == "estimated"]
    total_cost = round(sum(float(venue.get("estimated_batch_cost_usd") or 0.0) for venue in estimated), 4)
    total_reviews = sum(int(venue.get("estimated_review_count") or 0) for venue in estimated)
    total_storage = round(sum(float(venue.get("estimated_storage_mb") or 0.0) for venue in estimated), 2)
    blocked = [venue["venue_id"] for venue in venues if venue.get("estimate_status") != "estimated"]
    status = "blocked_missing_inventory_sample" if blocked or not venues else "ready_for_budget_review"
    if not blocked and total_cost > max_total_cost_usd:
        status = "blocked_cost_limit"
    return {
        "schema_version": SCALE_ESTIMATE_SCHEMA_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "max_total_cost_usd": max_total_cost_usd,
        "baseline": baseline,
        "summary": {
            "venue_count": len(venues),
            "estimated_venue_count": len(estimated),
            "blocked_venue_count": len(blocked),
            "blocked_venues": blocked,
            "estimated_review_count": total_reviews,
            "estimated_batch_cost_usd": total_cost,
            "estimated_storage_mb": total_storage,
        },
        "venues": venues,
    }


def render_openreview_scale_estimate_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    baseline = report.get("baseline") or {}
    lines = [
        "# OpenReview Scale Estimate",
        "",
        f"- Created: `{report.get('created_at', '')}`",
        f"- Status: `{report.get('status', '')}`",
        f"- Baseline requests: `{baseline.get('request_count', 0)}`",
        f"- Baseline cost/review USD: `{float(baseline.get('cost_per_review_usd') or 0):.6f}`",
        f"- Estimated venues: `{summary.get('estimated_venue_count', 0)}` / `{summary.get('venue_count', 0)}`",
        f"- Blocked venues: `{', '.join(summary.get('blocked_venues') or []) or '-'}`",
        f"- Estimated reviews: `{summary.get('estimated_review_count', 0)}`",
        f"- Estimated batch cost USD: `{float(summary.get('estimated_batch_cost_usd') or 0):.4f}`",
        f"- Estimated storage MB: `{float(summary.get('estimated_storage_mb') or 0):.2f}`",
        "",
        "## Venues",
        "",
        "| Venue | Status | Estimate status | Sample papers | Sample reviews | Est. reviews | Est. cost USD | Est. storage MB |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for venue in report.get("venues", []):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(venue.get("venue_id", "")),
                    str(venue.get("status", "")),
                    str(venue.get("estimate_status", "")),
                    str(venue.get("sample_paper_count", 0)),
                    str(venue.get("sample_review_count", 0)),
                    str(venue.get("estimated_review_count", 0)),
                    f"{float(venue.get('estimated_batch_cost_usd') or 0):.4f}",
                    f"{float(venue.get('estimated_storage_mb') or 0):.2f}",
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Estimate OpenReview 2025 full-scale review count, storage, and Batch scoring cost.")
    parser.add_argument("--inventory", default="data/validation/openreview_venue_inventory_2025.json")
    parser.add_argument("--batch-cost", default="data/validation/batch_cost_review.json")
    parser.add_argument("--out", default="data/validation/openreview_scale_estimate.json")
    parser.add_argument("--markdown", default="reports/validation/openreview_scale_estimate.md")
    parser.add_argument("--max-total-cost-usd", type=float, default=25.0)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    report = build_openreview_scale_estimate(
        inventory=read_json_if_exists(args.inventory),
        batch_cost=read_json_if_exists(args.batch_cost),
        max_total_cost_usd=args.max_total_cost_usd,
    )
    write_json(args.out, report)
    write_text(args.markdown, render_openreview_scale_estimate_markdown(report))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

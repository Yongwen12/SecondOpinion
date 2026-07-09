from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


PILOT_READINESS_VERSION = "openreview-pilot-readiness-v0.1"


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def venue_from_plan(plan: dict[str, Any], venue_id: str) -> dict[str, Any] | None:
    target = venue_id.upper()
    for venue in plan.get("venues", []):
        if str(venue.get("venue_id") or "").upper() == target:
            return venue
    return None


def file_state(path: str | Path) -> dict[str, Any]:
    item = Path(path)
    return {"path": str(path), "exists": item.exists(), "bytes": item.stat().st_size if item.exists() else 0}


def build_openreview_pilot_readiness(
    *,
    plan: dict[str, Any],
    venue_id: str,
    min_papers: int = 1,
    min_reviews: int = 1,
    max_empty_core_review_rate: float = 0.05,
) -> dict[str, Any]:
    venue = venue_from_plan(plan, venue_id)
    errors: list[str] = []
    warnings: list[str] = []
    if not venue:
        errors.append(f"venue not found in plan: {venue_id}")
        return readiness_payload(venue_id, None, {}, {}, {}, errors, warnings)

    paths = venue.get("paths") or {}
    normalized_state = file_state(paths.get("normalized", ""))
    quality_state = file_state(paths.get("quality_json", ""))
    batch_state = file_state(paths.get("batch_manifest", ""))

    quality: dict[str, Any] = {}
    batch: dict[str, Any] = {}
    if not normalized_state["exists"]:
        errors.append("missing_normalized_dataset")
    if not quality_state["exists"]:
        errors.append("missing_quality_report")
    else:
        quality = read_json(quality_state["path"])
    if not batch_state["exists"]:
        errors.append("missing_batch_manifest")
    else:
        batch = read_json(batch_state["path"])

    paper_count = int(quality.get("paper_count") or 0)
    review_count = int(quality.get("review_count") or 0)
    empty_rate = float(quality.get("empty_core_review_rate") or 0)
    request_count = int(batch.get("request_count") or 0)
    if quality:
        if paper_count < min_papers:
            errors.append("paper_count_below_minimum")
        if review_count < min_reviews:
            errors.append("review_count_below_minimum")
        if empty_rate > max_empty_core_review_rate:
            errors.append("empty_core_review_rate_too_high")
    if batch and request_count <= 0:
        errors.append("batch_manifest_has_no_requests")
    if venue.get("pull_limit") is None:
        warnings.append("venue plan is full-run, not a limited pilot")

    return readiness_payload(
        venue_id,
        venue,
        {"normalized": normalized_state, "quality": quality_state, "batch_manifest": batch_state},
        quality,
        batch,
        errors,
        warnings,
    )



def full_pull_command(venue_id: str) -> str:
    return (
        "python -m secondopinion.tools.openreview_safe_pipeline "
        "--venues data/config/openreview_venues_2025.json "
        f"--venue {venue_id.upper()} --execute-safe"
    )


def remediation_commands(venue_id: str, errors: list[str]) -> list[str]:
    commands: list[str] = []
    if any(error in errors for error in {"missing_normalized_dataset", "missing_quality_report", "missing_batch_manifest"}):
        commands.append(
            "python -m secondopinion.tools.openreview_safe_pipeline "
            "--venues data/config/openreview_venues_2025.json "
            f"--venue {venue_id.upper()} --pull-limit 50 --execute-safe"
        )
    if "missing_quality_report" in errors and "missing_normalized_dataset" not in errors:
        commands.append(
            "python -m secondopinion.tools.openreview_plan_runner "
            "--plan data/validation/openreview_ingestion_plan_2025.json "
            f"--venue {venue_id.upper()} --stage quality --skip-existing --check-inputs --execute"
        )
    if "missing_batch_manifest" in errors and "missing_normalized_dataset" not in errors:
        commands.append(
            "python -m secondopinion.tools.openreview_plan_runner "
            "--plan data/validation/openreview_ingestion_plan_2025.json "
            f"--venue {venue_id.upper()} --stage build_batch --stage split_batch --skip-existing --check-inputs --execute"
        )
    return list(dict.fromkeys(commands))


def readiness_payload(
    venue_id: str,
    venue: dict[str, Any] | None,
    files: dict[str, Any],
    quality: dict[str, Any],
    batch: dict[str, Any],
    errors: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    status = "ready_for_full_pull" if not errors else "not_ready"
    venue_upper = venue_id.upper()
    return {
        "schema_version": PILOT_READINESS_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "venue_id": venue_upper,
        "recommendation": "run_full_pull" if status == "ready_for_full_pull" else "fix_pilot_outputs",
        "next_commands": [full_pull_command(venue_upper)] if status == "ready_for_full_pull" else [],
        "remediation_commands": remediation_commands(venue_upper, errors) if status != "ready_for_full_pull" else [],
        "dataset_slug": (venue or {}).get("dataset_slug", ""),
        "pull_limit": (venue or {}).get("pull_limit"),
        "files": files,
        "quality_summary": {
            "paper_count": int(quality.get("paper_count") or 0),
            "review_count": int(quality.get("review_count") or 0),
            "empty_core_review_rate": float(quality.get("empty_core_review_rate") or 0),
            "rating_coverage_rate": float(quality.get("rating_coverage_rate") or 0),
            "confidence_coverage_rate": float(quality.get("confidence_coverage_rate") or 0),
        },
        "batch_summary": {
            "request_count": int(batch.get("request_count") or 0),
            "estimated_batch_cost_usd": float(batch.get("estimated_batch_cost_usd") or 0),
            "model": str(batch.get("model") or ""),
        },
        "errors": errors,
        "warnings": warnings,
    }


def render_pilot_readiness_markdown(report: dict[str, Any]) -> str:
    quality = report.get("quality_summary") or {}
    batch = report.get("batch_summary") or {}
    lines = [
        "# OpenReview Pilot Readiness",
        "",
        f"- Created: `{report.get('created_at', '')}`",
        f"- Status: `{report.get('status', '')}`",
        f"- Venue: `{report.get('venue_id', '')}`",
        f"- Dataset: `{report.get('dataset_slug', '')}`",
        f"- Pull limit: `{report.get('pull_limit', None)}`",
        f"- Papers: `{quality.get('paper_count', 0)}`",
        f"- Reviews: `{quality.get('review_count', 0)}`",
        f"- Empty core review rate: `{float(quality.get('empty_core_review_rate') or 0):.2%}`",
        f"- Batch requests: `{batch.get('request_count', 0)}`",
        f"- Estimated batch cost USD: `{float(batch.get('estimated_batch_cost_usd') or 0):.4f}`",
        f"- Recommendation: `{report.get('recommendation', '')}`",
        "",
        "## Next Commands",
        "",
    ]
    if report.get("next_commands"):
        lines.append("```powershell")
        lines.extend(str(command) for command in report.get("next_commands", []))
        lines.append("```")
    else:
        lines.append("- None")
    lines.extend([
        "",
        "## Remediation Commands",
        "",
    ])
    if report.get("remediation_commands"):
        lines.append("```powershell")
        lines.extend(str(command) for command in report.get("remediation_commands", []))
        lines.append("```")
    else:
        lines.append("- None")
    lines.extend([
        "",
        "## Issues",
        "",
    ])
    for error in report.get("errors", []):
        lines.append(f"- ERROR: {error}")
    for warning in report.get("warnings", []):
        lines.append(f"- WARNING: {warning}")
    if not report.get("errors") and not report.get("warnings"):
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check whether a limited OpenReview pilot dataset is ready to promote to full pull.")
    parser.add_argument("--plan", default="data/validation/openreview_ingestion_plan_2025.json")
    parser.add_argument("--venue", default="ICLR")
    parser.add_argument("--out", default="data/validation/openreview_pilot_readiness.json")
    parser.add_argument("--markdown", default="reports/validation/openreview_pilot_readiness.md")
    parser.add_argument("--min-papers", type=int, default=1)
    parser.add_argument("--min-reviews", type=int, default=1)
    parser.add_argument("--max-empty-core-review-rate", type=float, default=0.05)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    report = build_openreview_pilot_readiness(
        plan=read_json(args.plan),
        venue_id=args.venue,
        min_papers=args.min_papers,
        min_reviews=args.min_reviews,
        max_empty_core_review_rate=args.max_empty_core_review_rate,
    )
    write_json(args.out, report)
    write_text(args.markdown, render_pilot_readiness_markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any

from .batch_review_scoring import DEFAULT_BATCH_MODEL


INGESTION_PLAN_SCHEMA_VERSION = "openreview-ingestion-plan-v0.1"

READY_STATUSES = {"open_reviews_available", "partial_public_reviews"}
AUTH_STATUSES = {"challenge_required", "auth_required"}
SKIP_STATUSES = {"excluded_no_public_reviews", "excluded_not_openreview", "excluded_not_openreview_public_reviews"}


def read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def shell_quote(value: str) -> str:
    if not value:
        return '""'
    if all(char.isalnum() or char in "-_./:=\\" for char in value):
        return value
    return '"' + value.replace('"', '\\"') + '"'


def venue_slug(venue_id: str, year: int) -> str:
    return f"{venue_id.lower()}_{year}"


def first_invitation(venue: dict[str, Any]) -> str:
    selected = str(venue.get("selected_invitation") or "")
    if selected:
        return selected
    candidates = venue.get("invitation_candidates") or []
    return str(candidates[0]) if candidates else ""


def readiness_for_venue(venue: dict[str, Any]) -> tuple[str, str]:
    status = str(venue.get("status") or "unknown")
    if status in READY_STATUSES:
        return "ready", ""
    if status in AUTH_STATUSES:
        return "blocked_openreview_auth", "OpenReview challenge/auth required"
    if status in SKIP_STATUSES or status.startswith("excluded_"):
        return "excluded_not_scored", "No public OpenReview review corpus expected"
    return "needs_manual_inspection", f"inventory status is {status}"


def build_command(name: str, command: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": name, "command": command}
    payload.update(extra)
    return payload


def build_venue_plan(
    venue: dict[str, Any],
    *,
    model: str = DEFAULT_BATCH_MODEL,
    page_size: int = 100,
    polite_delay: float = 0.2,
    pull_limit: int | None = None,
    raw_root: str = "data/raw",
    normalized_dir: str = "data/normalized",
    validation_dir: str = "data/validation",
    report_dir: str = "reports/validation",
    batch_dir: str = "data/batch",
    max_estimated_input_tokens: int = 1_600_000,
) -> dict[str, Any]:
    venue_id = str(venue.get("venue_id") or venue.get("name") or "venue").upper()
    year = int(venue.get("year") or 2025)
    slug = venue_slug(venue_id, year)
    invitation = first_invitation(venue)
    readiness, blocked_reason = readiness_for_venue(venue)
    requires_auth = str(venue.get("status")) in AUTH_STATUSES
    rolling_venue = bool(venue.get("rolling_venue"))
    year_filter = str(venue.get("year_filter") or "decision_or_activity_year")

    dataset_slug = f"{slug}_full" if pull_limit is None else f"{slug}_sample{max(0, pull_limit)}"
    normalized_path = f"{normalized_dir}/{dataset_slug}.json"
    raw_normalized_path = f"{normalized_dir}/{dataset_slug}_unfiltered.json" if rolling_venue else normalized_path
    quality_json_path = f"{validation_dir}/{dataset_slug}_quality.json"
    quality_markdown_path = f"{report_dir}/{dataset_slug}_quality.md"
    batch_jsonl_path = f"{batch_dir}/{dataset_slug}_batch.jsonl"
    batch_manifest_path = f"{batch_dir}/{dataset_slug}_batch_manifest.json"
    batch_parts_dir = f"{batch_dir}/{dataset_slug}_parts"
    submission_path = f"{batch_dir}/{dataset_slug}_batch_submission.json"
    status_path = f"{batch_dir}/{dataset_slug}_batch_status.json"
    output_jsonl_path = f"{batch_dir}/{dataset_slug}_batch_output.jsonl"
    error_jsonl_path = f"{batch_dir}/{dataset_slug}_batch_errors.jsonl"

    pull_parts = [
        "python -m secondopinion.tools.openreview_pull",
        "--venue",
        shell_quote(venue_id),
        "--year",
        str(year),
        "--invitation",
        shell_quote(invitation),
        "--output",
        shell_quote(raw_normalized_path),
        "--details replies",
        "--page-size",
        str(page_size),
        "--polite-delay",
        str(polite_delay),
        "--snapshot",
        shell_quote(dataset_slug),
    ]
    if pull_limit is not None:
        pull_parts.extend(["--limit", str(max(0, pull_limit))])
    commands = [
        build_command(
            "pull",
            " ".join(pull_parts),
            writes=[raw_normalized_path],
            requires_network=True,
            requires_openreview_auth=requires_auth,
            limit=pull_limit,
        )
    ]
    if rolling_venue:
        commands.append(
            build_command(
                "filter_normalized",
                " ".join(
                    [
                        "python -m secondopinion.tools.filter_normalized",
                        "--input",
                        shell_quote(raw_normalized_path),
                        "--out",
                        shell_quote(normalized_path),
                        "--year",
                        str(year),
                        "--mode",
                        shell_quote(year_filter),
                    ]
                ),
                writes=[normalized_path],
                mode=year_filter,
            )
        )
    commands.extend(
        [
            build_command(
                "quality",
                " ".join(
                    [
                        "python -m secondopinion.tools.data_quality_report",
                        "--input",
                        shell_quote(normalized_path),
                        "--json-out",
                        shell_quote(quality_json_path),
                        "--markdown-out",
                        shell_quote(quality_markdown_path),
                    ]
                ),
                writes=[quality_json_path, quality_markdown_path],
            ),
            build_command(
                "ingest",
                " ".join(
                    [
                        "python -m secondopinion.tools.ingest_normalized",
                        "--input",
                        shell_quote(normalized_path),
                    ]
                ),
                writes=["SECONDOPINION_DATABASE_URL"],
            ),
            build_command(
                "build_batch",
                " ".join(
                    [
                        "python -m secondopinion.tools.build_scoring_batch",
                        "--input",
                        shell_quote(normalized_path),
                        "--output",
                        shell_quote(batch_jsonl_path),
                        "--manifest",
                        shell_quote(batch_manifest_path),
                        "--model",
                        shell_quote(model),
                    ]
                ),
                writes=[batch_jsonl_path, batch_manifest_path],
            ),
            build_command(
                "split_batch",
                " ".join(
                    [
                        "python -m secondopinion.tools.split_scoring_batch",
                        "--input",
                        shell_quote(batch_jsonl_path),
                        "--manifest",
                        shell_quote(batch_manifest_path),
                        "--output-dir",
                        shell_quote(batch_parts_dir),
                        "--prefix",
                        shell_quote(slug),
                        "--max-estimated-input-tokens",
                        str(max_estimated_input_tokens),
                    ]
                ),
                writes=[batch_parts_dir],
            ),
            build_command(
                "submit_batch_dry_run",
                " ".join(
                    [
                        "python -m secondopinion.tools.submit_scoring_batch",
                        "--input",
                        shell_quote(batch_jsonl_path),
                        "--manifest",
                        shell_quote(batch_manifest_path),
                        "--output",
                        shell_quote(submission_path),
                        "--dry-run",
                    ]
                ),
                writes=[submission_path],
                requires_openai_key=True,
            ),
            build_command(
                "submit_batch",
                " ".join(
                    [
                        "python -m secondopinion.tools.submit_scoring_batch",
                        "--input",
                        shell_quote(batch_jsonl_path),
                        "--manifest",
                        shell_quote(batch_manifest_path),
                        "--output",
                        shell_quote(submission_path),
                    ]
                ),
                writes=[submission_path],
                requires_openai_key=True,
                cost_source=f"{batch_manifest_path}: estimated_batch_cost_usd",
            ),
            build_command(
                "retrieve_batch",
                " ".join(
                    [
                        "python -m secondopinion.tools.retrieve_scoring_batch",
                        "--batch-id YOUR_BATCH_ID",
                        "--output",
                        shell_quote(output_jsonl_path),
                        "--status-out",
                        shell_quote(status_path),
                        "--error-output",
                        shell_quote(error_jsonl_path),
                    ]
                ),
                writes=[output_jsonl_path, status_path, error_jsonl_path],
                requires_openai_key=True,
            ),
            build_command(
                "import_results",
                " ".join(
                    [
                        "python -m secondopinion.tools.import_scoring_batch_results",
                        "--input",
                        shell_quote(output_jsonl_path),
                        "--manifest",
                        shell_quote(batch_manifest_path),
                    ]
                ),
                writes=["SECONDOPINION_DATABASE_URL", "data/server/batch_scoring"],
            ),
        ]
    )

    if readiness == "excluded_not_scored":
        commands = []

    return {
        "venue_id": venue_id,
        "name": venue.get("name", venue_id),
        "year": year,
        "status": venue.get("status", "unknown"),
        "readiness": readiness,
        "blocked_reason": blocked_reason,
        "recommendation": venue.get("recommendation", ""),
        "rolling_venue": rolling_venue,
        "year_filter": year_filter if rolling_venue else venue.get("year_filter", ""),
        "invitation": invitation,
        "dataset_slug": dataset_slug,
        "paths": {
            "raw_normalized": raw_normalized_path,
            "normalized": normalized_path,
            "quality_json": quality_json_path,
            "quality_markdown": quality_markdown_path,
            "batch_jsonl": batch_jsonl_path,
            "batch_manifest": batch_manifest_path,
            "batch_parts_dir": batch_parts_dir,
            "batch_submission": submission_path,
            "batch_status": status_path,
            "batch_output": output_jsonl_path,
            "batch_errors": error_jsonl_path,
            "snapshot_id": dataset_slug,
        },
        "sample_stats": venue.get("sample_stats", {}),
        "pull_limit": pull_limit,
        "commands_enabled": readiness == "ready",
        "commands": commands,
        "notes": venue.get("notes", []),
    }


def summarize_plan(venues: list[dict[str, Any]]) -> dict[str, Any]:
    readiness_counts: dict[str, int] = {}
    for venue in venues:
        readiness = str(venue.get("readiness") or "unknown")
        readiness_counts[readiness] = readiness_counts.get(readiness, 0) + 1
    return {
        "venue_count": len(venues),
        "readiness_counts": readiness_counts,
        "ready": [venue["venue_id"] for venue in venues if venue.get("readiness") == "ready"],
        "blocked_openreview_auth": [
            venue["venue_id"] for venue in venues if venue.get("readiness") == "blocked_openreview_auth"
        ],
        "manual_year_filter_required": [
            venue["venue_id"] for venue in venues if venue.get("readiness") == "manual_year_filter_required"
        ],
        "needs_manual_inspection": [
            venue["venue_id"] for venue in venues if venue.get("readiness") == "needs_manual_inspection"
        ],
        "excluded_not_scored": [
            venue["venue_id"] for venue in venues if venue.get("readiness") == "excluded_not_scored"
        ],
    }


def build_ingestion_plan(
    inventory: dict[str, Any],
    *,
    model: str = DEFAULT_BATCH_MODEL,
    page_size: int = 100,
    polite_delay: float = 0.2,
    pull_limit: int | None = None,
    raw_root: str = "data/raw",
    normalized_dir: str = "data/normalized",
    validation_dir: str = "data/validation",
    report_dir: str = "reports/validation",
    batch_dir: str = "data/batch",
    max_estimated_input_tokens: int = 1_600_000,
) -> dict[str, Any]:
    venues = [
        build_venue_plan(
            venue,
            model=model,
            page_size=page_size,
            polite_delay=polite_delay,
            pull_limit=pull_limit,
            raw_root=raw_root,
            normalized_dir=normalized_dir,
            validation_dir=validation_dir,
            report_dir=report_dir,
            batch_dir=batch_dir,
            max_estimated_input_tokens=max_estimated_input_tokens,
        )
        for venue in inventory.get("venues", [])
    ]
    return {
        "schema_version": INGESTION_PLAN_SCHEMA_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "source_inventory_created_at": inventory.get("created_at", ""),
        "model": model,
        "pull_limit": pull_limit,
        "summary": summarize_plan(venues),
        "venues": venues,
    }


def render_ingestion_plan_markdown(plan: dict[str, Any]) -> str:
    summary = plan.get("summary", {})
    lines = [
        "# OpenReview 2025 Ingestion Plan",
        "",
        f"- Created: `{plan.get('created_at', '')}`",
        f"- Source inventory: `{plan.get('source_inventory_created_at', '')}`",
        f"- Batch scoring model: `{plan.get('model', '')}`",
        f"- Pull limit: `{plan.get('pull_limit', None)}`",
        "",
        "## Summary",
        "",
        "| Readiness | Venues |",
        "| --- | ---: |",
    ]
    for readiness, count in sorted((summary.get("readiness_counts") or {}).items()):
        lines.append(f"| {readiness} | {count} |")
    lines.extend(
        [
            "",
            "## Queue",
            "",
            "| Venue | Status | Readiness | Invitation | Normalized output |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for venue in plan.get("venues", []):
        lines.append(
            "| {venue_id} | {status} | {readiness} | `{invitation}` | `{normalized}` |".format(
                venue_id=venue.get("venue_id", ""),
                status=venue.get("status", ""),
                readiness=venue.get("readiness", ""),
                invitation=venue.get("invitation", ""),
                normalized=(venue.get("paths") or {}).get("normalized", ""),
            )
        )

    lines.extend(
        [
            "",
            "## Auth Gate",
            "",
            "If venues are `blocked_openreview_auth`, verify OpenReview in a browser and set one local-only value:",
            "",
            "```powershell",
            '$env:OPENREVIEW_COOKIE_FILE = "data/secrets/openreview.cookie"',
            "# The file may contain either a raw Cookie header or a Netscape cookie jar export.",
            "# or, for a short value:",
            '$env:OPENREVIEW_COOKIE = "..."',
            "```",
            "Then verify auth and rerun inventory before executing venue pull commands:",
            "",
            "First inspect local secret wiring without printing secret values, then run the network gate:",
            "",
            "```powershell",
            "python -m secondopinion.tools.openreview_secret_check --out data/validation/openreview_secret_check.json",
            "python -m secondopinion.tools.openreview_pipeline_gate --venues data/config/openreview_venues_2025.json --out data/validation/openreview_pipeline_gate.json",
            "python -m secondopinion.tools.openreview_auth_check --out data/validation/openreview_auth_check.json",
            "python -m secondopinion.tools.openreview_venue_inventory --venues data/config/openreview_venues_2025.json --sample-limit 50 --out data/validation/openreview_venue_inventory_2025.json --markdown reports/validation/openreview_venue_inventory_2025.md",
            "python -m secondopinion.tools.openreview_ingestion_plan --inventory data/validation/openreview_venue_inventory_2025.json --out data/validation/openreview_ingestion_plan_2025.json --markdown reports/validation/openreview_ingestion_plan_2025.md",
            "python -m secondopinion.tools.openreview_plan_runner --plan data/validation/openreview_ingestion_plan_2025.json --out data/validation/openreview_plan_runner_last.json",
            "```",
            "",
            "## Commands",
            "",
        ]
    )

    for venue in plan.get("venues", []):
        lines.extend([f"### {venue.get('venue_id', '')}", ""])
        if venue.get("blocked_reason"):
            lines.append(f"- Blocked: {venue.get('blocked_reason')}")
        if venue.get("rolling_venue"):
            lines.append(
                f"- Rolling venue: `{venue.get('year_filter')}` is applied before quality checks, ingest, and scoring."
            )
        if not venue.get("commands_enabled"):
            lines.append("- Commands are recorded for handoff but should wait until readiness is `ready`.")
        lines.append("")
        lines.append("```powershell")
        for command in venue.get("commands", []):
            lines.append(str(command.get("command", "")))
        lines.append("```")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a deterministic OpenReview pull/score queue from venue inventory.")
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--out", default="data/validation/openreview_ingestion_plan_2025.json")
    parser.add_argument("--markdown", default="reports/validation/openreview_ingestion_plan_2025.md")
    parser.add_argument("--model", default=os.environ.get("SECONDOPINION_BATCH_MODEL", DEFAULT_BATCH_MODEL))
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--polite-delay", type=float, default=0.2)
    parser.add_argument("--pull-limit", type=int, default=None)
    parser.add_argument("--raw-root", default="data/raw")
    parser.add_argument("--normalized-dir", default="data/normalized")
    parser.add_argument("--validation-dir", default="data/validation")
    parser.add_argument("--report-dir", default="reports/validation")
    parser.add_argument("--batch-dir", default="data/batch")
    parser.add_argument("--max-estimated-input-tokens", type=int, default=1_600_000)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    inventory = read_json(args.inventory)
    plan = build_ingestion_plan(
        inventory,
        model=args.model,
        page_size=args.page_size,
        polite_delay=args.polite_delay,
        pull_limit=args.pull_limit,
        raw_root=args.raw_root,
        normalized_dir=args.normalized_dir,
        validation_dir=args.validation_dir,
        report_dir=args.report_dir,
        batch_dir=args.batch_dir,
        max_estimated_input_tokens=args.max_estimated_input_tokens,
    )
    write_json(args.out, plan)
    write_markdown(args.markdown, render_ingestion_plan_markdown(plan))
    print(json.dumps(plan["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

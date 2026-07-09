from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


SCOPE_AUDIT_VERSION = "openreview-scope-audit-v0.1"

REQUIRED_CORE_VENUES = {"ICLR", "ICML", "NEURIPS", "TMLR"}
EXPECTED_EXCLUDED_TOP_JOURNALS = {"JMLR", "JAIR", "MLJ"}
TARGET_SCOPE_DECISIONS = {"score_public_reviews", "probe_then_score_if_public"}
EXCLUDED_SCOPE_DECISIONS = {"exclude_no_public_reviews", "exclude_not_openreview"}


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_venues(path: str | Path) -> list[dict[str, Any]]:
    payload = read_json(path)
    venues = payload.get("venues", []) if isinstance(payload, dict) else payload
    return [item for item in venues if isinstance(item, dict)]


def by_venue_id(venues: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(venue.get("venue_id") or "").upper(): venue for venue in venues}


def venue_id(venue: dict[str, Any]) -> str:
    return str(venue.get("venue_id") or "").upper()


def priority(venue: dict[str, Any]) -> int:
    return int(venue.get("priority") or 99)


def scope_decision(venue: dict[str, Any]) -> str:
    return str(venue.get("scope_decision") or "")


def audit_openreview_scope(
    *,
    venues: list[dict[str, Any]],
    inventory: dict[str, Any] | None = None,
    plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    venue_map = by_venue_id(venues)
    ids = [str(venue.get("venue_id") or "").upper() for venue in venues]

    duplicates = sorted({venue_id for venue_id in ids if venue_id and ids.count(venue_id) > 1})
    for venue_id in duplicates:
        errors.append(f"duplicate venue_id in config: {venue_id}")

    missing_core = sorted(REQUIRED_CORE_VENUES - set(venue_map))
    for venue_id in missing_core:
        errors.append(f"missing required core venue: {venue_id}")

    for venue_id, venue in sorted(venue_map.items()):
        decision = str(venue.get("scope_decision") or "")
        if not decision:
            errors.append(f"venue missing scope_decision: {venue_id}")
        elif decision not in TARGET_SCOPE_DECISIONS | EXCLUDED_SCOPE_DECISIONS:
            errors.append(f"venue has unsupported scope_decision: {venue_id}={decision}")

    for venue_id in sorted(REQUIRED_CORE_VENUES & set(venue_map)):
        venue = venue_map[venue_id]
        if venue.get("include_in_inventory") is False:
            errors.append(f"core venue is excluded from inventory: {venue_id}")
        if str(venue.get("scope_decision") or "") not in TARGET_SCOPE_DECISIONS:
            errors.append(f"core venue must be targeted or probed for scoring: {venue_id}")
        if not venue.get("invitation_candidates"):
            errors.append(f"core venue has no invitation candidates: {venue_id}")
    tmlr = venue_map.get("TMLR")
    if tmlr and (not tmlr.get("rolling_venue") or not tmlr.get("year_filter")):
        errors.append("TMLR must be marked as a rolling venue with a year_filter")

    missing_exclusions = sorted(EXPECTED_EXCLUDED_TOP_JOURNALS - set(venue_map))
    for venue_id in missing_exclusions:
        warnings.append(f"top journal not explicitly classified: {venue_id}")
    for venue_id in sorted(EXPECTED_EXCLUDED_TOP_JOURNALS & set(venue_map)):
        venue = venue_map[venue_id]
        status = str(venue.get("manual_status") or "")
        if venue.get("include_in_inventory") is not False or not status.startswith("excluded_"):
            errors.append(f"non-OpenReview top journal must be manually excluded: {venue_id}")
        if str(venue.get("scope_decision") or "") not in EXCLUDED_SCOPE_DECISIONS:
            errors.append(f"non-OpenReview top journal must have excluded scope_decision: {venue_id}")

    inventory_summary = audit_inventory(inventory, set(venue_map), errors, warnings) if inventory else {}
    plan_summary = audit_plan(plan, errors, warnings) if plan else {}

    completeness = scope_completeness(venues)
    return {
        "schema_version": SCOPE_AUDIT_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "status": "failed" if errors else "passed",
        "completeness": completeness,
        "config": {
            "venue_count": len(venues),
            "core_venues": sorted(REQUIRED_CORE_VENUES & set(venue_map)),
            "missing_core_venues": missing_core,
            "target_scope_decisions": sorted(TARGET_SCOPE_DECISIONS),
            "excluded_scope_decisions": sorted(EXCLUDED_SCOPE_DECISIONS),
            "excluded_top_journals": sorted(EXPECTED_EXCLUDED_TOP_JOURNALS & set(venue_map)),
            "missing_excluded_top_journals": missing_exclusions,
        },
        "inventory": inventory_summary,
        "plan": plan_summary,
        "errors": errors,
        "warnings": warnings,
    }


def scope_completeness(venues: list[dict[str, Any]]) -> dict[str, Any]:
    buckets = {
        "priority1_core": [],
        "priority2_probe": [],
        "excluded_top_journals": [],
        "other": [],
    }
    target_ids = []
    excluded_ids = []
    for venue in sorted(venues, key=lambda item: (priority(item), venue_id(item))):
        vid = venue_id(venue)
        decision = scope_decision(venue)
        row = {
            "venue_id": vid,
            "priority": priority(venue),
            "category": str(venue.get("category") or ""),
            "scope_decision": decision,
            "review_policy": str(venue.get("review_policy") or ""),
            "candidate_count": len(venue.get("invitation_candidates") or []),
        }
        if decision in TARGET_SCOPE_DECISIONS:
            target_ids.append(vid)
        if decision in EXCLUDED_SCOPE_DECISIONS or venue.get("include_in_inventory") is False:
            excluded_ids.append(vid)
        if vid in REQUIRED_CORE_VENUES and decision in TARGET_SCOPE_DECISIONS:
            buckets["priority1_core"].append(row)
        elif priority(venue) == 2 and decision in TARGET_SCOPE_DECISIONS:
            buckets["priority2_probe"].append(row)
        elif vid in EXPECTED_EXCLUDED_TOP_JOURNALS:
            buckets["excluded_top_journals"].append(row)
        else:
            buckets["other"].append(row)
    return {
        "target_count": len(target_ids),
        "excluded_count": len(excluded_ids),
        "target_venue_ids": target_ids,
        "excluded_venue_ids": excluded_ids,
        "priority1_core_ids": [item["venue_id"] for item in buckets["priority1_core"]],
        "priority2_probe_ids": [item["venue_id"] for item in buckets["priority2_probe"]],
        "explicitly_excluded_top_journal_ids": [item["venue_id"] for item in buckets["excluded_top_journals"]],
        "buckets": buckets,
    }


def audit_inventory(
    inventory: dict[str, Any],
    config_ids: set[str],
    errors: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    venues = [item for item in inventory.get("venues", []) if isinstance(item, dict)]
    venue_map = by_venue_id(venues)
    missing = sorted(config_ids - set(venue_map))
    for venue_id in missing:
        errors.append(f"inventory missing configured venue: {venue_id}")
    for venue_id in sorted(EXPECTED_EXCLUDED_TOP_JOURNALS & set(venue_map)):
        status = str(venue_map[venue_id].get("status") or "")
        if not status.startswith("excluded_"):
            errors.append(f"excluded top journal inventory status is not excluded: {venue_id}")
    ready = list((inventory.get("summary") or {}).get("ready_to_pull_and_score") or [])
    needs_auth = list((inventory.get("summary") or {}).get("needs_openreview_auth") or [])
    if not ready and needs_auth:
        warnings.append("no venues are ready yet because OpenReview auth/challenge is still required")
    return {
        "venue_count": len(venues),
        "status_counts": dict((inventory.get("summary") or {}).get("status_counts") or {}),
        "ready_to_pull_and_score": ready,
        "needs_openreview_auth": needs_auth,
        "missing_configured_venues": missing,
    }


def audit_plan(plan: dict[str, Any], errors: list[str], warnings: list[str]) -> dict[str, Any]:
    venues = [item for item in plan.get("venues", []) if isinstance(item, dict)]
    venue_map = by_venue_id(venues)
    for venue_id in sorted(EXPECTED_EXCLUDED_TOP_JOURNALS & set(venue_map)):
        venue = venue_map[venue_id]
        if venue.get("readiness") != "excluded_not_scored":
            errors.append(f"excluded top journal plan readiness is wrong: {venue_id}")
        if venue.get("commands"):
            errors.append(f"excluded top journal has generated commands: {venue_id}")
    for venue_id in sorted(REQUIRED_CORE_VENUES & set(venue_map)):
        if venue_map[venue_id].get("readiness") == "excluded_not_scored":
            errors.append(f"core venue was excluded from scoring plan: {venue_id}")
    summary = plan.get("summary") or {}
    if not summary.get("ready") and summary.get("blocked_openreview_auth"):
        warnings.append("plan has no ready venues until OpenReview auth/challenge is solved")
    return {
        "venue_count": len(venues),
        "readiness_counts": dict(summary.get("readiness_counts") or {}),
        "ready": list(summary.get("ready") or []),
        "blocked_openreview_auth": list(summary.get("blocked_openreview_auth") or []),
        "excluded_not_scored": list(summary.get("excluded_not_scored") or []),
    }


def render_scope_audit_markdown(report: dict[str, Any]) -> str:
    completeness = report.get("completeness") or {}
    config = report.get("config") or {}
    inventory = report.get("inventory") or {}
    plan = report.get("plan") or {}
    lines = [
        "# OpenReview 2025 Scope Audit",
        "",
        f"- Created: `{report.get('created_at', '')}`",
        f"- Status: `{report.get('status', '')}`",
        f"- Config venues: `{config.get('venue_count', 0)}`",
        f"- Core venues: `{', '.join(config.get('core_venues') or [])}`",
        f"- Explicitly excluded top journals: `{', '.join(config.get('excluded_top_journals') or [])}`",
        f"- Target venues: `{', '.join(completeness.get('target_venue_ids') or []) or '-'}`",
        f"- Priority 1 core: `{', '.join(completeness.get('priority1_core_ids') or []) or '-'}`",
        f"- Priority 2 probe: `{', '.join(completeness.get('priority2_probe_ids') or []) or '-'}`",
        f"- Excluded top journals: `{', '.join(completeness.get('explicitly_excluded_top_journal_ids') or []) or '-'}`",
        "",
        "## Inventory",
        "",
        f"- Venues: `{inventory.get('venue_count', 0)}`",
        f"- Ready: `{', '.join(inventory.get('ready_to_pull_and_score') or []) or '-'}`",
        f"- Needs OpenReview auth: `{', '.join(inventory.get('needs_openreview_auth') or []) or '-'}`",
        "",
        "## Plan",
        "",
        f"- Venues: `{plan.get('venue_count', 0)}`",
        f"- Ready: `{', '.join(plan.get('ready') or []) or '-'}`",
        f"- Blocked by OpenReview auth: `{', '.join(plan.get('blocked_openreview_auth') or []) or '-'}`",
        f"- Excluded from scoring: `{', '.join(plan.get('excluded_not_scored') or []) or '-'}`",
        "",
        "## Issues",
        "",
    ]
    for error in report.get("errors", []):
        lines.append(f"- ERROR: {error}")
    for warning in report.get("warnings", []):
        lines.append(f"- WARNING: {warning}")
    if not report.get("errors") and not report.get("warnings"):
        lines.append("- None")
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit 2025 OpenReview venue scope before pull/score execution.")
    parser.add_argument("--venues", default="data/config/openreview_venues_2025.json")
    parser.add_argument("--inventory", default="data/validation/openreview_venue_inventory_2025.json")
    parser.add_argument("--plan", default="data/validation/openreview_ingestion_plan_2025.json")
    parser.add_argument("--out", default="data/validation/openreview_scope_audit_2025.json")
    parser.add_argument("--markdown", default="reports/validation/openreview_scope_audit_2025.md")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    inventory = read_json(args.inventory) if args.inventory and Path(args.inventory).exists() else None
    plan = read_json(args.plan) if args.plan and Path(args.plan).exists() else None
    report = audit_openreview_scope(venues=load_venues(args.venues), inventory=inventory, plan=plan)
    write_json(args.out, report)
    write_markdown(args.markdown, render_scope_audit_markdown(report))
    print(json.dumps({"status": report["status"], "errors": report["errors"], "warnings": report["warnings"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

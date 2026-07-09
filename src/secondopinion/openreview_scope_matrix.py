from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


SCOPE_MATRIX_VERSION = "openreview-scope-matrix-v0.1"
CORE_TARGET_DECISIONS = {"score_public_reviews", "probe_then_score_if_public"}
EXCLUDED_DECISIONS = {"exclude_no_public_reviews", "exclude_not_openreview"}


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
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
    return [dict(item) for item in venues if isinstance(item, dict)]


def inventory_by_id(inventory: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not inventory:
        return {}
    venues = [item for item in inventory.get("venues", []) if isinstance(item, dict)]
    return {str(item.get("venue_id") or "").upper(): item for item in venues}


def infer_scope_decision(spec: dict[str, Any]) -> str:
    if spec.get("scope_decision"):
        return str(spec["scope_decision"])
    if spec.get("include_in_inventory") is False or str(spec.get("manual_status") or "").startswith("excluded_"):
        return "exclude_no_public_reviews"
    if int(spec.get("priority") or 99) <= 1:
        return "score_public_reviews"
    return "probe_then_score_if_public"


def matrix_row(spec: dict[str, Any], inventory_row: dict[str, Any] | None = None) -> dict[str, Any]:
    venue_id = str(spec.get("venue_id") or "").upper()
    decision = infer_scope_decision(spec)
    inventory_status = str((inventory_row or {}).get("status") or "not_probed")
    recommendation = str((inventory_row or {}).get("recommendation") or "")
    if decision in EXCLUDED_DECISIONS:
        execution_state = "excluded"
    elif inventory_status in {"open_reviews_available", "partial_public_reviews"}:
        execution_state = "ready_to_pull"
    elif inventory_status in {"challenge_required", "auth_required"}:
        execution_state = "blocked_openreview_auth"
    elif inventory_status == "not_probed":
        execution_state = "needs_inventory_probe"
    else:
        execution_state = "needs_manual_inspection"
    return {
        "venue_id": venue_id,
        "name": str(spec.get("name") or venue_id),
        "year": int(spec.get("year") or 2025),
        "category": str(spec.get("category") or ""),
        "priority": int(spec.get("priority") or 99),
        "scope_decision": decision,
        "scope": str(spec.get("scope") or ""),
        "review_policy": str(spec.get("review_policy") or ""),
        "inventory_status": inventory_status,
        "inventory_recommendation": recommendation,
        "execution_state": execution_state,
        "selected_invitation": str((inventory_row or {}).get("selected_invitation") or ""),
        "public_review_evidence_state": str(((inventory_row or {}).get("public_review_evidence") or {}).get("state") or "missing"),
        "evidence_urls": list(spec.get("evidence_urls") or []),
        "invitation_candidates": list(spec.get("invitation_candidates") or []),
        "source_notes": list(spec.get("source_notes") or []),
    }


def build_scope_matrix(*, venues: list[dict[str, Any]], inventory: dict[str, Any] | None = None) -> dict[str, Any]:
    inv = inventory_by_id(inventory)
    rows = [matrix_row(spec, inv.get(str(spec.get("venue_id") or "").upper())) for spec in venues]
    counts: dict[str, int] = {}
    decision_counts: dict[str, int] = {}
    for row in rows:
        counts[row["execution_state"]] = counts.get(row["execution_state"], 0) + 1
        decision_counts[row["scope_decision"]] = decision_counts.get(row["scope_decision"], 0) + 1
    return {
        "schema_version": SCOPE_MATRIX_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "summary": {
            "venue_count": len(rows),
            "execution_state_counts": dict(sorted(counts.items())),
            "scope_decision_counts": dict(sorted(decision_counts.items())),
            "target_or_probe": [row["venue_id"] for row in rows if row["scope_decision"] in CORE_TARGET_DECISIONS],
            "excluded": [row["venue_id"] for row in rows if row["scope_decision"] in EXCLUDED_DECISIONS],
            "ready_to_pull": [row["venue_id"] for row in rows if row["execution_state"] == "ready_to_pull"],
            "blocked_openreview_auth": [row["venue_id"] for row in rows if row["execution_state"] == "blocked_openreview_auth"],
            "needs_inventory_probe": [row["venue_id"] for row in rows if row["execution_state"] == "needs_inventory_probe"],
        },
        "venues": sorted(rows, key=lambda row: (row["priority"], row["venue_id"])),
    }


def render_scope_matrix_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# OpenReview 2025 Scope Matrix",
        "",
        f"- Created: `{report.get('created_at', '')}`",
        f"- Venues: `{summary.get('venue_count', 0)}`",
        f"- Target/probe: `{', '.join(summary.get('target_or_probe') or []) or '-'}`",
        f"- Excluded: `{', '.join(summary.get('excluded') or []) or '-'}`",
        f"- Ready to pull: `{', '.join(summary.get('ready_to_pull') or []) or '-'}`",
        f"- Blocked by OpenReview auth: `{', '.join(summary.get('blocked_openreview_auth') or []) or '-'}`",
        f"- Needs inventory probe: `{', '.join(summary.get('needs_inventory_probe') or []) or '-'}`",
        "",
        "## Matrix",
        "",
        "| Venue | Category | Decision | Evidence | Review policy | Inventory status | Execution state | Invitation |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in report.get("venues", []):
        invitation = row.get("selected_invitation") or (row.get("invitation_candidates") or [""])[0]
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("venue_id", "")),
                    str(row.get("category", "")),
                    str(row.get("scope_decision", "")),
                    str(row.get("public_review_evidence_state", "")),
                    str(row.get("review_policy", "")),
                    str(row.get("inventory_status", "")),
                    str(row.get("execution_state", "")),
                    f"`{invitation}`",
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a 2025 OpenReview venue scope decision matrix.")
    parser.add_argument("--venues", default="data/config/openreview_venues_2025.json")
    parser.add_argument("--inventory", default="data/validation/openreview_venue_inventory_2025.json")
    parser.add_argument("--out", default="data/validation/openreview_scope_matrix_2025.json")
    parser.add_argument("--markdown", default="reports/validation/openreview_scope_matrix_2025.md")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    inventory = read_json(args.inventory) if args.inventory and Path(args.inventory).exists() else None
    report = build_scope_matrix(venues=load_venues(args.venues), inventory=inventory)
    write_json(args.out, report)
    write_markdown(args.markdown, render_scope_matrix_markdown(report))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

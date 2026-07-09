from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from .openreview_invitation_audit import audit_invitation_candidates, load_venues


PROBE_QUEUE_SCHEMA_VERSION = "openreview-probe-queue-v0.1"


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: str | Path, text: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


def build_probe_queue(*, venues: list[dict[str, Any]], sample_limit: int = 50) -> dict[str, Any]:
    audit = audit_invitation_candidates(venues)
    items: list[dict[str, Any]] = []
    for row in audit.get("venues", []):
        if row.get("status") == "excluded":
            continue
        candidates = row.get("invitation_candidates") or []
        for index, invitation in enumerate(candidates):
            paths = probe_output_paths(venue_id=str(row.get("venue_id", "")), candidate_index=index, sample_limit=sample_limit)
            items.append(
                {
                    "venue_id": row.get("venue_id", ""),
                    "priority": row.get("priority", 99),
                    "candidate_index": index,
                    "candidate_count": len(candidates),
                    "invitation": invitation,
                    "expected_group_url": "https://openreview.net/group?id=" + invitation.split("/-/", 1)[0],
                    "purpose": "resolve_multi_candidate" if len(candidates) > 1 else "confirm_public_reviews",
                    "result_json": paths["json"],
                    "result_markdown": paths["markdown"],
                    "command": probe_command(invitation=invitation, sample_limit=sample_limit, venue_id=str(row.get("venue_id", "")), candidate_index=index),
                }
            )
    items.sort(key=lambda item: (int(item["priority"]), str(item["venue_id"]), int(item["candidate_index"])))
    return {
        "schema_version": PROBE_QUEUE_SCHEMA_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "sample_limit": sample_limit,
        "summary": {
            "probe_count": len(items),
            "venue_count": len({item["venue_id"] for item in items}),
            "multi_candidate_probe_count": sum(1 for item in items if int(item["candidate_count"]) > 1),
            "core_priority1": [item["venue_id"] for item in items if int(item["priority"]) <= 1 and int(item["candidate_index"]) == 0],
            "probe_priority2": [item["venue_id"] for item in items if int(item["priority"]) == 2 and int(item["candidate_index"]) == 0],
        },
        "items": items,
    }



def probe_output_paths(*, venue_id: str, candidate_index: int, sample_limit: int) -> dict[str, str]:
    slug = venue_id.lower() or "venue"
    suffix = f"c{candidate_index + 1}"
    return {
        "json": f"data/validation/openreview_probe_{slug}_{suffix}_{sample_limit}.json",
        "markdown": f"reports/validation/openreview_probe_{slug}_{suffix}_{sample_limit}.md",
    }

def probe_command(*, invitation: str, sample_limit: int, venue_id: str, candidate_index: int = 0) -> str:
    slug = venue_id.lower() or "venue"
    safe_invitation = invitation.replace('"', '\\"')
    paths = probe_output_paths(venue_id=venue_id, candidate_index=candidate_index, sample_limit=sample_limit)
    return (
        "python -m secondopinion.tools.openreview_probe_invitation "
        f"--venue {slug.upper()} --invitation \"{safe_invitation}\" --sample-limit {sample_limit} "
        f"--out {paths['json']} "
        f"--markdown {paths['markdown']}"
    )


def render_probe_queue_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# OpenReview Probe Queue",
        "",
        f"- Created: `{report.get('created_at', '')}`",
        f"- Sample limit: `{report.get('sample_limit', '')}`",
        f"- Probe count: `{summary.get('probe_count', 0)}`",
        f"- Multi-candidate probes: `{summary.get('multi_candidate_probe_count', 0)}`",
        f"- Core priority 1: `{', '.join(summary.get('core_priority1') or []) or '-'}`",
        f"- Probe priority 2: `{', '.join(summary.get('probe_priority2') or []) or '-'}`",
        "",
        "## Queue",
        "",
        "| Venue | Priority | Candidate | Purpose | Invitation | Group URL |",
        "| --- | ---: | ---: | --- | --- | --- |",
    ]
    for item in report.get("items", []):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item.get("venue_id", "")),
                    str(item.get("priority", "")),
                    f"{int(item.get('candidate_index', 0)) + 1}/{item.get('candidate_count', 0)}",
                    str(item.get("purpose", "")),
                    f"`{item.get('invitation', '')}`",
                    f"`{item.get('expected_group_url', '')}`",
                ]
            )
            + " |"
        )
    lines.extend(["", "## Commands", "", "```powershell"])
    for item in report.get("items", []):
        lines.append(str(item.get("command", "")))
    lines.extend(["```", ""])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build an ordered OpenReview invitation probe queue.")
    parser.add_argument("--venues", default="data/config/openreview_venues_2025.json")
    parser.add_argument("--sample-limit", type=int, default=50)
    parser.add_argument("--out", default="data/validation/openreview_probe_queue_2025.json")
    parser.add_argument("--markdown", default="reports/validation/openreview_probe_queue_2025.md")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    report = build_probe_queue(venues=load_venues(args.venues), sample_limit=args.sample_limit)
    write_json(args.out, report)
    write_markdown(args.markdown, render_probe_queue_markdown(report))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

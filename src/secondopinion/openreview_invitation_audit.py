from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


INVITATION_AUDIT_SCHEMA_VERSION = "openreview-invitation-audit-v0.1"
OPENREVIEW_GROUP_PREFIX = "https://openreview.net/group?id="


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: str | Path, text: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


def load_venues(path: str | Path) -> list[dict[str, Any]]:
    payload = read_json(path)
    venues = payload.get("venues", []) if isinstance(payload, dict) else payload
    return [dict(item) for item in venues if isinstance(item, dict)]


def group_from_invitation(invitation: str) -> str:
    marker = "/-/"
    return invitation.split(marker, 1)[0] if marker in invitation else ""



def valid_invitation(invitation: str) -> bool:
    if not invitation or invitation.strip() != invitation or any(char.isspace() for char in invitation):
        return False
    if "/-/" not in invitation:
        return False
    group, suffix = invitation.split("/-/", 1)
    return bool(group and suffix and "/" not in suffix)

def expected_group_url(invitation: str) -> str:
    group = group_from_invitation(invitation)
    return OPENREVIEW_GROUP_PREFIX + group if group else ""


def audit_invitation_candidates(venues: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [audit_venue(venue) for venue in venues]
    issue_counts: dict[str, int] = {}
    for row in rows:
        for issue in row["issues"]:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
    return {
        "schema_version": INVITATION_AUDIT_SCHEMA_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "summary": {
            "venue_count": len(rows),
            "issue_counts": dict(sorted(issue_counts.items())),
            "ready_candidate_count": sum(1 for row in rows if row["status"] in {"ready_for_api_probe", "ready_for_multi_candidate_probe"}),
            "single_candidate_ready": [row["venue_id"] for row in rows if row["status"] == "ready_for_api_probe"],
            "multi_candidate_ready": [row["venue_id"] for row in rows if row["status"] == "ready_for_multi_candidate_probe"],
            "needs_attention": [row["venue_id"] for row in rows if row["status"] == "needs_attention"],
            "multi_candidate_venues": [row["venue_id"] for row in rows if len(row["invitation_candidates"]) > 1],
            "excluded": [row["venue_id"] for row in rows if row["status"] == "excluded"],
        },
        "venues": rows,
    }


def audit_venue(venue: dict[str, Any]) -> dict[str, Any]:
    venue_id = str(venue.get("venue_id") or "").upper()
    include = bool(venue.get("include_in_inventory", True))
    candidates = [str(value) for value in venue.get("invitation_candidates") or [] if str(value).strip()]
    evidence_urls = [str(value) for value in venue.get("evidence_urls") or [] if str(value).strip()]
    issues: list[str] = []
    selected = candidates[0] if candidates else ""
    if not include or str(venue.get("scope_decision") or "").startswith("exclude_"):
        status = "excluded"
    else:
        if not candidates:
            issues.append("missing_invitation_candidates")
        invalid = [candidate for candidate in candidates if not valid_invitation(candidate)]
        if invalid:
            issues.append("invalid_invitation_format")
        multi_candidate = len(candidates) > 1
        if selected and expected_group_url(selected) not in evidence_urls:
            issues.append("missing_selected_group_evidence_url")
        blocking_issues = [issue for issue in issues if issue not in {"multiple_invitation_candidates"}]
        if blocking_issues:
            status = "needs_attention"
        elif multi_candidate:
            issues.append("multiple_invitation_candidates")
            status = "ready_for_multi_candidate_probe"
        else:
            status = "ready_for_api_probe"
    return {
        "venue_id": venue_id,
        "name": str(venue.get("name") or venue_id),
        "priority": int(venue.get("priority") or 99),
        "scope_decision": str(venue.get("scope_decision") or ""),
        "status": status,
        "selected_invitation": selected,
        "selected_group": group_from_invitation(selected),
        "expected_group_url": expected_group_url(selected),
        "invitation_candidates": candidates,
        "evidence_urls": evidence_urls,
        "issues": issues,
    }


def render_invitation_audit_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# OpenReview Invitation Audit",
        "",
        f"- Created: `{report.get('created_at', '')}`",
        f"- Venues: `{summary.get('venue_count', 0)}`",
        f"- Ready candidates: `{summary.get('ready_candidate_count', 0)}`",
        f"- Single-candidate ready: `{', '.join(summary.get('single_candidate_ready') or []) or '-'}`",
        f"- Multi-candidate ready: `{', '.join(summary.get('multi_candidate_ready') or []) or '-'}`",
        f"- Needs attention: `{', '.join(summary.get('needs_attention') or []) or '-'}`",
        f"- Multi-candidate venues: `{', '.join(summary.get('multi_candidate_venues') or []) or '-'}`",
        "",
        "## Venues",
        "",
        "| Venue | Status | Selected invitation | Expected group URL | Candidates | Issues |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for row in sorted(report.get("venues", []), key=lambda item: (int(item.get("priority") or 99), item.get("venue_id", ""))):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("venue_id", "")),
                    str(row.get("status", "")),
                    f"`{row.get('selected_invitation', '')}`",
                    f"`{row.get('expected_group_url', '')}`",
                    str(len(row.get("invitation_candidates") or [])),
                    ", ".join(row.get("issues") or []) or "-",
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit OpenReview invitation candidates before API probing.")
    parser.add_argument("--venues", default="data/config/openreview_venues_2025.json")
    parser.add_argument("--out", default="data/validation/openreview_invitation_audit_2025.json")
    parser.add_argument("--markdown", default="reports/validation/openreview_invitation_audit_2025.md")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    report = audit_invitation_candidates(load_venues(args.venues))
    write_json(args.out, report)
    write_markdown(args.markdown, render_invitation_audit_markdown(report))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from .openreview_client import OpenReviewClient
from .openreview_venue_inventory import probe_invitation, summarize_paper_inventory, summarize_review_invitations


PROBE_INVITATION_SCHEMA_VERSION = "openreview-probe-invitation-v0.1"


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: str | Path, text: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


def run_probe_invitation(
    *,
    invitation: str,
    venue_id: str = "",
    sample_limit: int = 50,
    details: str = "replies",
    client: OpenReviewClient | None = None,
) -> dict[str, Any]:
    client = client or OpenReviewClient()
    attempt = probe_invitation(client, invitation, sample_limit=sample_limit, details=details)
    papers = attempt.get("paper_inventory") or []
    stats = summarize_paper_inventory(papers)
    status = attempt.get("probe_status", "unknown")
    if status == "success" and stats.get("review_count", 0) > 0:
        recommendation = "candidate_has_public_reviews"
    elif status == "success":
        recommendation = "candidate_has_no_public_reviews_in_sample"
    elif status in {"challenge_required", "auth_required"}:
        recommendation = "retry_with_browser_verified_cookie"
    elif status == "not_found":
        recommendation = "try_next_candidate"
    else:
        recommendation = "inspect_error"
    return {
        "schema_version": PROBE_INVITATION_SCHEMA_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "venue_id": venue_id.upper(),
        "invitation": invitation,
        "sample_limit": sample_limit,
        "details": details,
        "status": status,
        "recommendation": recommendation,
        "attempt": redact_attempt(attempt),
        "sample_stats": stats,
        "review_invitation_counts": summarize_review_invitations(papers),
    }


def redact_attempt(attempt: dict[str, Any]) -> dict[str, Any]:
    item = {
        "invitation": attempt.get("invitation", ""),
        "probe_status": attempt.get("probe_status", ""),
        "api_note_count": attempt.get("api_note_count", 0),
    }
    error = attempt.get("error")
    if isinstance(error, dict):
        payload = error.get("payload") if isinstance(error.get("payload"), dict) else {}
        item["error"] = {
            "status_code": error.get("status_code", 0),
            "name": payload.get("name", ""),
            "message": payload.get("message", ""),
            "challenge_url_present": bool(payload.get("challengeUrl")),
        }
    return item


def render_probe_invitation_markdown(report: dict[str, Any]) -> str:
    stats = report.get("sample_stats") or {}
    lines = [
        "# OpenReview Invitation Probe",
        "",
        f"- Created: `{report.get('created_at', '')}`",
        f"- Venue: `{report.get('venue_id', '')}`",
        f"- Invitation: `{report.get('invitation', '')}`",
        f"- Status: `{report.get('status', '')}`",
        f"- Recommendation: `{report.get('recommendation', '')}`",
        f"- Papers: `{stats.get('paper_count', 0)}`",
        f"- Reviews: `{stats.get('review_count', 0)}`",
        f"- Review coverage: `{float(stats.get('review_coverage_rate') or 0):.1%}`",
        "",
    ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe one OpenReview invitation candidate.")
    parser.add_argument("--invitation", required=True)
    parser.add_argument("--venue", default="")
    parser.add_argument("--sample-limit", type=int, default=50)
    parser.add_argument("--details", default="replies")
    parser.add_argument("--api-base", default="https://api2.openreview.net")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--out", default="data/validation/openreview_probe_invitation.json")
    parser.add_argument("--markdown", default="reports/validation/openreview_probe_invitation.md")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    report = run_probe_invitation(
        invitation=args.invitation,
        venue_id=args.venue,
        sample_limit=args.sample_limit,
        details=args.details,
        client=OpenReviewClient(base_url=args.api_base, timeout=args.timeout),
    )
    write_json(args.out, report)
    write_markdown(args.markdown, render_probe_invitation_markdown(report))
    print(json.dumps({"status": report["status"], "recommendation": report["recommendation"], "sample_stats": report["sample_stats"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

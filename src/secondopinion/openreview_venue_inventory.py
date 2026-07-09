from __future__ import annotations

import argparse
import datetime as dt
from collections import Counter
import json
from pathlib import Path
from typing import Any, Iterable

from .data_inventory import inventory_paper
from .openreview_client import OpenReviewAPIError, OpenReviewClient


VENUE_INVENTORY_VERSION = "openreview-venue-inventory-v0.1"
PUBLIC_REVIEW_POLICIES = {
    "fully_open_public_reviews",
    "open_public_reviews",
    "partially_open_public_reviews",
}


DEFAULT_OPENREVIEW_VENUES_2025: list[dict[str, Any]] = [
    {
        "venue_id": "ICLR",
        "name": "International Conference on Learning Representations",
        "year": 2025,
        "category": "top_conference",
        "priority": 1,
        "scope": "all_submissions",
        "review_policy": "fully_open_public_reviews",
        "source_notes": ["Spec target: full 2025 ICLR public OpenReview corpus."],
        "invitation_candidates": ["ICLR.cc/2025/Conference/-/Submission"],
    },
    {
        "venue_id": "ICML",
        "name": "International Conference on Machine Learning",
        "year": 2025,
        "category": "top_conference",
        "priority": 1,
        "scope": "accepted_plus_public_opt_in",
        "review_policy": "partially_open_public_reviews",
        "source_notes": ["Spec target: public ICML 2025 reviews, typically accepted plus public opt-in rejected papers."],
        "invitation_candidates": ["ICML.cc/2025/Conference/-/Submission"],
    },
    {
        "venue_id": "NEURIPS",
        "name": "Neural Information Processing Systems",
        "year": 2025,
        "category": "top_conference",
        "priority": 1,
        "scope": "accepted_plus_public_opt_in",
        "review_policy": "partially_open_public_reviews",
        "source_notes": ["Spec target: public NeurIPS 2025 reviews, typically accepted plus public opt-in rejected papers."],
        "invitation_candidates": ["NeurIPS.cc/2025/Conference/-/Submission"],
    },
    {
        "venue_id": "TMLR",
        "name": "Transactions on Machine Learning Research",
        "year": 2025,
        "category": "top_journal",
        "priority": 1,
        "scope": "rolling_2025_decision_or_activity",
        "review_policy": "open_public_reviews",
        "source_notes": ["Rolling OpenReview journal: pull all public submissions, then filter by 2025 decision/activity."],
        "rolling_venue": True,
        "year_filter": "decision_or_activity_year",
        "invitation_candidates": ["TMLR/-/Submission"],
    },
    {
        "venue_id": "COLM",
        "name": "Conference on Language Modeling",
        "year": 2025,
        "category": "top_conference",
        "priority": 2,
        "scope": "public_openreview_submissions",
        "review_policy": "verify_public_review_coverage",
        "invitation_candidates": ["colmweb.org/2025/Conference/-/Submission"],
    },
    {
        "venue_id": "AISTATS",
        "name": "International Conference on Artificial Intelligence and Statistics",
        "year": 2025,
        "category": "top_conference",
        "priority": 2,
        "scope": "public_openreview_submissions",
        "review_policy": "verify_public_review_coverage",
        "invitation_candidates": [
            "AISTATS.cc/2025/Conference/-/Submission",
            "aistats.org/AISTATS/2025/Conference/-/Submission",
        ],
    },
    {
        "venue_id": "UAI",
        "name": "Conference on Uncertainty in Artificial Intelligence",
        "year": 2025,
        "category": "top_conference",
        "priority": 2,
        "scope": "public_openreview_submissions",
        "review_policy": "verify_public_review_coverage",
        "invitation_candidates": [
            "auai.org/UAI/2025/Conference/-/Submission",
            "UAI.cc/2025/Conference/-/Submission",
        ],
    },
    {
        "venue_id": "CORL",
        "name": "Conference on Robot Learning",
        "year": 2025,
        "category": "top_conference",
        "priority": 2,
        "scope": "public_openreview_submissions",
        "review_policy": "verify_public_review_coverage",
        "invitation_candidates": [
            "robot-learning.org/CoRL/2025/Conference/-/Submission",
            "CoRL.cc/2025/Conference/-/Submission",
        ],
    },
]


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_venue_specs(path: str | Path | None = None) -> list[dict[str, Any]]:
    if not path:
        return [dict(item) for item in DEFAULT_OPENREVIEW_VENUES_2025]
    payload = read_json(path)
    if isinstance(payload, dict):
        venues = payload.get("venues", [])
    else:
        venues = payload
    return [dict(item) for item in venues if isinstance(item, dict)]


def run_openreview_venue_inventory(
    *,
    specs: Iterable[dict[str, Any]],
    sample_limit: int = 50,
    details: str = "replies",
    client: OpenReviewClient | None = None,
    min_review_coverage: float = 0.5,
) -> dict[str, Any]:
    client = client or OpenReviewClient()
    venues = [
        probe_venue(
            client,
            spec,
            sample_limit=sample_limit,
            details=details,
            min_review_coverage=min_review_coverage,
        )
        for spec in specs
    ]
    return {
        "schema_version": VENUE_INVENTORY_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "sample_limit": sample_limit,
        "details": details,
        "summary": summarize_venues(venues),
        "venues": venues,
    }


def probe_venue(
    client: OpenReviewClient,
    spec: dict[str, Any],
    *,
    sample_limit: int,
    details: str,
    min_review_coverage: float,
) -> dict[str, Any]:
    if spec.get("include_in_inventory") is False or spec.get("manual_status"):
        return build_manual_venue_result(spec)

    attempts = []
    for invitation in spec.get("invitation_candidates") or []:
        attempt = probe_invitation(client, str(invitation), sample_limit=sample_limit, details=details)
        attempts.append(attempt)
        if attempt["probe_status"] == "success":
            return build_venue_result(spec, attempt, attempts, min_review_coverage=min_review_coverage)
    return build_failed_venue_result(spec, attempts)


def probe_invitation(
    client: OpenReviewClient,
    invitation: str,
    *,
    sample_limit: int,
    details: str,
) -> dict[str, Any]:
    try:
        payload = client.get_notes(invitation, limit=sample_limit, offset=0, details=details)
    except OpenReviewAPIError as exc:
        return {
            "invitation": invitation,
            "probe_status": classify_openreview_error(exc),
            "error": exc.as_dict(),
        }
    notes = [note for note in payload.get("notes", []) if isinstance(note, dict)]
    papers = [inventory_paper(note) for note in notes]
    return {
        "invitation": invitation,
        "probe_status": "success",
        "api_note_count": len(notes),
        "paper_inventory": papers,
    }


def classify_openreview_error(exc: OpenReviewAPIError) -> str:
    lowered = exc.body.lower()
    if "challengerequirederror" in lowered or "challenge verification required" in lowered or "challengeurl" in lowered:
        return "challenge_required"
    if exc.status_code == 404:
        return "not_found"
    if exc.status_code in {401, 403}:
        return "auth_required"
    if exc.status_code == 400 and ("not found" in lowered or "invalid invitation" in lowered):
        return "not_found"
    if exc.status_code == 0:
        return "network_error"
    return "api_error"


def build_venue_result(
    spec: dict[str, Any],
    attempt: dict[str, Any],
    attempts: list[dict[str, Any]],
    *,
    min_review_coverage: float,
) -> dict[str, Any]:
    papers = attempt.get("paper_inventory", [])
    stats = summarize_paper_inventory(papers)
    review_invitations = summarize_review_invitations(papers)
    if stats["paper_count"] == 0:
        status = "no_sample_notes"
        recommendation = "inspect_invitation"
    elif stats["review_count"] == 0:
        status = "no_public_reviews"
        recommendation = "skip_scoring"
    elif stats["review_coverage_rate"] >= min_review_coverage:
        status = "open_reviews_available"
        recommendation = "pull_and_score"
    else:
        status = "partial_public_reviews"
        recommendation = "inspect_then_score"
    return {
        **venue_identity(spec),
        "status": status,
        "recommendation": recommendation,
        "public_review_evidence": public_review_evidence(spec, api_status=status),
        "selected_invitation": attempt["invitation"],
        "attempts": redact_attempts(attempts),
        "sample_stats": stats,
        "review_invitation_counts": review_invitations,
        "notes": venue_notes(spec, status),
    }


def build_failed_venue_result(spec: dict[str, Any], attempts: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = [attempt.get("probe_status") for attempt in attempts]
    if statuses and all(status == "challenge_required" for status in statuses):
        status = "challenge_required"
        recommendation = "retry_with_openreview_cookie"
    elif statuses and all(status in {"not_found", "no_sample_notes"} for status in statuses):
        status = "not_found"
        recommendation = "verify_invitation"
    elif any(status == "auth_required" for status in statuses):
        status = "auth_required"
        recommendation = "retry_with_openreview_cookie"
    elif any(status == "network_error" for status in statuses):
        status = "network_error"
        recommendation = "retry_later"
    else:
        status = "api_error"
        recommendation = "inspect_error"
    return {
        **venue_identity(spec),
        "status": status,
        "recommendation": recommendation,
        "public_review_evidence": public_review_evidence(spec, api_status=status),
        "selected_invitation": "",
        "attempts": redact_attempts(attempts),
        "sample_stats": empty_sample_stats(),
        "notes": venue_notes(spec, status),
    }


def build_manual_venue_result(spec: dict[str, Any]) -> dict[str, Any]:
    status = str(spec.get("manual_status") or "excluded_no_public_reviews")
    recommendation = str(spec.get("manual_recommendation") or "skip_no_public_reviews")
    return {
        **venue_identity(spec),
        "status": status,
        "recommendation": recommendation,
        "public_review_evidence": public_review_evidence(spec, api_status=status),
        "selected_invitation": "",
        "attempts": [],
        "sample_stats": empty_sample_stats(),
        "review_invitation_counts": {},
        "notes": venue_notes(spec, status),
    }


def venue_identity(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "venue_id": str(spec.get("venue_id") or "").upper(),
        "name": str(spec.get("name") or spec.get("venue_id") or ""),
        "year": int(spec.get("year") or 2025),
        "category": str(spec.get("category") or ""),
        "priority": int(spec.get("priority") or 99),
        "rolling_venue": bool(spec.get("rolling_venue")),
        "year_filter": str(spec.get("year_filter") or ""),
        "scope": str(spec.get("scope") or ""),
        "review_policy": str(spec.get("review_policy") or ""),
        "source_url": str(spec.get("source_url") or ""),
        "evidence_urls": list(spec.get("evidence_urls") or []),
        "source_notes": list(spec.get("source_notes") or []),
        "include_in_inventory": bool(spec.get("include_in_inventory", True)),
        "invitation_candidates": list(spec.get("invitation_candidates") or []),
    }


def public_review_evidence(spec: dict[str, Any], *, api_status: str) -> dict[str, Any]:
    policy = str(spec.get("review_policy") or "")
    scope_decision = str(spec.get("scope_decision") or "")
    priority = int(spec.get("priority") or 99)
    if spec.get("include_in_inventory") is False or scope_decision.startswith("exclude_") or api_status.startswith("excluded_"):
        state = "excluded_no_public_openreview_corpus"
    elif policy in PUBLIC_REVIEW_POLICIES and priority <= 1:
        state = "expected_public_reviews_api_verification_required"
    elif scope_decision == "probe_then_score_if_public":
        state = "candidate_requires_api_probe"
    else:
        state = "unknown_requires_manual_review"
    if api_status in {"open_reviews_available", "partial_public_reviews"}:
        state = "api_confirmed_public_reviews"
    elif api_status == "no_public_reviews":
        state = "api_confirmed_no_public_reviews"
    return {
        "state": state,
        "review_policy": policy,
        "scope_decision": scope_decision,
        "api_status": api_status,
        "evidence_urls": list(spec.get("evidence_urls") or []),
        "source_notes": list(spec.get("source_notes") or []),
    }


def summarize_paper_inventory(papers: list[dict[str, Any]]) -> dict[str, Any]:
    paper_count = len(papers)
    review_count = sum(int(paper.get("review_count") or 0) for paper in papers)
    reply_count = sum(int(paper.get("reply_count") or 0) for paper in papers)
    papers_with_reviews = sum(1 for paper in papers if int(paper.get("review_count") or 0) > 0)
    papers_with_decisions = sum(1 for paper in papers if int(paper.get("decision_count") or 0) > 0)
    papers_with_ratings = sum(1 for paper in papers if paper.get("rating_values"))
    papers_with_confidence = sum(1 for paper in papers if paper.get("confidence_values"))
    return {
        "paper_count": paper_count,
        "reply_count": reply_count,
        "review_count": review_count,
        "papers_with_reviews": papers_with_reviews,
        "review_coverage_rate": round(papers_with_reviews / paper_count, 4) if paper_count else 0,
        "mean_reviews_per_paper": round(review_count / paper_count, 3) if paper_count else 0,
        "papers_with_decisions": papers_with_decisions,
        "decision_coverage_rate": round(papers_with_decisions / paper_count, 4) if paper_count else 0,
        "papers_with_ratings": papers_with_ratings,
        "rating_coverage_rate": round(papers_with_ratings / paper_count, 4) if paper_count else 0,
        "papers_with_confidence": papers_with_confidence,
        "confidence_coverage_rate": round(papers_with_confidence / paper_count, 4) if paper_count else 0,
    }


def summarize_review_invitations(papers: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for paper in papers:
        for example in paper.get("examples", {}).get("official_review", []):
            invitation = str(example.get("invitation") or "")
            if invitation:
                counts[invitation] += 1
        # Fall back to counted official reviews when examples are absent; invitation details are unavailable then.
    return dict(sorted(counts.items()))


def empty_sample_stats() -> dict[str, Any]:
    return summarize_paper_inventory([])


def redact_attempts(attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    redacted = []
    for attempt in attempts:
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
        redacted.append(item)
    return redacted


def venue_notes(spec: dict[str, Any], status: str) -> list[str]:
    notes = list(spec.get("source_notes") or [])
    if spec.get("rolling_venue"):
        notes.append("Rolling venue: full pull must filter by 2025 decision or activity date after download.")
    if status == "challenge_required":
        notes.append("OpenReview challenge required: set OPENREVIEW_COOKIE or OPENREVIEW_TOKEN after browser verification.")
    if status == "partial_public_reviews":
        notes.append("Some sampled papers have public reviews; inspect coverage before full scoring.")
    if status.startswith("excluded_"):
        notes.append("Excluded from scoring queue: no public OpenReview review corpus is expected for this venue.")
    return notes


def summarize_venues(venues: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for venue in venues:
        status = str(venue.get("status") or "")
        counts[status] = counts.get(status, 0) + 1
    ready = [venue["venue_id"] for venue in venues if venue.get("recommendation") == "pull_and_score"]
    needs_auth = [venue["venue_id"] for venue in venues if venue.get("recommendation") == "retry_with_openreview_cookie"]
    inspect = [
        venue["venue_id"]
        for venue in venues
        if venue.get("recommendation") in {"inspect_invitation", "inspect_then_score", "verify_invitation", "inspect_error"}
    ]
    skipped = [venue["venue_id"] for venue in venues if str(venue.get("status") or "").startswith("excluded_")]
    return {
        "venue_count": len(venues),
        "status_counts": dict(sorted(counts.items())),
        "ready_to_pull_and_score": ready,
        "needs_openreview_auth": needs_auth,
        "needs_manual_inspection": inspect,
        "skipped_not_open_review": skipped,
    }


def render_venue_inventory_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# OpenReview Venue Inventory",
        "",
        f"- Created: `{report.get('created_at', '')}`",
        f"- Sample limit: `{report.get('sample_limit', '')}` papers per venue candidate",
        "",
        "## Summary",
        "",
        "| Status | Venues |",
        "| --- | ---: |",
    ]
    for status, count in report.get("summary", {}).get("status_counts", {}).items():
        lines.append(f"| {status} | {count} |")
    lines.extend(
        [
            "",
            "## Venues",
            "",
            "| Venue | Category | Scope | Status | Recommendation | Invitation | Papers | Reviews | Review coverage | Decision coverage | Review invitation samples |",
            "| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for venue in sorted(report.get("venues", []), key=lambda item: (int(item.get("priority") or 99), item.get("venue_id", ""))):
        stats = venue.get("sample_stats") or {}
        invitation = venue.get("selected_invitation") or first_invitation(venue)
        review_invites = ", ".join(list((venue.get("review_invitation_counts") or {}).keys())[:3]) or "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(venue.get("venue_id", "")),
                    str(venue.get("category", "")),
                    str(venue.get("scope", "")),
                    str(venue.get("status", "")),
                    str(venue.get("recommendation", "")),
                    f"`{invitation}`",
                    str(stats.get("paper_count", 0)),
                    str(stats.get("review_count", 0)),
                    f"{float(stats.get('review_coverage_rate') or 0):.1%}",
                    f"{float(stats.get('decision_coverage_rate') or 0):.1%}",
                    f"`{review_invites}`",
                ]
            )
            + " |"
        )
    lines.append("")
    lines.extend(render_attempt_details(report.get("venues", [])))
    return "\n".join(lines)


def first_invitation(venue: dict[str, Any]) -> str:
    candidates = venue.get("invitation_candidates") or []
    return str(candidates[0]) if candidates else ""


def render_attempt_details(venues: list[dict[str, Any]]) -> list[str]:
    lines = ["## Attempt Details", ""]
    for venue in venues:
        lines.append(f"### {venue.get('venue_id', '')}")
        lines.append("")
        for attempt in venue.get("attempts", []):
            line = f"- `{attempt.get('invitation', '')}`: `{attempt.get('probe_status', '')}`"
            error = attempt.get("error")
            if isinstance(error, dict) and error.get("message"):
                line += f" - {error['message']}"
            lines.append(line)
        for note in venue.get("notes", []):
            lines.append(f"- Note: {note}")
        lines.append("")
    return lines


def write_venue_inventory_markdown(report: dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_venue_inventory_markdown(report), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe 2025 OpenReview venues for public review availability.")
    parser.add_argument("--venues", default="", help="Optional JSON list/config of venue specs.")
    parser.add_argument("--out", default="data/validation/openreview_venue_inventory_2025.json")
    parser.add_argument("--markdown", default="reports/validation/openreview_venue_inventory_2025.md")
    parser.add_argument("--sample-limit", type=int, default=50)
    parser.add_argument("--details", default="replies")
    parser.add_argument("--api-base", default="https://api2.openreview.net")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--min-review-coverage", type=float, default=0.5)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    client = OpenReviewClient(base_url=args.api_base, timeout=args.timeout)
    report = run_openreview_venue_inventory(
        specs=load_venue_specs(args.venues or None),
        sample_limit=args.sample_limit,
        details=args.details,
        client=client,
        min_review_coverage=args.min_review_coverage,
    )
    write_json(args.out, report)
    write_venue_inventory_markdown(report, args.markdown)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import datetime as dt
from collections import Counter
from pathlib import Path
from typing import Any

from .normalize import (
    CONFIDENCE_KEYS,
    RATING_KEYS,
    get_replies,
    invitation_text,
    is_review,
    note_id,
    normalize_confidence,
    normalize_rating,
)
from .snapshot import load_snapshot_notes, read_json
from .text import clean_text, text_from_content


DATA_INVENTORY_VERSION = "openreview-data-inventory-v0.1"


def inventory_openreview_snapshot(snapshot_dir: str | Path) -> dict[str, Any]:
    snapshot_dir = Path(snapshot_dir)
    manifest = read_json(snapshot_dir / "manifest.json")
    notes = load_snapshot_notes(snapshot_dir)
    papers = [inventory_paper(note) for note in notes]
    return build_inventory_report(
        papers,
        snapshot={
            "snapshot_dir": str(snapshot_dir),
            "snapshot_id": manifest.get("snapshot_id", ""),
            "source": manifest.get("source", ""),
            "venue": manifest.get("venue", ""),
            "year": manifest.get("year"),
            "query": manifest.get("query", {}),
        },
    )


def inventory_paper(note: dict[str, Any]) -> dict[str, Any]:
    paper_id = note_id(note)
    content = note.get("content") or {}
    replies = get_replies(note)
    classified = [classify_reply(reply) for reply in replies]
    counts = Counter(item["type"] for item in classified)
    signature_counts = Counter(item["signer_role"] for item in classified)

    author_responses = [item for item in classified if item["type"] == "author_response"]
    reviews = [item for item in classified if item["type"] == "official_review"]
    meta_reviews = [item for item in classified if item["type"] == "meta_review"]
    decisions = [item for item in classified if item["type"] == "decision"]
    official_comments = [item for item in classified if item["type"] == "official_comment"]
    reviewer_discussion = [
        item
        for item in official_comments
        if item["signer_role"] in {"reviewer", "area_chair", "program_chair"}
    ]

    earliest_author_response = min((item["cdate_ms"] for item in author_responses if item["cdate_ms"] is not None), default=None)
    post_rebuttal_review_updates = [
        item
        for item in reviews
        if earliest_author_response is not None
        and item["modified_ms"] is not None
        and item["created_ms"] is not None
        and item["modified_ms"] > earliest_author_response
        and item["modified_ms"] > item["created_ms"]
    ]
    post_rebuttal_reviewer_comments = [
        item
        for item in reviewer_discussion
        if earliest_author_response is not None
        and item["created_ms"] is not None
        and item["created_ms"] > earliest_author_response
    ]

    decision_text = first_non_empty(decision["text"] for decision in decisions)
    decision_label = first_non_empty(decision["decision"] for decision in decisions) or clean_text(decision_text)
    rating_values = [item["rating_normalized"] for item in reviews if item["rating_normalized"] is not None]
    confidence_values = [item["confidence_normalized"] for item in reviews if item["confidence_normalized"] is not None]

    availability = {
        "has_reviews": bool(reviews),
        "has_two_or_more_reviews": len(reviews) >= 2,
        "has_ratings": bool(rating_values),
        "has_confidence": bool(confidence_values),
        "has_author_response": bool(author_responses),
        "has_meta_review": bool(meta_reviews),
        "has_meta_review_text": any(item["text"] for item in meta_reviews),
        "has_decision_note": bool(decisions),
        "has_decision_label": bool(decision_label),
        "has_decision_comment_text": any(item["comment_text"] for item in decisions),
        "has_official_comments": bool(official_comments),
        "has_reviewer_or_ac_discussion": bool(reviewer_discussion),
        "has_post_rebuttal_reviewer_comments": bool(post_rebuttal_reviewer_comments),
        "has_post_rebuttal_review_update": bool(post_rebuttal_review_updates),
    }

    return {
        "paper_id": paper_id,
        "forum_id": str(note.get("forum") or paper_id),
        "title": text_from_content(content, ["title"]),
        "decision": decision_label or "Unknown",
        "reply_count": len(replies),
        "note_type_counts": dict(sorted(counts.items())),
        "signer_role_counts": dict(sorted(signature_counts.items())),
        "availability": availability,
        "review_count": len(reviews),
        "author_response_count": len(author_responses),
        "meta_review_count": len(meta_reviews),
        "decision_count": len(decisions),
        "official_comment_count": len(official_comments),
        "reviewer_or_ac_discussion_count": len(reviewer_discussion),
        "post_rebuttal_reviewer_comment_count": len(post_rebuttal_reviewer_comments),
        "post_rebuttal_review_update_count": len(post_rebuttal_review_updates),
        "rating_values": rating_values,
        "confidence_values": confidence_values,
        "earliest_author_response_time": iso_from_ms(earliest_author_response),
        "metric_feasibility": metric_feasibility(availability),
        "examples": {
            "meta_review": note_examples(meta_reviews, limit=2),
            "decision": note_examples(decisions, limit=2),
            "author_response": note_examples(author_responses, limit=2),
            "reviewer_or_ac_discussion": note_examples(reviewer_discussion, limit=2),
            "post_rebuttal_reviewer_comment": note_examples(post_rebuttal_reviewer_comments, limit=2),
            "post_rebuttal_review_update": note_examples(post_rebuttal_review_updates, limit=2),
        },
    }


def classify_reply(reply: dict[str, Any]) -> dict[str, Any]:
    content = reply.get("content") or {}
    invite = invitation_text(reply).lower()
    title = text_from_content(content, ["title"])
    text = reply_text(content)
    signer_role = signer_role_from_signatures(reply.get("signatures") or [])
    note_type = classify_note_type(reply, invite=invite, title=title, text=text, signer_role=signer_role)
    rating_raw = text_from_content(content, RATING_KEYS)
    confidence_raw = text_from_content(content, CONFIDENCE_KEYS)
    return {
        "id": note_id(reply),
        "type": note_type,
        "invitation": invitation_text(reply),
        "signer_role": signer_role,
        "signatures": reply.get("signatures") or [],
        "title": title,
        "text": text,
        "comment_text": text_from_content(content, ["comment"]),
        "decision": text_from_content(content, ["decision", "recommendation"]),
        "rating_raw": rating_raw,
        "rating_normalized": normalize_rating(rating_raw),
        "confidence_raw": confidence_raw,
        "confidence_normalized": normalize_confidence(confidence_raw),
        "created_ms": timestamp_ms(reply, "cdate", "tcdate"),
        "cdate_ms": timestamp_ms(reply, "cdate", "tcdate"),
        "modified_ms": timestamp_ms(reply, "mdate", "tmdate", "tcdate"),
        "created_at": iso_from_ms(timestamp_ms(reply, "cdate", "tcdate")),
        "modified_at": iso_from_ms(timestamp_ms(reply, "mdate", "tmdate", "tcdate")),
        "content_keys": sorted(str(key) for key in content.keys()),
    }


def classify_note_type(
    reply: dict[str, Any],
    *,
    invite: str,
    title: str,
    text: str,
    signer_role: str,
) -> str:
    lowered_title = title.lower()
    lowered_text = text.lower()
    if "meta_review" in invite or "metareview" in invite or "meta-review" in invite:
        return "meta_review"
    if "decision" in invite:
        return "decision"
    if is_review(reply):
        return "official_review"
    if "withdraw" in invite:
        return "withdrawal"
    if is_author_response_like(invite, lowered_title, lowered_text, signer_role):
        return "author_response"
    if "official_comment" in invite or invite.endswith("/-/comment") or "/comment" in invite:
        return "official_comment"
    if "revision" in invite:
        return "revision"
    return "other"


def is_author_response_like(invite: str, title: str, text: str, signer_role: str) -> bool:
    if signer_role == "authors":
        return True
    return (
        "author" in invite
        or "rebuttal" in invite
        or "response" in invite
        or "author response" in title
        or "rebuttal" in title
        or title.startswith("response to reviewer")
        or text.startswith("we thank the reviewer")
        or text.startswith("we thank the reviewers")
    )


def signer_role_from_signatures(signatures: list[Any]) -> str:
    lowered = " ".join(str(signature).lower() for signature in signatures)
    if "authors" in lowered:
        return "authors"
    if "reviewer" in lowered:
        return "reviewer"
    if "area_chair" in lowered or "area-chair" in lowered or "areachair" in lowered:
        return "area_chair"
    if "program_chair" in lowered or "program-chair" in lowered:
        return "program_chair"
    if "ethics" in lowered:
        return "ethics_reviewer"
    if "conference" in lowered:
        return "conference_role"
    return "unknown"


def reply_text(content: dict[str, Any]) -> str:
    keys = [
        "metareview",
        "decision",
        "recommendation",
        "comment",
        "response",
        "rebuttal",
        "summary",
        "strengths",
        "weaknesses",
        "questions",
        "main_review",
        "review",
        "justification_for_why_not_higher_score",
        "justification_for_why_not_lower_score",
        "title",
    ]
    return text_from_content(content, keys)


def timestamp_ms(note: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = note.get(key)
        if isinstance(value, (int, float)):
            return int(value)
    return None


def iso_from_ms(value: int | None) -> str:
    if value is None:
        return ""
    return dt.datetime.fromtimestamp(value / 1000, tz=dt.timezone.utc).replace(microsecond=0).isoformat()


def metric_feasibility(availability: dict[str, bool]) -> dict[str, bool]:
    has_reviews = availability["has_reviews"]
    return {
        "claim_grounding": has_reviews,
        "rebuttal_alignment": has_reviews and availability["has_author_response"],
        "concern_survival_meta_review": has_reviews and availability["has_meta_review_text"],
        "concern_survival_decision_comment": has_reviews and availability["has_decision_comment_text"],
        "concern_survival_meta_or_decision": has_reviews
        and (availability["has_meta_review_text"] or availability["has_decision_comment_text"]),
        "reviewer_discussion_followup": has_reviews and availability["has_reviewer_or_ac_discussion"],
        "post_rebuttal_discussion_followup": has_reviews and availability["has_post_rebuttal_reviewer_comments"],
        "post_rebuttal_review_update_proxy": has_reviews and availability["has_post_rebuttal_review_update"],
        "inter_review_consensus": availability["has_two_or_more_reviews"],
        "rating_text_calibration": has_reviews and availability["has_ratings"],
        "confidence_calibration": has_reviews and availability["has_confidence"],
    }


def build_inventory_report(papers: list[dict[str, Any]], *, snapshot: dict[str, Any]) -> dict[str, Any]:
    paper_count = len(papers)
    availability_counts: Counter[str] = Counter()
    feasibility_counts: Counter[str] = Counter()
    note_type_counts: Counter[str] = Counter()
    signer_role_counts: Counter[str] = Counter()
    for paper in papers:
        availability_counts.update(key for key, value in paper["availability"].items() if value)
        feasibility_counts.update(key for key, value in paper["metric_feasibility"].items() if value)
        note_type_counts.update(paper["note_type_counts"])
        signer_role_counts.update(paper["signer_role_counts"])

    metrics = {
        key: {
            "paper_count": feasibility_counts.get(key, 0),
            "paper_rate": safe_rate(feasibility_counts.get(key, 0), paper_count),
            "status": feasibility_status(key, feasibility_counts.get(key, 0), paper_count),
        }
        for key in sorted(metric_names())
    }

    return {
        "schema_version": "0.1",
        "inventory_version": DATA_INVENTORY_VERSION,
        "snapshot": snapshot,
        "summary": {
            "paper_count": paper_count,
            "reply_count": sum(paper["reply_count"] for paper in papers),
            "note_type_counts": dict(sorted(note_type_counts.items())),
            "signer_role_counts": dict(sorted(signer_role_counts.items())),
            "availability_counts": availability_summary(availability_counts, paper_count),
            "metric_feasibility": metrics,
        },
        "papers": papers,
    }


def metric_names() -> set[str]:
    return set(metric_feasibility({key: True for key in [
        "has_reviews",
        "has_author_response",
        "has_meta_review_text",
        "has_decision_comment_text",
        "has_reviewer_or_ac_discussion",
        "has_post_rebuttal_reviewer_comments",
        "has_post_rebuttal_review_update",
        "has_two_or_more_reviews",
        "has_ratings",
        "has_confidence",
    ]}).keys())


def availability_summary(counts: Counter[str], paper_count: int) -> dict[str, dict[str, float | int]]:
    return {
        key: {"paper_count": count, "paper_rate": safe_rate(count, paper_count)}
        for key, count in sorted(counts.items())
    }


def feasibility_status(metric_name: str, count: int, paper_count: int) -> str:
    if count == 0:
        return "not_available"
    rate = count / paper_count if paper_count else 0.0
    if metric_name in {"post_rebuttal_review_update_proxy", "concern_survival_decision_comment"} and rate < 0.2:
        return "limited"
    if rate >= 0.8:
        return "strong"
    if rate >= 0.4:
        return "usable"
    return "limited"


def note_examples(notes: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    examples = []
    for note in notes[:limit]:
        examples.append(
            {
                "id": note["id"],
                "type": note["type"],
                "signer_role": note["signer_role"],
                "created_at": note["created_at"],
                "modified_at": note["modified_at"],
                "title": truncate(note["title"], 140),
                "text": truncate(note["text"], 360),
            }
        )
    return examples


def first_non_empty(values: Any) -> str:
    for value in values:
        cleaned = clean_text(value)
        if cleaned:
            return cleaned
    return ""


def write_inventory_markdown(report: dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_inventory_markdown(report), encoding="utf-8")


def render_inventory_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# OpenReview Data Inventory",
        "",
        f"- Snapshot: `{report['snapshot'].get('snapshot_id', '')}`",
        f"- Venue/year: `{report['snapshot'].get('venue', '')} {report['snapshot'].get('year', '')}`",
        f"- Papers: {summary['paper_count']}",
        f"- Replies: {summary['reply_count']}",
        "",
        "## Metric Feasibility",
        "",
        "| Metric | Papers | Rate | Status |",
        "| --- | ---: | ---: | --- |",
    ]
    for metric, item in summary["metric_feasibility"].items():
        lines.append(
            f"| `{metric}` | {item['paper_count']} | {format_rate(item['paper_rate'])} | `{item['status']}` |"
        )

    lines.extend(["", "## Availability", "", "| Signal | Papers | Rate |", "| --- | ---: | ---: |"])
    for signal, item in summary["availability_counts"].items():
        lines.append(f"| `{signal}` | {item['paper_count']} | {format_rate(item['paper_rate'])} |")

    lines.extend(["", "## Note Types", "", "| Type | Count |", "| --- | ---: |"])
    for note_type, count in summary["note_type_counts"].items():
        lines.append(f"| `{note_type}` | {count} |")

    lines.extend(["", "## Recommended Validation Tracks", ""])
    lines.extend(recommended_tracks(report))
    lines.extend(["", "## Papers With Rich Follow-Up", ""])
    rich = sorted(
        report["papers"],
        key=lambda paper: (
            paper["post_rebuttal_reviewer_comment_count"],
            paper["reviewer_or_ac_discussion_count"],
            paper["author_response_count"],
        ),
        reverse=True,
    )
    for paper in rich[:10]:
        lines.append(
            f"- `{paper['paper_id']}`: {paper['title']} "
            f"(responses={paper['author_response_count']}, reviewer/AC comments={paper['reviewer_or_ac_discussion_count']}, "
            f"post-rebuttal comments={paper['post_rebuttal_reviewer_comment_count']}, decision={paper['decision']})"
        )
    lines.append("")
    return "\n".join(lines)


def recommended_tracks(report: dict[str, Any]) -> list[str]:
    metrics = report["summary"]["metric_feasibility"]
    lines = []
    if metrics["concern_survival_meta_review"]["status"] in {"strong", "usable"}:
        lines.append("- `Concern Survival`: use claim overlap with meta-review as the first measurable downstream proxy.")
    if metrics["rebuttal_alignment"]["status"] in {"strong", "usable"}:
        lines.append("- `Rebuttal Alignment`: measure whether extracted claims are addressed by author responses.")
    if metrics["post_rebuttal_discussion_followup"]["status"] in {"strong", "usable", "limited"}:
        lines.append("- `Post-Rebuttal Follow-Up`: use reviewer/AC comments after rebuttal as a smaller but high-value signal.")
    if metrics["inter_review_consensus"]["status"] in {"strong", "usable"}:
        lines.append("- `Inter-Review Consensus`: measure whether independent reviewers raise similar claims.")
    if metrics["post_rebuttal_review_update_proxy"]["status"] == "not_available":
        lines.append("- `Score Movement`: not reliable from this snapshot alone unless raw note revision history is fetched.")
    return lines or ["- No strong validation track found in this snapshot."]


def safe_rate(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(count / total, 4)


def format_rate(rate: float) -> str:
    return f"{rate * 100:.1f}%"


def truncate(text: Any, limit: int) -> str:
    cleaned = clean_text(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."

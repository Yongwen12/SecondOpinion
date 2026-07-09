from __future__ import annotations

import datetime as dt
import hashlib
import re
from typing import Any

from .text import clean_text, first_number, text_from_content, unwrap_content_value


REVIEW_INVITATION_RE = re.compile(r"/-/((official_)?review\d*)$")

REVIEW_TEXT_KEYS = [
    "summary",
    "main_review",
    "review",
    "strengths",
    "weaknesses",
    "questions",
    "questions_for_authors",
    "limitations",
    "clarity,_quality,_novelty_and_reproducibility",
    "summary_of_the_paper",
    "contributions",
    "claims_and_evidence",
    "methods_and_evaluation_criteria",
    "theoretical_claims",
    "experimental_designs_or_analyses",
    "supplementary_material",
    "relation_to_broader_scientific_literature",
    "essential_references_not_discussed",
    "other_strengths_and_weaknesses",
    "other_comments_or_suggestions",
    "strengths_and_weaknesses",
    "quality",
    "clarity",
    "significance",
    "originality",
    "final_justification",
    "ethical_concerns",
    "paper_formatting_concerns",
]

SUMMARY_KEYS = ["summary", "summary_of_the_paper"]
STRENGTH_KEYS = ["strengths"]
WEAKNESS_KEYS = [
    "weaknesses",
    "limitations",
    "other_strengths_and_weaknesses",
    "strengths_and_weaknesses",
]
QUESTION_KEYS = ["questions", "questions_for_authors"]
RATING_KEYS = ["rating", "recommendation", "overall_recommendation"]
CONFIDENCE_KEYS = ["confidence", "reviewer_confidence"]


def normalize_rating(raw: str) -> float | None:
    number = first_number(raw)
    if number is None:
        return None
    lowered = raw.lower()
    if number <= 5 and ("/5" in lowered or "out of 5" in lowered):
        return round((number / 5) * 10, 2)
    if number <= 10:
        return round(number, 2)
    return None


def normalize_confidence(raw: str) -> float | None:
    number = first_number(raw)
    if number is None:
        return None
    if number <= 5:
        return round((number / 5) * 10, 2)
    if number <= 10:
        return round(number, 2)
    return None


def normalize_pdf_url(value: Any) -> str:
    value = unwrap_content_value(value)
    if not value:
        return ""
    text = str(value)
    if text.startswith("http"):
        return text
    if text.startswith("/"):
        return f"https://openreview.net{text}"
    if text.startswith("pdf?"):
        return f"https://openreview.net/{text}"
    return text


def note_id(note: dict[str, Any]) -> str:
    return str(note.get("id") or note.get("forum") or stable_id(note))


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


def note_timestamps(note: dict[str, Any]) -> dict[str, Any]:
    created_ms = timestamp_ms(note, "cdate", "tcdate")
    modified_ms = timestamp_ms(note, "mdate", "tmdate", "tcdate")
    return {
        "created_ms": created_ms,
        "modified_ms": modified_ms,
        "created_at": iso_from_ms(created_ms),
        "modified_at": iso_from_ms(modified_ms),
    }


def stable_id(value: Any) -> str:
    payload = repr(value).encode("utf-8")
    return hashlib.sha1(payload).hexdigest()[:12]


def invitation_values(note: dict[str, Any]) -> list[str]:
    raw_invitations = note.get("invitations") or []
    if isinstance(raw_invitations, str):
        invitations = [raw_invitations]
    elif isinstance(raw_invitations, list):
        invitations = list(raw_invitations)
    else:
        invitations = []
    invitation = note.get("invitation")
    if invitation:
        invitations.append(invitation)
    return [str(item) for item in invitations]


def invitation_text(note: dict[str, Any]) -> str:
    return " ".join(invitation_values(note))


def first_content_text(content: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        text = text_from_content(content, [key])
        if text:
            return text
    return ""


def is_review_invitation(invitation: str) -> bool:
    return bool(REVIEW_INVITATION_RE.search(invitation.lower()))


def get_replies(note: dict[str, Any]) -> list[dict[str, Any]]:
    details = note.get("details") or {}
    replies = details.get("replies") or note.get("replies") or []
    return [reply for reply in replies if isinstance(reply, dict)]


def is_review(reply: dict[str, Any]) -> bool:
    return any(is_review_invitation(invitation) for invitation in invitation_values(reply))


def is_decision(reply: dict[str, Any]) -> bool:
    invite = invitation_text(reply).lower()
    return "decision" in invite or "meta_review" in invite or "metareview" in invite


def is_rebuttal(reply: dict[str, Any]) -> bool:
    invite = invitation_text(reply).lower()
    content = reply.get("content") or {}
    title = text_from_content(content, ["title"]).lower()
    return (
        "author" in invite
        or "rebuttal" in invite
        or "response" in invite
        or "author response" in title
        or "rebuttal" in title
    )


def normalize_review(reply: dict[str, Any], paper_id: str, snapshot_time: str) -> dict[str, Any]:
    content = reply.get("content") or {}
    rating_raw = text_from_content(content, RATING_KEYS)
    confidence_raw = text_from_content(content, CONFIDENCE_KEYS)
    review_id = note_id(reply)
    review_text = text_from_content(content, REVIEW_TEXT_KEYS)
    return {
        "review_id": review_id,
        "paper_id": paper_id,
        "review_text": review_text,
        "summary": first_content_text(content, SUMMARY_KEYS),
        "strengths": text_from_content(content, STRENGTH_KEYS),
        "weaknesses": text_from_content(content, WEAKNESS_KEYS),
        "questions": text_from_content(content, QUESTION_KEYS),
        "rating_raw": rating_raw,
        "rating_normalized": normalize_rating(rating_raw),
        "confidence_raw": confidence_raw,
        "confidence_normalized": normalize_confidence(confidence_raw),
        "review_stage": "initial",
        "raw_invitation": invitation_text(reply),
        "snapshot_time": snapshot_time,
        "openreview_timestamps": note_timestamps(reply),
    }


def normalize_submission(note: dict[str, Any], *, venue: str, year: int) -> dict[str, Any]:
    snapshot_time = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    content = note.get("content") or {}
    paper_id = note_id(note)
    replies = get_replies(note)

    decision = "Unknown"
    decisions = []
    reviews = []
    for reply in replies:
        if is_review(reply):
            reviews.append(normalize_review(reply, paper_id, snapshot_time))
        elif is_decision(reply):
            decision_text = text_from_content(reply.get("content") or {}, ["decision", "recommendation", "comment"])
            if decision_text:
                decision = decision_text
            decisions.append({"id": note_id(reply), "text": decision_text, "openreview_timestamps": note_timestamps(reply)})

    return {
        "paper_id": paper_id,
        "openreview_forum_id": str(note.get("forum") or paper_id),
        "venue": venue,
        "year": year,
        "title": text_from_content(content, ["title"]),
        "abstract": text_from_content(content, ["abstract"]),
        "authors_anonymized": bool(text_from_content(content, ["authors"]).lower().find("anonymous") >= 0),
        "decision": clean_text(decision),
        "reviews": reviews,
        "decisions": decisions,
        "raw_invitation": invitation_text(note),
        "snapshot_time": snapshot_time,
        "openreview_timestamps": note_timestamps(note),
    }


def normalize_openreview_notes(notes: list[dict[str, Any]], *, venue: str, year: int) -> dict[str, Any]:
    papers = [normalize_submission(note, venue=venue, year=year) for note in notes]
    return {
        "dataset": f"{venue.lower()}_{year}",
        "schema_version": "0.1",
        "paper_count": len(papers),
        "review_count": sum(len(paper.get("reviews", [])) for paper in papers),
        "papers": papers,
    }

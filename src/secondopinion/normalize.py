from __future__ import annotations

import datetime as dt
import hashlib
from typing import Any

from .text import clean_text, first_number, text_from_content, unwrap_content_value


REVIEW_TEXT_KEYS = [
    "summary",
    "main_review",
    "review",
    "strengths",
    "weaknesses",
    "questions",
    "limitations",
    "clarity,_quality,_novelty_and_reproducibility",
    "summary_of_the_paper",
    "contributions",
]

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


def stable_id(value: Any) -> str:
    payload = repr(value).encode("utf-8")
    return hashlib.sha1(payload).hexdigest()[:12]


def invitation_text(note: dict[str, Any]) -> str:
    invitations = note.get("invitations") or []
    if isinstance(invitations, str):
        invitations = [invitations]
    invitation = note.get("invitation")
    if invitation:
        invitations.append(invitation)
    return " ".join(str(item) for item in invitations)


def get_replies(note: dict[str, Any]) -> list[dict[str, Any]]:
    details = note.get("details") or {}
    replies = details.get("replies") or note.get("replies") or []
    return [reply for reply in replies if isinstance(reply, dict)]


def is_review(reply: dict[str, Any]) -> bool:
    invite = invitation_text(reply).lower()
    return "official_review" in invite or invite.endswith("/-/review") or "/review" in invite


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
    field_text = {key: text_from_content(content, [key]) for key in REVIEW_TEXT_KEYS if key in content}
    review_text = text_from_content(content, REVIEW_TEXT_KEYS)
    return {
        "review_id": review_id,
        "paper_id": paper_id,
        "review_text": review_text,
        "summary": field_text.get("summary", "") or field_text.get("summary_of_the_paper", ""),
        "strengths": field_text.get("strengths", ""),
        "weaknesses": field_text.get("weaknesses", ""),
        "questions": field_text.get("questions", ""),
        "rating_raw": rating_raw,
        "rating_normalized": normalize_rating(rating_raw),
        "confidence_raw": confidence_raw,
        "confidence_normalized": normalize_confidence(confidence_raw),
        "review_stage": "initial",
        "raw_invitation": invitation_text(reply),
        "snapshot_time": snapshot_time,
    }


def normalize_submission(note: dict[str, Any], *, venue: str, year: int) -> dict[str, Any]:
    snapshot_time = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    content = note.get("content") or {}
    paper_id = note_id(note)
    replies = get_replies(note)

    decision = "Unknown"
    decisions = []
    rebuttals = []
    reviews = []
    for reply in replies:
        if is_review(reply):
            reviews.append(normalize_review(reply, paper_id, snapshot_time))
        elif is_decision(reply):
            decision_text = text_from_content(reply.get("content") or {}, ["decision", "recommendation", "comment"])
            if decision_text:
                decision = decision_text
            decisions.append({"id": note_id(reply), "text": decision_text})
        elif is_rebuttal(reply):
            rebuttals.append(
                {
                    "id": note_id(reply),
                    "text": text_from_content(reply.get("content") or {}, ["comment", "response", "rebuttal", "title"]),
                }
            )

    return {
        "paper_id": paper_id,
        "openreview_forum_id": str(note.get("forum") or paper_id),
        "venue": venue,
        "year": year,
        "title": text_from_content(content, ["title"]),
        "abstract": text_from_content(content, ["abstract"]),
        "authors_anonymized": bool(text_from_content(content, ["authors"]).lower().find("anonymous") >= 0),
        "pdf_url": normalize_pdf_url(content.get("pdf")),
        "decision": clean_text(decision),
        "reviews": reviews,
        "rebuttals": rebuttals,
        "decisions": decisions,
        "raw_invitation": invitation_text(note),
        "snapshot_time": snapshot_time,
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

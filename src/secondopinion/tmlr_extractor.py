from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import time
from pathlib import Path
from typing import Any, Iterable

from .normalize import clean_text, iso_from_ms, note_id, note_timestamps
from .openreview_client import OpenReviewClient
from .text import text_from_content


def content_value(content: dict[str, Any], key: str) -> str:
    return text_from_content(content, [key])


def invitation_values(note: dict[str, Any]) -> list[str]:
    raw = note.get("invitations") or []
    values = [raw] if isinstance(raw, str) else list(raw) if isinstance(raw, list) else []
    if note.get("invitation"):
        values.append(note["invitation"])
    return [str(value) for value in values]


def is_official_comment(note: dict[str, Any]) -> bool:
    return any("/-/Official_Comment" in invitation for invitation in invitation_values(note))


def timestamp_year(note: dict[str, Any]) -> int | None:
    stamps = [note.get(key) for key in ("mdate", "tmdate", "tcdate", "cdate")]
    for stamp in stamps:
        if isinstance(stamp, (int, float)):
            return dt.datetime.fromtimestamp(int(stamp) / 1000, tz=dt.timezone.utc).year
    return None


def venue_status(note: dict[str, Any]) -> str:
    venue = (note.get("content") or {}).get("venue")
    if isinstance(venue, dict):
        venue = venue.get("value")
    return str(venue or "")


def include_submission(note: dict[str, Any], *, year: int) -> bool:
    status = venue_status(note).lower()
    decided = any(word in status for word in ("accepted", "rejected", "withdrawn"))
    return decided or timestamp_year(note) == year


def substantial_comment_text(note: dict[str, Any]) -> str:
    content = note.get("content") or {}
    title = content_value(content, "title")
    comment = content_value(content, "comment")
    text = "\n".join(part for part in [title, comment] if part).strip()
    # Skip administrative one-liners; keep the threshold low because TMLR comments can be compact.
    return text if len(re.sub(r"\s+", " ", text)) >= 80 else ""



AUTHOR_RESPONSE_PATTERNS = [
    re.compile(pattern, re.I | re.S)
    for pattern in [
        r"\b(response|reply) to (reviewer|referee|comments?)\b",
        r"\bauthor response\b|\brebuttal\b",
        r"\bwe (sincerely )?(thank|appreciate) (the |all )?(reviewer|reviewers|referee|referees|action editor|ae)\b",
        r"\bwe have (uploaded|revised|updated|added|included|addressed|incorporated)\b.{0,120}\b(manuscript|paper|revision|version|appendix|section)\b",
        r"\b(uploaded|submitted) (a )?(revised|revision|camera-ready|camera ready|deanonymi[sz]ed|final)\b",
        r"\bsummary of changes\b|\brevised manuscript\b|\bfinal version\b|\bcamera-ready\b|\bcamera ready\b",
        r"\bdear (action editor|ae|reviewer|reviewers|referee|referees)\b",
        r"\bplease confirm\b|\bmay we ask\b|\bcould you please\b",
    ]
]

REVIEWER_SIGNAL_PATTERNS = [
    re.compile(pattern, re.I | re.S)
    for pattern in [
        r"\b(weakness|weaknesses|strength|strengths|concern|concerns|limitation|limitations)\b",
        r"\b(the paper|this paper|the manuscript|this manuscript|the submission|this submission)\b",
        r"\b(recommend|accept|reject|revision|required|minor revision|major revision)\b",
        r"\bthe authors?\b",
    ]
]


def is_likely_author_or_admin_comment(text: str) -> bool:
    compact = re.sub(r"\s+", " ", text or "").strip()
    if not compact:
        return True
    return any(pattern.search(compact) for pattern in AUTHOR_RESPONSE_PATTERNS)


def is_likely_review_comment(note: dict[str, Any]) -> bool:
    text = substantial_comment_text(note)
    if not text or is_likely_author_or_admin_comment(text):
        return False
    return any(pattern.search(text) for pattern in REVIEWER_SIGNAL_PATTERNS)

def normalize_tmlr_comment(comment: dict[str, Any], paper_id: str, snapshot_time: str) -> dict[str, Any]:
    content = comment.get("content") or {}
    title = content_value(content, "title")
    body = content_value(content, "comment")
    text = "\n".join(part for part in [title, body] if part).strip()
    return {
        "review_id": note_id(comment),
        "paper_id": paper_id,
        "review_text": clean_text(text),
        "summary": clean_text(title),
        "strengths": "",
        "weaknesses": clean_text(body),
        "questions": "",
        "rating_raw": "",
        "rating_normalized": None,
        "confidence_raw": "",
        "confidence_normalized": None,
        "review_stage": "tmlr_official_comment",
        "raw_invitation": " ".join(invitation_values(comment)),
        "snapshot_time": snapshot_time,
        "openreview_timestamps": note_timestamps(comment),
    }


def normalize_tmlr_submission(note: dict[str, Any], *, year: int, snapshot_time: str) -> dict[str, Any]:
    content = note.get("content") or {}
    paper_id = note_id(note)
    replies = (note.get("details") or {}).get("replies") or note.get("replies") or []
    comments = [reply for reply in replies if isinstance(reply, dict) and is_official_comment(reply) and is_likely_review_comment(reply)]
    reviews = [normalize_tmlr_comment(comment, paper_id, snapshot_time) for comment in comments]
    status = venue_status(note)
    return {
        "paper_id": paper_id,
        "openreview_forum_id": str(note.get("forum") or paper_id),
        "venue": "TMLR",
        "year": year,
        "title": content_value(content, "title"),
        "abstract": content_value(content, "abstract"),
        "authors_anonymized": "anonymous" in content_value(content, "authors").lower(),
        "decision": clean_text(status or "Unknown"),
        "reviews": reviews,
        "decisions": [],
        "raw_invitation": " ".join(invitation_values(note)),
        "snapshot_time": snapshot_time,
        "openreview_timestamps": note_timestamps(note),
    }


def pull_tmlr_normalized(
    *,
    year: int = 2025,
    limit: int | None = None,
    page_size: int = 100,
    max_pages: int | None = None,
    polite_delay: float = 0.1,
    output: str | Path,
) -> dict[str, Any]:
    client = OpenReviewClient(timeout=90)
    snapshot_time = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    papers: list[dict[str, Any]] = []
    scanned = 0
    offset = 0
    pages = 0
    while True:
        if limit is not None and len(papers) >= limit:
            break
        if max_pages is not None and pages >= max_pages:
            break
        payload = client.get_notes("TMLR/-/Submission", limit=page_size, offset=offset, details="all")
        notes = [note for note in payload.get("notes") or [] if isinstance(note, dict)]
        if not notes:
            break
        scanned += len(notes)
        for note in notes:
            if not include_submission(note, year=year):
                continue
            paper = normalize_tmlr_submission(note, year=year, snapshot_time=snapshot_time)
            if paper["reviews"]:
                papers.append(paper)
                if limit is not None and len(papers) >= limit:
                    break
        offset += len(notes)
        pages += 1
        if len(notes) < page_size:
            break
        if polite_delay:
            time.sleep(polite_delay)
    payload = {
        "dataset": f"tmlr_{year}",
        "schema_version": "0.1",
        "source": "TMLR/-/Submission + paper-level Official_Comment replies",
        "scanned_submission_count": scanned,
        "paper_count": len(papers),
        "review_count": sum(len(paper.get("reviews", [])) for paper in papers),
        "papers": papers,
    }
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "output": str(out),
        "scanned_submission_count": scanned,
        "paper_count": payload["paper_count"],
        "review_count": payload["review_count"],
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Pull TMLR public Official_Comment threads into normalized format.")
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--limit", type=int, default=None, help="Limit normalized papers with extracted comments.")
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--polite-delay", type=float, default=0.1)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(pull_tmlr_normalized(**vars(args)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

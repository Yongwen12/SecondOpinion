from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


PUBLIC_SCORECARD_VERSION = "reviewer-public-scorecard-v0.1"

DIMENSION_LABELS = {
    "specificity": ("Specificity", "How concrete and inspectable the reviewer comment is."),
    "substantiation": ("Evidence Link", "Whether the comment gives reasons, evidence, or manuscript anchors."),
    "actionability": ("Actionability", "Whether the authors can turn the comment into a response or revision."),
    "consensus_conflict": ("Peer Support", "Whether nearby reviewer signals support or conflict with this concern."),
    "rebuttal_robustness": ("Rebuttal Risk", "Whether the concern still matters after the author response."),
    "professionalism": ("Tone", "Whether the comment is constructive, calibrated, and professional."),
}

STOPWORDS = {
    "the", "and", "that", "this", "with", "from", "into", "after", "before", "should", "would", "could",
    "paper", "review", "reviewer", "authors", "author", "claim", "claims", "method", "response", "section",
    "more", "some", "which", "what", "when", "where", "why", "how", "does", "still", "about", "against",
}

NICKNAME_RULES = [
    ("baseline", "Baseline Hawk"),
    ("runtime", "Baseline Hawk"),
    ("theorem", "Assumption Mapper"),
    ("assumption", "Assumption Mapper"),
    ("ablation", "Evidence Anchor"),
    ("evidence", "Evidence Anchor"),
    ("novelty", "Novelty Scout"),
    ("tone", "Tone Drift"),
]

FALLBACK_NICKNAMES = [
    "Signal Cartographer",
    "Checklist Pilot",
    "Careful Mapper",
    "Scope Needle",
    "Polite Fog",
    "Vague Thunder",
]


PUBLIC_DATASET_STUB = {
    "schema_version": PUBLIC_SCORECARD_VERSION,
    "paper": {
        "title": "SecondOpinion reviewer scorecard",
        "conference": "ICLR",
        "year": 2026,
    },
    "summary": {},
    "reviewers": [],
    "comments": [],
    "topics": [],
    "leaderboards": {"red": [], "black": []},
}


def build_public_scorecard(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload.get("reviewers"), list):
        raise ValueError("Input does not contain a reviewers list.")
    reviewers = [public_reviewer(item, index) for index, item in enumerate(payload.get("reviewers", []), start=1)]
    comments = [comment for reviewer in reviewers for comment in reviewer.pop("_comments")]
    for index, comment in enumerate(comments, start=1):
        comment["chunk_id"] = f"C{index}"
    topics = build_topics(reviewers, comments)
    public = {
        "schema_version": PUBLIC_SCORECARD_VERSION,
        "paper": public_paper(payload.get("paper", {})),
        "summary": public_summary(payload.get("summary", {}), reviewers, comments),
        "reviewers": reviewers,
        "comments": comments,
        "topics": topics,
        "leaderboards": build_leaderboards(reviewers),
    }
    return public


def public_paper(paper: dict[str, Any]) -> dict[str, Any]:
    venue = str(paper.get("venue", "ICLR") or "ICLR")
    year = paper.get("year", 2026)
    title = str(paper.get("title", "Reviewer Signal Demo Submission") or "Reviewer Signal Demo Submission")
    if "hybrid scoring memory" in title.lower():
        title = "Reviewer Signal Demo Submission"
    return {
        "title": title,
        "conference": f"{venue} {year}".strip(),
        "venue": venue,
        "year": year,
    }


def public_summary(summary: dict[str, Any], reviewers: list[dict[str, Any]], comments: list[dict[str, Any]]) -> dict[str, Any]:
    overall = round(mean(reviewer["score"] for reviewer in reviewers)) if reviewers else 0
    return {
        "overall_score": overall,
        "signal_label": signal_label(overall),
        "reviewer_count": len(reviewers),
        "comment_count": len(comments),
        "topic_count": len({topic for comment in comments for topic in comment.get("topics", [])}),
        "situation": "Reviewer comments are scored first, then surfaced as public-facing review signals.",
    }


def public_reviewer(reviewer: dict[str, Any], index: int) -> dict[str, Any]:
    internal_id = str(reviewer.get("display_id", f"R{index}") or f"R{index}")
    claims = [claim for claim in reviewer.get("claims", []) if isinstance(claim, dict)]
    dimension_scores = aggregate_dimensions(claims)
    score = round(mean(dimension_scores.values())) if dimension_scores else 0
    text_blob = " ".join(str(claim.get("claim_text", "")) for claim in claims)
    nickname = nickname_for(text_blob, index=index, score=score)
    comments = public_comments(internal_id, nickname, claims)
    return {
        "reviewer_key": internal_id,
        "nickname": nickname,
        "avatar_key": avatar_key(index),
        "score": score,
        "tone": tone_for_score(score),
        "label": signal_label(score),
        "summary": str(reviewer.get("summary", "Reviewer comments scored by SecondOpinion.")),
        "rating": reviewer.get("rating"),
        "confidence": reviewer.get("confidence"),
        "social": default_social_counts(score, index),
        "dimensions": [
            {
                "key": key,
                "label": DIMENSION_LABELS[key][0],
                "score": dimension_scores.get(key, 0),
                "criterion": dimension_criterion(key, dimension_scores.get(key, 0)),
            }
            for key in DIMENSION_LABELS
        ],
        "topics": top_keywords(text_blob, limit=5),
        "_comments": comments,
    }


def aggregate_dimensions(claims: list[dict[str, Any]]) -> dict[str, int]:
    values: dict[str, list[float]] = {key: [] for key in DIMENSION_LABELS}
    for claim in claims:
        scores = claim.get("hybrid_scores", {})
        if not isinstance(scores, dict):
            continue
        for key in DIMENSION_LABELS:
            score = scores.get(key, {})
            if isinstance(score, dict) and score.get("final_score") is not None:
                values[key].append(float(score["final_score"]) * 100)
    return {key: round(mean(items)) for key, items in values.items() if items}


def public_comments(reviewer_key: str, nickname: str, claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    comments = []
    for index, claim in enumerate(claims, start=1):
        text = str(claim.get("claim_text") or claim.get("source_sentence") or "").strip()
        if not text:
            continue
        take = str(claim.get("second_opinion_take") or claim.get("rebuttal_guidance", {}).get("suggested_response") or "SecondOpinion found a review signal here.")
        score = round(mean(score.get("final_score", 0) * 100 for score in claim.get("hybrid_scores", {}).values() if isinstance(score, dict)))
        comments.append(
            {
                "reviewer_key": reviewer_key,
                "nickname": nickname,
                "chunk_id": f"C{len(comments) + 1}",
                "text": text,
                "second_opinion": take,
                "tone": tone_for_score(score),
                "up": 0,
                "down": 0,
                "topics": top_keywords(text, limit=4),
            }
        )
    return comments


def build_topics(reviewers: list[dict[str, Any]], comments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(topic for comment in comments for topic in comment.get("topics", []))
    topics = []
    for index, (topic, count) in enumerate(counts.most_common(24)):
        comment = next((item for item in comments if topic in item.get("topics", [])), {})
        reviewer = next((item for item in reviewers if item.get("reviewer_key") == comment.get("reviewer_key")), {})
        topics.append(
            {
                "text": topic,
                "size": max(25, min(76, 26 + count * 11 + len(topic))),
                "x": 70 + (index * 154) % 880,
                "y": 64 + (index * 92) % 390,
                "tone": comment.get("tone", "gold"),
                "reviewer_key": comment.get("reviewer_key", ""),
                "nickname": reviewer.get("nickname", comment.get("nickname", "Reviewer")),
                "chunk": comment.get("text", ""),
            }
        )
    return topics


def build_leaderboards(reviewers: list[dict[str, Any]]) -> dict[str, list[str]]:
    red = sorted(reviewers, key=lambda item: (-int(item.get("score") or 0), str(item.get("reviewer_key") or "")))
    black = sorted(reviewers, key=lambda item: (int(item.get("score") or 0), str(item.get("reviewer_key") or "")))
    return {
        "red": [item["reviewer_key"] for item in red[:10]],
        "black": [item["reviewer_key"] for item in black[:10]],
    }




def nickname_for(text: str, *, index: int, score: int) -> str:
    lowered = text.lower()
    if score < 50:
        return "Vague Thunder"
    for needle, nickname in NICKNAME_RULES:
        if needle in lowered:
            return nickname
    return FALLBACK_NICKNAMES[(index - 1) % len(FALLBACK_NICKNAMES)]


def top_keywords(text: str, *, limit: int) -> list[str]:
    words = [word.lower() for word in re.findall(r"[A-Za-z][A-Za-z-]{2,}", text)]
    counts = Counter(word for word in words if word not in STOPWORDS)
    return [word for word, _ in counts.most_common(limit)]


def dimension_criterion(key: str, score: int) -> str:
    label, description = DIMENSION_LABELS[key]
    if score >= 85:
        return f"Strong {label.lower()}: {description}"
    if score >= 70:
        return f"Solid {label.lower()}: {description}"
    if score >= 40:
        return f"Mixed {label.lower()}: useful but uneven."
    return f"Weak {label.lower()}: needs a clearer signal."


def default_social_counts(score: int, index: int) -> dict[str, int]:
    # Community counts come only from real votes in the `votes` table. No seeding.
    return {"up": 0, "down": 0}


def avatar_key(index: int) -> str:
    return f"R{((index - 1) % 3) + 1}"


def signal_label(score: int | float) -> str:
    value = float(score)
    if value >= 85:
        return "High Signal"
    if value >= 70:
        return "Solid Signal"
    if value >= 40:
        return "Needs Signal"
    return "Weak Signal"


def tone_for_score(score: int | float) -> str:
    value = float(score)
    if value >= 85:
        return "green"
    if value >= 70:
        return "blue"
    if value >= 40:
        return "gold"
    return "red"


def mean(values: Any) -> float:
    items = [float(value) for value in values]
    return sum(items) / len(items) if items else 0.0


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Export reviewer-facing public scorecard JSON.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    write_json(args.out, build_public_scorecard(read_json(args.input)))
    print(f"Saved reviewer public scorecard to {args.out}.")


if __name__ == "__main__":
    main()




from __future__ import annotations

import re
from typing import Any

from .text import clean_text, split_review_sentences, tokens


CLAIM_EXTRACTION_VERSION = "claim-extraction-rule-v0.2"

NEGATION_WORDS = ("no ", "not ", "lack", "lacks", "lacking", "missing", "insufficient", "without", "fails to")
ACTION_WORDS = ("should", "could", "recommend", "suggest", "need to", "needs to", "clarify", "include", "compare")
SPECIFICITY_HINTS = (
    "section",
    "table",
    "figure",
    "appendix",
    "experiment",
    "baseline",
    "ablation",
    "equation",
    "theorem",
    "metric",
    "dataset",
    "citation",
    "hyperparameter",
    "training setup",
    "failure case",
)
TONE_PROBLEM_WORDS = (
    "nonsense",
    "ridiculous",
    "lazy",
    "obviously bad",
    "do not understand",
    "no idea",
    "terrible",
    "worthless",
)

CLAIM_TYPES = {
    "tone": TONE_PROBLEM_WORDS,
    "ablation": ("ablation", "component removal", "component study"),
    "baseline": ("baseline", "compare", "comparison", "sota", "state-of-the-art"),
    "experiment": ("experiment", "evaluation", "empirical", "result", "metric"),
    "methodology": ("method", "approach", "algorithm", "architecture", "assumption"),
    "theory": ("theorem", "proof", "lemma", "theory"),
    "novelty": ("novel", "novelty", "original", "incremental"),
    "clarity": ("clarity", "unclear", "notation", "explain", "presentation", "clarify"),
    "writing": ("writing", "grammar", "typo", "readability"),
    "ethics": ("ethic", "privacy", "harm", "safety"),
}

SOURCE_PRIORITY = {
    "weaknesses": 4,
    "questions": 3,
    "review_text": 1,
}


def classify_claim_type(text: str) -> str:
    lowered = text.lower()
    for claim_type, keywords in CLAIM_TYPES.items():
        if any(keyword in lowered for keyword in keywords):
            return claim_type
    return "general"


def infer_importance(text: str, claim_type: str) -> str:
    lowered = text.lower()
    if claim_type == "tone":
        return "tone-only"
    if any(word in lowered for word in ("fatal", "major", "central", "main", "critical", "core")):
        return "major"
    if any(word in lowered for word in ("minor", "small", "typo", "detail")):
        return "minor"
    if lowered.endswith("?"):
        return "question"
    if claim_type in {"baseline", "ablation", "methodology", "experiment", "theory", "novelty"}:
        return "major"
    return "medium"


def extract_claims(review: dict[str, Any], max_claims: int = 8) -> list[dict[str, Any]]:
    candidates = []
    extraction_order = 0
    for source in claim_sources(review):
        for sentence_index, sentence in enumerate(split_review_sentences(source["text"])):
            for fragment_index, fragment in enumerate(split_compound_claims(sentence)):
                candidate = build_candidate(fragment, source["field"], sentence_index, sentence)
                if candidate:
                    candidate["source_fragment_index"] = fragment_index
                    candidate["extraction_order"] = extraction_order
                    extraction_order += 1
                    candidates.append(candidate)

    deduped = dedupe_candidates(candidates)
    deduped.sort(
        key=lambda claim: (
            -SOURCE_PRIORITY.get(str(claim["source_field"]), 0),
            int(claim["source_sentence_index"]),
            int(claim["source_fragment_index"]),
            -int(claim["extraction_score"]),
        )
    )
    return deduped[:max_claims]


def claim_sources(review: dict[str, Any]) -> list[dict[str, str]]:
    sources = []
    for field in ("weaknesses", "questions"):
        value = clean_text(review.get(field))
        if value:
            sources.append({"field": field, "text": value})
    if sources:
        return sources

    review_text = clean_text(review.get("review_text"))
    if not review_text:
        return []
    return [{"field": "review_text", "text": review_text}]


def split_compound_claims(sentence: str) -> list[str]:
    sentence = clean_text(sentence)
    if not sentence:
        return []
    parts = re.split(r"\s+(?:and|but|however|while)\s+", sentence)
    if len(parts) == 1 or len(parts) > 4:
        return [sentence]

    fragments = []
    for part in parts:
        fragment = normalize_fragment(part)
        if fragment:
            fragments.append(fragment)
    return fragments or [sentence]


def normalize_fragment(fragment: str) -> str:
    fragment = clean_text(fragment.strip(" ,;:"))
    if not fragment:
        return ""
    lowered = fragment.lower()
    if re.match(r"^(?:does|do|did|is|are|has|have|lacks?|fails?|missing|should|could|needs?|cannot|not)\b", lowered):
        fragment = f"The paper {fragment}"
    elif re.match(r"^(?:include|provide|discuss|explain|clarify|compare|report)\b", lowered):
        fragment = f"The paper should {fragment}"
    if fragment[-1] not in ".!?":
        fragment += "."
    return fragment


def build_candidate(
    text: str,
    source_field: str,
    source_sentence_index: int,
    source_sentence: str,
) -> dict[str, Any] | None:
    text = clean_text(text)
    if len(tokens(text)) < 3:
        return None

    lowered = text.lower()
    reasons = []
    score = SOURCE_PRIORITY.get(source_field, 1)
    claim_type = classify_claim_type(text)

    if source_field == "questions" or text.endswith("?"):
        reasons.append("question")
        score += 2
    if any(word in lowered for word in NEGATION_WORDS) or any(word in lowered for word in ("unclear", "confusing")):
        reasons.append("criticism-cue")
        score += 3
    if any(word in lowered for word in SPECIFICITY_HINTS):
        reasons.append("specific-evidence-target")
        score += 2
    if any(word in lowered for word in ACTION_WORDS):
        reasons.append("actionable-request")
        score += 2
    if any(word in lowered for word in TONE_PROBLEM_WORDS):
        reasons.append("tone-issue")
        score += 4
    if claim_type != "general":
        reasons.append(f"type:{claim_type}")
        score += 1

    if not reasons:
        return None

    return {
        "claim_text": text,
        "claim_type": claim_type,
        "importance": infer_importance(text, claim_type),
        "source_field": source_field,
        "source_sentence_index": source_sentence_index,
        "source_sentence": clean_text(source_sentence),
        "extraction_reason": ", ".join(reasons),
        "extraction_score": score,
        "extraction_version": CLAIM_EXTRACTION_VERSION,
    }


def dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best_by_text: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        key = re.sub(r"\W+", " ", str(candidate["claim_text"]).lower()).strip()
        previous = best_by_text.get(key)
        if previous is None or candidate["extraction_score"] > previous["extraction_score"]:
            best_by_text[key] = candidate
    return list(best_by_text.values())

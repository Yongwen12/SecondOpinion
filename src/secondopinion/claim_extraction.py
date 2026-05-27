from __future__ import annotations

import json
import re
from typing import Any, Protocol

from .model_config import DEFAULT_CHEAP_MODEL
from .prompt_assets import load_prompt
from .text import clean_text


CLAIM_EXTRACTION_VERSION = "claim-extraction-llm-v0.3"
DEFAULT_CLAIM_MODEL = DEFAULT_CHEAP_MODEL

CLAIM_TYPE_VALUES = (
    "ablation",
    "baseline",
    "experiment",
    "methodology",
    "theory",
    "novelty",
    "clarity",
    "writing",
    "ethics",
    "tone",
    "general",
)
IMPORTANCE_VALUES = ("major", "medium", "minor", "question", "tone-only")
SOURCE_FIELDS = ("weaknesses", "questions", "review_text", "strengths", "summary")

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

NEGATIVE_OR_LIMITATION_CUES = (
    "lack",
    "lacks",
    "lacking",
    "missing",
    "insufficient",
    "inadequate",
    "incomplete",
    "unclear",
    "vague",
    "ambiguous",
    "confusing",
    "limited",
    "weak",
    "concern",
    "issue",
    "problem",
    "fails",
    "failure",
    "hard to",
    "difficult to",
    "does not",
    "do not",
    "doesn't",
    "don't",
    "cannot",
    "can't",
    "without comparison",
    "without ablation",
    "without baseline",
    "without evaluation",
    "without experiment",
    "without analysis",
    "without explanation",
    "overclaim",
    "overstate",
    "not convincing",
    "not clear",
    "not enough",
    "not well",
)
ACTIONABLE_CUES = (
    "should",
    "recommend",
    "suggest",
    "need to",
    "needs to",
    "clarify",
    "include",
    "compare",
    "improve",
    "add",
    "address",
    "explain",
    "discuss",
    "justify",
    "would benefit",
)
QUESTION_STARTERS = (
    "what",
    "why",
    "how",
    "when",
    "where",
    "which",
    "could",
    "can",
    "would",
    "does",
    "do",
    "did",
    "is",
    "are",
)
CONTRAST_CUES = (
    "but",
    "however",
    "although",
    "though",
    "nevertheless",
    "yet",
    "despite",
    "while",
    "whereas",
    "on the other hand",
)
SCORE_JUSTIFICATION_CUES = (
    "rating",
    "score",
    "weak accept",
    "weak reject",
    "borderline",
    "accept",
    "reject",
)
DEDUPE_STOPWORDS = {
    "a",
    "an",
    "and",
    "any",
    "are",
    "author",
    "authors",
    "be",
    "could",
    "does",
    "for",
    "in",
    "is",
    "it",
    "lack",
    "lacks",
    "limitation",
    "limitations",
    "more",
    "no",
    "not",
    "note",
    "notes",
    "of",
    "paper",
    "provide",
    "provides",
    "review",
    "should",
    "submission",
    "that",
    "the",
    "there",
    "this",
    "to",
    "which",
    "with",
}
DEDUPE_ACTION_WORDS = {
    "add",
    "address",
    "clarify",
    "discuss",
    "explain",
    "include",
    "need",
    "needs",
    "report",
    "request",
    "suggest",
}
DEDUPE_SYNONYMS = {
    "broader": "broad",
    "clearer": "clear",
    "clearly": "clear",
    "cases": "case",
    "details": "detail",
    "experiments": "experiment",
    "failures": "failure",
    "modules": "module",
    "studies": "study",
}
EXTRACTION_META_CUES = (
    "auditable point",
    "auditable points",
    "combine two related critiques",
    "separate items",
    "source sentence",
    "source field",
    "split into separate",
    "not a technical claim",
    "rate or justify",
    "reviewer confidence",
    "rejection status",
    "there is a request to",
    "two related critiques",
)


class StructuredLLMClient(Protocol):
    def complete_json(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        schema_name: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        ...


def extract_claims(
    review: dict[str, Any],
    *,
    llm_client: StructuredLLMClient | None = None,
    model: str = DEFAULT_CLAIM_MODEL,
    max_claims: int = 8,
) -> list[dict[str, Any]]:
    if llm_client is None:
        from .llm_client import OpenAIChatClient

        llm_client = OpenAIChatClient.from_env()

    payload = llm_client.complete_json(
        model=model,
        messages=build_claim_messages(review, max_claims=max_claims),
        schema_name="review_claim_extraction",
        schema=claim_extraction_schema(max_claims=max_claims),
    )
    claims = validate_claim_payload(payload, review, max_claims=max_claims)
    for claim in claims:
        claim["extraction_version"] = CLAIM_EXTRACTION_VERSION
    return claims


def build_claim_messages(review: dict[str, Any], *, max_claims: int) -> list[dict[str, str]]:
    review_payload = {
        field: clean_text(review.get(field))
        for field in SOURCE_FIELDS
        if clean_text(review.get(field))
    }
    review_payload["rating_raw"] = clean_text(review.get("rating_raw"))
    review_payload["rating_normalized"] = review.get("rating_normalized")

    return [
        {
            "role": "system",
            "content": load_prompt("claim_extraction_system_v0.3.md"),
        },
        {
            "role": "user",
            "content": load_prompt(
                "claim_extraction_user_v0.3.md",
                max_claims=max_claims,
                review_json=json.dumps(review_payload, ensure_ascii=False, indent=2),
            ),
        },
    ]


def claim_extraction_schema(*, max_claims: int) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "claim_text": {
                            "type": "string",
                            "description": "Concise faithful criticism, question, actionable request, or score justification; no pure praise or neutral summary.",
                        },
                        "claim_type": {"type": "string", "enum": list(CLAIM_TYPE_VALUES)},
                        "importance": {"type": "string", "enum": list(IMPORTANCE_VALUES)},
                        "source_field": {"type": "string", "enum": list(SOURCE_FIELDS)},
                        "source_sentence": {
                            "type": "string",
                            "description": "Exact contiguous quote from the selected source_field.",
                        },
                        "rationale": {
                            "type": "string",
                            "description": "Why this is an auditable review claim.",
                        },
                    },
                    "required": [
                        "claim_text",
                        "claim_type",
                        "importance",
                        "source_field",
                        "source_sentence",
                        "rationale",
                    ],
                },
            }
        },
        "required": ["claims"],
    }


def validate_claim_payload(
    payload: dict[str, Any],
    review: dict[str, Any],
    *,
    max_claims: int,
) -> list[dict[str, Any]]:
    raw_claims = payload.get("claims", [])
    if not isinstance(raw_claims, list):
        return []

    candidates = []
    seen = set()
    seen_token_sets = []
    for raw_claim in raw_claims:
        if not isinstance(raw_claim, dict):
            continue
        claim = validate_claim(raw_claim, review)
        if claim is None:
            continue
        dedupe_key = dedupe_claim_key(claim)
        token_set = dedupe_claim_tokens(claim)
        if (
            dedupe_key in seen
            or is_near_duplicate_claim(token_set, seen_token_sets)
            or is_composite_duplicate_claim(token_set, seen_token_sets)
        ):
            continue
        seen.add(dedupe_key)
        seen_token_sets.append(token_set)
        claim["source_sentence_index"] = source_sentence_index(review, claim["source_field"], claim["source_sentence"])
        candidates.append(claim)
    return remove_composite_duplicate_claims(candidates)[:max_claims]


def validate_claim(raw_claim: dict[str, Any], review: dict[str, Any]) -> dict[str, Any] | None:
    claim_text = clean_text(raw_claim.get("claim_text"))
    source_field = clean_text(raw_claim.get("source_field"))
    source_sentence = clean_text(raw_claim.get("source_sentence"))
    if not claim_text or not source_field or not source_sentence:
        return None
    if source_field not in SOURCE_FIELDS:
        return None
    source_text = clean_text(review.get(source_field))
    if not source_text:
        return None
    if not contains_normalized(source_text, source_sentence):
        return None
    claim_text = repair_meta_claim_text(claim_text, source_sentence)
    claim_text = clean_extracted_claim_text(claim_text)
    if not claim_text:
        return None

    claim_type = clean_text(raw_claim.get("claim_type"))
    importance = clean_text(raw_claim.get("importance"))
    if claim_type not in CLAIM_TYPE_VALUES:
        claim_type = "general"
    if importance not in IMPORTANCE_VALUES:
        importance = "medium"
    if not is_auditable_review_point(
        claim_text=claim_text,
        source_sentence=source_sentence,
        source_field=source_field,
        claim_type=claim_type,
        importance=importance,
    ):
        return None

    return {
        "claim_text": claim_text,
        "claim_type": claim_type,
        "importance": importance,
        "source_field": source_field,
        "source_sentence": source_sentence,
        "extraction_reason": clean_text(raw_claim.get("rationale")) or "llm-extracted-source-validated",
    }


def repair_meta_claim_text(claim_text: str, source_sentence: str) -> str:
    if not is_extraction_meta_artifact(claim_text):
        return claim_text
    repaired = re.sub(
        r"^\s*(summary|strengths|weaknesses|questions|rating|confidence)\s*:\s*",
        "",
        source_sentence,
        flags=re.IGNORECASE,
    ).strip()
    if is_extraction_meta_artifact(repaired):
        return ""
    return clean_text(repaired)


def clean_extracted_claim_text(claim_text: str) -> str:
    return clean_text(re.sub(r"\s*\((implied|implicit|inferred)[^)]*\)\.?\s*$", "", claim_text, flags=re.IGNORECASE))


def is_extraction_meta_artifact(text: str) -> bool:
    normalized = normalize_for_match(text)
    if any(cue in normalized for cue in EXTRACTION_META_CUES):
        return True
    return re.search(r"\brating of\s+\d", normalized) is not None


def dedupe_claim_key(claim: dict[str, Any]) -> str:
    return " ".join(sorted(dedupe_claim_tokens(claim)))


def dedupe_claim_tokens(claim: dict[str, Any]) -> set[str]:
    text = str(claim.get("claim_text") or "") or str(claim.get("source_sentence") or "")
    normalized = normalize_claim_for_dedupe(text)
    return {token for token in normalized.split() if token}


def normalize_claim_for_dedupe(text: str) -> str:
    text = normalize_for_match(text)
    text = re.sub(r"\b(summary|strengths|weaknesses|questions|rating|confidence)\s*:\s*", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    tokens_for_match = []
    for token in re.sub(r"\s+", " ", text).strip().split():
        token = DEDUPE_SYNONYMS.get(token, token)
        if token.endswith("ing") and len(token) > 5:
            token = token[:-3]
        elif token.endswith("ed") and len(token) > 4:
            token = token[:-2]
        elif token.endswith("s") and len(token) > 4:
            token = token[:-1]
        token = DEDUPE_SYNONYMS.get(token, token)
        if token in DEDUPE_STOPWORDS or token in DEDUPE_ACTION_WORDS:
            continue
        tokens_for_match.append(token)
    return " ".join(tokens_for_match)


def is_near_duplicate_claim(token_set: set[str], seen_token_sets: list[set[str]]) -> bool:
    if not token_set:
        return False
    for seen in seen_token_sets:
        if not seen:
            continue
        overlap = len(token_set & seen)
        smaller = min(len(token_set), len(seen))
        larger = max(len(token_set), len(seen))
        if smaller and overlap / smaller >= 0.8 and overlap / larger >= 0.6:
            return True
    return False


def is_composite_duplicate_claim(token_set: set[str], seen_token_sets: list[set[str]]) -> bool:
    if len(seen_token_sets) < 2 or len(token_set) < 5:
        return False
    covered_by = 0
    covered_tokens = set()
    for seen in seen_token_sets:
        if not seen:
            continue
        overlap = token_set & seen
        if len(overlap) / min(len(token_set), len(seen)) >= 0.55:
            covered_by += 1
            covered_tokens.update(overlap)
    if covered_by < 2:
        return False
    return len(covered_tokens) / len(token_set) >= 0.75


def remove_composite_duplicate_claims(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(claims) < 2:
        return claims
    token_sets = [dedupe_claim_tokens(claim) for claim in claims]
    composite_indexes = set()
    for index, tokens in enumerate(token_sets):
        other_token_sets = [other for other_index, other in enumerate(token_sets) if other_index != index]
        if is_composite_duplicate_claim(tokens, other_token_sets):
            composite_indexes.add(index)

    remaining = [
        (claim, tokens)
        for index, (claim, tokens) in enumerate(zip(claims, token_sets, strict=True))
        if index not in composite_indexes
    ]
    if len(remaining) < 2:
        return [claim for claim, _tokens in remaining]

    filtered = []
    remaining_token_sets = [tokens for _claim, tokens in remaining]
    for index, (claim, tokens) in enumerate(remaining):
        other_token_sets = [other for other_index, other in enumerate(remaining_token_sets) if other_index != index]
        if is_subsumed_duplicate_claim(tokens, other_token_sets):
            continue
        filtered.append(claim)
    return filtered


def is_subsumed_duplicate_claim(token_set: set[str], other_token_sets: list[set[str]]) -> bool:
    if len(token_set) < 2:
        return False
    for other in other_token_sets:
        if len(other) <= len(token_set):
            continue
        overlap = len(token_set & other)
        if overlap / len(token_set) >= 0.85:
            return True
    return False


def is_auditable_review_point(
    *,
    claim_text: str,
    source_sentence: str,
    source_field: str,
    claim_type: str,
    importance: str,
) -> bool:
    combined = normalize_for_match(f"{claim_text} {source_sentence}")
    field = normalize_for_match(source_field)
    has_tone_problem = any(contains_phrase(combined, cue) for cue in TONE_PROBLEM_WORDS)
    if claim_type == "tone" or importance == "tone-only":
        return has_tone_problem
    if has_tone_problem:
        return True
    if is_question_like(claim_text) or is_question_like(source_sentence) or importance == "question":
        return True
    if is_score_justification(combined):
        return True

    has_negative_or_limitation = any(contains_phrase(combined, cue) for cue in NEGATIVE_OR_LIMITATION_CUES)
    has_actionable_request = any(contains_phrase(combined, cue) for cue in ACTIONABLE_CUES)
    has_contrast = any(contains_phrase(combined, cue) for cue in CONTRAST_CUES)

    if field in {"summary", "strengths"}:
        return has_negative_or_limitation or has_actionable_request or (has_contrast and has_negative_or_limitation)
    return has_negative_or_limitation or has_actionable_request


def is_question_like(text: str) -> bool:
    normalized = normalize_for_match(text)
    if not normalized:
        return False
    if normalized.endswith("?"):
        return True
    first_word = normalized.split(" ", 1)[0]
    return first_word in QUESTION_STARTERS and "?" in text


def is_score_justification(text: str) -> bool:
    if not any(contains_phrase(text, cue) for cue in SCORE_JUSTIFICATION_CUES):
        return False
    return any(contains_phrase(text, cue) for cue in ("because", "due to", "given", "therefore"))


def contains_phrase(text: str, phrase: str) -> bool:
    escaped = re.escape(phrase)
    return re.search(rf"(^|\W){escaped}($|\W)", text) is not None


def contains_normalized(haystack: str, needle: str) -> bool:
    return normalize_for_match(needle) in normalize_for_match(haystack)


def normalize_for_match(text: str) -> str:
    text = clean_text(text).lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def source_sentence_index(review: dict[str, Any], source_field: str, source_sentence: str) -> int | None:
    source_text = clean_text(review.get(source_field))
    if not source_text:
        return None
    normalized_sentence = normalize_for_match(source_sentence)
    pieces = re.split(r"(?<=[.!?])\s+|\n+", source_text)
    for index, piece in enumerate(piece for piece in pieces if clean_text(piece)):
        if normalize_for_match(piece) == normalized_sentence or normalized_sentence in normalize_for_match(piece):
            return index
    return None

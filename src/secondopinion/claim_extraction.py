from __future__ import annotations

import json
import re
from typing import Any, Protocol

from .text import clean_text


CLAIM_EXTRACTION_VERSION = "claim-extraction-llm-v0.1"
DEFAULT_CLAIM_MODEL = "gpt-4o-mini"

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
            "content": (
                "You extract auditable peer-review claims from OpenReview reviews. "
                "Return JSON matching the schema. Extract only criticisms, questions, or actionable requests "
                "about the submitted paper. Do not extract praise or summary. "
                "Each claim must be faithful to a single exact source_sentence copied from one supplied field. "
                "Do not invent claims, evidence, or paper facts."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Extract up to {max_claims} auditable claims. "
                "Split distinct criticisms into separate claims when the review makes multiple points. "
                "Use source_field only from weaknesses, questions, review_text, strengths, or summary. "
                "source_sentence must be an exact contiguous quote from that source_field.\n\n"
                f"Review JSON:\n{json.dumps(review_payload, ensure_ascii=False, indent=2)}"
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
                            "description": "Concise faithful claim, without adding facts not in source_sentence.",
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

    validated = []
    seen = set()
    for raw_claim in raw_claims:
        if not isinstance(raw_claim, dict):
            continue
        claim = validate_claim(raw_claim, review)
        if claim is None:
            continue
        dedupe_key = normalize_for_match(f"{claim['source_field']} {claim['claim_text']}")
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        claim["source_sentence_index"] = source_sentence_index(review, claim["source_field"], claim["source_sentence"])
        validated.append(claim)
        if len(validated) >= max_claims:
            break
    return validated


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

    claim_type = clean_text(raw_claim.get("claim_type"))
    importance = clean_text(raw_claim.get("importance"))
    if claim_type not in CLAIM_TYPE_VALUES:
        claim_type = "general"
    if importance not in IMPORTANCE_VALUES:
        importance = "medium"

    return {
        "claim_text": claim_text,
        "claim_type": claim_type,
        "importance": importance,
        "source_field": source_field,
        "source_sentence": source_sentence,
        "extraction_reason": clean_text(raw_claim.get("rationale")) or "llm-extracted-source-validated",
    }


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

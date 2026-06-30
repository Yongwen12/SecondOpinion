from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from .config import ServerSettings
from .models import Paper, ScoringJob, utcnow
from .repository import job_to_public_dict, store_scorecard
from ..reviewer_public_scorecard import build_public_scorecard
from ..scoring_memory import read_jsonl as read_scoring_jsonl
from ..scoring_memory import score_dimensions_with_memory


PRODUCT_DIMENSIONS = [
    "specificity",
    "substantiation",
    "actionability",
    "consensus_conflict",
    "rebuttal_robustness",
    "professionalism",
]

SCORER_SCHEMA_VERSION = "server-internal-scoring-payload-v0.1"


@lru_cache(maxsize=4)
def load_memory_records_cached(path: str) -> tuple[dict[str, Any], ...]:
    memory_path = Path(path)
    if not memory_path.exists():
        return tuple()
    return tuple(read_scoring_jsonl(memory_path))


def load_memory_records(path: str | Path) -> list[dict[str, Any]]:
    return list(load_memory_records_cached(str(path)))


def score_paper(
    session: Session,
    *,
    paper_id: str,
    settings: ServerSettings,
    job_id: str = "",
    memory_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise ValueError(f"paper not found: {paper_id}")
    memory = memory_records if memory_records is not None else load_memory_records(settings.scoring_memory_path)
    internal_payload = build_internal_scoring_payload(
        paper,
        memory_records=memory,
        max_claims_per_review=settings.max_claims_per_review,
        settings=settings,
    )
    public_json = build_public_scorecard(internal_payload)
    artifact_path = write_internal_artifact(settings.artifact_root, job_id or "manual", internal_payload)
    store_scorecard(
        session,
        paper=paper,
        public_json=public_json,
        internal_artifact_path=str(artifact_path),
        scorer_version=settings.scorer_version,
        memory_index_version=settings.memory_index_version,
    )
    return public_json


def build_internal_scoring_payload(
    paper: Paper,
    *,
    memory_records: list[dict[str, Any]],
    max_claims_per_review: int = 8,
    settings: ServerSettings | None = None,
) -> dict[str, Any]:
    reviewers = []
    for index, review in enumerate(sorted(paper.reviews, key=lambda item: item.reviewer_index), start=1):
        claim_texts = extract_claim_texts(review_text_for_claims(review), limit=max_claims_per_review)
        claims = []
        for claim_index, claim_text in enumerate(claim_texts, start=1):
            llm_scores = dimension_scores_for_claim(claim_text, settings=settings)
            scored = score_dimensions_with_memory(
                query_text=claim_text,
                memory_records=memory_records,
                llm_scores=llm_scores,
                dimensions=PRODUCT_DIMENSIONS,
                top_k=5,
                llm_weight=0.6,
            )
            claims.append(
                {
                    "claim_id": f"{review.review_id}:claim:{claim_index}",
                    "claim_text": claim_text,
                    "source_sentence": claim_text,
                    "second_opinion_take": public_take_for_claim(claim_text, scored.get("overall_score")),
                    "hybrid_scores": scored["hybrid_scores"],
                    "metadata": {
                        "scorer": "heuristic_llm_proxy_plus_external_memory",
                        "review_id": review.review_id,
                    },
                }
            )
        reviewers.append(
            {
                "display_id": f"R{index}",
                "review_id": review.review_id,
                "summary": review.summary or summarize_text(review.review_text),
                "rating": review.rating_normalized,
                "confidence": review.confidence_normalized,
                "claims": claims,
            }
        )
    return {
        "schema_version": SCORER_SCHEMA_VERSION,
        "paper": {
            "paper_id": paper.paper_id,
            "title": paper.title,
            "venue": paper.venue,
            "year": paper.year,
            "decision": paper.decision,
        },
        "summary": {
            "reviewer_count": len(reviewers),
            "source": "server_worker",
        },
        "reviewers": reviewers,
    }


def review_text_for_claims(review: Any) -> str:
    parts = [review.weaknesses, review.questions, review.review_text]
    return "\n".join(part for part in parts if part)


def extract_claim_texts(text: str, *, limit: int) -> list[str]:
    candidates = []
    for block in re.split(r"\n{2,}|\r\n\r\n", text or ""):
        block = clean_claim(block)
        if not block:
            continue
        split_items = split_bullets_or_sentences(block)
        candidates.extend(clean_claim(item) for item in split_items)
    seen = set()
    claims = []
    for candidate in candidates:
        if not is_claim_like(candidate):
            continue
        key = re.sub(r"\W+", " ", candidate.lower()).strip()
        if key in seen:
            continue
        seen.add(key)
        claims.append(candidate)
        if len(claims) >= limit:
            break
    if not claims and text.strip():
        claims.append(clean_claim(text)[:600])
    return claims


def split_bullets_or_sentences(text: str) -> list[str]:
    bullet_parts = re.split(r"(?:^|\n)\s*(?:[-*]|\(?\d+[.)])\s+", text)
    parts = [part.strip() for part in bullet_parts if part.strip()]
    if len(parts) > 1:
        return parts
    sentence_parts = re.split(r"(?<=[.!?])\s+(?=[A-Z(])", text)
    return [part.strip() for part in sentence_parts if part.strip()]


def clean_claim(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    text = re.sub(r"^(weaknesses?|questions?|concerns?|comments?)\s*[:=-]\s*", "", text, flags=re.I)
    return text.strip()


def is_claim_like(text: str) -> bool:
    if len(text) < 24:
        return False
    lowered = text.lower()
    weak_markers = [
        "lack",
        "missing",
        "unclear",
        "not clear",
        "should",
        "could",
        "need",
        "needs",
        "question",
        "compare",
        "baseline",
        "ablation",
        "experiment",
        "evidence",
        "novelty",
        "limitation",
        "why",
        "how",
    ]
    return any(marker in lowered for marker in weak_markers) or text.endswith("?")


def dimension_scores_for_claim(text: str, *, settings: ServerSettings | None = None) -> dict[str, float]:
    if settings and settings.llm_scorer_enabled:
        try:
            return llm_dimension_scores(text, model=settings.llm_scorer_model)
        except Exception:
            return heuristic_dimension_scores(text)
    return heuristic_dimension_scores(text)

def heuristic_dimension_scores(text: str) -> dict[str, float]:
    lowered = text.lower()
    word_count = len(re.findall(r"\w+", text))
    has_anchor = bool(re.search(r"\b(table|figure|section|appendix|equation|line|baseline|dataset|ablation)\b", lowered))
    has_action = bool(re.search(r"\b(add|compare|report|clarify|include|provide|explain|analyze|evaluate|discuss)\b", lowered))
    has_polite = not bool(re.search(r"\b(lazy|terrible|awful|nonsense|ridiculous|badly written)\b", lowered))
    has_rebuttal_risk = bool(re.search(r"\b(missing|lack|not clear|unclear|insufficient|unsupported|baseline|ablation)\b", lowered))
    specificity = 0.75 if has_anchor else 0.6
    if word_count >= 35:
        specificity += 0.08
    if word_count < 12:
        specificity -= 0.18
    substantiation = 0.76 if has_anchor else 0.55
    actionability = 0.82 if has_action else 0.52
    consensus_conflict = 0.58
    rebuttal_robustness = 0.74 if has_rebuttal_risk else 0.5
    professionalism = 0.82 if has_polite else 0.25
    return {
        "specificity": clamp01(specificity),
        "substantiation": clamp01(substantiation),
        "actionability": clamp01(actionability),
        "consensus_conflict": clamp01(consensus_conflict),
        "rebuttal_robustness": clamp01(rebuttal_robustness),
        "professionalism": clamp01(professionalism),
    }


def llm_dimension_scores(text: str, *, model: str) -> dict[str, float]:
    from ..llm_client import OpenAIChatClient

    client = OpenAIChatClient.from_env()
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            **{dimension: {"type": "number", "minimum": 0, "maximum": 1} for dimension in PRODUCT_DIMENSIONS},
            "rationale": {"type": "string"},
        },
        "required": [*PRODUCT_DIMENSIONS, "rationale"],
    }
    payload = client.complete_json(
        model=model,
        schema_name="reviewer_comment_dimension_scores",
        schema=schema,
        messages=[
            {
                "role": "system",
                "content": (
                    "Score one peer-review comment for SecondOpinion. Return calibrated numbers from 0 to 1. "
                    "Higher means the comment is more useful, concrete, evidence-linked, actionable, peer-supported, "
                    "robust after rebuttal, or professional for that dimension."
                ),
            },
            {
                "role": "user",
                "content": "Reviewer comment:\n" + text,
            },
        ],
    )
    return {dimension: clamp01(float(payload.get(dimension, 0.0))) for dimension in PRODUCT_DIMENSIONS}

def clamp01(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def public_take_for_claim(claim_text: str, overall_score: float | None) -> str:
    # Short, plain-spoken, lightly wry verdict on the *review comment* — never the people.
    # Deterministic (varies by score band + a stable hash) so re-scoring needs no LLM.
    score = 0.0 if overall_score is None else overall_score
    if score >= 0.75:
        variants = [
            "Sharp and specific — basically a ready-made checklist item.",
            "Concrete enough to act on. No notes.",
            "Specific, answerable, fair. The good kind of nitpick.",
        ]
    elif score >= 0.55:
        variants = [
            "Useful-ish — real point, fuzzy aim. Name the target.",
            "Right neighborhood, no address. Pin down the ask.",
            "Half a point: good instinct, thin on specifics.",
        ]
    else:
        variants = [
            "Hard to act on — gestures at a problem without naming one.",
            "More vibe than ask. Needs a concrete target.",
            "Too vague to check. Say what's actually missing.",
        ]
    index = sum(ord(ch) for ch in claim_text) % len(variants)
    return variants[index]


def summarize_text(text: str, *, limit: int = 180) -> str:
    text = clean_claim(text)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def write_internal_artifact(root: str | Path, job_id: str, payload: dict[str, Any]) -> Path:
    path = Path(root) / "scoring" / f"{job_id}_internal_scorecard.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def run_next_scoring_job(
    session_factory: sessionmaker[Session],
    *,
    settings: ServerSettings,
    memory_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    session = session_factory()
    try:
        statement = (
            select(ScoringJob)
            .where(ScoringJob.status == "queued")
            .order_by(ScoringJob.created_at.asc())
            .limit(1)
        )
        bind = session.get_bind()
        if bind.dialect.name != "sqlite":
            statement = statement.with_for_update(skip_locked=True)
        job = session.execute(statement).scalar_one_or_none()
        if job is None:
            return None
        job.status = "running"
        job.updated_at = utcnow()
        session.commit()
        job_id = job.job_id
    finally:
        session.close()

    session = session_factory()
    try:
        job = session.get(ScoringJob, job_id)
        if job is None:
            return None
        public_json = score_paper(
            session,
            paper_id=job.paper_id,
            settings=settings,
            job_id=job.job_id,
            memory_records=memory_records,
        )
        job.status = "succeeded"
        job.completed_at = utcnow()
        job.output_artifact_path = str(Path(settings.artifact_root) / "scoring" / f"{job.job_id}_internal_scorecard.json")
        session.commit()
        result = job_to_public_dict(job)
        result["scorecard_summary"] = public_json.get("summary", {})
        return result
    except Exception as exc:
        session.rollback()
        failed_session = session_factory()
        try:
            failed = failed_session.get(ScoringJob, job_id)
            if failed is not None:
                failed.status = "failed"
                failed.error = str(exc)
                failed.completed_at = utcnow()
                failed_session.commit()
                return job_to_public_dict(failed)
        finally:
            failed_session.close()
        raise
    finally:
        session.close()


def run_worker_loop(
    session_factory: sessionmaker[Session],
    *,
    settings: ServerSettings,
    once: bool = False,
    sleep_seconds: float = 3.0,
) -> Iterable[dict[str, Any] | None]:
    import time

    while True:
        yield run_next_scoring_job(session_factory, settings=settings)
        if once:
            return
        time.sleep(sleep_seconds)

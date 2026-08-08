from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import select

from .batch_review_scoring import (
    OPENAI_BATCH_ENDPOINT,
    OpenAIBatchClient,
    clean_ws,
    compact_core_review_text,
    write_jsonl,
)
from .llm_client import OpenAIChatClient
from .model_config import apply_chat_completion_cost_controls
from .server.config import settings_from_env
from .server.database import make_engine, make_session_factory
from .server.models import Paper, Review, ReviewerScore
from .server.repository import _outrage_candidate_items


MODEL = "gpt-5.6-luna"
SCORER_VERSION = "outrage-v2-luna-2026-08-07"
TYPES = (
    "NOT_OUTRAGEOUS",
    "PERSONAL_ATTACK",
    "UNSUPPORTED_ALLEGATION",
    "DISMISSIVE_VERDICT",
    "PROCEDURAL_OVERREACH",
    "EMPTY_REVIEW",
    "CONFIDENTLY_VAGUE",
)


def schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "outrageous": {"type": "boolean"},
            "outrage_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "primary_type": {"type": "string", "enum": list(TYPES)},
            "secondary_type": {"type": ["string", "null"], "enum": [*TYPES[1:], None]},
            "quote": {"type": "string", "maxLength": 220},
            "roast": {"type": "string", "maxLength": 160},
            "reason": {"type": "string", "maxLength": 240},
        },
        "required": [
            "outrageous",
            "outrage_score",
            "primary_type",
            "secondary_type",
            "quote",
            "roast",
            "reason",
        ],
    }


SYSTEM_PROMPT = """You classify whether a public academic peer review is genuinely outrageous.

This product is ONLY about outrageous reviewing behavior. Do not confuse a negative, short,
imperfect, vague, or unhelpful review with an outrageous one. Technical disagreement, requests
for experiments, novelty criticism, rejection, and uncertainty are normal peer review unless
the language or conduct crosses a clear professional boundary.

Allowed primary types:
- PERSONAL_ATTACK: insults, contempt, humiliation, or attacks on authors as people.
- UNSUPPORTED_ALLEGATION: serious accusations (fraud, plagiarism, AI generation, policy abuse,
  bad faith) asserted without adequate evidence in the quoted review.
- DISMISSIVE_VERDICT: sweeping rejection or ridicule that substitutes contempt for engagement.
- PROCEDURAL_OVERREACH: weaponizing process/policy or demanding authority beyond a reviewer's role.
- EMPTY_REVIEW: effectively no evaluation at all, e.g. a one-line approval/rejection or placeholder.
- CONFIDENTLY_VAGUE: strong consequential judgment delivered with striking confidence but no
  identifiable technical basis. Mere lack of detail is not enough.
- NOT_OUTRAGEOUS: everything else.

Scoring anchors:
0-24 normal review; 25-49 poor but not outrageous; 50-69 borderline; 70-84 clearly outrageous;
85-100 extreme. Set outrageous=true only at 70+. If false, primary_type must be NOT_OUTRAGEOUS
and secondary_type must be null. EMPTY_REVIEW requires near-total absence of evaluation, not a
summary that happens to lack critique. UNSUPPORTED_ALLEGATION requires an actual serious allegation.

quote must be a verbatim excerpt from the review. roast is a terse, human, dry one-liner suitable
for a CS forum; punch at the review, never the reviewer or authors. No AI-sounding explanation,
no preamble, no moral lecture. reason is a concise audit note. Return only schema-valid JSON."""


def messages(paper: Paper, review: Review) -> list[dict[str, str]]:
    review_payload = {
        "summary": review.summary,
        "strengths": review.strengths,
        "weaknesses": review.weaknesses,
        "questions": review.questions,
        "review_text": review.review_text,
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Paper title: {clean_ws(paper.title)}\n"
                f"Abstract: {clean_ws(paper.abstract)[:1800]}\n"
                f"Reviewer rating: {clean_ws(review.rating_raw)}\n"
                f"Reviewer confidence: {clean_ws(review.confidence_raw)}\n\n"
                f"Review text:\n{compact_core_review_text(review_payload)}"
            ),
        },
    ]


def normalize_result(value: dict[str, Any]) -> dict[str, Any]:
    result = dict(value)
    score = max(0, min(100, int(result.get("outrage_score") or 0)))
    outrageous = bool(result.get("outrageous")) and score >= 70
    primary = str(result.get("primary_type") or "NOT_OUTRAGEOUS")
    secondary = result.get("secondary_type")
    if primary not in TYPES:
        primary = "NOT_OUTRAGEOUS"
    if not outrageous:
        primary, secondary = "NOT_OUTRAGEOUS", None
    elif primary == "NOT_OUTRAGEOUS":
        outrageous = False
        secondary = None
    if secondary not in TYPES[1:] or secondary == primary:
        secondary = None
    return {
        "outrageous": outrageous,
        "outrage_score": score,
        "primary_type": primary,
        "secondary_type": secondary,
        "quote": clean_ws(str(result.get("quote") or ""))[:220],
        "roast": clean_ws(str(result.get("roast") or ""))[:160],
        "reason": clean_ws(str(result.get("reason") or ""))[:240],
    }


def candidate_tasks(limit: int | None = None) -> list[dict[str, Any]]:
    settings = settings_from_env()
    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)
    tasks: list[dict[str, Any]] = []
    with session_factory() as session:
        items = sorted(
            _outrage_candidate_items(session),
            key=lambda item: (-item["_outrage_seed"], -item["_row_id"]),
        )
        if limit is not None:
            items = items[:limit]
        for item in items:
            reviewer_match = re.fullmatch(r"R(\d+)", item["reviewer_key"])
            if not reviewer_match:
                continue
            review = session.scalar(
                select(Review).where(
                    Review.paper_id == item["paper_id"],
                    Review.reviewer_index == int(reviewer_match.group(1)),
                    Review.review_stage == "initial",
                )
            )
            paper = session.get(Paper, item["paper_id"])
            if not review or not paper:
                continue
            tasks.append(
                {
                    "custom_id": f"outrage-v2-{item['_row_id']}",
                    "row_id": item["_row_id"],
                    "old_outrage": item["_outrage_seed"],
                    "paper_id": paper.paper_id,
                    "review_id": review.review_id,
                    "reviewer_key": item["reviewer_key"],
                    "title": paper.title,
                    "messages": messages(paper, review),
                }
            )
    return tasks


def request_for_task(task: dict[str, Any]) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": MODEL,
        "messages": task["messages"],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "outrage_v2", "strict": True, "schema": schema()},
        },
        "max_completion_tokens": 500,
    }
    apply_chat_completion_cost_controls(body, model=MODEL)
    return {"custom_id": task["custom_id"], "method": "POST", "url": OPENAI_BATCH_ENDPOINT, "body": body}


def prepare(*, limit: int | None, output_dir: Path) -> dict[str, Any]:
    tasks = candidate_tasks(limit)
    output_dir.mkdir(parents=True, exist_ok=True)
    batch_path = output_dir / "requests.jsonl"
    manifest_path = output_dir / "manifest.json"
    write_jsonl(batch_path, (request_for_task(task) for task in tasks))
    manifest = {
        "schema_version": SCORER_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "model": MODEL,
        "request_count": len(tasks),
        "batch_path": str(batch_path),
        "tasks": [{k: v for k, v in task.items() if k != "messages"} for task in tasks],
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def run_sync(*, limit: int, output_dir: Path) -> dict[str, Any]:
    tasks = candidate_tasks(limit)
    client = OpenAIChatClient.from_env()
    results = []
    for task in tasks:
        value = client.complete_json(
            model=MODEL,
            messages=task["messages"],
            schema_name="outrage_v2",
            schema=schema(),
        )
        results.append({**{k: v for k, v in task.items() if k != "messages"}, **normalize_result(value)})
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / "sample_results.json"
    result_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {
        "model": MODEL,
        "count": len(results),
        "outrageous_count": sum(1 for item in results if item["outrageous"]),
        "type_counts": {kind: sum(1 for item in results if item["primary_type"] == kind) for kind in TYPES},
        "result_path": str(result_path),
    }
    (output_dir / "sample_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def submit(*, output_dir: Path) -> dict[str, Any]:
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    client = OpenAIBatchClient.from_env()
    uploaded = client.upload_file(output_dir / "requests.jsonl")
    batch = client.create_batch(
        input_file_id=uploaded["id"],
        metadata={"project": "secondopinion", "scorer": SCORER_VERSION, "model": MODEL},
    )
    record = {"file": uploaded, "batch": batch, "manifest": manifest}
    (output_dir / "submission.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Strict Luna outrage V2 scoring")
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--limit", type=int)
    prep.add_argument("--output-dir", type=Path, required=True)
    sample = sub.add_parser("sample")
    sample.add_argument("--limit", type=int, default=50)
    sample.add_argument("--output-dir", type=Path, required=True)
    send = sub.add_parser("submit")
    send.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "prepare":
        payload = prepare(limit=args.limit, output_dir=args.output_dir)
    elif args.command == "sample":
        payload = run_sync(limit=args.limit, output_dir=args.output_dir)
    else:
        payload = submit(output_dir=args.output_dir)
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

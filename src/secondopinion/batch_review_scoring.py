from __future__ import annotations

import argparse
import datetime as dt
import json
import mimetypes
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy.orm import Session

from .llm_client import LLMClientError, load_dotenv
from .model_config import apply_chat_completion_cost_controls
from .normalize import normalize_openreview_notes
from .openreview_client import OpenReviewClient
from .reviewer_public_scorecard import PUBLIC_SCORECARD_VERSION, top_keywords
from .server.config import ServerSettings, settings_from_env
from .server.database import init_db, make_engine, make_session_factory, session_scope
from .server.ingest import import_normalized_dataset
from .server.models import Conference, Paper, Review
from .server.repository import store_scorecard
from .snapshot import normalize_snapshot, save_openreview_snapshot, write_json


BATCH_SCORER_VERSION = "batch-outrage-scorer-v0.1"
BATCH_MEMORY_VERSION = "openreview-comments-v0.1"
DEFAULT_BATCH_MODEL = "gpt-5.4-nano"
OPENAI_BATCH_ENDPOINT = "/v1/chat/completions"

VENUE_INVITATIONS = {
    "ICLR": "ICLR.cc/{year}/Conference/-/Submission",
    "NEURIPS": "NeurIPS.cc/{year}/Conference/-/Submission",
    "ICML": "ICML.cc/{year}/Conference/-/Submission",
}


def default_invitation(venue: str, year: int) -> str:
    template = VENUE_INVITATIONS.get(venue.strip().upper())
    if not template:
        return f"{venue.strip()}.cc/{year}/Conference/-/Submission"
    return template.format(year=year)


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def write_jsonl(path: str | Path, records: Iterable[dict[str, Any]]) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")
            count += 1
    return count


def fetch_openreview_normalized_without_raw_snapshot(
    client: OpenReviewClient,
    *,
    venue: str,
    year: int,
    invitation: str,
    details: str = "replies",
    limit: int | None = None,
    page_size: int = 100,
    polite_delay: float = 0.1,
    snapshot_id: str | None = None,
) -> dict[str, Any]:
    notes: list[dict[str, Any]] = []
    offset = 0
    while True:
        remaining = None if limit is None else max(limit - len(notes), 0)
        if remaining == 0:
            break
        batch_size = min(page_size, remaining) if remaining is not None else page_size
        payload = client.get_notes(invitation, limit=batch_size, offset=offset, details=details)
        batch = list(payload.get("notes", []))
        if not batch:
            break
        notes.extend(batch)
        if len(batch) < batch_size:
            break
        offset += len(batch)
        if polite_delay:
            sleep = getattr(client, "sleep_func", time.sleep)
            sleep(max(polite_delay, 0.0))

    normalized = normalize_openreview_notes(notes, venue=venue.upper(), year=year)
    normalized["source_snapshot"] = {
        "snapshot_id": snapshot_id or "no-raw-snapshot",
        "source": "openreview",
        "venue": venue.upper(),
        "year": year,
        "api": client.base_url,
        "invitation": invitation,
        "details": details,
        "raw_snapshot_retained": False,
    }
    return normalized


def pull_openreview_normalized(
    *,
    venue: str,
    year: int,
    limit: int | None,
    output: str | Path,
    raw_root: str | Path = "data/raw",
    invitation: str | None = None,
    page_size: int = 100,
    details: str = "replies",
    polite_delay: float = 0.1,
    resume: bool = False,
    snapshot_id: str | None = None,
    raw_snapshot: bool = False,
) -> dict[str, Any]:
    client = OpenReviewClient()
    invitation = invitation or default_invitation(venue, year)
    raw_snapshot = bool(raw_snapshot or resume)
    snapshot_dir = ""
    if raw_snapshot:
        snapshot = save_openreview_snapshot(
            client,
            venue=venue.upper(),
            year=year,
            invitation=invitation,
            details=details,
            limit=limit,
            page_size=page_size,
            polite_delay=polite_delay,
            root=raw_root,
            snapshot=snapshot_id,
            resume=resume,
        )
        normalized = normalize_snapshot(snapshot["snapshot_dir"], venue=venue.upper(), year=year)
        snapshot_id = str(snapshot["manifest"].get("snapshot_id", snapshot_id or ""))
        snapshot_dir = str(snapshot["snapshot_dir"])
    else:
        normalized = fetch_openreview_normalized_without_raw_snapshot(
            client,
            venue=venue.upper(),
            year=year,
            invitation=invitation,
            details=details,
            limit=limit,
            page_size=page_size,
            polite_delay=polite_delay,
            snapshot_id=snapshot_id,
        )
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "venue": venue.upper(),
        "year": year,
        "limit": limit,
        "invitation": invitation,
        "snapshot_id": snapshot_id or normalized.get("source_snapshot", {}).get("snapshot_id", ""),
        "snapshot_dir": snapshot_dir,
        "raw_snapshot_retained": raw_snapshot,
        "normalized_path": str(output_path),
        "paper_count": normalized.get("paper_count", 0),
        "review_count": normalized.get("review_count", 0),
    }


AUTHOR_OR_ADMIN_REVIEW_PATTERNS = [
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


def is_scoreable_review(review: dict[str, Any]) -> bool:
    text = compact_core_review_text(review)
    if not text:
        return False
    return not any(pattern.search(text) for pattern in AUTHOR_OR_ADMIN_REVIEW_PATTERNS)


def compact_core_review_text(review: dict[str, Any], *, max_chars: int = 6000) -> str:
    parts = [
        ("Summary", review.get("summary")),
        ("Strengths", review.get("strengths")),
        ("Weaknesses", review.get("weaknesses")),
        ("Questions", review.get("questions")),
        ("Review", review.get("review_text")),
    ]
    text_parts = []
    seen = set()
    for label, value in parts:
        text = clean_ws(str(value or ""))
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        text_parts.append(f"{label}: {text}")
    text = "\n".join(text_parts)
    return text[:max_chars].strip()


def clean_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def normalized_quality_report(payload: dict[str, Any]) -> dict[str, Any]:
    papers = [paper for paper in payload.get("papers", []) if isinstance(paper, dict)]
    review_records = []
    reviews_per_paper = []
    for paper in papers:
        reviews = [review for review in paper.get("reviews", []) if isinstance(review, dict)]
        reviews_per_paper.append(len(reviews))
        for review in reviews:
            review_records.append((paper, review))

    empty_core = sum(1 for _, review in review_records if not compact_core_review_text(review))
    decisions = [clean_ws(str(paper.get("decision") or "")) for paper in papers]
    known_decisions = [decision for decision in decisions if decision and decision.lower() != "unknown"]
    abstracts = [clean_ws(str(paper.get("abstract") or "")) for paper in papers]
    ratings = [review for _, review in review_records if review.get("rating_raw") or review.get("rating_normalized") is not None]
    confidences = [
        review
        for _, review in review_records
        if review.get("confidence_raw") or review.get("confidence_normalized") is not None
    ]
    per_paper_counts = Counter(reviews_per_paper)
    review_count = len(review_records)
    paper_count = len(papers)
    return {
        "dataset": payload.get("dataset", ""),
        "paper_count": paper_count,
        "review_count": review_count,
        "reviews_per_paper": {
            "min": min(reviews_per_paper) if reviews_per_paper else 0,
            "max": max(reviews_per_paper) if reviews_per_paper else 0,
            "mean": round(review_count / paper_count, 3) if paper_count else 0,
            "histogram": {str(key): per_paper_counts[key] for key in sorted(per_paper_counts)},
        },
        "empty_core_review_count": empty_core,
        "empty_core_review_rate": round(empty_core / review_count, 4) if review_count else 0,
        "decision_coverage_count": len(known_decisions),
        "decision_coverage_rate": round(len(known_decisions) / paper_count, 4) if paper_count else 0,
        "abstract_coverage_count": sum(1 for abstract in abstracts if abstract),
        "abstract_coverage_rate": round(sum(1 for abstract in abstracts if abstract) / paper_count, 4) if paper_count else 0,
        "rating_coverage_count": len(ratings),
        "rating_coverage_rate": round(len(ratings) / review_count, 4) if review_count else 0,
        "confidence_coverage_count": len(confidences),
        "confidence_coverage_rate": round(len(confidences) / review_count, 4) if review_count else 0,
        "decision_counts": dict(Counter(known_decisions).most_common(20)),
    }


def write_quality_report(
    *,
    normalized_path: str | Path,
    json_out: str | Path,
    markdown_out: str | Path,
) -> dict[str, Any]:
    payload = read_json(normalized_path)
    report = normalized_quality_report(payload)
    json_path = Path(json_out)
    md_path = Path(markdown_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(quality_report_markdown(report, normalized_path), encoding="utf-8")
    return report | {"json_path": str(json_path), "markdown_path": str(md_path)}


def quality_report_markdown(report: dict[str, Any], normalized_path: str | Path) -> str:
    rows = [
        ("Papers", report["paper_count"]),
        ("Reviews", report["review_count"]),
        ("Mean reviews/paper", report["reviews_per_paper"]["mean"]),
        ("Empty core reviews", f"{report['empty_core_review_count']} ({report['empty_core_review_rate']:.1%})"),
        ("Decision coverage", f"{report['decision_coverage_count']} ({report['decision_coverage_rate']:.1%})"),
        ("Abstract coverage", f"{report['abstract_coverage_count']} ({report['abstract_coverage_rate']:.1%})"),
        ("Rating coverage", f"{report['rating_coverage_count']} ({report['rating_coverage_rate']:.1%})"),
        ("Confidence coverage", f"{report['confidence_coverage_count']} ({report['confidence_coverage_rate']:.1%})"),
    ]
    lines = [
        "# Normalized Data Quality",
        "",
        f"- Input: `{normalized_path}`",
        f"- Dataset: `{report.get('dataset', '')}`",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {label} | {value} |" for label, value in rows)
    lines.extend(["", "## Review Count Histogram", "", "| Reviews per paper | Papers |", "| ---: | ---: |"])
    for bucket, count in report["reviews_per_paper"]["histogram"].items():
        lines.append(f"| {bucket} | {count} |")
    lines.extend(["", "## Top Decisions", "", "| Decision | Papers |", "| --- | ---: |"])
    for decision, count in report["decision_counts"].items():
        lines.append(f"| {decision} | {count} |")
    lines.append("")
    return "\n".join(lines)


def scoring_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "outrage": {"type": "integer", "minimum": 0, "maximum": 100},
            "toxicity": {"type": "integer", "minimum": 0, "maximum": 100},
            "helpfulness": {"type": "integer", "minimum": 0, "maximum": 100},
            "quote": {"type": "string", "maxLength": 180},
            "verdict": {"type": "string", "maxLength": 80},
            "evidence": {"type": "string", "maxLength": 180},
            "actionable": {"type": "boolean"},
        },
        "required": ["outrage", "toxicity", "helpfulness", "quote", "verdict", "evidence", "actionable"],
    }


def scoring_messages(paper: dict[str, Any], review: dict[str, Any]) -> list[dict[str, str]]:
    title = clean_ws(str(paper.get("title") or "Untitled submission"))
    abstract = clean_ws(str(paper.get("abstract") or ""))[:1800]
    review_text = compact_core_review_text(review)
    rating = clean_ws(str(review.get("rating_raw") or review.get("rating_normalized") or ""))
    confidence = clean_ws(str(review.get("confidence_raw") or review.get("confidence_normalized") or ""))
    return [
        {
            "role": "system",
            "content": (
                "Score one public peer-review comment for Weak Reject / SecondOpinion. "
                "Score the review comment, not the paper and not the person. "
                "Use a 0-100 percentage scale, not a 0-10 scale. "
                "50 means neutral or mixed. 70+ means clearly high. 90+ means extreme. "
                "outrage is high when the comment is performative, vague, unfair, or over-harsh. "
                "toxicity is high for insults, contempt, or personal attacks. "
                "helpfulness is high for specific, evidence-linked, actionable feedback. "
                "A normal actionable but imperfect review should usually have helpfulness 55-75, not 5-7. "
                "Keep quote under 25 words, verdict under 8 words, and evidence under 30 words. "
                "Return only JSON matching the schema."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Paper title: {title}\n"
                f"Abstract: {abstract}\n"
                f"Reviewer rating: {rating}\n"
                f"Reviewer confidence: {confidence}\n\n"
                f"Review text:\n{review_text}"
            ),
        },
    ]


def stable_custom_id(*, venue: str, year: int, paper_id: str, review_id: str) -> str:
    safe_paper = re.sub(r"[^A-Za-z0-9_.:-]+", "_", paper_id)[:64]
    safe_review = re.sub(r"[^A-Za-z0-9_.:-]+", "_", review_id)[:64]
    return f"{venue.upper()}-{year}-{safe_paper}-{safe_review}"


def iter_review_tasks(
    normalized: dict[str, Any],
    *,
    limit_reviews: int | None = None,
    skip_empty: bool = True,
) -> Iterable[dict[str, Any]]:
    venue = str(normalized.get("venue") or normalized.get("dataset", "ICLR").split("_")[0]).upper()
    year = int(normalized.get("year") or str(normalized.get("dataset", "0").split("_")[-1] or 0))
    count = 0
    for paper in normalized.get("papers", []):
        if not isinstance(paper, dict):
            continue
        paper_id = str(paper.get("paper_id") or paper.get("openreview_forum_id") or "").strip()
        if not paper_id:
            continue
        for review_index, review in enumerate(paper.get("reviews") or [], start=1):
            if not isinstance(review, dict):
                continue
            if skip_empty and not is_scoreable_review(review):
                continue
            review_id = str(review.get("review_id") or f"{paper_id}:review:{review_index}")
            yield {
                "venue": venue,
                "year": year,
                "paper_id": paper_id,
                "review_id": review_id,
                "reviewer_index": review_index,
                "paper": paper,
                "review": review,
                "custom_id": stable_custom_id(venue=venue, year=year, paper_id=paper_id, review_id=review_id),
            }
            count += 1
            if limit_reviews is not None and count >= limit_reviews:
                return


def batch_request_for_task(task: dict[str, Any], *, model: str) -> dict[str, Any]:
    body = {
        "model": model,
        "messages": scoring_messages(task["paper"], task["review"]),
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "weak_reject_review_score",
                "strict": True,
                "schema": scoring_schema(),
            },
        },
        "max_completion_tokens": 480,
    }
    apply_chat_completion_cost_controls(body, model=model)
    return {
        "custom_id": task["custom_id"],
        "method": "POST",
        "url": OPENAI_BATCH_ENDPOINT,
        "body": body,
    }


def estimate_tokens(text: str) -> int:
    return max(1, round(len(text) / 4))


def build_scoring_batch(
    *,
    normalized_path: str | Path,
    output_jsonl: str | Path,
    manifest_path: str | Path,
    model: str = DEFAULT_BATCH_MODEL,
    limit_reviews: int | None = None,
    exclude_custom_ids: set[str] | None = None,
) -> dict[str, Any]:
    normalized = read_json(normalized_path)
    excluded = exclude_custom_ids or set()
    tasks = []
    for task in iter_review_tasks(normalized):
        if task["custom_id"] in excluded:
            continue
        tasks.append(task)
        if limit_reviews is not None and len(tasks) >= limit_reviews:
            break
    requests = [batch_request_for_task(task, model=model) for task in tasks]
    count = write_jsonl(output_jsonl, requests)
    prompt_tokens = sum(estimate_tokens(json.dumps(request["body"]["messages"], ensure_ascii=False)) for request in requests)
    estimated_output_tokens = count * 100
    manifest = {
        "schema_version": "weak-reject-batch-manifest-v0.1",
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "normalized_path": str(normalized_path),
        "jsonl_path": str(output_jsonl),
        "model": model,
        "endpoint": OPENAI_BATCH_ENDPOINT,
        "request_count": count,
        "estimated_input_tokens": prompt_tokens,
        "estimated_output_tokens": estimated_output_tokens,
        "estimated_batch_cost_usd": estimate_batch_cost(prompt_tokens, estimated_output_tokens),
        "excluded_request_count": len(excluded),
        "tasks": [
            {
                "custom_id": task["custom_id"],
                "venue": task["venue"],
                "year": task["year"],
                "paper_id": task["paper_id"],
                "review_id": task["review_id"],
                "reviewer_index": task["reviewer_index"],
            }
            for task in tasks
        ],
    }
    manifest_out = Path(manifest_path)
    manifest_out.parent.mkdir(parents=True, exist_ok=True)
    manifest_out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def estimate_batch_cost(input_tokens: int, output_tokens: int) -> float:
    # Current public gpt-5.4-nano Batch rates used for planning:
    # input $0.10 / 1M tokens, output $0.625 / 1M tokens.
    return round((input_tokens / 1_000_000 * 0.10) + (output_tokens / 1_000_000 * 0.625), 4)


def split_scoring_batch(
    *,
    batch_jsonl: str | Path,
    manifest_path: str | Path,
    output_dir: str | Path,
    prefix: str,
    max_estimated_input_tokens: int = 1_600_000,
    max_requests: int | None = None,
) -> dict[str, Any]:
    records = read_jsonl(batch_jsonl)
    manifest = read_json(manifest_path)
    task_map = {str(task.get("custom_id")): task for task in manifest.get("tasks", []) if isinstance(task, dict)}
    output_base = Path(output_dir)
    output_base.mkdir(parents=True, exist_ok=True)
    chunks: list[dict[str, Any]] = []
    current_records: list[dict[str, Any]] = []
    current_input_tokens = 0

    def record_input_tokens(record: dict[str, Any]) -> int:
        body = record.get("body") if isinstance(record.get("body"), dict) else {}
        messages = body.get("messages", [])
        return estimate_tokens(json.dumps(messages, ensure_ascii=False))

    def flush() -> None:
        nonlocal current_records, current_input_tokens
        if not current_records:
            return
        index = len(chunks) + 1
        jsonl_path = output_base / f"{prefix}_part{index:02d}_batch.jsonl"
        part_manifest_path = output_base / f"{prefix}_part{index:02d}_manifest.json"
        request_count = write_jsonl(jsonl_path, current_records)
        custom_ids = [str(record.get("custom_id")) for record in current_records]
        tasks = [task_map[custom_id] for custom_id in custom_ids if custom_id in task_map]
        output_tokens = request_count * 100
        part_manifest = {key: value for key, value in manifest.items() if key != "tasks"}
        part_manifest.update(
            {
                "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
                "jsonl_path": str(jsonl_path),
                "source_manifest_path": str(manifest_path),
                "request_count": request_count,
                "estimated_input_tokens": current_input_tokens,
                "estimated_output_tokens": output_tokens,
                "estimated_batch_cost_usd": estimate_batch_cost(current_input_tokens, output_tokens),
                "tasks": tasks,
            }
        )
        part_manifest_path.write_text(json.dumps(part_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        chunks.append(
            {
                "index": index,
                "jsonl_path": str(jsonl_path),
                "manifest_path": str(part_manifest_path),
                "request_count": request_count,
                "estimated_input_tokens": current_input_tokens,
                "estimated_batch_cost_usd": part_manifest["estimated_batch_cost_usd"],
            }
        )
        current_records = []
        current_input_tokens = 0

    for record in records:
        tokens = record_input_tokens(record)
        too_many_tokens = current_records and current_input_tokens + tokens > max_estimated_input_tokens
        too_many_requests = max_requests is not None and current_records and len(current_records) >= max_requests
        if too_many_tokens or too_many_requests:
            flush()
        current_records.append(record)
        current_input_tokens += tokens
    flush()
    return {
        "source_jsonl_path": str(batch_jsonl),
        "source_manifest_path": str(manifest_path),
        "chunk_count": len(chunks),
        "request_count": len(records),
        "max_estimated_input_tokens": max_estimated_input_tokens,
        "max_requests": max_requests,
        "chunks": chunks,
    }


class OpenAIBatchClient:
    def __init__(self, *, api_key: str, base_url: str = "https://api.openai.com/v1", timeout: int = 180):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> "OpenAIBatchClient":
        load_dotenv()
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise LLMClientError("OPENAI_API_KEY is required to submit or retrieve OpenAI Batch jobs.")
        return cls(
            api_key=api_key,
            base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            timeout=int(os.environ.get("OPENAI_TIMEOUT", "180")),
        )

    def request_json(self, path: str, *, method: str = "GET", body: dict[str, Any] | None = None) -> dict[str, Any]:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            raise LLMClientError(f"OpenAI API request failed: {message}") from exc
        except (TimeoutError, urllib.error.URLError) as exc:
            raise LLMClientError(f"OpenAI API request failed: {exc}") from exc

    def upload_file(self, path: str | Path, *, purpose: str = "batch") -> dict[str, Any]:
        path = Path(path)
        boundary = f"----secondopinion-{uuid.uuid4().hex}"
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        parts = [
            (
                f"--{boundary}\r\n"
                'Content-Disposition: form-data; name="purpose"\r\n\r\n'
                f"{purpose}\r\n"
            ).encode("utf-8"),
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
                f"Content-Type: {mime}\r\n\r\n"
            ).encode("utf-8"),
            path.read_bytes(),
            f"\r\n--{boundary}--\r\n".encode("utf-8"),
        ]
        request = urllib.request.Request(
            f"{self.base_url}/files",
            data=b"".join(parts),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            raise LLMClientError(f"OpenAI file upload failed: {message}") from exc
        except (TimeoutError, urllib.error.URLError) as exc:
            raise LLMClientError(f"OpenAI file upload failed: {exc}") from exc

    def create_batch(self, *, input_file_id: str, metadata: dict[str, str] | None = None) -> dict[str, Any]:
        body = {
            "input_file_id": input_file_id,
            "endpoint": OPENAI_BATCH_ENDPOINT,
            "completion_window": "24h",
        }
        if metadata:
            body["metadata"] = metadata
        return self.request_json("/batches", method="POST", body=body)

    def retrieve_batch(self, batch_id: str) -> dict[str, Any]:
        return self.request_json(f"/batches/{urllib.parse.quote(batch_id)}")

    def download_file(self, file_id: str, output: str | Path) -> str:
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(
            f"{self.base_url}/files/{urllib.parse.quote(file_id)}/content",
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                output.write_bytes(response.read())
            return str(output)
        except urllib.error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            raise LLMClientError(f"OpenAI file download failed: {message}") from exc
        except (TimeoutError, urllib.error.URLError) as exc:
            raise LLMClientError(f"OpenAI file download failed: {exc}") from exc


def submit_scoring_batch(
    *,
    jsonl_path: str | Path,
    manifest_path: str | Path,
    submission_out: str | Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    if dry_run:
        payload = {"dry_run": True, "input": str(jsonl_path), "manifest": manifest}
    else:
        client = OpenAIBatchClient.from_env()
        file_payload = client.upload_file(jsonl_path, purpose="batch")
        batch_payload = client.create_batch(
            input_file_id=file_payload["id"],
            metadata={
                "project": "secondopinion",
                "dataset": Path(str(manifest.get("normalized_path", ""))).stem[:64],
                "model": str(manifest.get("model", ""))[:64],
            },
        )
        payload = {"dry_run": False, "file": file_payload, "batch": batch_payload, "manifest": manifest}
    out = Path(submission_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def retrieve_scoring_batch(
    *,
    batch_id: str,
    output_jsonl: str | Path,
    status_out: str | Path,
    error_jsonl: str | Path | None = None,
) -> dict[str, Any]:
    client = OpenAIBatchClient.from_env()
    batch = client.retrieve_batch(batch_id)
    status_path = Path(status_out)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if batch.get("output_file_id"):
        client.download_file(str(batch["output_file_id"]), output_jsonl)
    if error_jsonl and batch.get("error_file_id"):
        client.download_file(str(batch["error_file_id"]), error_jsonl)
    return batch


def parse_batch_score_result(record: dict[str, Any]) -> dict[str, Any] | None:
    if record.get("error"):
        return None
    response = record.get("response") or {}
    if int(response.get("status_code") or 0) != 200:
        return None
    body = response.get("body") or {}
    message = ((body.get("choices") or [{}])[0].get("message") or {})
    content = message.get("content")
    if isinstance(content, list):
        content = "".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
    if not isinstance(content, str) or not content.strip():
        return None
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return None
    return normalize_score_payload(payload)


def normalize_score_payload(payload: dict[str, Any]) -> dict[str, Any]:
    raw_scores = {
        "outrage": clamp_int(payload.get("outrage")),
        "toxicity": clamp_int(payload.get("toxicity")),
        "helpfulness": clamp_int(payload.get("helpfulness")),
    }
    if raw_scores and 0 < max(raw_scores.values()) <= 10:
        raw_scores = {key: clamp_int(value * 10) for key, value in raw_scores.items()}
    return {
        "outrage": raw_scores["outrage"],
        "toxicity": raw_scores["toxicity"],
        "helpfulness": raw_scores["helpfulness"],
        "quote": truncate_clean_text(payload.get("quote"), 180),
        "verdict": truncate_clean_text(payload.get("verdict"), 80),
        "evidence": truncate_clean_text(payload.get("evidence"), 180),
        "actionable": bool(payload.get("actionable")),
    }


def truncate_clean_text(value: Any, max_chars: int) -> str:
    text = clean_ws(str(value or ""))
    if len(text) <= max_chars:
        return text
    clipped = text[: max(0, max_chars - 1)].rstrip()
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0].rstrip()
    return f"{clipped}..."


def clamp_int(value: Any) -> int:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, number))


def import_batch_results(
    *,
    results_jsonl: str | Path,
    manifest_path: str | Path,
    database_url: str | None = None,
    artifact_root: str | Path | None = None,
    scorer_version: str = BATCH_SCORER_VERSION,
    memory_index_version: str = BATCH_MEMORY_VERSION,
) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    results = read_jsonl(results_jsonl)
    by_custom_id = {str(record.get("custom_id")): parse_batch_score_result(record) for record in results}
    task_map = {str(task["custom_id"]): task for task in manifest.get("tasks", []) if isinstance(task, dict)}
    settings = settings_from_env()
    if database_url:
        settings = ServerSettings(
            database_url=database_url,
            artifact_root=settings.artifact_root,
            scoring_memory_path=settings.scoring_memory_path,
            scorer_version=settings.scorer_version,
            memory_index_version=settings.memory_index_version,
            cors_origins=settings.cors_origins,
            max_claims_per_review=settings.max_claims_per_review,
            llm_scorer_enabled=settings.llm_scorer_enabled,
            llm_scorer_model=settings.llm_scorer_model,
        )
    artifact_base = Path(artifact_root or settings.artifact_root)
    engine = make_engine(settings.database_url)
    init_db(engine)
    session_factory = make_session_factory(engine)
    imported = 0
    failed = 0
    papers_seen = set()
    with session_scope(session_factory) as session:
        grouped: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
        for custom_id, task in task_map.items():
            score = by_custom_id.get(custom_id)
            if not score:
                failed += 1
                continue
            grouped[str(task["paper_id"])].append((task, score))
        for paper_id, scored_reviews in grouped.items():
            paper = session.get(Paper, paper_id)
            if paper is None:
                continue
            public = build_public_scorecard_from_review_scores(paper, scored_reviews)
            artifact_path = write_scorecard_artifact(artifact_base, paper.paper_id, public)
            store_scorecard(
                session,
                paper=paper,
                public_json=public,
                internal_artifact_path=str(artifact_path),
                scorer_version=scorer_version,
                memory_index_version=memory_index_version,
            )
            papers_seen.add(paper_id)
            imported += len(scored_reviews)
    return {
        "result_count": len(results),
        "task_count": len(task_map),
        "imported_review_scores": imported,
        "failed_or_missing_review_scores": failed,
        "scorecard_count": len(papers_seen),
        "scorer_version": scorer_version,
        "memory_index_version": memory_index_version,
    }


def build_public_scorecard_from_review_scores(
    paper: Paper,
    scored_reviews: list[tuple[dict[str, Any], dict[str, Any]]],
) -> dict[str, Any]:
    reviews_by_id = {review.review_id: review for review in paper.reviews}
    reviewers = []
    comments = []
    for index, (task, score) in enumerate(sorted(scored_reviews, key=lambda item: item[0]["reviewer_index"]), start=1):
        review = reviews_by_id.get(str(task["review_id"]))
        reviewer_key = f"R{int(task.get('reviewer_index') or index)}"
        nickname = nickname_for_batch_score(score, index)
        text = score["quote"] or (review_snippet(review) if review else "")
        verdict = score["verdict"] or "Scored by the Weak Reject batch scorer."
        dimensions = batch_dimensions(score)
        reviewers.append(
            {
                "reviewer_key": reviewer_key,
                "nickname": nickname,
                "avatar_key": f"r{index}",
                "score": score["outrage"],
                "tone": "red" if score["outrage"] >= 70 else "gold" if score["helpfulness"] >= 65 else "black",
                "label": "Outrage" if score["outrage"] >= 70 else "Helpful" if score["helpfulness"] >= 65 else "Mixed",
                "summary": verdict,
                "rating": review.rating_normalized if review else None,
                "confidence": review.confidence_normalized if review else None,
                "social": {"up": 0, "down": 0},
                "dimensions": dimensions,
                "topics": top_keywords((review_snippet(review) if review else "") + " " + verdict, limit=5),
            }
        )
        comments.append(
            {
                "reviewer_key": reviewer_key,
                "nickname": nickname,
                "chunk_id": f"C{len(comments) + 1}",
                "text": text,
                "second_opinion": verdict,
                "tone": "red" if score["outrage"] >= 70 else "gold" if score["helpfulness"] >= 65 else "black",
                "up": 0,
                "down": 0,
                "topics": top_keywords(text + " " + verdict, limit=4),
            }
        )
    return {
        "schema_version": PUBLIC_SCORECARD_VERSION,
        "scoring_schema_version": "weak-reject-review-batch-v0.1",
        "paper": {
            "paper_id": paper.paper_id,
            "title": paper.title,
            "conference": f"{paper.venue} {paper.year}",
            "venue": paper.venue,
            "year": paper.year,
            "decision": paper.decision,
        },
        "summary": {
            "overall_score": round(mean(item["score"] for item in reviewers)) if reviewers else 0,
            "signal_label": "Outrage Index",
            "reviewer_count": len(reviewers),
            "comment_count": len(comments),
            "topic_count": len({topic for comment in comments for topic in comment.get("topics", [])}),
            "situation": "Reviewer comments scored by the offline Weak Reject batch scorer.",
        },
        "reviewers": reviewers,
        "comments": comments,
        "topics": [],
        "leaderboards": per_paper_leaderboards(reviewers),
    }


def batch_dimensions(score: dict[str, Any]) -> list[dict[str, Any]]:
    quote = score.get("quote", "")
    verdict = score.get("verdict", "")
    evidence = score.get("evidence", "")
    return [
        {
            "key": "outrage",
            "label": "Outrage",
            "score": score["outrage"],
            "criterion": "Performative, vague, unfair, or over-harsh review energy.",
            "quote": quote,
            "verdict": verdict,
            "evidence": evidence,
            "actionable": score["actionable"],
        },
        {
            "key": "toxicity",
            "label": "Toxicity",
            "score": score["toxicity"],
            "criterion": "Insults, contempt, or personal attacks in the comment.",
            "quote": quote,
            "verdict": verdict,
            "evidence": evidence,
            "actionable": score["actionable"],
        },
        {
            "key": "helpfulness",
            "label": "Helpfulness",
            "score": score["helpfulness"],
            "criterion": "Specific, evidence-linked, actionable feedback.",
            "quote": quote,
            "verdict": verdict,
            "evidence": evidence,
            "actionable": score["actionable"],
        },
    ]


def per_paper_leaderboards(reviewers: list[dict[str, Any]]) -> dict[str, list[str]]:
    return {
        "overall": [
            item["reviewer_key"]
            for item in sorted(reviewers, key=lambda item: (-dimension_value(item, "outrage"), item["reviewer_key"]))[:10]
        ],
        "toxic": [
            item["reviewer_key"]
            for item in sorted(reviewers, key=lambda item: (-dimension_value(item, "toxicity"), item["reviewer_key"]))[:10]
        ],
        "helpful": [
            item["reviewer_key"]
            for item in sorted(reviewers, key=lambda item: (-dimension_value(item, "helpfulness"), item["reviewer_key"]))[:10]
        ],
        "red": [
            item["reviewer_key"]
            for item in sorted(reviewers, key=lambda item: (-int(item.get("score") or 0), item["reviewer_key"]))[:10]
        ],
        "black": [
            item["reviewer_key"]
            for item in sorted(reviewers, key=lambda item: (int(item.get("score") or 0), item["reviewer_key"]))[:10]
        ],
    }


def dimension_value(reviewer: dict[str, Any], key: str) -> int:
    for dimension in reviewer.get("dimensions", []):
        if isinstance(dimension, dict) and dimension.get("key") == key:
            return clamp_int(dimension.get("score"))
    return clamp_int(reviewer.get("score"))


def nickname_for_batch_score(score: dict[str, Any], index: int) -> str:
    if score["toxicity"] >= 65:
        return "Tone Alarm"
    if score["outrage"] >= 75:
        return "Outrage Beacon"
    if score["helpfulness"] >= 75:
        return "Actual Reviewer"
    if score["helpfulness"] <= 35:
        return "Vague Thunder"
    return ["Signal Judge", "Margin Critic", "Baseline Siren", "Scope Checker"][(index - 1) % 4]


def review_snippet(review: Review | None, *, max_chars: int = 260) -> str:
    if review is None:
        return ""
    text = clean_ws("\n".join(part for part in [review.weaknesses, review.questions, review.review_text] if part))
    return text[:max_chars]


def write_scorecard_artifact(root: str | Path, paper_id: str, public: dict[str, Any]) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.:-]+", "_", paper_id)[:80]
    path = Path(root) / "batch_scoring" / f"{safe}_public_scorecard.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def mean(values: Iterable[float]) -> float:
    items = list(values)
    return sum(items) / len(items) if items else 0.0


def import_normalized_to_db(path: str | Path, *, database_url: str | None = None) -> dict[str, Any]:
    settings = settings_from_env()
    engine = make_engine(database_url or settings.database_url)
    init_db(engine)
    session_factory = make_session_factory(engine)
    with session_scope(session_factory) as session:
        return import_normalized_dataset(session, path)


def command_pull(args: argparse.Namespace) -> None:
    output = args.output or f"data/normalized/{args.venue.lower()}_{args.year}_{'full' if args.limit is None else args.limit}.json"
    summary = pull_openreview_normalized(
        venue=args.venue,
        year=args.year,
        limit=args.limit,
        output=output,
        raw_root=args.raw_root,
        invitation=args.invitation or None,
        page_size=args.page_size,
        details=args.details,
        polite_delay=args.polite_delay,
        resume=args.resume,
        snapshot_id=args.snapshot or None,
        raw_snapshot=args.raw_snapshot,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def command_quality(args: argparse.Namespace) -> None:
    report = write_quality_report(
        normalized_path=args.input,
        json_out=args.json_out,
        markdown_out=args.markdown_out,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


def command_ingest(args: argparse.Namespace) -> None:
    summary = import_normalized_to_db(args.input, database_url=args.database_url or None)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def command_build_batch(args: argparse.Namespace) -> None:
    excluded = load_custom_ids(args.exclude_custom_ids)
    manifest = build_scoring_batch(
        normalized_path=args.input,
        output_jsonl=args.output,
        manifest_path=args.manifest,
        model=args.model,
        limit_reviews=args.limit_reviews,
        exclude_custom_ids=excluded,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


def command_split_batch(args: argparse.Namespace) -> None:
    summary = split_scoring_batch(
        batch_jsonl=args.input,
        manifest_path=args.manifest,
        output_dir=args.output_dir,
        prefix=args.prefix,
        max_estimated_input_tokens=args.max_estimated_input_tokens,
        max_requests=args.max_requests,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def command_submit_batch(args: argparse.Namespace) -> None:
    payload = submit_scoring_batch(
        jsonl_path=args.input,
        manifest_path=args.manifest,
        submission_out=args.output,
        dry_run=args.dry_run,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def command_retrieve_batch(args: argparse.Namespace) -> None:
    batch = retrieve_scoring_batch(
        batch_id=args.batch_id,
        output_jsonl=args.output,
        status_out=args.status_out,
        error_jsonl=args.error_output or None,
    )
    print(json.dumps(batch, ensure_ascii=False, indent=2))


def command_import_results(args: argparse.Namespace) -> None:
    summary = import_batch_results(
        results_jsonl=args.input,
        manifest_path=args.manifest,
        database_url=args.database_url or None,
        artifact_root=args.artifact_root or None,
        scorer_version=args.scorer_version,
        memory_index_version=args.memory_index_version,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def load_custom_ids(paths: list[str]) -> set[str]:
    custom_ids: set[str] = set()
    for raw_path in paths:
        path = Path(raw_path)
        if not raw_path or not path.exists():
            continue
        if path.suffix.lower() == ".jsonl":
            records = read_jsonl(path)
            custom_ids.update(str(record.get("custom_id")) for record in records if record.get("custom_id"))
            continue
        payload = read_json(path)
        if isinstance(payload.get("tasks"), list):
            custom_ids.update(str(task.get("custom_id")) for task in payload["tasks"] if isinstance(task, dict) and task.get("custom_id"))
    return custom_ids


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OpenReview pull and cheap Batch scoring tools.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    pull = subparsers.add_parser("pull")
    pull.add_argument("--venue", default="ICLR")
    pull.add_argument("--year", type=int, default=2025)
    pull.add_argument("--limit", type=int, default=None)
    pull.add_argument("--output", default="")
    pull.add_argument("--raw-root", default="data/raw")
    pull.add_argument("--invitation", default="")
    pull.add_argument("--page-size", type=int, default=100)
    pull.add_argument("--details", default="replies")
    pull.add_argument("--polite-delay", type=float, default=0.1)
    pull.add_argument("--snapshot", default="", help="Source snapshot id to record; with --raw-snapshot/--resume it names the raw snapshot directory.")
    pull.add_argument("--raw-snapshot", action="store_true", help="Persist full raw OpenReview API pages. Off by default for data minimization.")
    pull.add_argument("--resume", action="store_true")
    pull.set_defaults(func=command_pull)

    quality = subparsers.add_parser("quality")
    quality.add_argument("--input", required=True)
    quality.add_argument("--json-out", required=True)
    quality.add_argument("--markdown-out", required=True)
    quality.set_defaults(func=command_quality)

    ingest = subparsers.add_parser("ingest")
    ingest.add_argument("--input", required=True)
    ingest.add_argument("--database-url", default=os.environ.get("SECONDOPINION_DATABASE_URL", ""))
    ingest.set_defaults(func=command_ingest)

    build = subparsers.add_parser("build-batch")
    build.add_argument("--input", required=True)
    build.add_argument("--output", required=True)
    build.add_argument("--manifest", required=True)
    build.add_argument("--model", default=os.environ.get("SECONDOPINION_BATCH_MODEL", DEFAULT_BATCH_MODEL))
    build.add_argument("--limit-reviews", type=int, default=None)
    build.add_argument("--exclude-custom-ids", action="append", default=[])
    build.set_defaults(func=command_build_batch)

    split = subparsers.add_parser("split-batch")
    split.add_argument("--input", required=True)
    split.add_argument("--manifest", required=True)
    split.add_argument("--output-dir", required=True)
    split.add_argument("--prefix", required=True)
    split.add_argument("--max-estimated-input-tokens", type=int, default=1_600_000)
    split.add_argument("--max-requests", type=int, default=None)
    split.set_defaults(func=command_split_batch)

    submit = subparsers.add_parser("submit-batch")
    submit.add_argument("--input", required=True)
    submit.add_argument("--manifest", required=True)
    submit.add_argument("--output", required=True)
    submit.add_argument("--dry-run", action="store_true")
    submit.set_defaults(func=command_submit_batch)

    retrieve = subparsers.add_parser("retrieve-batch")
    retrieve.add_argument("--batch-id", required=True)
    retrieve.add_argument("--output", required=True)
    retrieve.add_argument("--status-out", required=True)
    retrieve.add_argument("--error-output", default="")
    retrieve.set_defaults(func=command_retrieve_batch)

    import_results = subparsers.add_parser("import-results")
    import_results.add_argument("--input", required=True)
    import_results.add_argument("--manifest", required=True)
    import_results.add_argument("--database-url", default=os.environ.get("SECONDOPINION_DATABASE_URL", ""))
    import_results.add_argument("--artifact-root", default="")
    import_results.add_argument("--scorer-version", default=BATCH_SCORER_VERSION)
    import_results.add_argument("--memory-index-version", default=BATCH_MEMORY_VERSION)
    import_results.set_defaults(func=command_import_results)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

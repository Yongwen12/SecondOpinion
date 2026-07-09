from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
from pathlib import Path
from typing import Any

from sqlalchemy import func

from .server.config import settings_from_env
from .server.database import make_engine, make_session_factory, session_scope
from .server.models import Paper, Review

DATA_MINIMIZATION_AUDIT_VERSION = "openreview-data-minimization-audit-v0.1"
FORBIDDEN_NORMALIZED_KEYS = {
    "full_text",
    "paper_text",
    "pdf_text",
    "body_text",
    "body",
    "sections",
    "paragraphs",
    "pdf_url",
    "rebuttals",
}
FORBIDDEN_BATCH_MARKERS = [
    "pdf_url",
    "full_text",
    "paper_text",
    "pdf_text",
    "body_text",
]
ALLOWED_NORMALIZED_PAPER_KEYS = {
    "paper_id",
    "openreview_forum_id",
    "venue",
    "year",
    "title",
    "abstract",
    "authors_anonymized",
    "decision",
    "reviews",
    "decisions",
    "raw_invitation",
    "snapshot_time",
    "openreview_timestamps",
}
ALLOWED_NORMALIZED_REVIEW_KEYS = {
    "review_id",
    "paper_id",
    "review_text",
    "summary",
    "strengths",
    "weaknesses",
    "questions",
    "rating_raw",
    "rating_normalized",
    "confidence_raw",
    "confidence_normalized",
    "review_stage",
    "raw_invitation",
    "snapshot_time",
    "openreview_timestamps",
}


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def write_text(path: str | Path, text: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def expand_patterns(patterns: list[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        matches = [Path(item) for item in glob.glob(pattern, recursive=True)]
        paths.extend(path for path in matches if path.is_file())
    return sorted(dict.fromkeys(paths))


def nested_forbidden_keys(value: Any, *, prefix: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            path = f"{prefix}.{key_text}" if prefix else key_text
            if key_text.lower() in FORBIDDEN_NORMALIZED_KEYS:
                hits.append(path)
            hits.extend(nested_forbidden_keys(child, prefix=path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(nested_forbidden_keys(child, prefix=f"{prefix}[{index}]"))
    return hits


def audit_normalized_file(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    papers = [paper for paper in payload.get("papers", []) if isinstance(paper, dict)]
    paper_extra_keys = sorted({key for paper in papers for key in paper if key not in ALLOWED_NORMALIZED_PAPER_KEYS})
    review_extra_keys = sorted(
        {
            key
            for paper in papers
            for review in paper.get("reviews", [])
            if isinstance(review, dict)
            for key in review
            if key not in ALLOWED_NORMALIZED_REVIEW_KEYS
        }
    )
    forbidden_paths = nested_forbidden_keys(payload)
    return {
        "path": str(path),
        "paper_count": len(papers),
        "review_count": sum(len(paper.get("reviews") or []) for paper in papers),
        "paper_extra_keys": paper_extra_keys,
        "review_extra_keys": review_extra_keys,
        "forbidden_paths": forbidden_paths[:50],
        "forbidden_path_count": len(forbidden_paths),
        "pdf_url_pointer_count": sum(1 for paper in papers if paper.get("pdf_url")),
        "status": "failed" if forbidden_paths else "ok",
    }


def audit_batch_file(path: Path) -> dict[str, Any]:
    request_count = 0
    marker_counts = {marker: 0 for marker in FORBIDDEN_BATCH_MARKERS}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        request_count += 1
        lowered = line.lower()
        for marker in FORBIDDEN_BATCH_MARKERS:
            if marker.lower() in lowered:
                marker_counts[marker] += 1
    hits = {marker: count for marker, count in marker_counts.items() if count}
    return {
        "path": str(path),
        "request_count": request_count,
        "forbidden_marker_counts": hits,
        "status": "failed" if hits else "ok",
    }


def audit_raw_openreview_root(root: str | Path = "data/raw/openreview") -> dict[str, Any]:
    root_path = Path(root)
    if not root_path.exists():
        return {
            "root": str(root_path),
            "file_count": 0,
            "total_bytes": 0,
            "total_gb": 0.0,
            "status": "ok",
            "recommendation": "no raw OpenReview snapshots found",
        }
    files = [path for path in root_path.rglob("*") if path.is_file()]
    total_bytes = sum(path.stat().st_size for path in files)
    risky_files = [path for path in files if path.name.startswith("notes_page_") and path.suffix.lower() == ".json"]
    status = "requires_cleanup" if risky_files else "ok"
    recommendation = (
        "delete or archive raw OpenReview API snapshots after explicit approval; normalized, batch, and database artifacts are sufficient for production"
        if risky_files
        else "no raw OpenReview note pages found"
    )
    return {
        "root": str(root_path),
        "file_count": len(files),
        "raw_note_page_count": len(risky_files),
        "total_bytes": total_bytes,
        "total_gb": round(total_bytes / 1_000_000_000, 3),
        "sample_files": [str(path) for path in risky_files[:10]],
        "status": status,
        "recommendation": recommendation,
    }


def audit_database() -> dict[str, Any]:
    settings = settings_from_env()
    engine = make_engine(settings.database_url)
    factory = make_session_factory(engine)
    paper_source_forbidden = 0
    review_source_forbidden = 0
    paper_source_keys: dict[str, int] = {}
    review_source_keys: dict[str, int] = {}
    with session_scope(factory) as session:
        paper_count = int(session.query(func.count(Paper.paper_id)).scalar() or 0)
        review_count = int(session.query(func.count(Review.review_id)).scalar() or 0)
        pdf_url_nonempty_count = int(session.query(func.count(Paper.paper_id)).filter(Paper.pdf_url != "").scalar() or 0)
        for (source,) in session.query(Paper.source_json).yield_per(1000):
            if not isinstance(source, dict):
                continue
            if nested_forbidden_keys(source):
                paper_source_forbidden += 1
            for key in source:
                paper_source_keys[str(key)] = paper_source_keys.get(str(key), 0) + 1
        for (source,) in session.query(Review.source_json).yield_per(1000):
            if not isinstance(source, dict):
                continue
            if nested_forbidden_keys(source):
                review_source_forbidden += 1
            for key in source:
                review_source_keys[str(key)] = review_source_keys.get(str(key), 0) + 1
    return {
        "paper_count": paper_count,
        "review_count": review_count,
        "pdf_url_nonempty_count": pdf_url_nonempty_count,
        "paper_source_forbidden_count": paper_source_forbidden,
        "review_source_forbidden_count": review_source_forbidden,
        "paper_source_keys": dict(sorted(paper_source_keys.items())),
        "review_source_keys": dict(sorted(review_source_keys.items())),
        "status": "failed" if pdf_url_nonempty_count or paper_source_forbidden or review_source_forbidden else "ok",
    }


def build_data_minimization_audit(
    *,
    normalized_patterns: list[str] | None = None,
    batch_patterns: list[str] | None = None,
    include_database: bool = False,
    raw_root: str | Path | None = None,
    fail_on_raw: bool = False,
) -> dict[str, Any]:
    normalized_files = expand_patterns(["data/normalized/**/*.json"] if normalized_patterns is None else normalized_patterns)
    batch_files = expand_patterns(["data/batch/**/*.jsonl"] if batch_patterns is None else batch_patterns)
    normalized = [audit_normalized_file(path) for path in normalized_files]
    batches = [audit_batch_file(path) for path in batch_files]
    database = audit_database() if include_database else {}
    raw = audit_raw_openreview_root(raw_root) if raw_root is not None else {}
    errors = []
    for item in normalized:
        if item["status"] != "ok":
            errors.append(f"normalized file contains forbidden full-text fields: {item['path']}")
    for item in batches:
        if item["status"] != "ok":
            errors.append(f"batch prompt contains disallowed full-text/pdf marker: {item['path']}")
    if database and database.get("status") != "ok":
        errors.append("database contains disallowed PDF pointers or forbidden source_json fields")
    if fail_on_raw and raw and raw.get("status") != "ok":
        errors.append("raw OpenReview API snapshots remain; delete or archive them outside the production workspace")
    return {
        "schema_version": DATA_MINIMIZATION_AUDIT_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "status": "failed" if errors else "passed",
        "policy": {
            "normalized_allowed_core": "title, abstract, decision metadata, official review fields, ratings/confidence, and timestamps only; no PDF pointer/body and no author response/rebuttal text",
            "ai_scoring_allowed_core": "title, abstract, rating/confidence, and compacted public review text only",
            "forbidden_normalized_keys": sorted(FORBIDDEN_NORMALIZED_KEYS),
            "forbidden_batch_markers": FORBIDDEN_BATCH_MARKERS,
            "allowed_review_text_links": ["openreview.net/pdf", "arxiv.org/pdf"],
        },
        "summary": {
            "normalized_file_count": len(normalized),
            "batch_file_count": len(batches),
            "normalized_failed_count": sum(1 for item in normalized if item["status"] != "ok"),
            "batch_failed_count": sum(1 for item in batches if item["status"] != "ok"),
            "total_papers_seen": sum(int(item.get("paper_count") or 0) for item in normalized),
            "total_reviews_seen": sum(int(item.get("review_count") or 0) for item in normalized),
            "batch_request_count": sum(int(item.get("request_count") or 0) for item in batches),
            "database_checked": bool(database),
            "database_status": database.get("status", "not_checked") if database else "not_checked",
            "raw_checked": bool(raw),
            "raw_status": raw.get("status", "not_checked") if raw else "not_checked",
            "raw_total_gb": raw.get("total_gb", 0.0) if raw else 0.0,
            "fail_on_raw": fail_on_raw,
        },
        "normalized_files": normalized,
        "batch_files": batches,
        "database": database,
        "raw": raw,
        "errors": errors,
    }


def render_data_minimization_audit_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    policy = report.get("policy") or {}
    lines = [
        "# OpenReview Data Minimization Audit",
        "",
        f"- Created: `{report.get('created_at', '')}`",
        f"- Status: `{report.get('status', '')}`",
        f"- Normalized files: `{summary.get('normalized_file_count', 0)}`",
        f"- Batch files: `{summary.get('batch_file_count', 0)}`",
        f"- Papers seen: `{summary.get('total_papers_seen', 0)}`",
        f"- Reviews seen: `{summary.get('total_reviews_seen', 0)}`",
        f"- Batch requests: `{summary.get('batch_request_count', 0)}`",
        f"- Database checked: `{summary.get('database_checked', False)}`",
        f"- Database status: `{summary.get('database_status', 'not_checked')}`",
        f"- Raw checked: `{summary.get('raw_checked', False)}`",
        f"- Raw status: `{summary.get('raw_status', 'not_checked')}`",
        f"- Raw size GB: `{summary.get('raw_total_gb', 0.0)}`",
        f"- Fail on raw: `{summary.get('fail_on_raw', False)}`",
        "",
        "## Policy",
        "",
        f"- Normalized: {policy.get('normalized_allowed_core', '')}",
        f"- AI scoring: {policy.get('ai_scoring_allowed_core', '')}",
        f"- Forbidden normalized keys: `{', '.join(policy.get('forbidden_normalized_keys') or []) or '-'}`",
        f"- Forbidden batch markers: `{', '.join(policy.get('forbidden_batch_markers') or []) or '-'}`",
        "",
        "## Issues",
        "",
    ]
    if report.get("errors"):
        lines.extend(f"- ERROR: {error}" for error in report.get("errors", []))
    else:
        lines.append("- None")
    raw = report.get("raw") or {}
    if raw and raw.get("status") != "ok":
        lines.extend([
            "",
            "## Raw Snapshot Retention",
            "",
            f"- Status: `{raw.get('status', '')}`",
            f"- Files: `{raw.get('file_count', 0)}`",
            f"- Raw note pages: `{raw.get('raw_note_page_count', 0)}`",
            f"- Size GB: `{raw.get('total_gb', 0.0)}`",
            f"- Recommendation: {raw.get('recommendation', '')}",
        ])
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit that OpenReview normalized data and AI batch prompts avoid paper full text/PDF content.")
    parser.add_argument("--normalized", action="append", default=[], help="Normalized JSON glob. Repeatable.")
    parser.add_argument("--batch", action="append", default=[], help="Batch JSONL glob. Repeatable.")
    parser.add_argument("--include-database", action="store_true", help="Also audit the configured SecondOpinion database for PDF pointers and forbidden source_json fields.")
    parser.add_argument("--raw-root", default="", help="Optional raw OpenReview snapshot root to report as cleanup-required if raw note pages remain.")
    parser.add_argument("--fail-on-raw", action="store_true", help="Fail the audit if raw OpenReview note pages remain under --raw-root.")
    parser.add_argument("--out", default="data/validation/openreview_data_minimization_audit.json")
    parser.add_argument("--markdown", default="reports/validation/openreview_data_minimization_audit.md")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    report = build_data_minimization_audit(
        normalized_patterns=args.normalized or None,
        batch_patterns=args.batch or None,
        include_database=args.include_database,
        raw_root=args.raw_root or None,
        fail_on_raw=args.fail_on_raw,
    )
    write_json(args.out, report)
    write_text(args.markdown, render_data_minimization_audit_markdown(report))
    print(json.dumps({"status": report["status"], **report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
from pathlib import Path
from typing import Any


BATCH_COST_REVIEW_VERSION = "batch-cost-review-v0.1"


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def discover_manifest_paths(patterns: list[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        matches = glob.glob(pattern, recursive=True)
        if matches:
            paths.extend(Path(match) for match in matches)
        else:
            candidate = Path(pattern)
            if candidate.exists():
                paths.append(candidate)
    return sorted({path.resolve(): path for path in paths}.values(), key=lambda path: str(path))


def manifest_record(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    payload = read_json(path)
    source_manifest = str(payload.get("source_manifest_path") or "")
    is_part = bool(source_manifest)
    return {
        "path": str(path),
        "dataset": str(payload.get("dataset") or payload.get("normalized_path") or path.stem),
        "model": str(payload.get("model") or ""),
        "request_count": int(payload.get("request_count") or 0),
        "estimated_input_tokens": int(payload.get("estimated_input_tokens") or 0),
        "estimated_output_tokens": int(payload.get("estimated_output_tokens") or 0),
        "estimated_batch_cost_usd": float(payload.get("estimated_batch_cost_usd") or 0.0),
        "excluded_request_count": int(payload.get("excluded_request_count") or 0),
        "is_part_manifest": is_part,
        "source_manifest_path": source_manifest,
        "included_in_total": True,
        "excluded_from_total_reason": "",
    }


def _normalized_manifest_path(path: str | Path, *, base_dir: Path | None = None) -> str:
    candidate = Path(path)
    if not candidate.is_absolute() and base_dir is not None:
        candidate = base_dir / candidate
    try:
        return str(candidate.resolve())
    except OSError:
        return str(candidate.absolute())


def dedupe_split_manifest_totals(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source_paths = {
        _normalized_manifest_path(record["source_manifest_path"])
        for record in records
        if record.get("is_part_manifest") and record.get("source_manifest_path")
    }
    if not source_paths:
        return records

    deduped: list[dict[str, Any]] = []
    for record in records:
        copy = dict(record)
        if not copy.get("is_part_manifest") and _normalized_manifest_path(copy["path"]) in source_paths:
            copy["included_in_total"] = False
            copy["excluded_from_total_reason"] = "replaced_by_part_manifests"
        deduped.append(copy)
    return deduped


def review_batch_costs(
    *,
    patterns: list[str],
    max_total_cost_usd: float | None = None,
    include_part_manifests: bool = True,
    dedupe_split_manifests: bool = True,
) -> dict[str, Any]:
    records = [manifest_record(path) for path in discover_manifest_paths(patterns)]
    if not include_part_manifests:
        records = [record for record in records if not record["is_part_manifest"]]
    elif dedupe_split_manifests:
        records = dedupe_split_manifest_totals(records)
    included_records = [record for record in records if record.get("included_in_total", True)]
    total_cost = round(sum(float(record["estimated_batch_cost_usd"]) for record in included_records), 4)
    total_requests = sum(int(record["request_count"]) for record in included_records)
    total_input_tokens = sum(int(record["estimated_input_tokens"]) for record in included_records)
    total_output_tokens = sum(int(record["estimated_output_tokens"]) for record in included_records)
    over_limit = max_total_cost_usd is not None and total_cost > max_total_cost_usd
    return {
        "schema_version": BATCH_COST_REVIEW_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "status": "blocked_cost_limit" if over_limit else "ready_for_cost_review",
        "max_total_cost_usd": max_total_cost_usd,
        "summary": {
            "manifest_count": len(records),
            "included_manifest_count": len(included_records),
            "excluded_manifest_count": len(records) - len(included_records),
            "request_count": total_requests,
            "estimated_input_tokens": total_input_tokens,
            "estimated_output_tokens": total_output_tokens,
            "estimated_batch_cost_usd": total_cost,
        },
        "manifests": records,
    }


def render_batch_cost_review_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# Batch Cost Review",
        "",
        f"- Created: `{report.get('created_at', '')}`",
        f"- Status: `{report.get('status', '')}`",
        f"- Max total cost USD: `{report.get('max_total_cost_usd', None)}`",
        f"- Manifest count: `{summary.get('manifest_count', 0)}`",
        f"- Request count: `{summary.get('request_count', 0)}`",
        f"- Estimated batch cost USD: `{float(summary.get('estimated_batch_cost_usd') or 0):.4f}`",
        "",
        "## Manifests",
        "",
        "| Path | Requests | Input tokens | Output tokens | Cost USD | Part | Included | Reason |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for record in report.get("manifests", []):
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{record.get('path', '')}`",
                    str(record.get("request_count", 0)),
                    str(record.get("estimated_input_tokens", 0)),
                    str(record.get("estimated_output_tokens", 0)),
                    f"{float(record.get('estimated_batch_cost_usd') or 0):.4f}",
                    str(bool(record.get("is_part_manifest"))),
                    str(bool(record.get("included_in_total", True))),
                    str(record.get("excluded_from_total_reason") or ""),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review batch scoring manifests and aggregate estimated costs.")
    parser.add_argument("--manifest", action="append", default=[], help="Manifest path or glob. Repeatable.")
    parser.add_argument("--out", default="data/validation/batch_cost_review.json")
    parser.add_argument("--markdown", default="reports/validation/batch_cost_review.md")
    parser.add_argument("--max-total-cost-usd", type=float, default=None)
    parser.add_argument("--exclude-part-manifests", action="store_true")
    parser.add_argument("--no-dedupe-split-manifests", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    patterns = args.manifest or ["data/batch/**/*_manifest.json"]
    report = review_batch_costs(
        patterns=patterns,
        max_total_cost_usd=args.max_total_cost_usd,
        include_part_manifests=not args.exclude_part_manifests,
        dedupe_split_manifests=not args.no_dedupe_split_manifests,
    )
    write_json(args.out, report)
    write_markdown(args.markdown, render_batch_cost_review_markdown(report))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

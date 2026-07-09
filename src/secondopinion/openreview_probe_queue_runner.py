from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from .openreview_client import OpenReviewClient
from .openreview_probe_invitation import render_probe_invitation_markdown, run_probe_invitation, write_json, write_markdown


PROBE_QUEUE_RUNNER_SCHEMA_VERSION = "openreview-probe-queue-runner-v0.1"


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_report(path: str | Path, payload: dict[str, Any]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


def run_probe_queue(
    *,
    queue: dict[str, Any],
    execute: bool = False,
    venue_filter: list[str] | None = None,
    client: OpenReviewClient | None = None,
    max_items: int | None = None,
    skip_existing: bool = False,
) -> dict[str, Any]:
    wanted = {value.upper() for value in venue_filter or []}
    items = [item for item in queue.get("items", []) if not wanted or str(item.get("venue_id") or "").upper() in wanted]
    if max_items is not None and max_items >= 0:
        items = items[:max_items]
    results = []
    client = client if execute else None
    for item in items:
        result = run_queue_item(item, execute=execute, client=client, skip_existing=skip_existing)
        results.append(result)
        if execute and result.get("status") in {"challenge_required", "auth_required"}:
            break
    counts: dict[str, int] = {}
    for result in results:
        status = str(result.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return {
        "schema_version": PROBE_QUEUE_RUNNER_SCHEMA_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "execute": execute,
        "selected_venues": sorted(wanted),
        "probe_count": len(items),
        "status_counts": dict(sorted(counts.items())),
        "max_items": max_items,
        "skip_existing": skip_existing,
        "openai_submit_used": False,
        "results": results,
    }


def run_queue_item(item: dict[str, Any], *, execute: bool, client: OpenReviewClient | None, skip_existing: bool = False) -> dict[str, Any]:
    base = {
        "venue_id": str(item.get("venue_id") or "").upper(),
        "candidate_index": int(item.get("candidate_index") or 0),
        "invitation": str(item.get("invitation") or ""),
        "result_json": str(item.get("result_json") or ""),
        "result_markdown": str(item.get("result_markdown") or ""),
        "command": str(item.get("command") or ""),
    }
    if not execute:
        return {**base, "status": "dry_run", "recommendation": "rerun_with_execute"}
    existing = load_existing_probe_result(base["result_json"]) if skip_existing else {}
    if existing:
        return {
            **base,
            "status": str(existing.get("status") or "existing_result"),
            "recommendation": str(existing.get("recommendation") or "using_existing_result"),
            "skipped_existing": True,
        }
    report = run_probe_invitation(
        invitation=base["invitation"],
        venue_id=base["venue_id"],
        sample_limit=int(item.get("sample_limit") or 50),
        client=client,
    )
    write_json(base["result_json"], report)
    write_markdown(base["result_markdown"], render_probe_invitation_markdown(report))
    return {**base, "status": report.get("status", "unknown"), "recommendation": report.get("recommendation", "")}


def load_existing_probe_result(path: str) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if payload.get("schema_version") != "openreview-probe-invitation-v0.1":
        return {}
    return payload


def render_probe_queue_runner_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# OpenReview Probe Queue Runner",
        "",
        f"- Created: `{report.get('created_at', '')}`",
        f"- Execute: `{report.get('execute', False)}`",
        f"- Probe count: `{report.get('probe_count', 0)}`",
        f"- Status counts: `{report.get('status_counts', {})}`",
        f"- Max items: `{report.get('max_items', None)}`",
        f"- Skip existing: `{report.get('skip_existing', False)}`",
        f"- OpenAI submit used: `{report.get('openai_submit_used', False)}`",
        "",
        "## Results",
        "",
        "| Venue | Candidate | Status | Recommendation | Output |",
        "| --- | ---: | --- | --- | --- |",
    ]
    for item in report.get("results", []):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item.get("venue_id", "")),
                    str(int(item.get("candidate_index") or 0) + 1),
                    str(item.get("status", "")),
                    str(item.get("recommendation", "")),
                    f"`{item.get('result_json', '')}`",
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run OpenReview invitation probe queue. Default is dry-run.")
    parser.add_argument("--queue", default="data/validation/openreview_probe_queue_2025.json")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--venue", action="append", default=[])
    parser.add_argument("--max-items", type=int, default=None)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--api-base", default="https://api2.openreview.net")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--out", default="data/validation/openreview_probe_queue_runner.json")
    parser.add_argument("--markdown", default="reports/validation/openreview_probe_queue_runner.md")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    client = OpenReviewClient(base_url=args.api_base, timeout=args.timeout) if args.execute else None
    report = run_probe_queue(
        queue=read_json(args.queue),
        execute=args.execute,
        venue_filter=args.venue or None,
        client=client,
        max_items=args.max_items,
        skip_existing=args.skip_existing,
    )
    write_report(args.out, report)
    write_text(args.markdown, render_probe_queue_runner_markdown(report))
    print(json.dumps({"execute": report["execute"], "status_counts": report["status_counts"], "probe_count": report["probe_count"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

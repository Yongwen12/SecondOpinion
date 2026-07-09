from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

SNAPSHOT_RECOVERY_SCHEMA_VERSION = "openreview-snapshot-recovery-v0.1"


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def discover_snapshot_manifests(root: str | Path = "data/raw/openreview") -> list[Path]:
    root_path = Path(root)
    if not root_path.exists():
        return []
    return sorted(root_path.glob("**/manifest.json"))


def shell_quote(value: str) -> str:
    if not value:
        return '""'
    if all(char.isalnum() or char in "-_./:=\\" for char in value):
        return value
    return '"' + value.replace('"', '\\"') + '"'


def build_resume_command(manifest: dict[str, Any], *, raw_root: str = "data/raw") -> str:
    query = manifest.get("query") or {}
    venue = str(manifest.get("venue") or "")
    year = int(manifest.get("year") or 0)
    invitation = str(query.get("invitation") or "")
    details = str(query.get("details") or "replies")
    page_size = int(query.get("page_size") or 100)
    polite_delay = float(query.get("polite_delay") or 0.2)
    limit = query.get("limit")
    parts = [
        "python -m secondopinion.tools.openreview_pull",
        "--venue",
        shell_quote(venue),
        "--year",
        str(year),
        "--invitation",
        shell_quote(invitation),
        "--output",
        shell_quote(f"data/normalized/{venue.lower()}_{year}_recovered.json"),
        "--raw-root",
        shell_quote(raw_root),
        "--snapshot",
        shell_quote(str(manifest.get("snapshot_id") or "")),
        "--details",
        shell_quote(details),
        "--page-size",
        str(page_size),
        "--polite-delay",
        str(polite_delay),
        "--resume",
    ]
    if limit is not None:
        parts.extend(["--limit", str(limit)])
    return " ".join(parts)


def snapshot_record(manifest_path: str | Path, *, raw_root: str = "data/raw") -> dict[str, Any]:
    path = Path(manifest_path)
    manifest = read_json(path)
    query = manifest.get("query") or {}
    limit = query.get("limit")
    paper_count = int(manifest.get("paper_count") or 0)
    has_complete_field = "complete" in manifest
    inferred_complete = bool(limit is not None and paper_count >= int(limit or 0))
    complete = bool(manifest.get("complete")) if has_complete_field else inferred_complete
    failed = bool(manifest.get("failed"))
    error = manifest.get("error") if isinstance(manifest.get("error"), dict) else {}
    recoverable = failed or not complete
    return {
        "manifest_path": str(path),
        "snapshot_dir": str(path.parent),
        "venue": str(manifest.get("venue") or ""),
        "year": int(manifest.get("year") or 0),
        "snapshot_id": str(manifest.get("snapshot_id") or ""),
        "complete": complete,
        "complete_source": "manifest" if has_complete_field else "inferred_limit_reached" if inferred_complete else "missing",
        "failed": failed,
        "recoverable": recoverable,
        "paper_count": paper_count,
        "reply_count": int(manifest.get("reply_count") or 0),
        "raw_file_count": len(manifest.get("raw_files") or []),
        "next_offset": int(manifest.get("next_offset") or manifest.get("paper_count") or 0),
        "updated_at": str(manifest.get("updated_at") or ""),
        "error": {
            "type": str(error.get("type") or ""),
            "message": str(error.get("message") or ""),
            "offset": error.get("offset"),
        },
        "resume_command": build_resume_command(manifest, raw_root=raw_root) if recoverable else "",
    }


def build_openreview_snapshot_recovery_report(
    *,
    root: str | Path = "data/raw/openreview",
    raw_root: str = "data/raw",
) -> dict[str, Any]:
    records = [snapshot_record(path, raw_root=raw_root) for path in discover_snapshot_manifests(root)]
    status_counts: dict[str, int] = {}
    for record in records:
        if record["complete"]:
            status = "complete"
        elif record["failed"]:
            status = "failed_recoverable"
        else:
            status = "incomplete_recoverable"
        status_counts[status] = status_counts.get(status, 0) + 1
    recoverable = [record for record in records if record["recoverable"]]
    return {
        "schema_version": SNAPSHOT_RECOVERY_SCHEMA_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "root": str(root),
        "summary": {
            "snapshot_count": len(records),
            "recoverable_count": len(recoverable),
            "status_counts": dict(sorted(status_counts.items())),
            "recoverable_snapshots": [record["snapshot_dir"] for record in recoverable],
        },
        "snapshots": records,
    }


def render_openreview_snapshot_recovery_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# OpenReview Snapshot Recovery",
        "",
        f"- Created: `{report.get('created_at', '')}`",
        f"- Root: `{report.get('root', '')}`",
        f"- Snapshots: `{summary.get('snapshot_count', 0)}`",
        f"- Recoverable: `{summary.get('recoverable_count', 0)}`",
        "",
        "## Status Counts",
        "",
        "| Status | Count |",
        "| --- | ---: |",
    ]
    for status, count in sorted((summary.get("status_counts") or {}).items()):
        lines.append(f"| {status} | {count} |")
    lines.extend([
        "",
        "## Snapshots",
        "",
        "| Venue | Year | Snapshot | Complete | Source | Failed | Papers | Next offset | Error |",
        "| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- |",
    ])
    for record in report.get("snapshots", []):
        error = record.get("error") or {}
        error_text = error.get("type") or "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(record.get("venue", "")),
                    str(record.get("year", "")),
                    f"`{record.get('snapshot_id', '')}`",
                    str(bool(record.get("complete"))),
                    str(record.get("complete_source", "")),
                    str(bool(record.get("failed"))),
                    str(record.get("paper_count", 0)),
                    str(record.get("next_offset", 0)),
                    str(error_text),
                ]
            )
            + " |"
        )
    commands = [record.get("resume_command") for record in report.get("snapshots", []) if record.get("resume_command")]
    lines.extend(["", "## Resume Commands", "", "```powershell"])
    lines.extend(commands or ["# No recoverable snapshots found."])
    lines.extend(["```", ""])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan OpenReview raw snapshots and list recoverable interrupted pulls.")
    parser.add_argument("--root", default="data/raw/openreview")
    parser.add_argument("--raw-root", default="data/raw")
    parser.add_argument("--out", default="data/validation/openreview_snapshot_recovery.json")
    parser.add_argument("--markdown", default="reports/validation/openreview_snapshot_recovery.md")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    report = build_openreview_snapshot_recovery_report(root=args.root, raw_root=args.raw_root)
    write_json(args.out, report)
    write_text(args.markdown, render_openreview_snapshot_recovery_markdown(report))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

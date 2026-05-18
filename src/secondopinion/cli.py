from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .audit import audit_dataset
from .normalize import normalize_openreview_notes
from .openreview_client import OpenReviewClient
from .report import write_html_report, write_markdown_report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="secondopinion", description="SecondOpinion MVP review audit toolkit.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan-iclr", help="Fetch and normalize public ICLR OpenReview submissions.")
    scan.add_argument("--year", type=int, default=2024)
    scan.add_argument("--limit", type=int, default=25)
    scan.add_argument("--out", default="data/normalized/iclr_2024_sample.json")
    scan.add_argument("--raw-out", default="")

    audit = subparsers.add_parser("audit", help="Audit a normalized dataset and write JSON/Markdown/HTML reports.")
    audit.add_argument("--input", required=True)
    audit.add_argument("--out", default="data/audits/audit_results.json")
    audit.add_argument("--markdown", default="reports/audit_report.md")
    audit.add_argument("--html", default="reports/audit_report.html")

    demo = subparsers.add_parser("demo", help="Run the MVP on the bundled sample dataset.")
    demo.add_argument("--out", default="data/audits/demo_audit_results.json")
    demo.add_argument("--markdown", default="reports/mvp_demo.md")
    demo.add_argument("--html", default="reports/mvp_demo.html")

    args = parser.parse_args(argv)
    if args.command == "scan-iclr":
        command_scan_iclr(args)
    elif args.command == "audit":
        command_audit(args)
    elif args.command == "demo":
        command_demo(args)


def command_scan_iclr(args: argparse.Namespace) -> None:
    client = OpenReviewClient()
    notes = client.get_iclr_submissions(args.year, limit=args.limit)
    if args.raw_out:
        write_json({"notes": notes}, args.raw_out)
    normalized = normalize_openreview_notes(notes, venue="ICLR", year=args.year)
    write_json(normalized, args.out)
    print(
        f"Saved {normalized['paper_count']} papers and {normalized['review_count']} reviews to {args.out}."
    )


def command_audit(args: argparse.Namespace) -> None:
    dataset = read_json(args.input)
    result = audit_dataset(dataset)
    write_outputs(result, args.out, args.markdown, args.html)


def command_demo(args: argparse.Namespace) -> None:
    dataset = read_json("examples/sample_normalized_dataset.json")
    result = audit_dataset(dataset)
    write_outputs(result, args.out, args.markdown, args.html)


def write_outputs(result: dict[str, Any], json_path: str, markdown_path: str, html_path: str) -> None:
    write_json(result, json_path)
    write_markdown_report(result, markdown_path)
    write_html_report(result, html_path)
    print(f"Saved audit JSON to {json_path}.")
    print(f"Saved Markdown report to {markdown_path}.")
    print(f"Saved HTML report to {html_path}.")


def read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(payload: dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


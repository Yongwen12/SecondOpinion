from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from .annotation import (
    DEFAULT_ANNOTATION_MODEL,
    compare_annotations,
    default_task_paths,
    export_annotation_tasks,
    llm_label_tasks,
    read_jsonl,
    validate_labels,
    write_annotation_html,
    write_comparison_html,
    write_comparison_markdown,
    write_json as write_annotation_json,
    write_jsonl,
)
from .audit import DEFAULT_JUDGE_MODEL, audit_dataset
from .claim_extraction import DEFAULT_CLAIM_MODEL
from .llm_client import OpenAIChatClient
from .normalize import normalize_openreview_notes
from .openreview_client import OpenReviewClient
from .pdf_store import build_evidence_store
from .report import write_html_report, write_markdown_report
from .snapshot import normalize_snapshot, save_openreview_snapshot
from .storage import resolve_artifact_path, storage_root, suggested_drive_storage_root


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="secondopinion", description="SecondOpinion MVP review audit toolkit.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    storage_parent = argparse.ArgumentParser(add_help=False)
    storage_parent.add_argument(
        "--storage-root",
        default=None,
        help="Optional artifact root. Relative data/... and reports/... paths are read/written under this root.",
    )

    scan = subparsers.add_parser(
        "scan-iclr",
        parents=[storage_parent],
        help="Fetch and normalize public ICLR OpenReview submissions.",
    )
    scan.add_argument("--year", type=int, default=2024)
    scan.add_argument("--limit", type=int, default=25)
    scan.add_argument("--out", default="data/normalized/iclr_2024_sample.json")
    scan.add_argument("--raw-out", default="")

    snapshot = subparsers.add_parser(
        "snapshot-iclr",
        parents=[storage_parent],
        help="Save a full raw OpenReview snapshot for ICLR.",
    )
    snapshot.add_argument("--year", type=int, default=2024)
    snapshot.add_argument("--limit", type=int, default=25)
    snapshot.add_argument("--page-size", type=int, default=100)
    snapshot.add_argument("--root", default="data/raw")
    snapshot.add_argument("--normalize-out", default="")

    normalize = subparsers.add_parser(
        "normalize-snapshot",
        parents=[storage_parent],
        help="Create normalized data from a raw snapshot.",
    )
    normalize.add_argument("--snapshot", required=True)
    normalize.add_argument("--out", required=True)

    evidence = subparsers.add_parser(
        "build-evidence-store",
        parents=[storage_parent],
        help="Download PDFs and attach parsed paper sections.",
    )
    evidence.add_argument("--input", required=True)
    evidence.add_argument("--out", required=True)
    evidence.add_argument("--pdf-root", default="data/pdfs")
    evidence.add_argument("--limit", type=int, default=None)
    evidence.add_argument("--force", action="store_true")

    audit = subparsers.add_parser(
        "audit",
        parents=[storage_parent],
        help="Audit a normalized dataset and write JSON/Markdown/HTML reports.",
    )
    audit.add_argument("--input", required=True)
    audit.add_argument("--out", default="data/audits/audit_results.json")
    audit.add_argument("--markdown", default="reports/audit_report.md")
    audit.add_argument("--html", default="reports/audit_report.html")
    audit.add_argument("--claim-model", default=os.environ.get("SECONDOPINION_CLAIM_MODEL", DEFAULT_CLAIM_MODEL))
    audit.add_argument("--llm-judge", action="store_true", help="Use an LLM judge for evidence-grounded claim verdicts.")
    audit.add_argument("--judge-model", default=os.environ.get("SECONDOPINION_JUDGE_MODEL", DEFAULT_JUDGE_MODEL))

    demo = subparsers.add_parser(
        "demo",
        parents=[storage_parent],
        help="Run the MVP on the bundled sample dataset.",
    )
    demo.add_argument("--out", default="data/audits/demo_audit_results.json")
    demo.add_argument("--markdown", default="reports/mvp_demo.md")
    demo.add_argument("--html", default="reports/mvp_demo.html")
    demo.add_argument("--claim-model", default=os.environ.get("SECONDOPINION_CLAIM_MODEL", DEFAULT_CLAIM_MODEL))
    demo.add_argument("--llm-judge", action="store_true", help="Use an LLM judge for evidence-grounded claim verdicts.")
    demo.add_argument("--judge-model", default=os.environ.get("SECONDOPINION_JUDGE_MODEL", DEFAULT_JUDGE_MODEL))

    storage = subparsers.add_parser("storage-info", help="Show artifact storage and Google Drive suggestions.")
    storage.add_argument("--storage-root", default=None)

    annotation_export = subparsers.add_parser(
        "annotation-export",
        parents=[storage_parent],
        help="Export audit results into annotation tasks and a static HTML packet.",
    )
    annotation_export.add_argument("--audit", required=True)
    annotation_export.add_argument("--run-id", default="")
    annotation_export.add_argument("--tasks-out", default="")
    annotation_export.add_argument("--html", default="")

    annotation_llm = subparsers.add_parser(
        "annotation-llm-label",
        parents=[storage_parent],
        help="Generate independent LLM labels for annotation tasks.",
    )
    annotation_llm.add_argument("--tasks", required=True)
    annotation_llm.add_argument("--out", default="")
    annotation_llm.add_argument("--model", default=os.environ.get("SECONDOPINION_ANNOTATION_MODEL", DEFAULT_ANNOTATION_MODEL))
    annotation_llm.add_argument("--annotator-id", default="")

    annotation_compare = subparsers.add_parser(
        "annotation-compare",
        parents=[storage_parent],
        help="Compare human annotation labels with LLM labels.",
    )
    annotation_compare.add_argument("--human", required=True)
    annotation_compare.add_argument("--llm", required=True)
    annotation_compare.add_argument("--tasks", default="")
    annotation_compare.add_argument("--out", default="")
    annotation_compare.add_argument("--markdown", default="")
    annotation_compare.add_argument("--html", default="")

    annotation_validate = subparsers.add_parser(
        "annotation-validate-labels",
        parents=[storage_parent],
        help="Validate annotation labels JSONL.",
    )
    annotation_validate.add_argument("--labels", required=True)

    args = parser.parse_args(argv)
    if args.command == "scan-iclr":
        command_scan_iclr(args)
    elif args.command == "snapshot-iclr":
        command_snapshot_iclr(args)
    elif args.command == "normalize-snapshot":
        command_normalize_snapshot(args)
    elif args.command == "build-evidence-store":
        command_build_evidence_store(args)
    elif args.command == "audit":
        command_audit(args)
    elif args.command == "demo":
        command_demo(args)
    elif args.command == "storage-info":
        command_storage_info(args)
    elif args.command == "annotation-export":
        command_annotation_export(args)
    elif args.command == "annotation-llm-label":
        command_annotation_llm_label(args)
    elif args.command == "annotation-compare":
        command_annotation_compare(args)
    elif args.command == "annotation-validate-labels":
        command_annotation_validate_labels(args)


def command_scan_iclr(args: argparse.Namespace) -> None:
    client = OpenReviewClient()
    notes = client.get_iclr_submissions(args.year, limit=args.limit)
    if args.raw_out:
        write_json({"notes": notes}, artifact_path(args.raw_out, args))
    normalized = normalize_openreview_notes(notes, venue="ICLR", year=args.year)
    out = artifact_path(args.out, args)
    write_json(normalized, out)
    print(
        f"Saved {normalized['paper_count']} papers and {normalized['review_count']} reviews to {out}."
    )


def command_snapshot_iclr(args: argparse.Namespace) -> None:
    client = OpenReviewClient()
    invitation = f"ICLR.cc/{args.year}/Conference/-/Submission"
    result = save_openreview_snapshot(
        client,
        venue="ICLR",
        year=args.year,
        invitation=invitation,
        details="replies",
        limit=args.limit,
        page_size=args.page_size,
        root=artifact_path(args.root, args),
    )
    manifest = result["manifest"]
    print(
        f"Saved raw snapshot to {result['snapshot_dir']} "
        f"({manifest['paper_count']} papers, {manifest['reply_count']} replies)."
    )
    if args.normalize_out:
        normalized = normalize_snapshot(result["snapshot_dir"])
        normalize_out = artifact_path(args.normalize_out, args)
        write_json(normalized, normalize_out)
        print(f"Saved normalized data to {normalize_out}.")


def command_normalize_snapshot(args: argparse.Namespace) -> None:
    normalized = normalize_snapshot(artifact_path(args.snapshot, args))
    out = artifact_path(args.out, args)
    write_json(normalized, out)
    print(
        f"Saved {normalized['paper_count']} papers and {normalized['review_count']} reviews to {out}."
    )


def command_build_evidence_store(args: argparse.Namespace) -> None:
    dataset = read_json(artifact_path(args.input, args))
    enriched, manifest = build_evidence_store(
        dataset,
        pdf_root=artifact_path(args.pdf_root, args),
        limit=args.limit,
        force=args.force,
    )
    out = artifact_path(args.out, args)
    write_json(enriched, out)
    evidence = enriched.get("evidence_store", {})
    print(
        f"Saved evidence dataset to {out} "
        f"({manifest['pdf_count']} PDFs, {evidence.get('chunk_count', 0)} chunks)."
    )


def command_audit(args: argparse.Namespace) -> None:
    dataset = read_json(artifact_path(args.input, args))
    result = audit_dataset(
        dataset,
        claim_model=args.claim_model,
        judge_model=args.judge_model,
        use_llm_judge=args.llm_judge,
    )
    write_outputs(
        result,
        artifact_path(args.out, args),
        artifact_path(args.markdown, args),
        artifact_path(args.html, args),
    )


def command_demo(args: argparse.Namespace) -> None:
    dataset = read_json("examples/sample_normalized_dataset.json")
    result = audit_dataset(
        dataset,
        claim_model=args.claim_model,
        judge_model=args.judge_model,
        use_llm_judge=args.llm_judge,
    )
    write_outputs(
        result,
        artifact_path(args.out, args),
        artifact_path(args.markdown, args),
        artifact_path(args.html, args),
    )


def command_storage_info(args: argparse.Namespace) -> None:
    root = storage_root(args.storage_root)
    suggestion = suggested_drive_storage_root()
    if root:
        print(f"Artifact storage root: {root}")
    else:
        print("Artifact storage root: local project directory")
    if suggestion:
        print(f"Suggested Google Drive root: {suggestion}")
    else:
        print("Suggested Google Drive root: not found")


def command_annotation_export(args: argparse.Namespace) -> None:
    audit_result = read_json(artifact_path(args.audit, args))
    run_id, tasks = export_annotation_tasks(audit_result, run_id=args.run_id or None)
    defaults = default_task_paths(run_id)
    tasks_out = artifact_path(args.tasks_out or defaults["tasks"], args)
    html_out = artifact_path(args.html or defaults["html"], args)
    write_jsonl(tasks_out, tasks)
    write_annotation_html(tasks, html_out)
    print(f"Saved {len(tasks)} annotation tasks to {tasks_out}.")
    print(f"Saved annotation HTML to {html_out}.")


def command_annotation_llm_label(args: argparse.Namespace) -> None:
    tasks_path = artifact_path(args.tasks, args)
    tasks = read_jsonl(tasks_path)
    run_id = tasks[0]["run_id"] if tasks else "annotations"
    defaults = default_task_paths(run_id)
    out = artifact_path(args.out or defaults["llm_labels"], args)
    client = OpenAIChatClient.from_env()
    labels = llm_label_tasks(
        tasks,
        llm_client=client,
        model=args.model,
        annotator_id=args.annotator_id or None,
    )
    write_jsonl(out, labels)
    print(f"Saved {len(labels)} LLM annotation labels to {out}.")


def command_annotation_compare(args: argparse.Namespace) -> None:
    human_labels = read_jsonl(artifact_path(args.human, args))
    llm_labels = read_jsonl(artifact_path(args.llm, args))
    human_issues = validate_labels(human_labels)
    llm_issues = validate_labels(llm_labels)
    if human_issues or llm_issues:
        raise SystemExit(f"Invalid labels: human={human_issues[:3]} llm={llm_issues[:3]}")
    tasks = read_jsonl(artifact_path(args.tasks, args)) if args.tasks else []
    run_id = (tasks[0]["run_id"] if tasks else (human_labels[0].get("run_id") if human_labels else "annotations"))
    defaults = default_task_paths(run_id)
    out = artifact_path(args.out or defaults["comparison"], args)
    markdown = artifact_path(args.markdown or defaults["comparison_markdown"], args)
    html = artifact_path(args.html or defaults["comparison_html"], args)
    comparison = compare_annotations(human_labels, llm_labels, tasks=tasks)
    write_annotation_json(out, comparison)
    write_comparison_markdown(comparison, markdown)
    write_comparison_html(comparison, html)
    print(f"Saved annotation comparison JSON to {out}.")
    print(f"Saved annotation comparison Markdown to {markdown}.")
    print(f"Saved annotation comparison HTML to {html}.")


def command_annotation_validate_labels(args: argparse.Namespace) -> None:
    labels = read_jsonl(artifact_path(args.labels, args))
    issues = validate_labels(labels)
    if issues:
        raise SystemExit(f"Found {len(issues)} invalid labels: {issues[:5]}")
    print(f"Validated {len(labels)} annotation labels.")


def artifact_path(path: str | Path, args: argparse.Namespace) -> Path:
    return resolve_artifact_path(path, root=getattr(args, "storage_root", None))


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

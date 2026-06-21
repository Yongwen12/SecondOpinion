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
    export_evidence_chain_benchmark_annotation_tasks,
    export_evidence_chain_annotation_tasks,
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
from .concern_calibration import (
    DEFAULT_CONCERN_CALIBRATION_MODEL,
    build_negative_calibration_sample,
    build_concern_calibration_report,
    build_gold_expansion_calibration_sample,
    build_preference_pairs,
    build_rag_memory_records,
    build_sft_examples,
    label_concern_calibration_item,
    merge_calibration_labels,
    write_concern_calibration_markdown,
)
from .concern_survival import (
    build_concern_survival_calibration_sample,
    validate_concern_survival_for_snapshot,
    write_concern_survival_calibration_jsonl,
    write_concern_survival_calibration_markdown,
    write_concern_survival_markdown,
)
from .data_inventory import inventory_openreview_snapshot, write_inventory_markdown
from .external_evidence import DEFAULT_COLLECTOR_MODEL, enrich_dataset_with_external_evidence
from .external_dataset_adapters import (
    DATASET_SPECS,
    normalize_contrasciview_csv,
    normalize_dataset_records,
    read_records as read_external_records,
    summarize_normalized,
)
from .external_dataset_ingestion import (
    ingest_external_scoring_datasets,
    render_ingestion_markdown,
    write_json as write_ingestion_json,
    write_markdown as write_ingestion_markdown,
)
from .evidence_chain import (
    build_benchmark_validation_report,
    build_evidence_chain_benchmark,
    build_evidence_chain_benchmark_from_calibration,
    build_evidence_chain_demo,
    build_pseudo_expert_labels,
    build_pseudo_expert_report,
    write_pseudo_expert_markdown,
    write_benchmark_markdown,
    write_validation_story,
    write_json as write_evidence_chain_json,
)
from .external_providers.openalex import OpenAlexClient
from .grounding_validation import (
    RetryingStructuredLLMClient,
    validate_grounding_for_dataset,
    write_grounding_markdown,
)
from .llm_client import LLMClientError, OpenAIChatClient
from .normalize import normalize_openreview_notes
from .openreview_client import OpenReviewClient
from .pdf_store import build_evidence_store
from .rag_validation import (
    DEFAULT_RAG_VALIDATION_MODEL,
    parse_top_ks,
    run_rag_judgment_ablation,
    validate_concern_rag,
    write_json as write_rag_validation_json,
    write_rag_validation_markdown,
)
from .report import write_html_report, write_markdown_report
from .reviewer_public_scorecard import (
    build_public_scorecard,
    write_json as write_public_scorecard_json,
)
from .reviewer_calibration import (
    DEFAULT_CONSENSUS_CALIBRATION_MODEL,
    DEFAULT_REBUTTAL_RESOLUTION_CALIBRATION_MODEL,
    build_consensus_calibration_report,
    build_consensus_calibration_sample,
    build_rebuttal_resolution_calibration_report,
    build_rebuttal_resolution_calibration_sample,
    calibrate_reviewer_reliability,
    label_consensus_item,
    label_rebuttal_resolution_item,
    merge_consensus_labels,
    merge_rebuttal_resolution_labels,
    write_jsonl as write_reviewer_calibration_jsonl,
    write_json as write_reviewer_calibration_json,
    write_consensus_calibration_markdown,
    write_rebuttal_resolution_calibration_markdown,
    write_reviewer_calibration_markdown,
)
from .scoring_memory import (
    build_scoring_benchmark_suite,
    build_guardrail_report,
    build_memory_records,
    build_memory_records_from_normalized,
    parse_fields,
    parse_label_score_map,
    read_json as read_scoring_json,
    read_jsonl as read_scoring_jsonl,
    render_guardrail_markdown,
    render_scoring_suite_markdown,
    score_dimensions_with_memory,
    score_with_memory,
    write_markdown as write_scoring_markdown,
    write_json as write_scoring_json,
    write_jsonl as write_scoring_jsonl,
)
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
    snapshot_openreview = subparsers.add_parser(
        "snapshot-openreview",
        parents=[storage_parent],
        help="Save a raw OpenReview snapshot for a configurable venue invitation.",
    )
    snapshot_openreview.add_argument("--venue", required=True, help="Venue label used in manifests and paths, e.g. ICLR.")
    snapshot_openreview.add_argument("--year", type=int, required=True)
    snapshot_openreview.add_argument(
        "--invitation",
        default="",
        help="OpenReview submission invitation. If omitted, a common venue template is used.",
    )
    snapshot_openreview.add_argument("--limit", type=int, default=25)
    snapshot_openreview.add_argument("--page-size", type=int, default=100)
    snapshot_openreview.add_argument("--details", default="replies")
    snapshot_openreview.add_argument("--api-base", default="https://api2.openreview.net")
    snapshot_openreview.add_argument("--root", default="data/raw")
    snapshot_openreview.add_argument("--normalize-out", default="")

    normalize = subparsers.add_parser(
        "normalize-snapshot",
        parents=[storage_parent],
        help="Create normalized data from a raw snapshot.",
    )
    normalize.add_argument("--snapshot", required=True)
    normalize.add_argument("--out", required=True)

    inventory = subparsers.add_parser(
        "inventory-openreview-data",
        parents=[storage_parent],
        help="Inventory raw OpenReview replies and report which validation signals are available.",
    )
    inventory.add_argument("--snapshot", required=True)
    inventory.add_argument("--out", default="data/validation/openreview_data_inventory.json")
    inventory.add_argument("--markdown", default="reports/validation/openreview_data_inventory.md")

    evidence = subparsers.add_parser(
        "build-evidence-store",
        parents=[storage_parent],
        help="Download PDFs and attach parsed evidence chunks.",
    )
    evidence.add_argument("--input", required=True)
    evidence.add_argument("--out", required=True)
    evidence.add_argument("--pdf-root", default="data/pdfs")
    evidence.add_argument("--limit", type=int, default=None)
    evidence.add_argument("--force", action="store_true")

    external = subparsers.add_parser(
        "enrich-external-evidence",
        parents=[storage_parent],
        help="Attach low-cost venue guideline and OpenAlex metadata evidence to a normalized dataset.",
    )
    external.add_argument("--input", required=True)
    external.add_argument("--out", required=True)
    external.add_argument("--providers", default=os.environ.get("SECONDOPINION_EXTERNAL_PROVIDERS", "venue_guidelines,openalex"))
    external.add_argument("--claim-model", default=os.environ.get("SECONDOPINION_CLAIM_MODEL", DEFAULT_CLAIM_MODEL))
    external.add_argument("--collector-model", default=os.environ.get("SECONDOPINION_COLLECTOR_MODEL", DEFAULT_COLLECTOR_MODEL))
    external.add_argument("--openalex-mailto", default=os.environ.get("SECONDOPINION_OPENALEX_MAILTO", ""))
    external.add_argument("--openalex-cache", default=os.environ.get("SECONDOPINION_OPENALEX_CACHE", "data/cache/openalex"))
    external.add_argument("--refresh-openalex-cache", action="store_true")
    external.add_argument("--offline-openalex-cache", action="store_true")
    external.add_argument("--openalex-timeout", type=int, default=30)
    external.add_argument("--max-external-claims-per-review", type=int, default=5)
    external.add_argument("--max-queries-per-claim", type=int, default=2)
    external.add_argument("--max-openalex-results-per-query", type=int, default=5)
    external.add_argument("--max-evidence-per-claim", type=int, default=3)
    external.add_argument("--no-llm-planner", action="store_true", help="Use deterministic query planning and grading.")

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
    audit.add_argument("--external-evidence", action="store_true", help="Collect venue/OpenAlex external evidence before retrieval.")
    audit.add_argument(
        "--external-providers",
        default=os.environ.get("SECONDOPINION_EXTERNAL_PROVIDERS", "venue_guidelines,openalex"),
    )
    audit.add_argument("--collector-model", default=os.environ.get("SECONDOPINION_COLLECTOR_MODEL", DEFAULT_COLLECTOR_MODEL))
    audit.add_argument("--openalex-mailto", default=os.environ.get("SECONDOPINION_OPENALEX_MAILTO", ""))
    audit.add_argument("--openalex-cache", default=os.environ.get("SECONDOPINION_OPENALEX_CACHE", "data/cache/openalex"))
    audit.add_argument("--refresh-openalex-cache", action="store_true")
    audit.add_argument("--offline-openalex-cache", action="store_true")
    audit.add_argument("--openalex-timeout", type=int, default=30)

    grounding = subparsers.add_parser(
        "validate-grounding",
        parents=[storage_parent],
        help="Validate that extracted claims are grounded in exact source sentences from the original reviews.",
    )
    grounding.add_argument("--input", required=True)
    grounding.add_argument("--out", default="data/validation/grounding_validation.json")
    grounding.add_argument("--markdown", default="reports/validation/grounding_validation.md")
    grounding.add_argument("--review-limit", type=int, default=200)
    grounding.add_argument("--max-claims", type=int, default=8)
    grounding.add_argument("--claim-model", default=os.environ.get("SECONDOPINION_CLAIM_MODEL", DEFAULT_CLAIM_MODEL))
    grounding.add_argument("--openai-timeout", type=int, default=90)
    grounding.add_argument("--retries", type=int, default=2)

    survival = subparsers.add_parser(
        "validate-concern-survival",
        parents=[storage_parent],
        help="Measure whether extracted reviewer claims survive into meta-review text.",
    )
    survival.add_argument("--snapshot", required=True)
    survival.add_argument("--out", default="data/validation/concern_survival.json")
    survival.add_argument("--markdown", default="reports/validation/concern_survival.md")
    survival.add_argument("--paper-limit", type=int, default=None)
    survival.add_argument("--review-limit", type=int, default=None)
    survival.add_argument("--max-claims", type=int, default=8)
    survival.add_argument("--claim-model", default=os.environ.get("SECONDOPINION_CLAIM_MODEL", DEFAULT_CLAIM_MODEL))
    survival.add_argument("--openai-timeout", type=int, default=90)
    survival.add_argument("--retries", type=int, default=2)
    survival.add_argument("--survived-threshold", type=float, default=0.34)
    survival.add_argument("--partial-threshold", type=float, default=0.2)
    survival.add_argument("--calibration-jsonl", default="")
    survival.add_argument("--calibration-markdown", default="")
    survival.add_argument("--calibration-sample-size", type=int, default=0)
    survival.add_argument("--calibration-seed", type=int, default=7)

    survival_calibration = subparsers.add_parser(
        "calibrate-concern-survival",
        parents=[storage_parent],
        help="Use an LLM to semantically calibrate concern-survival sample labels and export high-confidence records.",
    )
    survival_calibration.add_argument("--input", required=True)
    survival_calibration.add_argument("--labels-out", default="data/validation/concern_survival_llm_labels.jsonl")
    survival_calibration.add_argument("--merged-out", default="data/validation/concern_survival_llm_merged.jsonl")
    survival_calibration.add_argument(
        "--high-confidence-out",
        default="data/validation/concern_survival_high_confidence.jsonl",
    )
    survival_calibration.add_argument("--markdown", default="reports/validation/concern_survival_llm_calibration.md")
    survival_calibration.add_argument(
        "--model",
        default=os.environ.get("SECONDOPINION_CONCERN_CALIBRATION_MODEL", DEFAULT_CONCERN_CALIBRATION_MODEL),
    )
    survival_calibration.add_argument("--limit", type=int, default=None)
    survival_calibration.add_argument("--openai-timeout", type=int, default=90)
    survival_calibration.add_argument("--retries", type=int, default=2)

    negative_sample = subparsers.add_parser(
        "sample-concern-negatives",
        parents=[storage_parent],
        help="Sample low-score auto not_found concern-survival records for negative calibration.",
    )
    negative_sample.add_argument("--input", required=True, help="Concern survival full JSON report.")
    negative_sample.add_argument("--out", default="data/validation/concern_survival_negative_calibration.jsonl")
    negative_sample.add_argument("--sample-size", type=int, default=100)
    negative_sample.add_argument("--seed", type=int, default=11)
    negative_sample.add_argument("--max-auto-score", type=float, default=0.16)

    gold_expansion_sample = subparsers.add_parser(
        "sample-concern-gold-expansion",
        parents=[storage_parent],
        help="Sample concern-survival records targeted at expanding balanced high-confidence gold labels.",
    )
    gold_expansion_sample.add_argument("--input", required=True, help="Concern survival full JSON report.")
    gold_expansion_sample.add_argument("--existing", nargs="*", default=[], help="Existing calibrated JSONL records to exclude.")
    gold_expansion_sample.add_argument("--out", default="data/validation/concern_survival_gold_expansion_calibration.jsonl")
    gold_expansion_sample.add_argument("--sample-size", type=int, default=500)
    gold_expansion_sample.add_argument("--seed", type=int, default=29)

    training_export = subparsers.add_parser(
        "export-concern-training-data",
        parents=[storage_parent],
        help="Export high-confidence concern calibration records to RAG, SFT, and preference JSONL formats.",
    )
    training_export.add_argument("--input", nargs="+", required=True)
    training_export.add_argument("--rag-out", default="data/training/concern_rag_memory.jsonl")
    training_export.add_argument("--sft-out", default="data/training/concern_sft.jsonl")
    training_export.add_argument("--preference-out", default="data/training/concern_preferences.jsonl")
    training_export.add_argument("--only-high-confidence", action="store_true")

    rag_validation = subparsers.add_parser(
        "validate-concern-rag",
        parents=[storage_parent],
        help="Validate whether historical concern RAG memory retrieves useful claim-level cases.",
    )
    rag_validation.add_argument("--records", nargs="+", required=True, help="Gold calibrated concern records JSONL.")
    rag_validation.add_argument("--memory", required=True, help="RAG memory JSONL.")
    rag_validation.add_argument("--out", default="data/validation/concern_rag_validation.json")
    rag_validation.add_argument("--markdown", default="reports/validation/concern_rag_validation.md")
    rag_validation.add_argument("--top-ks", default="1,3,5")
    rag_validation.add_argument("--exclude-same-paper", action="store_true")
    rag_validation.add_argument(
        "--only-decisive-meta-labels",
        action="store_true",
        help="Drop records whose semantic meta-review match label is unsure or missing.",
    )
    rag_validation.add_argument(
        "--only-high-confidence",
        action="store_true",
        help="Drop records that are not high-confidence calibration/training candidates.",
    )
    rag_validation.add_argument("--llm-ablation", action="store_true")
    rag_validation.add_argument("--open-book-llm", action="store_true", help="Include current paper meta-review in LLM ablation input.")
    rag_validation.add_argument("--llm-limit", type=int, default=24)
    rag_validation.add_argument("--llm-top-k", type=int, default=3)
    rag_validation.add_argument("--llm-out", default="data/validation/concern_rag_llm_ablation.json")
    rag_validation.add_argument("--model", default=os.environ.get("SECONDOPINION_RAG_VALIDATION_MODEL", DEFAULT_RAG_VALIDATION_MODEL))
    rag_validation.add_argument("--openai-timeout", type=int, default=90)
    rag_validation.add_argument("--retries", type=int, default=2)

    reviewer_calibration = subparsers.add_parser(
        "validate-reviewer-calibration",
        parents=[storage_parent],
        help="Mine inter-reviewer consensus, rebuttal resolution, and review reliability signals.",
    )
    reviewer_calibration.add_argument("--concern-survival", required=True)
    reviewer_calibration.add_argument("--snapshot", default="", help="Optional raw OpenReview snapshot dir with replies.")
    reviewer_calibration.add_argument(
        "--rebuttal-labels",
        nargs="*",
        default=[],
        help="Optional LLM-calibrated rebuttal-resolution JSONL files to backfill review reliability scores.",
    )
    reviewer_calibration.add_argument(
        "--consensus-labels",
        nargs="*",
        default=[],
        help="Optional LLM-calibrated inter-reviewer consensus JSONL files to backfill review reliability scores.",
    )
    reviewer_calibration.add_argument("--out", default="data/validation/reviewer_calibration.json")
    reviewer_calibration.add_argument("--markdown", default="reports/validation/reviewer_calibration.md")

    rebuttal_sample = subparsers.add_parser(
        "sample-rebuttal-resolution",
        parents=[storage_parent],
        help="Sample reviewer-claim / author-response pairs for LLM rebuttal-resolution calibration.",
    )
    rebuttal_sample.add_argument("--reviewer-calibration", required=True)
    rebuttal_sample.add_argument("--out", default="data/validation/rebuttal_resolution_calibration_sample.jsonl")
    rebuttal_sample.add_argument("--sample-size", type=int, default=120)
    rebuttal_sample.add_argument("--seed", type=int, default=43)

    rebuttal_calibration = subparsers.add_parser(
        "calibrate-rebuttal-resolution",
        parents=[storage_parent],
        help="Use an LLM to calibrate whether author responses address reviewer claims.",
    )
    rebuttal_calibration.add_argument("--input", required=True)
    rebuttal_calibration.add_argument("--labels-out", default="data/validation/rebuttal_resolution_llm_labels.jsonl")
    rebuttal_calibration.add_argument("--merged-out", default="data/validation/rebuttal_resolution_llm_merged.jsonl")
    rebuttal_calibration.add_argument("--high-confidence-out", default="data/validation/rebuttal_resolution_high_confidence.jsonl")
    rebuttal_calibration.add_argument("--markdown", default="reports/validation/rebuttal_resolution_llm_calibration.md")
    rebuttal_calibration.add_argument(
        "--model",
        default=os.environ.get("SECONDOPINION_REBUTTAL_RESOLUTION_MODEL", DEFAULT_REBUTTAL_RESOLUTION_CALIBRATION_MODEL),
    )
    rebuttal_calibration.add_argument("--limit", type=int, default=None)
    rebuttal_calibration.add_argument("--openai-timeout", type=int, default=90)
    rebuttal_calibration.add_argument("--retries", type=int, default=2)

    consensus_sample = subparsers.add_parser(
        "sample-inter-reviewer-consensus",
        parents=[storage_parent],
        help="Sample reviewer-claim pairs for LLM inter-reviewer consensus calibration.",
    )
    consensus_sample.add_argument("--reviewer-calibration", required=True)
    consensus_sample.add_argument("--out", default="data/validation/inter_reviewer_consensus_calibration_sample.jsonl")
    consensus_sample.add_argument("--sample-size", type=int, default=120)
    consensus_sample.add_argument("--seed", type=int, default=59)

    consensus_calibration = subparsers.add_parser(
        "calibrate-inter-reviewer-consensus",
        parents=[storage_parent],
        help="Use an LLM to calibrate whether two reviewer claims express the same concern.",
    )
    consensus_calibration.add_argument("--input", required=True)
    consensus_calibration.add_argument("--labels-out", default="data/validation/inter_reviewer_consensus_llm_labels.jsonl")
    consensus_calibration.add_argument("--merged-out", default="data/validation/inter_reviewer_consensus_llm_merged.jsonl")
    consensus_calibration.add_argument("--high-confidence-out", default="data/validation/inter_reviewer_consensus_high_confidence.jsonl")
    consensus_calibration.add_argument("--markdown", default="reports/validation/inter_reviewer_consensus_llm_calibration.md")
    consensus_calibration.add_argument(
        "--model",
        default=os.environ.get("SECONDOPINION_CONSENSUS_MODEL", DEFAULT_CONSENSUS_CALIBRATION_MODEL),
    )
    consensus_calibration.add_argument("--limit", type=int, default=None)
    consensus_calibration.add_argument("--openai-timeout", type=int, default=90)
    consensus_calibration.add_argument("--retries", type=int, default=2)

    evidence_chain_demo = subparsers.add_parser(
        "build-evidence-chain-demo",
        parents=[storage_parent],
        help="Merge audit and reviewer-calibration outputs into frontend evidence-chain JSON.",
    )
    evidence_chain_demo.add_argument("--audit", required=True)
    evidence_chain_demo.add_argument("--reviewer-calibration", default="")
    evidence_chain_demo.add_argument("--paper-id", default="")
    evidence_chain_demo.add_argument("--out", default="frontend/demos/evidence_chain_demo.json")

    evidence_chain_benchmark = subparsers.add_parser(
        "build-evidence-chain-benchmark",
        parents=[storage_parent],
        help="Create a review-only/manuscript/full-chain benchmark packet for evidence-chain ablations.",
    )
    evidence_chain_benchmark.add_argument("--audit", required=True)
    evidence_chain_benchmark.add_argument("--reviewer-calibration", default="")
    evidence_chain_benchmark.add_argument("--out", default="data/validation/evidence_chain_benchmark.json")
    evidence_chain_benchmark.add_argument("--markdown", default="reports/validation/evidence_chain_benchmark.md")
    evidence_chain_benchmark.add_argument("--paper-limit", type=int, default=50)
    evidence_chain_benchmark.add_argument("--claims-per-paper", type=int, default=8)
    evidence_chain_benchmark.add_argument("--sample-size", type=int, default=300)

    evidence_chain_calibration_benchmark = subparsers.add_parser(
        "build-evidence-chain-calibration-benchmark",
        parents=[storage_parent],
        help="Create an evidence-chain benchmark packet directly from reviewer calibration outputs.",
    )
    evidence_chain_calibration_benchmark.add_argument("--reviewer-calibration", required=True)
    evidence_chain_calibration_benchmark.add_argument("--normalized", default="")
    evidence_chain_calibration_benchmark.add_argument("--out", default="data/validation/evidence_chain_calibration_benchmark.json")
    evidence_chain_calibration_benchmark.add_argument(
        "--markdown",
        default="reports/validation/evidence_chain_calibration_benchmark.md",
    )
    evidence_chain_calibration_benchmark.add_argument("--paper-limit", type=int, default=50)
    evidence_chain_calibration_benchmark.add_argument("--claims-per-paper", type=int, default=5)
    evidence_chain_calibration_benchmark.add_argument("--sample-size", type=int, default=150)

    pseudo_expert = subparsers.add_parser(
        "label-evidence-chain-pseudo-expert",
        parents=[storage_parent],
        help="Generate rule-based pseudo-expert labels and agreement report for evidence-chain annotation tasks.",
    )
    pseudo_expert.add_argument("--tasks", required=True)
    pseudo_expert.add_argument("--labels-out", default="data/annotations/labels/llm/evidence_chain_pseudo_expert.jsonl")
    pseudo_expert.add_argument("--report-out", default="data/validation/evidence_chain_pseudo_expert_report.json")
    pseudo_expert.add_argument("--markdown", default="reports/validation/evidence_chain_pseudo_expert_report.md")
    pseudo_expert.add_argument("--annotator-id", default="pseudo-expert:v0.1")

    validation_story = subparsers.add_parser(
        "write-evidence-chain-validation-story",
        parents=[storage_parent],
        help="Write a concise validation story from evidence-chain demo, benchmark, and pseudo-expert report.",
    )
    validation_story.add_argument("--demo", required=True)
    validation_story.add_argument("--benchmark", required=True)
    validation_story.add_argument("--pseudo-report", required=True)
    validation_story.add_argument("--out", default="reports/validation/evidence_chain_validation_story_v0.1.md")

    normalize_external = subparsers.add_parser(
        "normalize-external-scoring-dataset",
        parents=[storage_parent],
        help="Normalize external reviewer-comment datasets into the shared scoring benchmark schema.",
    )
    normalize_external.add_argument("--dataset", choices=["contrasciview", *sorted(DATASET_SPECS)], required=True)
    normalize_external.add_argument("--input", required=True)
    normalize_external.add_argument("--out", default="data/validation/external_scoring_dataset.jsonl")
    normalize_external.add_argument("--dimension", default="")
    normalize_external.add_argument("--baseline", choices=["polarity", "polarity_overlap", "majority"], default="polarity")
    normalize_external.add_argument("--overlap-threshold", type=float, default=0.10)
    normalize_external.add_argument("--limit", type=int, default=None)

    ingest_external = subparsers.add_parser(
        "ingest-external-scoring-datasets",
        parents=[storage_parent],
        help="Download public external scoring datasets, normalize them, and build a local scoring-memory corpus.",
    )
    ingest_external.add_argument("--datasets", default="first,second,re2")
    ingest_external.add_argument("--external-root", default="data/external")
    ingest_external.add_argument("--normalized-out", default="data/normalized/external_scoring_memory_full_lite_corpus_v0.1.jsonl")
    ingest_external.add_argument("--memory-out", default="data/normalized/scoring_memory_external_full_lite_v0.1.jsonl")
    ingest_external.add_argument("--manifest-out", default="data/validation/external_full_lite_ingestion_manifest_v0.1.json")
    ingest_external.add_argument("--markdown", default="reports/validation/external_full_lite_ingestion_v0.1.md")
    ingest_external.add_argument("--limit-per-dataset", type=int, default=None)
    ingest_external.add_argument("--force", action="store_true")
    ingest_external.add_argument("--skip-download", action="store_true")

    public_scorecard = subparsers.add_parser(
        "build-reviewer-public-scorecard",
        parents=[storage_parent],
        help="Export reviewer-facing scorecard JSON for the static frontend.",
    )
    public_scorecard.add_argument("--input", default="frontend/demos/hybrid_scoring_demo.json")
    public_scorecard.add_argument("--out", default="frontend/demos/reviewer_public_scorecard_v0.1.json")

    scoring_memory = subparsers.add_parser(
        "build-scoring-memory",
        parents=[storage_parent],
        help="Convert normalized external benchmark records into scoring-memory examples.",
    )
    scoring_memory.add_argument("--input", required=True)
    scoring_memory.add_argument("--out", default="data/scoring_memory/scoring_memory.jsonl")
    scoring_memory.add_argument("--dimension", required=True, help="Scoring dimension, or 'auto' to use each record's dimension field.")
    scoring_memory.add_argument("--dataset", default="")
    scoring_memory.add_argument("--text-fields", default="input_text,comment,claim_text,premise,hypothesis,review_text")
    scoring_memory.add_argument("--context-fields", default="context_text,paper_title,aspect,rebuttal,response")
    scoring_memory.add_argument("--label-field", default="gold_label")
    scoring_memory.add_argument("--score-field", default="")
    scoring_memory.add_argument("--label-score", action="append", default=[])
    scoring_memory.add_argument("--limit", type=int, default=None)

    score_memory = subparsers.add_parser(
        "score-with-memory",
        parents=[storage_parent],
        help="Retrieve external scoring-memory examples and combine their prior with an optional LLM score.",
    )
    score_memory.add_argument("--memory", required=True)
    score_memory.add_argument("--query", required=True)
    score_memory.add_argument("--dimension", required=True)
    score_memory.add_argument("--out", default="data/validation/scoring_memory_result.json")
    score_memory.add_argument("--top-k", type=int, default=5)
    score_memory.add_argument("--llm-score", type=float, default=None)
    score_memory.add_argument("--llm-weight", type=float, default=0.6)
    score_memory.add_argument("--min-similarity", type=float, default=0.0)

    score_dimensions = subparsers.add_parser(
        "score-dimensions-with-memory",
        parents=[storage_parent],
        help="Score all reviewer-comment dimensions with memory priors and optional LLM scores.",
    )
    score_dimensions.add_argument("--memory", required=True)
    score_dimensions.add_argument("--query", required=True)
    score_dimensions.add_argument("--out", default="data/validation/hybrid_scoring_result.json")
    score_dimensions.add_argument("--dimensions", default="specificity,substantiation,actionability,consensus_conflict,rebuttal_robustness,professionalism")
    score_dimensions.add_argument("--llm-score", action="append", default=[], help="dimension=score; repeatable.")
    score_dimensions.add_argument("--top-k", type=int, default=5)
    score_dimensions.add_argument("--llm-weight", type=float, default=0.6)
    score_dimensions.add_argument("--min-similarity", type=float, default=0.0)

    scoring_suite = subparsers.add_parser(
        "run-scoring-memory-suite",
        parents=[storage_parent],
        help="Run dimension-level benchmark and optional guardrail reports for normalized scoring records.",
    )
    scoring_suite.add_argument("--input", required=True)
    scoring_suite.add_argument("--out", default="data/validation/scoring_memory_suite.json")
    scoring_suite.add_argument("--markdown", default="reports/validation/scoring_memory_suite.md")
    scoring_suite.add_argument("--guardrail-out", default="")
    scoring_suite.add_argument("--guardrail-markdown", default="")
    scoring_suite.add_argument("--baseline", default="")
    scoring_suite.add_argument("--min-accuracy", type=float, default=None)
    scoring_suite.add_argument("--min-macro-f1", type=float, default=None)
    scoring_suite.add_argument("--max-accuracy-drop", type=float, default=0.02)
    scoring_suite.add_argument("--max-macro-f1-drop", type=float, default=0.02)

    scoring_guardrail = subparsers.add_parser(
        "scoring-guardrail",
        parents=[storage_parent],
        help="Fail/pass a component benchmark against thresholds or a previous benchmark report.",
    )
    scoring_guardrail.add_argument("--current", required=True)
    scoring_guardrail.add_argument("--baseline", default="")
    scoring_guardrail.add_argument("--out", default="data/validation/scoring_guardrail.json")
    scoring_guardrail.add_argument("--markdown", default="reports/validation/scoring_guardrail.md")
    scoring_guardrail.add_argument("--min-accuracy", type=float, default=None)
    scoring_guardrail.add_argument("--min-macro-f1", type=float, default=None)
    scoring_guardrail.add_argument("--max-accuracy-drop", type=float, default=0.02)
    scoring_guardrail.add_argument("--max-macro-f1-drop", type=float, default=0.02)

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

    server_init = subparsers.add_parser("server-init-db", help="Create SecondOpinion server database tables.")
    server_init.add_argument("--database-url", default=os.environ.get("SECONDOPINION_DATABASE_URL", ""))

    server_ingest = subparsers.add_parser(
        "server-ingest-normalized",
        help="Import normalized ICLR paper/review JSON files into the server database.",
    )
    server_ingest.add_argument("inputs", nargs="*")
    server_ingest.add_argument("--database-url", default=os.environ.get("SECONDOPINION_DATABASE_URL", ""))

    server_demo = subparsers.add_parser(
        "server-import-demo-scorecard",
        help="Import the static frontend public scorecard fixture into the server database.",
    )
    server_demo.add_argument("--input", default="frontend/demos/reviewer_public_scorecard_v0.1.json")
    server_demo.add_argument("--paper-id", default="second-opinion-demo")
    server_demo.add_argument("--database-url", default=os.environ.get("SECONDOPINION_DATABASE_URL", ""))

    server_memory = subparsers.add_parser(
        "server-register-memory-index",
        help="Register the external scoring memory JSONL used by the server worker.",
    )
    server_memory.add_argument("--memory", default="data/normalized/scoring_memory_external_full_lite_v0.1.jsonl")
    server_memory.add_argument("--version", default=os.environ.get("SECONDOPINION_MEMORY_INDEX_VERSION", "external-full-lite-v0.1"))
    server_memory.add_argument("--database-url", default=os.environ.get("SECONDOPINION_DATABASE_URL", ""))

    server_worker = subparsers.add_parser("server-run-worker", help="Run queued server scoring jobs.")
    server_worker.add_argument("--database-url", default=os.environ.get("SECONDOPINION_DATABASE_URL", ""))
    server_worker.add_argument("--once", action="store_true")
    server_worker.add_argument("--sleep-seconds", type=float, default=3.0)
    server_enqueue = subparsers.add_parser(
        "server-enqueue-scoring",
        help="Create queued scoring jobs for matching server papers.",
    )
    server_enqueue.add_argument("--database-url", default=os.environ.get("SECONDOPINION_DATABASE_URL", ""))
    server_enqueue.add_argument("--conference", default="ICLR")
    server_enqueue.add_argument("--year", type=int, default=None)
    server_enqueue.add_argument("--paper-id", action="append", default=[])
    server_enqueue.add_argument("--limit", type=int, default=None)
    server_enqueue.add_argument("--include-scored", action="store_true", help="Also enqueue papers that already have a scorecard for this scorer/memory version.")
    server_enqueue.add_argument("--dry-run", action="store_true")

    server_status = subparsers.add_parser(
        "server-scoring-status",
        help="Report scoring coverage and queued/running/failed paper counts.",
    )
    server_status.add_argument("--database-url", default=os.environ.get("SECONDOPINION_DATABASE_URL", ""))
    server_status.add_argument("--conference", default="ICLR")
    server_status.add_argument("--year", type=int, default=None)

    server_retry = subparsers.add_parser(
        "server-retry-failed-scoring",
        help="Create fresh queued jobs for failed scoring papers.",
    )
    server_retry.add_argument("--database-url", default=os.environ.get("SECONDOPINION_DATABASE_URL", ""))
    server_retry.add_argument("--conference", default="ICLR")
    server_retry.add_argument("--year", type=int, default=None)
    server_retry.add_argument("--limit", type=int, default=None)

    annotation_export = subparsers.add_parser(
        "annotation-export",
        parents=[storage_parent],
        help="Export audit results into annotation tasks and a static HTML packet.",
    )
    annotation_export.add_argument("--audit", default="")
    annotation_export.add_argument("--evidence-chain-demo", default="", help="Optional evidence-chain demo JSON for expert evidence-chain tasks.")
    annotation_export.add_argument("--evidence-chain-benchmark", default="", help="Optional evidence-chain benchmark JSON for expert evidence-chain tasks.")
    annotation_export.add_argument("--run-id", default="")
    annotation_export.add_argument("--tasks-out", default="")
    annotation_export.add_argument("--html", default="")
    annotation_export.add_argument("--sample-size", type=int, default=None)

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
    elif args.command == "snapshot-openreview":
        command_snapshot_openreview(args)
    elif args.command == "normalize-snapshot":
        command_normalize_snapshot(args)
    elif args.command == "inventory-openreview-data":
        command_inventory_openreview_data(args)
    elif args.command == "build-evidence-store":
        command_build_evidence_store(args)
    elif args.command == "enrich-external-evidence":
        command_enrich_external_evidence(args)
    elif args.command == "audit":
        command_audit(args)
    elif args.command == "validate-grounding":
        command_validate_grounding(args)
    elif args.command == "validate-concern-survival":
        command_validate_concern_survival(args)
    elif args.command == "calibrate-concern-survival":
        command_calibrate_concern_survival(args)
    elif args.command == "sample-concern-negatives":
        command_sample_concern_negatives(args)
    elif args.command == "sample-concern-gold-expansion":
        command_sample_concern_gold_expansion(args)
    elif args.command == "export-concern-training-data":
        command_export_concern_training_data(args)
    elif args.command == "validate-concern-rag":
        command_validate_concern_rag(args)
    elif args.command == "validate-reviewer-calibration":
        command_validate_reviewer_calibration(args)
    elif args.command == "sample-rebuttal-resolution":
        command_sample_rebuttal_resolution(args)
    elif args.command == "calibrate-rebuttal-resolution":
        command_calibrate_rebuttal_resolution(args)
    elif args.command == "sample-inter-reviewer-consensus":
        command_sample_inter_reviewer_consensus(args)
    elif args.command == "calibrate-inter-reviewer-consensus":
        command_calibrate_inter_reviewer_consensus(args)
    elif args.command == "build-evidence-chain-demo":
        command_build_evidence_chain_demo(args)
    elif args.command == "build-evidence-chain-benchmark":
        command_build_evidence_chain_benchmark(args)
    elif args.command == "build-evidence-chain-calibration-benchmark":
        command_build_evidence_chain_calibration_benchmark(args)
    elif args.command == "label-evidence-chain-pseudo-expert":
        command_label_evidence_chain_pseudo_expert(args)
    elif args.command == "write-evidence-chain-validation-story":
        command_write_evidence_chain_validation_story(args)
    elif args.command == "normalize-external-scoring-dataset":
        command_normalize_external_scoring_dataset(args)
    elif args.command == "ingest-external-scoring-datasets":
        command_ingest_external_scoring_datasets(args)
    elif args.command == "build-reviewer-public-scorecard":
        command_build_reviewer_public_scorecard(args)
    elif args.command == "build-scoring-memory":
        command_build_scoring_memory(args)
    elif args.command == "score-with-memory":
        command_score_with_memory(args)
    elif args.command == "score-dimensions-with-memory":
        command_score_dimensions_with_memory(args)
    elif args.command == "run-scoring-memory-suite":
        command_run_scoring_memory_suite(args)
    elif args.command == "scoring-guardrail":
        command_scoring_guardrail(args)
    elif args.command == "demo":
        command_demo(args)
    elif args.command == "storage-info":
        command_storage_info(args)
    elif args.command == "server-init-db":
        command_server_init_db(args)
    elif args.command == "server-ingest-normalized":
        command_server_ingest_normalized(args)
    elif args.command == "server-import-demo-scorecard":
        command_server_import_demo_scorecard(args)
    elif args.command == "server-register-memory-index":
        command_server_register_memory_index(args)
    elif args.command == "server-run-worker":
        command_server_run_worker(args)
    elif args.command == "server-enqueue-scoring":
        command_server_enqueue_scoring(args)
    elif args.command == "server-scoring-status":
        command_server_scoring_status(args)
    elif args.command == "server-retry-failed-scoring":
        command_server_retry_failed_scoring(args)
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
    args.venue = "ICLR"
    args.invitation = f"ICLR.cc/{args.year}/Conference/-/Submission"
    args.details = "replies"
    args.api_base = "https://api2.openreview.net"
    command_snapshot_openreview(args)


def command_snapshot_openreview(args: argparse.Namespace) -> None:
    client = OpenReviewClient(base_url=args.api_base)
    invitation = args.invitation or default_openreview_submission_invitation(args.venue, args.year)
    result = save_openreview_snapshot(
        client,
        venue=args.venue,
        year=args.year,
        invitation=invitation,
        details=args.details,
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


def default_openreview_submission_invitation(venue: str, year: int) -> str:
    normalized = venue.strip().lower()
    venue_ids = {
        "iclr": "ICLR.cc",
        "neurips": "NeurIPS.cc",
        "nips": "NeurIPS.cc",
        "icml": "ICML.cc",
        "colm": "colmweb.org",
    }
    if normalized in {"tmlr", "transactions on machine learning research"}:
        return "TMLR/-/Submission"
    venue_id = venue_ids.get(normalized)
    if not venue_id:
        raise SystemExit(
            "No default OpenReview invitation template for "
            f"{venue!r}. Pass --invitation explicitly, for example "
            f"--invitation {venue}.cc/{year}/Conference/-/Submission."
        )
    return f"{venue_id}/{year}/Conference/-/Submission"

def command_normalize_snapshot(args: argparse.Namespace) -> None:
    normalized = normalize_snapshot(artifact_path(args.snapshot, args))
    out = artifact_path(args.out, args)
    write_json(normalized, out)
    print(
        f"Saved {normalized['paper_count']} papers and {normalized['review_count']} reviews to {out}."
    )


def command_inventory_openreview_data(args: argparse.Namespace) -> None:
    report = inventory_openreview_snapshot(artifact_path(args.snapshot, args))
    out = artifact_path(args.out, args)
    markdown = artifact_path(args.markdown, args)
    write_json(report, out)
    write_inventory_markdown(report, markdown)
    summary = report["summary"]
    print(
        f"Saved OpenReview data inventory to {out} and {markdown}. "
        f"papers={summary['paper_count']}; replies={summary['reply_count']}."
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


def command_enrich_external_evidence(args: argparse.Namespace) -> None:
    dataset = read_json(artifact_path(args.input, args))
    try:
        client = OpenAIChatClient.from_env()
    except LLMClientError as exc:
        raise SystemExit(f"LLM setup error: {exc}") from exc
    collector_client = None if args.no_llm_planner else client
    openalex_client = OpenAlexClient(
        mailto=args.openalex_mailto,
        timeout=args.openalex_timeout,
        cache_root=artifact_path(args.openalex_cache, args) if args.openalex_cache else None,
        refresh_cache=args.refresh_openalex_cache,
        offline=args.offline_openalex_cache,
    )
    enriched, manifest = enrich_dataset_with_external_evidence(
        dataset,
        claim_llm_client=client,
        claim_model=args.claim_model,
        collector_llm_client=collector_client,
        collector_model=args.collector_model,
        providers=args.providers,
        openalex_client=openalex_client,
        max_external_claims_per_review=args.max_external_claims_per_review,
        max_queries_per_claim=args.max_queries_per_claim,
        max_openalex_results_per_query=args.max_openalex_results_per_query,
        max_evidence_per_claim=args.max_evidence_per_claim,
    )
    out = artifact_path(args.out, args)
    write_json(enriched, out)
    print(
        f"Saved external-evidence dataset to {out} "
        f"({manifest['record_count']} records across {manifest['paper_count']} papers)."
    )


def command_audit(args: argparse.Namespace) -> None:
    dataset = read_json(artifact_path(args.input, args))
    openalex_client = None
    external_provider_names = [item.strip() for item in args.external_providers.replace("-", "_").lower().split(",")]
    if args.external_evidence and "openalex" in external_provider_names:
        openalex_client = OpenAlexClient(
            mailto=args.openalex_mailto,
            timeout=args.openalex_timeout,
            cache_root=artifact_path(args.openalex_cache, args) if args.openalex_cache else None,
            refresh_cache=args.refresh_openalex_cache,
            offline=args.offline_openalex_cache,
        )
    try:
        result = audit_dataset(
            dataset,
            claim_model=args.claim_model,
            judge_model=args.judge_model,
            use_llm_judge=args.llm_judge,
            use_external_evidence=args.external_evidence,
            external_providers=args.external_providers,
            external_model=args.collector_model,
            openalex_client=openalex_client,
        )
    except LLMClientError as exc:
        raise SystemExit(f"LLM setup error: {exc}") from exc
    write_outputs(
        result,
        artifact_path(args.out, args),
        artifact_path(args.markdown, args),
        artifact_path(args.html, args),
    )


def command_validate_grounding(args: argparse.Namespace) -> None:
    dataset = read_json(artifact_path(args.input, args))
    try:
        client = OpenAIChatClient.from_env()
    except LLMClientError as exc:
        raise SystemExit(f"LLM setup error: {exc}") from exc
    client.timeout = args.openai_timeout
    llm_client = RetryingStructuredLLMClient(client, retries=args.retries)
    report = validate_grounding_for_dataset(
        dataset,
        llm_client=llm_client,
        model=args.claim_model,
        review_limit=args.review_limit,
        max_claims=args.max_claims,
    )
    out = artifact_path(args.out, args)
    markdown = artifact_path(args.markdown, args)
    write_json(report, out)
    write_grounding_markdown(report, markdown)
    stats = report["stats"]
    print(
        f"Saved grounding validation to {out} and {markdown}. "
        f"Status={report['status']}; reviews={stats['review_count']}; "
        f"claims={stats['final_claim_count']}; "
        f"grounding={stats['final_grounding_pass_rate']:.1%}."
    )


def command_validate_concern_survival(args: argparse.Namespace) -> None:
    try:
        client = OpenAIChatClient.from_env()
    except LLMClientError as exc:
        raise SystemExit(f"LLM setup error: {exc}") from exc
    client.timeout = args.openai_timeout
    llm_client = RetryingStructuredLLMClient(client, retries=args.retries)
    report = validate_concern_survival_for_snapshot(
        artifact_path(args.snapshot, args),
        llm_client=llm_client,
        model=args.claim_model,
        paper_limit=args.paper_limit,
        review_limit=args.review_limit,
        max_claims=args.max_claims,
        survived_threshold=args.survived_threshold,
        partial_threshold=args.partial_threshold,
    )
    out = artifact_path(args.out, args)
    markdown = artifact_path(args.markdown, args)
    write_json(report, out)
    write_concern_survival_markdown(report, markdown)
    summary = report["summary"]
    calibration_message = ""
    if args.calibration_sample_size or args.calibration_jsonl or args.calibration_markdown:
        calibration = build_concern_survival_calibration_sample(
            report,
            sample_size=args.calibration_sample_size or 100,
            seed=args.calibration_seed,
        )
        if args.calibration_jsonl:
            calibration_jsonl = artifact_path(args.calibration_jsonl, args)
            write_concern_survival_calibration_jsonl(calibration, calibration_jsonl)
            calibration_message += f" calibration_jsonl={calibration_jsonl};"
        if args.calibration_markdown:
            calibration_markdown = artifact_path(args.calibration_markdown, args)
            write_concern_survival_calibration_markdown(calibration, calibration_markdown)
            calibration_message += f" calibration_markdown={calibration_markdown};"
    print(
        f"Saved concern survival validation to {out} and {markdown}. "
        f"papers={summary['evaluable_paper_count']}; claims={summary['claim_count']}; "
        f"loose_survival={summary['loose_survival_rate']:.1%}.{calibration_message}"
    )


def command_calibrate_concern_survival(args: argparse.Namespace) -> None:
    items = read_jsonl(artifact_path(args.input, args))
    if args.limit is not None:
        items = items[: max(0, args.limit)]
    try:
        client = OpenAIChatClient.from_env()
    except LLMClientError as exc:
        raise SystemExit(f"LLM setup error: {exc}") from exc
    client.timeout = args.openai_timeout
    llm_client = RetryingStructuredLLMClient(client, retries=args.retries)

    labels = []
    for index, item in enumerate(items, start=1):
        labels.append(label_concern_calibration_item(item, llm_client=llm_client, model=args.model))
        print(f"Labeled {index}/{len(items)} {item.get('task_id', '')}", flush=True)

    merged = merge_calibration_labels(items, labels)
    high_confidence = [item for item in merged if item.get("high_confidence_training_candidate")]
    report = build_concern_calibration_report(items=items, labels=labels, merged=merged)

    labels_out = artifact_path(args.labels_out, args)
    merged_out = artifact_path(args.merged_out, args)
    high_confidence_out = artifact_path(args.high_confidence_out, args)
    markdown = artifact_path(args.markdown, args)
    write_jsonl(labels_out, labels)
    write_jsonl(merged_out, merged)
    write_jsonl(high_confidence_out, high_confidence)
    write_concern_calibration_markdown(report, markdown)
    print(
        f"Saved concern calibration labels to {labels_out}; "
        f"merged={merged_out}; high_confidence={high_confidence_out}; "
        f"high_confidence_count={len(high_confidence)}; "
        f"agreement={report['auto_llm_agreement_rate']:.1%}."
    )


def command_sample_concern_negatives(args: argparse.Namespace) -> None:
    survival_report = read_json(artifact_path(args.input, args))
    sample = build_negative_calibration_sample(
        survival_report,
        sample_size=args.sample_size,
        seed=args.seed,
        max_auto_score=args.max_auto_score,
    )
    out = artifact_path(args.out, args)
    write_jsonl(out, sample["items"])
    print(
        f"Saved {sample['sample_size']} negative calibration items to {out}. "
        f"max_auto_score={sample['max_auto_score']}."
    )


def command_sample_concern_gold_expansion(args: argparse.Namespace) -> None:
    survival_report = read_json(artifact_path(args.input, args))
    existing = []
    for path in args.existing:
        existing.extend(read_jsonl(artifact_path(path, args)))
    sample = build_gold_expansion_calibration_sample(
        survival_report,
        existing_records=existing,
        sample_size=args.sample_size,
        seed=args.seed,
    )
    out = artifact_path(args.out, args)
    write_jsonl(out, sample["items"])
    summary = sample["summary"]
    print(
        f"Saved {sample['sample_size']} gold-expansion calibration items to {out}. "
        f"excluded_existing={sample['excluded_existing_count']}; "
        f"auto_labels={summary['sample_auto_label_counts']}; "
        f"reasons={summary['sample_reason_counts']}."
    )


def command_export_concern_training_data(args: argparse.Namespace) -> None:
    records = []
    for input_path in args.input:
        records.extend(read_jsonl(artifact_path(input_path, args)))
    if args.only_high_confidence:
        records = [record for record in records if record.get("high_confidence_training_candidate")]
    rag_records = build_rag_memory_records(records)
    sft_examples = build_sft_examples(records)
    preference_pairs = build_preference_pairs(records)

    rag_out = artifact_path(args.rag_out, args)
    sft_out = artifact_path(args.sft_out, args)
    preference_out = artifact_path(args.preference_out, args)
    write_jsonl(rag_out, rag_records)
    write_jsonl(sft_out, sft_examples)
    write_jsonl(preference_out, preference_pairs)
    print(
        f"Saved concern training exports: rag={len(rag_records)} to {rag_out}; "
        f"sft={len(sft_examples)} to {sft_out}; "
        f"preference={len(preference_pairs)} to {preference_out}."
    )


def command_validate_concern_rag(args: argparse.Namespace) -> None:
    records = []
    for path in args.records:
        records.extend(read_jsonl(artifact_path(path, args)))
    memory = read_jsonl(artifact_path(args.memory, args))
    report = validate_concern_rag(
        records,
        memory,
        top_ks=parse_top_ks(args.top_ks),
        exclude_same_paper=args.exclude_same_paper,
        only_decisive_meta_labels=args.only_decisive_meta_labels,
        only_high_confidence=args.only_high_confidence,
    )
    out = artifact_path(args.out, args)
    markdown = artifact_path(args.markdown, args)
    write_rag_validation_json(out, report)
    write_rag_validation_markdown(report, markdown)
    summary = report["summary"]
    print(
        f"Saved concern RAG validation to {out} and {markdown}. "
        f"queries={summary['query_count']}; "
        f"match_hit@5={summary.get('match_hit@5', 0):.1%}; "
        f"match_knn@3={summary.get('match_knn_accuracy@3', 0):.1%}."
    )

    if args.llm_ablation:
        try:
            client = OpenAIChatClient.from_env()
        except LLMClientError as exc:
            raise SystemExit(f"LLM setup error: {exc}") from exc
        client.timeout = args.openai_timeout
        llm_client = RetryingStructuredLLMClient(client, retries=args.retries)
        llm_report = run_rag_judgment_ablation(
            records,
            memory,
            llm_client=llm_client,
            model=args.model,
            limit=args.llm_limit,
            top_k=args.llm_top_k,
            exclude_same_paper=args.exclude_same_paper,
            include_current_meta_review=args.open_book_llm,
        )
        llm_out = artifact_path(args.llm_out, args)
        write_rag_validation_json(llm_out, llm_report)
        llm_summary = llm_report["summary"]
        print(
            f"Saved LLM RAG ablation to {llm_out}. "
            f"no_rag_match={llm_summary['no_rag_match_accuracy']:.1%}; "
            f"with_rag_match={llm_summary['with_rag_match_accuracy']:.1%}; "
            f"no_rag_quality={llm_summary['no_rag_quality_accuracy']:.1%}; "
            f"with_rag_quality={llm_summary['with_rag_quality_accuracy']:.1%}."
        )


def command_validate_reviewer_calibration(args: argparse.Namespace) -> None:
    concern_report = read_json(artifact_path(args.concern_survival, args))
    snapshot_dir = artifact_path(args.snapshot, args) if args.snapshot else None
    rebuttal_labels = []
    for path in args.rebuttal_labels:
        rebuttal_labels.extend(read_jsonl(artifact_path(path, args)))
    consensus_labels = []
    for path in args.consensus_labels:
        consensus_labels.extend(read_jsonl(artifact_path(path, args)))
    report = calibrate_reviewer_reliability(
        concern_report,
        snapshot_dir=snapshot_dir,
        rebuttal_labels=rebuttal_labels,
        consensus_labels=consensus_labels,
    )
    out = artifact_path(args.out, args)
    markdown = artifact_path(args.markdown, args)
    write_reviewer_calibration_json(out, report)
    write_reviewer_calibration_markdown(report, markdown)
    summary = report["summary"]
    print(
        f"Saved reviewer calibration to {out} and {markdown}. "
        f"reviews={summary['review_count']}; claims={summary['claim_count']}; "
        f"mean_reliability={summary['mean_review_reliability_score']:.1%}; "
        f"mean_llm_calibrated={summary['mean_llm_calibrated_review_reliability_score']:.1%}; "
        f"mean_consensus={summary['mean_inter_review_consensus_rate']:.1%}; "
        f"mean_rebuttal_addressed={summary['mean_rebuttal_addressed_rate']:.1%}."
    )


def command_sample_rebuttal_resolution(args: argparse.Namespace) -> None:
    reviewer_report = read_json(artifact_path(args.reviewer_calibration, args))
    sample = build_rebuttal_resolution_calibration_sample(
        reviewer_report,
        sample_size=args.sample_size,
        seed=args.seed,
    )
    out = artifact_path(args.out, args)
    write_reviewer_calibration_jsonl(out, sample["items"])
    print(
        f"Saved {sample['sample_size']} rebuttal-resolution calibration items to {out}. "
        f"proxy_labels={sample['summary']['sample_proxy_label_counts']}; "
        f"reasons={sample['summary']['sample_reason_counts']}."
    )


def command_calibrate_rebuttal_resolution(args: argparse.Namespace) -> None:
    items = read_jsonl(artifact_path(args.input, args))
    if args.limit is not None:
        items = items[: max(0, args.limit)]
    try:
        client = OpenAIChatClient.from_env()
    except LLMClientError as exc:
        raise SystemExit(f"LLM setup error: {exc}") from exc
    client.timeout = args.openai_timeout
    llm_client = RetryingStructuredLLMClient(client, retries=args.retries)

    labels = []
    for index, item in enumerate(items, start=1):
        labels.append(label_rebuttal_resolution_item(item, llm_client=llm_client, model=args.model))
        print(f"Labeled {index}/{len(items)} {item.get('task_id', '')}", flush=True)

    merged = merge_rebuttal_resolution_labels(items, labels)
    high_confidence = [item for item in merged if item.get("high_confidence_training_candidate")]
    report = build_rebuttal_resolution_calibration_report(items=items, labels=labels, merged=merged)

    labels_out = artifact_path(args.labels_out, args)
    merged_out = artifact_path(args.merged_out, args)
    high_confidence_out = artifact_path(args.high_confidence_out, args)
    markdown = artifact_path(args.markdown, args)
    write_reviewer_calibration_jsonl(labels_out, labels)
    write_reviewer_calibration_jsonl(merged_out, merged)
    write_reviewer_calibration_jsonl(high_confidence_out, high_confidence)
    write_rebuttal_resolution_calibration_markdown(report, markdown)
    print(
        f"Saved rebuttal-resolution labels to {labels_out}; "
        f"merged={merged_out}; high_confidence={high_confidence_out}; "
        f"high_confidence_count={len(high_confidence)}; "
        f"agreement={report['proxy_llm_agreement_rate']:.1%}."
    )


def command_sample_inter_reviewer_consensus(args: argparse.Namespace) -> None:
    reviewer_report = read_json(artifact_path(args.reviewer_calibration, args))
    sample = build_consensus_calibration_sample(
        reviewer_report,
        sample_size=args.sample_size,
        seed=args.seed,
    )
    out = artifact_path(args.out, args)
    write_reviewer_calibration_jsonl(out, sample["items"])
    print(
        f"Saved {sample['sample_size']} inter-reviewer consensus calibration items to {out}. "
        f"proxy_labels={sample['summary']['sample_proxy_label_counts']}; "
        f"reasons={sample['summary']['sample_reason_counts']}."
    )


def command_calibrate_inter_reviewer_consensus(args: argparse.Namespace) -> None:
    items = read_jsonl(artifact_path(args.input, args))
    if args.limit is not None:
        items = items[: max(0, args.limit)]
    try:
        client = OpenAIChatClient.from_env()
    except LLMClientError as exc:
        raise SystemExit(f"LLM setup error: {exc}") from exc
    client.timeout = args.openai_timeout
    llm_client = RetryingStructuredLLMClient(client, retries=args.retries)

    labels = []
    for index, item in enumerate(items, start=1):
        labels.append(label_consensus_item(item, llm_client=llm_client, model=args.model))
        print(f"Labeled {index}/{len(items)} {item.get('task_id', '')}", flush=True)

    merged = merge_consensus_labels(items, labels)
    high_confidence = [item for item in merged if item.get("high_confidence_training_candidate")]
    report = build_consensus_calibration_report(items=items, labels=labels, merged=merged)

    labels_out = artifact_path(args.labels_out, args)
    merged_out = artifact_path(args.merged_out, args)
    high_confidence_out = artifact_path(args.high_confidence_out, args)
    markdown = artifact_path(args.markdown, args)
    write_reviewer_calibration_jsonl(labels_out, labels)
    write_reviewer_calibration_jsonl(merged_out, merged)
    write_reviewer_calibration_jsonl(high_confidence_out, high_confidence)
    write_consensus_calibration_markdown(report, markdown)
    print(
        f"Saved inter-reviewer consensus labels to {labels_out}; "
        f"merged={merged_out}; high_confidence={high_confidence_out}; "
        f"high_confidence_count={len(high_confidence)}; "
        f"agreement={report['proxy_llm_agreement_rate']:.1%}."
    )


def command_build_evidence_chain_demo(args: argparse.Namespace) -> None:
    audit_result = read_json(artifact_path(args.audit, args))
    reviewer_calibration = read_json(artifact_path(args.reviewer_calibration, args)) if args.reviewer_calibration else None
    demo = build_evidence_chain_demo(
        audit_result,
        reviewer_calibration=reviewer_calibration,
        paper_id=args.paper_id or None,
    )
    out = artifact_path(args.out, args)
    write_evidence_chain_json(out, demo)
    summary = demo["summary"]
    print(
        f"Saved evidence-chain frontend JSON to {out}. "
        f"reviews={summary['review_count']}; claims={summary['claim_count']}; "
        f"high_priority={summary['high_priority_claim_count']}."
    )


def command_build_evidence_chain_benchmark(args: argparse.Namespace) -> None:
    audit_result = read_json(artifact_path(args.audit, args))
    reviewer_calibration = read_json(artifact_path(args.reviewer_calibration, args)) if args.reviewer_calibration else None
    benchmark = build_evidence_chain_benchmark(
        audit_result,
        reviewer_calibration=reviewer_calibration,
        paper_limit=args.paper_limit,
        claims_per_paper=args.claims_per_paper,
        sample_size=args.sample_size,
    )
    report = build_benchmark_validation_report(benchmark)
    out = artifact_path(args.out, args)
    markdown = artifact_path(args.markdown, args)
    write_evidence_chain_json(out, benchmark)
    write_benchmark_markdown(report, markdown)
    print(
        f"Saved evidence-chain benchmark to {out} and {markdown}. "
        f"items={benchmark['summary']['item_count']}; variants={benchmark['summary']['variant_count']}."
    )


def command_build_evidence_chain_calibration_benchmark(args: argparse.Namespace) -> None:
    reviewer_calibration = read_json(artifact_path(args.reviewer_calibration, args))
    normalized_dataset = read_json(artifact_path(args.normalized, args)) if args.normalized else None
    benchmark = build_evidence_chain_benchmark_from_calibration(
        reviewer_calibration,
        normalized_dataset=normalized_dataset,
        paper_limit=args.paper_limit,
        claims_per_paper=args.claims_per_paper,
        sample_size=args.sample_size,
    )
    report = build_benchmark_validation_report(benchmark)
    out = artifact_path(args.out, args)
    markdown = artifact_path(args.markdown, args)
    write_evidence_chain_json(out, benchmark)
    write_benchmark_markdown(report, markdown)
    print(
        f"Saved calibration evidence-chain benchmark to {out} and {markdown}. "
        f"papers={benchmark['summary']['paper_count']}; items={benchmark['summary']['item_count']}; "
        f"variants={benchmark['summary']['variant_count']}."
    )


def command_label_evidence_chain_pseudo_expert(args: argparse.Namespace) -> None:
    tasks = read_jsonl(artifact_path(args.tasks, args))
    labels = build_pseudo_expert_labels(tasks, annotator_id=args.annotator_id)
    report = build_pseudo_expert_report(tasks, labels)
    labels_out = artifact_path(args.labels_out, args)
    report_out = artifact_path(args.report_out, args)
    markdown = artifact_path(args.markdown, args)
    write_jsonl(labels_out, labels)
    write_evidence_chain_json(report_out, report)
    write_pseudo_expert_markdown(report, markdown)
    summary = report["summary"]
    print(
        f"Saved pseudo-expert labels to {labels_out}; report={report_out}; markdown={markdown}. "
        f"labels={summary['label_count']}; exact_match={summary['exact_match_rate']:.1%}."
    )


def command_write_evidence_chain_validation_story(args: argparse.Namespace) -> None:
    demo = read_json(artifact_path(args.demo, args))
    benchmark = read_json(artifact_path(args.benchmark, args))
    pseudo_report = read_json(artifact_path(args.pseudo_report, args))
    out = artifact_path(args.out, args)
    write_validation_story(out, demo, benchmark, pseudo_report)
    print(f"Saved evidence-chain validation story to {out}.")


def command_normalize_external_scoring_dataset(args: argparse.Namespace) -> None:
    if args.dataset == "contrasciview":
        records = normalize_contrasciview_csv(
            artifact_path(args.input, args),
            baseline=args.baseline,
            overlap_threshold=args.overlap_threshold,
            limit=args.limit,
        )
    else:
        source_records = read_external_records(artifact_path(args.input, args))
        records = normalize_dataset_records(
            source_records,
            dataset_key=args.dataset,
            dimension=args.dimension or None,
            limit=args.limit,
        )
    out = artifact_path(args.out, args)
    write_scoring_jsonl(out, records)
    summary = summarize_normalized(records)
    print(
        f"Saved {summary['record_count']} normalized scoring records to {out}. "
        f"datasets={summary['dataset_counts']}; dimensions={summary['dimension_counts']}."
    )


def command_ingest_external_scoring_datasets(args: argparse.Namespace) -> None:
    normalized_out = artifact_path(args.normalized_out, args)
    memory_out = artifact_path(args.memory_out, args)
    manifest_out = artifact_path(args.manifest_out, args)
    markdown_out = artifact_path(args.markdown, args)
    records, manifest = ingest_external_scoring_datasets(
        datasets=args.datasets,
        external_root=artifact_path(args.external_root, args),
        normalized_out=normalized_out,
        force=args.force,
        skip_download=args.skip_download,
        limit_per_dataset=args.limit_per_dataset,
    )
    memory = build_memory_records_from_normalized(records)
    write_scoring_jsonl(memory_out, memory)
    manifest["memory_out"] = str(memory_out)
    manifest.setdefault("summary", {})["memory_record_count"] = len(memory)
    write_ingestion_json(manifest_out, manifest)
    write_ingestion_markdown(markdown_out, render_ingestion_markdown(manifest))
    summary = manifest.get("summary", {})
    print(
        f"Saved {summary.get('normalized_record_count', len(records))} normalized external scoring records to {normalized_out}. "
        f"Saved {len(memory)} scoring-memory records to {memory_out}. "
        f"ready={summary.get('ready_dataset_count', 0)}; blocked={summary.get('blocked_dataset_count', 0)}; "
        f"manifest={manifest_out}; markdown={markdown_out}."
    )


def command_build_reviewer_public_scorecard(args: argparse.Namespace) -> None:
    payload = read_json(artifact_path(args.input, args))
    public_scorecard = build_public_scorecard(payload)
    out = artifact_path(args.out, args)
    write_public_scorecard_json(out, public_scorecard)
    summary = public_scorecard.get("summary", {})
    print(
        f"Saved reviewer public scorecard to {out}. "
        f"reviewers={summary.get('reviewer_count', 0)}; comments={summary.get('comment_count', 0)}; "
        f"overall={summary.get('overall_score', 0)}."
    )


def command_build_scoring_memory(args: argparse.Namespace) -> None:
    records = read_scoring_jsonl(artifact_path(args.input, args))
    if args.dimension == "auto":
        memory = build_memory_records_from_normalized(
            records,
            dataset=args.dataset,
            text_fields=parse_fields(args.text_fields),
            context_fields=parse_fields(args.context_fields),
            label_field=args.label_field,
            score_field=args.score_field or "mapped_score",
            limit=args.limit,
        )
    else:
        memory = build_memory_records(
            records,
            dimension=args.dimension,
            dataset=args.dataset,
            text_fields=parse_fields(args.text_fields),
            context_fields=parse_fields(args.context_fields),
            label_field=args.label_field,
            score_field=args.score_field,
            label_score_map=parse_label_score_map(args.label_score) or None,
            limit=args.limit,
        )
    out = artifact_path(args.out, args)
    write_scoring_jsonl(out, memory)
    print(f"Saved {len(memory)} scoring-memory records to {out}.")


def command_score_with_memory(args: argparse.Namespace) -> None:
    memory = read_scoring_jsonl(artifact_path(args.memory, args))
    result = score_with_memory(
        query_text=args.query,
        memory_records=memory,
        dimension=args.dimension,
        llm_score=args.llm_score,
        top_k=args.top_k,
        llm_weight=args.llm_weight,
        min_similarity=args.min_similarity,
    )
    out = artifact_path(args.out, args)
    write_scoring_json(out, result)
    print(
        f"Saved scoring-memory result to {out}. "
        f"source={result['source']}; final_score={result['final_score']}; "
        f"examples={len(result['retrieved_examples'])}."
    )


def command_score_dimensions_with_memory(args: argparse.Namespace) -> None:
    memory = read_scoring_jsonl(artifact_path(args.memory, args))
    result = score_dimensions_with_memory(
        query_text=args.query,
        memory_records=memory,
        llm_scores=parse_dimension_scores(args.llm_score),
        dimensions=parse_fields(args.dimensions),
        top_k=args.top_k,
        llm_weight=args.llm_weight,
        min_similarity=args.min_similarity,
    )
    out = artifact_path(args.out, args)
    write_scoring_json(out, result)
    print(
        f"Saved hybrid dimension scores to {out}. "
        f"overall_score={result['overall_score']}; dimensions={len(result['hybrid_scores'])}."
    )


def command_run_scoring_memory_suite(args: argparse.Namespace) -> None:
    records = read_scoring_jsonl(artifact_path(args.input, args))
    report = build_scoring_benchmark_suite(records)
    out = artifact_path(args.out, args)
    markdown = artifact_path(args.markdown, args)
    write_scoring_json(out, report)
    write_scoring_markdown(markdown, render_scoring_suite_markdown(report))
    print(
        f"Saved scoring benchmark suite to {out} and {markdown}. "
        f"records={report['summary']['record_count']}; accuracy={report['summary']['accuracy']:.1%}."
    )
    if args.guardrail_out:
        baseline = read_scoring_json(artifact_path(args.baseline, args)) if args.baseline else None
        guardrail = build_guardrail_report(
            report,
            baseline_report=baseline,
            min_accuracy=args.min_accuracy,
            min_macro_f1=args.min_macro_f1,
            max_accuracy_drop=args.max_accuracy_drop,
            max_macro_f1_drop=args.max_macro_f1_drop,
        )
        guardrail_out = artifact_path(args.guardrail_out, args)
        write_scoring_json(guardrail_out, guardrail)
        if args.guardrail_markdown:
            write_scoring_markdown(artifact_path(args.guardrail_markdown, args), render_guardrail_markdown(guardrail))
        print(f"Scoring suite guardrail {guardrail['status']}: saved to {guardrail_out}.")


def command_scoring_guardrail(args: argparse.Namespace) -> None:
    current = read_scoring_json(artifact_path(args.current, args))
    baseline = read_scoring_json(artifact_path(args.baseline, args)) if args.baseline else None
    report = build_guardrail_report(
        current,
        baseline_report=baseline,
        min_accuracy=args.min_accuracy,
        min_macro_f1=args.min_macro_f1,
        max_accuracy_drop=args.max_accuracy_drop,
        max_macro_f1_drop=args.max_macro_f1_drop,
    )
    out = artifact_path(args.out, args)
    markdown = artifact_path(args.markdown, args)
    write_scoring_json(out, report)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_guardrail_markdown(report), encoding="utf-8")
    print(f"Scoring guardrail {report['status']}: saved to {out} and {markdown}.")


def parse_dimension_scores(items: list[str] | None) -> dict[str, float]:
    scores = {}
    for item in items or []:
        if "=" not in item:
            raise SystemExit(f"Expected --llm-score dimension=score, got {item!r}")
        dimension, score = item.split("=", 1)
        scores[dimension.strip()] = float(score)
    return scores


def command_demo(args: argparse.Namespace) -> None:
    dataset = read_json("examples/sample_normalized_dataset.json")
    try:
        result = audit_dataset(
            dataset,
            claim_model=args.claim_model,
            judge_model=args.judge_model,
            use_llm_judge=args.llm_judge,
        )
    except LLMClientError as exc:
        raise SystemExit(f"LLM setup error: {exc}") from exc
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



def server_settings_for_cli(args: argparse.Namespace):
    from dataclasses import replace
    from .server.config import settings_from_env

    settings = settings_from_env()
    database_url = getattr(args, "database_url", "")
    if database_url:
        settings = replace(settings, database_url=database_url)
    return settings


def command_server_init_db(args: argparse.Namespace) -> None:
    from .server.database import init_db, make_engine

    settings = server_settings_for_cli(args)
    engine = make_engine(settings.database_url)
    init_db(engine)
    print(f"Initialized SecondOpinion server database at {settings.database_url}.")


def command_server_ingest_normalized(args: argparse.Namespace) -> None:
    from .server.config import normalized_inputs_from_env
    from .server.database import init_db, make_engine, make_session_factory, session_scope
    from .server.ingest import import_normalized_dataset

    settings = server_settings_for_cli(args)
    engine = make_engine(settings.database_url)
    init_db(engine)
    session_factory = make_session_factory(engine)
    inputs = [Path(item) for item in args.inputs] if args.inputs else normalized_inputs_from_env()
    summaries = []
    with session_scope(session_factory) as session:
        for input_path in inputs:
            summaries.append(import_normalized_dataset(session, input_path))
    total_papers = sum(int(item.get("paper_count", 0)) for item in summaries)
    total_reviews = sum(int(item.get("review_count", 0)) for item in summaries)
    print(f"Imported {len(summaries)} normalized datasets: papers={total_papers}; reviews={total_reviews}.")


def command_server_import_demo_scorecard(args: argparse.Namespace) -> None:
    from .server.database import init_db, make_engine, make_session_factory, session_scope
    from .server.ingest import import_public_scorecard

    settings = server_settings_for_cli(args)
    engine = make_engine(settings.database_url)
    init_db(engine)
    session_factory = make_session_factory(engine)
    with session_scope(session_factory) as session:
        summary = import_public_scorecard(
            session,
            path=args.input,
            paper_id=args.paper_id,
            scorer_version=settings.scorer_version,
            memory_index_version=settings.memory_index_version,
        )
    print(
        f"Imported demo scorecard for paper={summary['paper_id']}; "
        f"reviewers={summary['reviewer_count']}; scorecard={summary['scorecard_id']}."
    )


def command_server_register_memory_index(args: argparse.Namespace) -> None:
    from .server.database import init_db, make_engine, make_session_factory, session_scope
    from .server.ingest import register_scoring_memory_from_file

    settings = server_settings_for_cli(args)
    engine = make_engine(settings.database_url)
    init_db(engine)
    session_factory = make_session_factory(engine)
    with session_scope(session_factory) as session:
        summary = register_scoring_memory_from_file(session, path=args.memory, version=args.version)
    print(f"Registered memory index {summary['version']} with {summary['record_count']} records at {summary['path']}.")


def command_server_run_worker(args: argparse.Namespace) -> None:
    from .server.database import init_db, make_engine, make_session_factory
    from .server.worker import run_worker_loop

    settings = server_settings_for_cli(args)
    engine = make_engine(settings.database_url)
    init_db(engine)
    session_factory = make_session_factory(engine)
    for result in run_worker_loop(
        session_factory,
        settings=settings,
        once=args.once,
        sleep_seconds=args.sleep_seconds,
    ):
        if result is None:
            print("No queued scoring job found.")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))

def command_server_enqueue_scoring(args: argparse.Namespace) -> None:
    from .server.database import init_db, make_engine, make_session_factory, session_scope
    from .server.repository import enqueue_scoring_jobs

    settings = server_settings_for_cli(args)
    engine = make_engine(settings.database_url)
    init_db(engine)
    session_factory = make_session_factory(engine)
    with session_scope(session_factory) as session:
        summary = enqueue_scoring_jobs(
            session,
            conference_id=args.conference or None,
            year=args.year,
            paper_ids=list(args.paper_id or []) or None,
            limit=args.limit,
            requested_by_session="server_batch_cli",
            scorer_version=settings.scorer_version,
            memory_index_version=settings.memory_index_version,
            missing_only=not args.include_scored,
            dry_run=args.dry_run,
        )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def command_server_scoring_status(args: argparse.Namespace) -> None:
    from .server.database import init_db, make_engine, make_session_factory, session_scope
    from .server.repository import scoring_status

    settings = server_settings_for_cli(args)
    engine = make_engine(settings.database_url)
    init_db(engine)
    session_factory = make_session_factory(engine)
    with session_scope(session_factory) as session:
        summary = scoring_status(
            session,
            conference_id=args.conference or None,
            year=args.year,
            scorer_version=settings.scorer_version,
            memory_index_version=settings.memory_index_version,
        )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def command_server_retry_failed_scoring(args: argparse.Namespace) -> None:
    from .server.database import init_db, make_engine, make_session_factory, session_scope
    from .server.repository import retry_failed_scoring_jobs

    settings = server_settings_for_cli(args)
    engine = make_engine(settings.database_url)
    init_db(engine)
    session_factory = make_session_factory(engine)
    with session_scope(session_factory) as session:
        summary = retry_failed_scoring_jobs(
            session,
            conference_id=args.conference or None,
            year=args.year,
            limit=args.limit,
            scorer_version=settings.scorer_version,
            memory_index_version=settings.memory_index_version,
        )
    print(json.dumps(summary, ensure_ascii=False, indent=2))

def command_annotation_export(args: argparse.Namespace) -> None:
    if args.evidence_chain_demo:
        evidence_chain_demo = read_json(artifact_path(args.evidence_chain_demo, args))
        run_id, tasks = export_evidence_chain_annotation_tasks(evidence_chain_demo, run_id=args.run_id or None)
    elif args.evidence_chain_benchmark:
        evidence_chain_benchmark = read_json(artifact_path(args.evidence_chain_benchmark, args))
        run_id, tasks = export_evidence_chain_benchmark_annotation_tasks(
            evidence_chain_benchmark,
            run_id=args.run_id or None,
            sample_size=args.sample_size,
        )
    elif args.audit:
        audit_result = read_json(artifact_path(args.audit, args))
        run_id, tasks = export_annotation_tasks(audit_result, run_id=args.run_id or None)
    else:
        raise SystemExit("annotation-export requires --audit, --evidence-chain-demo, or --evidence-chain-benchmark.")
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
    try:
        client = OpenAIChatClient.from_env()
    except LLMClientError as exc:
        raise SystemExit(f"LLM setup error: {exc}") from exc
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

from __future__ import annotations

import csv
import json
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from .external_dataset_adapters import (
    normalize_ape_records,
    normalize_aries_records,
    normalize_betterpr_records,
    normalize_contrasciview_csv,
    normalize_disapere_records,
    normalize_politepeer_records,
    normalize_react_records,
    normalize_substanreview_records,
    read_records,
    summarize_normalized,
)


EXTERNAL_INGESTION_VERSION = "external-full-lite-ingestion-v0.1"

FIRST_BATCH = [
    "react",
    "betterpr",
    "substanreview",
    "reviewcritique",
    "politepeer",
    "contrasciview",
    "revci",
    "disapere",
]
SECOND_BATCH = ["rbtact", "ape", "aries", "ampere", "asap_review"]
RE2_BATCH = ["re2"]

DATASET_GROUPS = {
    "first": FIRST_BATCH,
    "batch1": FIRST_BATCH,
    "first_batch": FIRST_BATCH,
    "second": SECOND_BATCH,
    "batch2": SECOND_BATCH,
    "second_batch": SECOND_BATCH,
    "re2": RE2_BATCH,
    "all": FIRST_BATCH + SECOND_BATCH + RE2_BATCH,
}

PUBLIC_DATASET_SPECS: dict[str, dict[str, Any]] = {
    "react": {
        "dataset": "ReAct",
        "batch": "first",
        "mode": "full-lite",
        "dimensions": ["actionability"],
        "estimated_size": "1,250 labeled review-comment sentences; raw CSV is small.",
        "use_in_scoring": "Constructive/actionable comment examples for the actionability prior.",
        "resources": [
            {
                "name": "processed_data",
                "url": "https://raw.githubusercontent.com/gtmdotme/ReAct/main/processed_data.csv",
                "filename": "processed_data.csv",
                "kind": "csv",
            }
        ],
    },
    "betterpr": {
        "dataset": "BetterPR",
        "batch": "first",
        "mode": "full-lite",
        "dimensions": ["actionability"],
        "estimated_size": "1,496 toxicbert.csv comments; main Apple Numbers sheet requires manual conversion.",
        "use_in_scoring": "Constructive vs non-constructive comments for actionability and reviewer helpfulness.",
        "notes": [
            "The public toxicbert.csv is directly usable.",
            "The larger Dataset.numbers file is tracked as a conversion task instead of being parsed in this no-dependency pass.",
        ],
        "resources": [
            {
                "name": "toxicbert",
                "url": "https://raw.githubusercontent.com/PrabhatkrBharti/BetterPR/main/datasets/toxicbert.csv",
                "filename": "toxicbert.csv",
                "kind": "csv",
            }
        ],
    },
    "substanreview": {
        "dataset": "SubstanReview",
        "batch": "first",
        "mode": "full-lite",
        "dimensions": ["substantiation"],
        "estimated_size": "Train/test JSONL together are about 1.6 MB.",
        "use_in_scoring": "Evaluation/justification spans become substantiated vs unsupported reviewer claims.",
        "resources": [
            {
                "name": "train",
                "url": "https://raw.githubusercontent.com/YanzhuGuo/SubstanReview/main/annotation_final/train.jsonl",
                "filename": "train.jsonl",
                "kind": "jsonl",
            },
            {
                "name": "test",
                "url": "https://raw.githubusercontent.com/YanzhuGuo/SubstanReview/main/annotation_final/test.jsonl",
                "filename": "test.jsonl",
                "kind": "jsonl",
            },
        ],
    },
    "reviewcritique": {
        "dataset": "ReviewCritique",
        "batch": "first",
        "mode": "metadata-only",
        "dimensions": ["substantiation"],
        "estimated_size": "Paper reports 100 human papers, 380 human reviews, and 11,376 human review segments.",
        "use_in_scoring": "Planned deficiency labels would strengthen substantiation/deficiency priors.",
        "source_url": "https://arxiv.org/abs/2503.12307",
        "blocker": "No stable public raw dataset URL was found during the 2026-06-20 pass.",
        "resources": [],
    },
    "politepeer": {
        "dataset": "PolitePEER",
        "batch": "first",
        "mode": "full-lite",
        "dimensions": ["professionalism"],
        "estimated_size": "Full public CSV is about 375 KB.",
        "use_in_scoring": "Tone labels turn professionalism from LLM-only into an external-data-backed prior.",
        "resources": [
            {
                "name": "full",
                "url": "https://raw.githubusercontent.com/PrabhatkrBharti/PolitePEER/main/PolitenessDataset-FULL.csv",
                "filename": "PolitenessDataset-FULL.csv",
                "kind": "csv",
            }
        ],
    },
    "contrasciview": {
        "dataset": "ContraSciView",
        "batch": "first",
        "mode": "full-lite",
        "dimensions": ["consensus_conflict"],
        "estimated_size": "Annotated CSV is about 15 MB.",
        "use_in_scoring": "Contradictory review-pair labels support consensus/conflict guardrails.",
        "resources": [
            {
                "name": "annotated",
                "url": "https://raw.githubusercontent.com/sandeep82945/Contradiction-in-Peer-Review/main/Sdata_annotated.csv",
                "filename": "Sdata_annotated.csv",
                "kind": "csv",
            }
        ],
    },
    "revci": {
        "dataset": "RevCI",
        "batch": "first",
        "mode": "metadata-only",
        "dimensions": ["consensus_conflict"],
        "estimated_size": "Paper reports 800 expert-annotated review pairs plus about 2,000 teacher-generated pairs.",
        "use_in_scoring": "Would add evidence-level contradiction intensity beyond binary conflict.",
        "source_url": "https://arxiv.org/abs/2605.10171",
        "blocker": "Paper is public, but no stable raw artifact URL was found during the 2026-06-20 pass.",
        "resources": [],
    },
    "disapere": {
        "dataset": "DISAPERE",
        "batch": "first",
        "mode": "full-lite",
        "dimensions": ["rebuttal_robustness"],
        "estimated_size": "Public ZIP is about 3.1 MB.",
        "use_in_scoring": "Review-sentence/rebuttal-sentence alignments support rebuttal robustness and response specificity.",
        "resources": [
            {
                "name": "annotations",
                "url": "https://raw.githubusercontent.com/nnkennard/DISAPERE/main/DISAPERE.zip",
                "filename": "DISAPERE.zip",
                "kind": "zip",
            }
        ],
    },
    "rbtact": {
        "dataset": "RbtAct",
        "batch": "second",
        "mode": "metadata-only",
        "dimensions": ["rebuttal_robustness", "actionability"],
        "estimated_size": "Paper reports RMR-75K.",
        "use_in_scoring": "Would connect review actionability to author uptake and revision impact.",
        "source_url": "https://arxiv.org/abs/2603.09723",
        "blocker": "No stable public RMR-75K raw artifact URL was found during the 2026-06-20 pass.",
        "resources": [],
    },
    "ape": {
        "dataset": "APE",
        "batch": "second",
        "mode": "semi-connect",
        "dimensions": ["rebuttal_alignment"],
        "estimated_size": "Public ZIP is about 7.9 MB.",
        "use_in_scoring": "Argument-pair labels support review-comment to rebuttal alignment.",
        "resources": [
            {
                "name": "review_rebuttal_pairs",
                "url": "https://raw.githubusercontent.com/LiyingCheng95/ArgumentPairExtraction/master/data/ReviewRebuttalnew2.txt.zip",
                "filename": "ReviewRebuttalnew2.txt.zip",
                "kind": "zip",
            }
        ],
    },
    "aries": {
        "dataset": "ARIES",
        "batch": "second",
        "mode": "semi-connect",
        "dimensions": ["revision_alignment"],
        "estimated_size": "Required annotation files are about 2 MB; full paper_edits file is about 13 MB and skipped for now.",
        "use_in_scoring": "Comment-to-edit links open a lightweight path from review concerns to revision alignment.",
        "resources": [
            {
                "name": "review_comments",
                "url": "https://ai2-s2-research-public.s3.us-west-2.amazonaws.com/aries/review_comments.jsonl",
                "filename": "review_comments.jsonl",
                "kind": "jsonl",
            },
            {
                "name": "edit_labels_train",
                "url": "https://ai2-s2-research-public.s3.us-west-2.amazonaws.com/aries/edit_labels_train.jsonl",
                "filename": "edit_labels_train.jsonl",
                "kind": "jsonl",
            },
            {
                "name": "edit_labels_test",
                "url": "https://ai2-s2-research-public.s3.us-west-2.amazonaws.com/aries/edit_labels_test.jsonl",
                "filename": "edit_labels_test.jsonl",
                "kind": "jsonl",
            },
        ],
    },
    "ampere": {
        "dataset": "AMPERE",
        "batch": "second",
        "mode": "metadata-only",
        "dimensions": ["argument_role"],
        "estimated_size": "Public raw file location not confirmed in this pass.",
        "use_in_scoring": "Would tag review-comment argument roles such as request, evaluation, fact, and reference.",
        "blocker": "No stable public raw dataset URL was found during the 2026-06-20 pass.",
        "resources": [],
    },
    "asap_review": {
        "dataset": "ASAP-Review",
        "batch": "second",
        "mode": "metadata-only",
        "dimensions": ["review_aspect"],
        "estimated_size": "ReviewAdvisor dataset is distributed through a Google Drive package.",
        "use_in_scoring": "Would add aspect labels for soundness, novelty, comparison, presentation, and related review facets.",
        "source_url": "https://github.com/neulab/ReviewAdvisor",
        "blocker": "Requires Google Drive download flow; not pulled in the no-dependency public-URL ingester.",
        "resources": [],
    },
    "re2": {
        "dataset": "Re2",
        "batch": "re2",
        "mode": "metadata-only",
        "dimensions": ["rebuttal_robustness"],
        "estimated_size": "Paper reports 19,926 submissions, 70,668 reviews, and 53,818 rebuttals.",
        "use_in_scoring": "Strategic review/rebuttal subset for multi-turn rebuttal robustness once a stable artifact is reachable.",
        "source_url": "https://anonymous.4open.science/r/ReviewBench_anon/",
        "blocker": "Dataset URL is an anonymous repository landing page; no direct raw subset URL was confirmed in this pass.",
        "resources": [],
    },
}


NORMALIZERS: dict[str, Callable[..., list[dict[str, Any]]]] = {
    "react": normalize_react_records,
    "betterpr": normalize_betterpr_records,
    "substanreview": normalize_substanreview_records,
    "politepeer": normalize_politepeer_records,
}


def expand_dataset_keys(items: str | Iterable[str] | None) -> list[str]:
    tokens: list[str] = []
    if items is None:
        tokens = ["all"]
    elif isinstance(items, str):
        tokens = split_dataset_tokens(items)
    else:
        for item in items:
            tokens.extend(split_dataset_tokens(str(item)))

    expanded: list[str] = []
    for token in tokens or ["all"]:
        key = normalize_dataset_key(token)
        group = DATASET_GROUPS.get(key)
        if group:
            for dataset_key in group:
                append_unique(expanded, dataset_key)
            continue
        if key not in PUBLIC_DATASET_SPECS:
            raise ValueError(f"Unknown external scoring dataset or group: {token!r}")
        append_unique(expanded, key)
    return expanded


def ingest_external_scoring_datasets(
    *,
    datasets: str | Iterable[str] | None,
    external_root: str | Path,
    normalized_out: str | Path,
    force: bool = False,
    skip_download: bool = False,
    limit_per_dataset: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    dataset_keys = expand_dataset_keys(datasets)
    external_root = Path(external_root)
    normalized_out = Path(normalized_out)
    manifest = {
        "schema_version": EXTERNAL_INGESTION_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "selected_datasets": dataset_keys,
        "external_root": str(external_root),
        "normalized_out": str(normalized_out),
        "policy": {
            "raw_data_committed": False,
            "raw_data_location": "data/external/<dataset>/",
            "normalized_data_committed": False,
            "normalized_data_location": "data/normalized/",
            "training_strategy": "no fine-tuning; use as external scoring memory and benchmark corpus",
        },
        "datasets": [],
    }

    all_records: list[dict[str, Any]] = []
    for dataset_key in dataset_keys:
        download_entry = prepare_dataset_resources(
            dataset_key,
            external_root=external_root,
            force=force,
            skip_download=skip_download,
        )
        records, normalize_entry = normalize_downloaded_dataset(
            dataset_key,
            external_root=external_root,
            limit=limit_per_dataset,
        )
        all_records.extend(records)
        manifest["datasets"].append(merge_dataset_entries(download_entry, normalize_entry))

    write_jsonl(normalized_out, all_records)
    manifest["summary"] = summarize_ingestion(manifest["datasets"], all_records)
    return all_records, manifest


def prepare_dataset_resources(
    dataset_key: str,
    *,
    external_root: str | Path,
    force: bool = False,
    skip_download: bool = False,
) -> dict[str, Any]:
    spec = PUBLIC_DATASET_SPECS[dataset_key]
    dataset_dir = Path(external_root) / dataset_key
    resources = []
    blockers = []

    if spec.get("blocker"):
        blockers.append(spec["blocker"])
    if not spec.get("resources"):
        return base_dataset_entry(dataset_key) | {
            "download_status": "blocked",
            "resources": [],
            "blockers": blockers,
        }

    dataset_dir.mkdir(parents=True, exist_ok=True)
    for resource in spec["resources"]:
        path = dataset_dir / resource["filename"]
        item = {
            "name": resource["name"],
            "url": resource["url"],
            "path": str(path),
            "kind": resource.get("kind", ""),
        }
        if skip_download and not path.exists():
            item.update({"status": "missing", "bytes": 0, "error": "skip_download was set"})
            blockers.append(f"{resource['name']} is missing locally and --skip-download was set.")
        elif path.exists() and not force:
            item.update({"status": "existing", "bytes": path.stat().st_size})
        else:
            try:
                bytes_written = download_url(resource["url"], path)
                item.update({"status": "downloaded", "bytes": bytes_written})
            except Exception as exc:  # pragma: no cover - exercised by real network failures.
                item.update({"status": "error", "bytes": 0, "error": str(exc)})
                blockers.append(f"{resource['name']} download failed: {exc}")
        resources.append(item)

    has_error = any(resource["status"] in {"error", "missing"} for resource in resources)
    return base_dataset_entry(dataset_key) | {
        "download_status": "blocked" if blockers and has_error else ("ready" if not has_error else "partial"),
        "resources": resources,
        "blockers": blockers,
    }


def normalize_downloaded_dataset(
    dataset_key: str,
    *,
    external_root: str | Path,
    limit: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    spec = PUBLIC_DATASET_SPECS[dataset_key]
    dataset_dir = Path(external_root) / dataset_key
    if not spec.get("resources"):
        return [], {
            "normalize_status": "blocked",
            "normalized_records": 0,
            "normalize_blockers": [spec.get("blocker", "No public resources configured.")],
        }

    try:
        if dataset_key == "contrasciview":
            records = normalize_contrasciview_csv(dataset_dir / "Sdata_annotated.csv", limit=limit)
        elif dataset_key == "disapere":
            records = normalize_disapere_records(read_disapere_zip(dataset_dir / "DISAPERE.zip"), limit=limit)
        elif dataset_key == "ape":
            records = normalize_ape_records(read_ape_zip(dataset_dir / "ReviewRebuttalnew2.txt.zip"), limit=limit)
        elif dataset_key == "aries":
            records = normalize_aries_records(read_aries_joined_records(dataset_dir), limit=limit)
        else:
            source_records = []
            for resource in spec["resources"]:
                path = dataset_dir / resource["filename"]
                if path.exists():
                    source_records.extend(read_records(path))
            if not source_records:
                raise FileNotFoundError(f"No downloaded source records found under {dataset_dir}")
            records = NORMALIZERS[dataset_key](source_records, limit=limit)
    except Exception as exc:
        return [], {
            "normalize_status": "blocked",
            "normalized_records": 0,
            "normalize_blockers": [str(exc)],
        }

    return records, {
        "normalize_status": "ready" if records else "empty",
        "normalized_records": len(records),
        "normalized_summary": summarize_normalized(records),
        "normalize_blockers": [] if records else ["Normalizer produced zero usable records."],
    }


def read_disapere_zip(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            normalized_name = name.replace("\\", "/")
            if not normalized_name.endswith(".json") or "/extra_annotations/" not in normalized_name:
                continue
            payload = json.loads(archive.read(name).decode("utf-8"))
            if isinstance(payload, list):
                for item in payload:
                    if isinstance(item, dict):
                        item.setdefault("_source_file", normalized_name)
                        records.append(item)
            elif isinstance(payload, dict):
                payload.setdefault("_source_file", normalized_name)
                records.append(payload)
    return records


def read_ape_zip(path: str | Path) -> list[dict[str, Any]]:
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".txt")]
        if not names:
            raise ValueError(f"No text file found in {path}")
        text = archive.read(names[0]).decode("utf-8", errors="replace")
    return parse_ape_argument_pairs(text.splitlines())


def parse_ape_argument_pairs(lines: Iterable[str]) -> list[dict[str, Any]]:
    pairs: dict[tuple[str, str], dict[str, list[str]]] = {}
    for line in lines:
        if not line.strip():
            continue
        columns = [column.strip() for column in line.split("\t")]
        if len(columns) < 5:
            continue
        text, _bio_role, pair_tag, side, group_id = columns[:5]
        pair_id = parse_ape_pair_id(pair_tag)
        side_key = side.strip().lower()
        if not text or not pair_id or side_key not in {"review", "reply"}:
            continue
        item = pairs.setdefault((group_id or "unknown", pair_id), {"review": [], "reply": []})
        item[side_key].append(text)

    records = []
    for index, ((group_id, pair_id), item) in enumerate(sorted(pairs.items())):
        review_argument = " ".join(item["review"]).strip()
        rebuttal_argument = " ".join(item["reply"]).strip()
        if not review_argument:
            continue
        records.append(
            {
                "task_id": f"ape:{group_id}:{pair_id}:{index}",
                "review_argument": review_argument,
                "rebuttal_argument": rebuttal_argument,
                "is_pair": "yes" if rebuttal_argument else "no",
                "source_group_id": group_id,
                "source_pair_id": pair_id,
            }
        )
    return records


def parse_ape_pair_id(value: str) -> str:
    value = value.strip()
    if not value or value == "O":
        return ""
    if "-" in value:
        return value.split("-", 1)[1]
    return value


def read_aries_joined_records(dataset_dir: str | Path) -> list[dict[str, Any]]:
    dataset_dir = Path(dataset_dir)
    comments_path = dataset_dir / "review_comments.jsonl"
    if not comments_path.exists():
        raise FileNotFoundError(f"Missing ARIES comments file: {comments_path}")
    comments = {aries_key(item): item for item in read_jsonl(comments_path)}

    records = []
    for labels_path in sorted(dataset_dir.glob("edit_labels_*.jsonl")):
        split = labels_path.stem.replace("edit_labels_", "")
        for index, label in enumerate(read_jsonl(labels_path)):
            comment = comments.get(aries_key(label), {})
            positive_edits = label.get("positive_edits", [])
            review_comment = first_text(comment.get("comment"), label.get("comment"), label.get("review_comment"))
            if not review_comment:
                continue
            records.append(
                {
                    "task_id": f"aries:{label.get('doc_id', '')}:{label.get('comment_id', '')}:{split}:{index}",
                    "review_comment": review_comment,
                    "paper_edit": stringify_edit_list(positive_edits),
                    "is_linked": "yes" if positive_edits else "no",
                    "annotation": first_text(label.get("annotation"), comment.get("annotation")),
                    "split": split,
                    "doc_id": label.get("doc_id", ""),
                    "comment_id": label.get("comment_id", ""),
                    "positive_edit_count": len(positive_edits) if isinstance(positive_edits, list) else 0,
                    "negative_edit_count": len(label.get("negative_edits", [])) if isinstance(label.get("negative_edits", []), list) else 0,
                }
            )
    return records


def render_ingestion_markdown(manifest: dict[str, Any]) -> str:
    summary = manifest.get("summary", {})
    lines = [
        "# External Scoring Dataset Ingestion",
        "",
        f"- Schema: `{manifest.get('schema_version', '')}`",
        f"- Generated at: `{manifest.get('generated_at', '')}`",
        f"- Selected datasets: {len(manifest.get('selected_datasets', []))}",
        f"- Normalized records: {summary.get('normalized_record_count', 0)}",
        f"- Scoring-memory records: {summary.get('memory_record_count', 0)}",
        f"- Ready datasets: {summary.get('ready_dataset_count', 0)}",
        f"- Blocked datasets: {summary.get('blocked_dataset_count', 0)}",
        "",
        "## Dataset Status",
        "",
        "| Dataset | Batch | Mode | Status | Records | Dimensions | Use |",
        "| --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for item in manifest.get("datasets", []):
        status = item.get("status", "")
        dimensions = ", ".join(f"`{dimension}`" for dimension in item.get("dimensions", []))
        use = clean_markdown_cell(item.get("use_in_scoring", ""))
        lines.append(
            f"| {item.get('dataset', item.get('dataset_key', ''))} | {item.get('batch', '')} | "
            f"{item.get('mode', '')} | `{status}` | {item.get('normalized_records', 0)} | {dimensions} | {use} |"
        )

    lines.extend(["", "## Blockers", ""])
    blocker_keys = set()
    blockers = []
    for item in manifest.get("datasets", []):
        dataset = item.get("dataset", item.get("dataset_key", ""))
        for blocker in item.get("blockers", []) + item.get("normalize_blockers", []):
            key = (dataset, blocker)
            if key in blocker_keys:
                continue
            blocker_keys.add(key)
            blockers.append(key)
    if blockers:
        for dataset, blocker in blockers:
            lines.append(f"- **{dataset}**: {blocker}")
    else:
        lines.append("- None.")

    lines.extend(
        [
            "",
            "## Scoring Use",
            "",
            "- The connected records are normalized into the shared external scoring schema.",
            "- The CLI can build lexical scoring memory from the normalized corpus without fine-tuning.",
            "- Blocked datasets remain represented in the manifest so the backlog is explicit and reproducible.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: str | Path, records: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n" for record in records), encoding="utf-8")


def write_markdown(path: str | Path, markdown: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8-sig").split("\n") if line.strip()]


def download_url(url: str, path: Path, *, timeout: int = 120) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "SecondOpinion-ingestion/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read()
    path.write_bytes(data)
    return len(data)


def base_dataset_entry(dataset_key: str) -> dict[str, Any]:
    spec = PUBLIC_DATASET_SPECS[dataset_key]
    return {
        "dataset_key": dataset_key,
        "dataset": spec.get("dataset", dataset_key),
        "batch": spec.get("batch", ""),
        "mode": spec.get("mode", ""),
        "dimensions": spec.get("dimensions", []),
        "estimated_size": spec.get("estimated_size", ""),
        "use_in_scoring": spec.get("use_in_scoring", ""),
        "source_url": spec.get("source_url", ""),
        "notes": spec.get("notes", []),
    }


def merge_dataset_entries(download_entry: dict[str, Any], normalize_entry: dict[str, Any]) -> dict[str, Any]:
    merged = download_entry | normalize_entry
    if merged.get("normalize_status") == "ready":
        merged["status"] = "ready"
    elif merged.get("download_status") == "blocked" or merged.get("normalize_status") == "blocked":
        merged["status"] = "blocked"
    elif merged.get("normalize_status") == "empty":
        merged["status"] = "empty"
    else:
        merged["status"] = "partial"
    return merged


def summarize_ingestion(dataset_entries: list[dict[str, Any]], records: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = Counter(entry.get("status", "") for entry in dataset_entries)
    return {
        "dataset_count": len(dataset_entries),
        "ready_dataset_count": statuses.get("ready", 0),
        "blocked_dataset_count": statuses.get("blocked", 0),
        "partial_dataset_count": statuses.get("partial", 0),
        "empty_dataset_count": statuses.get("empty", 0),
        "normalized_record_count": len(records),
        "dataset_record_counts": dict(Counter(record.get("dataset", "") for record in records)),
        "dimension_record_counts": dict(Counter(record.get("dimension", "") for record in records)),
    }


def split_dataset_tokens(value: str) -> list[str]:
    return [token.strip() for token in value.replace(";", ",").split(",") if token.strip()]


def normalize_dataset_key(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def append_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def aries_key(item: dict[str, Any]) -> str:
    return f"{item.get('doc_id', '')}:{item.get('comment_id', '')}"


def first_text(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def stringify_edit_list(value: Any) -> str:
    if not value:
        return ""
    if not isinstance(value, list):
        return str(value)
    rendered = []
    for item in value:
        if isinstance(item, dict):
            rendered.append(stringify_edit_dict(item))
        else:
            rendered.append(str(item))
    return "\n".join(text for text in rendered if text.strip())


def stringify_edit_dict(item: dict[str, Any]) -> str:
    for field in ("after", "revised_text", "text", "edit_text", "sentence", "content"):
        text = first_text(item.get(field))
        if text:
            return text
    return json.dumps(item, ensure_ascii=False, sort_keys=True)


def clean_markdown_cell(value: Any) -> str:
    return str(value or "").replace("|", "/").replace("\n", " ")

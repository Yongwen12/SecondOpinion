import json
import uuid
from pathlib import Path

import secondopinion.openreview_data_minimization_audit as audit_module
from secondopinion.openreview_data_minimization_audit import build_data_minimization_audit


def scratch_dir(name: str) -> Path:
    path = Path("tmp_test_openreview_data_minimization_audit") / f"{name}_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_data_minimization_audit_allows_core_review_data_only():
    root = scratch_dir("core")
    normalized = root / "normalized" / "sample.json"
    normalized.parent.mkdir(parents=True)
    normalized.write_text(
        json.dumps(
            {
                "dataset": "iclr_2025",
                "papers": [
                    {
                        "paper_id": "paper1",
                        "openreview_forum_id": "paper1",
                        "venue": "ICLR",
                        "year": 2025,
                        "title": "A Paper",
                        "abstract": "Abstract only.",
                        "decision": "Accept",
                        "reviews": [{"review_id": "r1", "weaknesses": "Needs an ablation."}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    batch = root / "batch" / "sample.jsonl"
    batch.parent.mkdir(parents=True)
    batch.write_text(
        json.dumps(
            {
                "custom_id": "ICLR-2025-paper1-r1",
                "body": {
                    "messages": [
                        {"role": "user", "content": "Paper title: A Paper\nAbstract: Abstract only.\nReview text: Needs an ablation."}
                    ]
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = build_data_minimization_audit(normalized_patterns=[str(normalized)], batch_patterns=[str(batch)])

    assert report["status"] == "passed"
    assert report["summary"]["normalized_file_count"] == 1
    assert report["summary"]["batch_request_count"] == 1
    assert report["normalized_files"][0]["pdf_url_pointer_count"] == 0
    assert "pdf_url" not in batch.read_text(encoding="utf-8")


def test_data_minimization_audit_fails_on_pdf_pointer_or_rebuttal():
    normalized = scratch_dir("pdf_rebuttal") / "normalized.json"
    normalized.write_text(
        json.dumps(
            {
                "papers": [
                    {
                        "paper_id": "paper1",
                        "title": "T",
                        "abstract": "A",
                        "pdf_url": "https://openreview.net/pdf?id=paper1",
                        "rebuttals": [{"text": "Author response"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = build_data_minimization_audit(normalized_patterns=[str(normalized)], batch_patterns=[])

    assert report["status"] == "failed"
    assert report["summary"]["normalized_failed_count"] == 1


def test_data_minimization_audit_fails_on_full_text_key():
    normalized = scratch_dir("full_text") / "normalized.json"
    normalized.write_text(
        json.dumps({"papers": [{"paper_id": "paper1", "title": "T", "abstract": "A", "full_text": "too much"}]}),
        encoding="utf-8",
    )

    report = build_data_minimization_audit(normalized_patterns=[str(normalized)], batch_patterns=[])

    assert report["status"] == "failed"
    assert report["summary"]["normalized_failed_count"] == 1
    assert report["errors"]


def test_data_minimization_audit_database_check_is_opt_in():
    report = build_data_minimization_audit(normalized_patterns=[], batch_patterns=[])

    assert report["status"] == "passed"
    assert report["summary"]["database_checked"] is False
    assert report["database"] == {}


def test_data_minimization_audit_fails_when_database_has_forbidden_fields(monkeypatch):
    monkeypatch.setattr(
        audit_module,
        "audit_database",
        lambda: {
            "status": "failed",
            "paper_count": 1,
            "review_count": 1,
            "pdf_url_nonempty_count": 1,
            "paper_source_forbidden_count": 0,
            "review_source_forbidden_count": 0,
            "paper_source_keys": {},
            "review_source_keys": {},
        },
    )

    report = build_data_minimization_audit(normalized_patterns=[], batch_patterns=[], include_database=True)

    assert report["status"] == "failed"
    assert report["summary"]["database_checked"] is True
    assert report["summary"]["database_status"] == "failed"
    assert report["errors"]

def test_data_minimization_audit_reports_raw_snapshot_retention_without_failing_core_audit():
    root = scratch_dir("raw")
    raw_root = root / "data" / "raw" / "openreview" / "iclr" / "2025" / "snap"
    raw_root.mkdir(parents=True)
    (raw_root / "notes_page_0000.json").write_text(json.dumps({"notes": []}), encoding="utf-8")

    report = build_data_minimization_audit(normalized_patterns=[], batch_patterns=[], raw_root=root / "data" / "raw" / "openreview")

    assert report["status"] == "passed"
    assert report["summary"]["raw_checked"] is True
    assert report["summary"]["raw_status"] == "requires_cleanup"
    assert report["raw"]["raw_note_page_count"] == 1

def test_data_minimization_audit_can_fail_on_raw_snapshot_retention():
    root = scratch_dir("raw_fail")
    raw_root = root / "data" / "raw" / "openreview" / "iclr" / "2025" / "snap"
    raw_root.mkdir(parents=True)
    (raw_root / "notes_page_0000.json").write_text(json.dumps({"notes": []}), encoding="utf-8")

    report = build_data_minimization_audit(
        normalized_patterns=[],
        batch_patterns=[],
        raw_root=root / "data" / "raw" / "openreview",
        fail_on_raw=True,
    )

    assert report["status"] == "failed"
    assert report["summary"]["fail_on_raw"] is True
    assert any("raw OpenReview API snapshots remain" in error for error in report["errors"])

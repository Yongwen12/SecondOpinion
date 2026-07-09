import json
import uuid
from pathlib import Path

from secondopinion.batch_cost_review import review_batch_costs, render_batch_cost_review_markdown


def write_manifest(path, **values):
    payload = {
        "request_count": 10,
        "estimated_input_tokens": 1000,
        "estimated_output_tokens": 500,
        "estimated_batch_cost_usd": 0.25,
    }
    payload.update(values)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_batch_cost_review_sums_manifest_costs():
    root = Path("data/test_tmp") / f"batch_cost_{uuid.uuid4().hex}"
    write_manifest(root / "a_manifest.json", request_count=2, estimated_batch_cost_usd=0.1)
    write_manifest(root / "b_manifest.json", request_count=3, estimated_batch_cost_usd=0.2)

    report = review_batch_costs(patterns=[str(root / "*_manifest.json")], max_total_cost_usd=1.0)
    markdown = render_batch_cost_review_markdown(report)

    assert report["status"] == "ready_for_cost_review"
    assert report["summary"]["manifest_count"] == 2
    assert report["summary"]["included_manifest_count"] == 2
    assert report["summary"]["excluded_manifest_count"] == 0
    assert report["summary"]["request_count"] == 5
    assert report["summary"]["estimated_batch_cost_usd"] == 0.3
    assert "Batch Cost Review" in markdown


def test_batch_cost_review_blocks_over_limit():
    root = Path("data/test_tmp") / f"batch_cost_{uuid.uuid4().hex}"
    write_manifest(root / "a_manifest.json", estimated_batch_cost_usd=1.5)

    report = review_batch_costs(patterns=[str(root / "*_manifest.json")], max_total_cost_usd=1.0)

    assert report["status"] == "blocked_cost_limit"


def test_batch_cost_review_can_exclude_part_manifests():
    root = Path("data/test_tmp") / f"batch_cost_{uuid.uuid4().hex}"
    write_manifest(root / "main_manifest.json", request_count=10, estimated_batch_cost_usd=1.0)
    write_manifest(
        root / "part_manifest.json",
        request_count=4,
        estimated_batch_cost_usd=0.4,
        source_manifest_path="main_manifest.json",
    )

    report = review_batch_costs(patterns=[str(root / "*manifest.json")], include_part_manifests=False)

    assert report["summary"]["manifest_count"] == 1
    assert report["summary"]["request_count"] == 10


def test_batch_cost_review_dedupes_split_manifest_totals_by_default():
    root = Path("data/test_tmp") / f"batch_cost_{uuid.uuid4().hex}"
    main = root / "main_manifest.json"
    write_manifest(main, request_count=10, estimated_batch_cost_usd=1.0)
    write_manifest(
        root / "part_a_manifest.json",
        request_count=4,
        estimated_batch_cost_usd=0.4,
        source_manifest_path=str(main),
    )
    write_manifest(
        root / "part_b_manifest.json",
        request_count=5,
        estimated_batch_cost_usd=0.5,
        source_manifest_path=str(main),
    )

    report = review_batch_costs(patterns=[str(root / "*manifest.json")])
    main_record = next(record for record in report["manifests"] if record["path"].endswith("main_manifest.json"))

    assert report["summary"]["manifest_count"] == 3
    assert report["summary"]["included_manifest_count"] == 2
    assert report["summary"]["excluded_manifest_count"] == 1
    assert report["summary"]["request_count"] == 9
    assert report["summary"]["estimated_batch_cost_usd"] == 0.9
    assert main_record["included_in_total"] is False
    assert main_record["excluded_from_total_reason"] == "replaced_by_part_manifests"


def test_batch_cost_review_can_disable_split_manifest_dedupe():
    root = Path("data/test_tmp") / f"batch_cost_{uuid.uuid4().hex}"
    main = root / "main_manifest.json"
    write_manifest(main, request_count=10, estimated_batch_cost_usd=1.0)
    write_manifest(
        root / "part_manifest.json",
        request_count=4,
        estimated_batch_cost_usd=0.4,
        source_manifest_path=str(main),
    )

    report = review_batch_costs(patterns=[str(root / "*manifest.json")], dedupe_split_manifests=False)

    assert report["summary"]["manifest_count"] == 2
    assert report["summary"]["included_manifest_count"] == 2
    assert report["summary"]["request_count"] == 14
    assert report["summary"]["estimated_batch_cost_usd"] == 1.4

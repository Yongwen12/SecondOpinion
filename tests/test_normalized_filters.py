import json

from secondopinion.normalized_filters import filter_normalized_dataset, parse_datetime


def ts(year: int) -> dict:
    created_ms = int(parse_datetime(f"{year}-02-01T00:00:00+00:00").timestamp() * 1000)
    return {
        "created_ms": created_ms,
        "modified_ms": created_ms,
        "created_at": f"{year}-02-01T00:00:00+00:00",
        "modified_at": f"{year}-02-01T00:00:00+00:00",
    }


def paper(paper_id: str, *, decision: str, decision_year: int, review_year: int = 2025) -> dict:
    return {
        "paper_id": paper_id,
        "decision": decision,
        "openreview_timestamps": ts(review_year),
        "reviews": [{"review_id": f"{paper_id}-r1", "openreview_timestamps": ts(review_year)}],
        "decisions": [{"id": f"{paper_id}-d1", "text": decision, "openreview_timestamps": ts(decision_year)}],
    }


def test_filter_normalized_dataset_keeps_decision_year_slice():
    payload = {
        "dataset": "tmlr_2025",
        "papers": [
            paper("keep", decision="Accept", decision_year=2025),
            paper("old", decision="Accept", decision_year=2024),
            paper("reject", decision="Reject", decision_year=2025),
        ],
    }

    filtered = filter_normalized_dataset(payload, year=2025, mode="decision_year")

    assert [item["paper_id"] for item in filtered["papers"]] == ["keep", "reject"]
    assert filtered["paper_count"] == 2
    assert filtered["review_count"] == 2
    assert filtered["filter_metadata"]["dropped_wrong_year_count"] == 1


def test_filter_normalized_dataset_can_keep_accepted_only():
    payload = {
        "dataset": "tmlr_2025",
        "papers": [
            paper("keep", decision="Certified for publication", decision_year=2025),
            paper("reject", decision="Reject", decision_year=2025),
        ],
    }

    filtered = filter_normalized_dataset(payload, year=2025, mode="decision_year", accepted_only=True)

    assert [item["paper_id"] for item in filtered["papers"]] == ["keep"]
    assert filtered["filter_metadata"]["dropped_decision_count"] == 1


def test_filter_normalized_cli_round_trip(tmp_path):
    source = tmp_path / "input.json"
    output = tmp_path / "output.json"
    source.write_text(json.dumps({"papers": [paper("keep", decision="Accept", decision_year=2025)]}), encoding="utf-8")

    from secondopinion.normalized_filters import main

    main(["--input", str(source), "--out", str(output), "--year", "2025", "--mode", "decision_year"])

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["paper_count"] == 1

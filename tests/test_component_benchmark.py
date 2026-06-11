from secondopinion.component_benchmark import benchmark_alignment, benchmark_classification, render_markdown


def test_benchmark_classification_reports_accuracy_and_majority_baseline():
    report = benchmark_classification(
        [
            {"task_id": "1", "dataset": "ReAct", "gold_label": "actionable", "predicted_label": "actionable"},
            {"task_id": "2", "dataset": "ReAct", "gold_label": "actionable", "predicted_label": "not_actionable"},
            {"task_id": "3", "dataset": "ReAct", "gold_label": "not_actionable", "predicted_label": "not_actionable"},
        ]
    )

    assert report["task_type"] == "classification"
    assert report["summary"]["record_count"] == 3
    assert report["summary"]["accuracy"] == 0.6667
    assert report["summary"]["majority_baseline"] == 0.6667
    assert report["summary"]["balanced_accuracy"] == 0.75
    assert report["per_label"]["actionable"]["recall"] == 0.5


def test_benchmark_alignment_reports_overlap_and_f1():
    report = benchmark_alignment(
        [
            {"task_id": "1", "dataset": "APE", "gold_ids": ["r1"], "predicted_ids": ["r1", "r2"]},
            {"task_id": "2", "dataset": "APE", "gold_ids": ["r3"], "predicted_ids": ["r4"]},
        ]
    )

    assert report["task_type"] == "alignment"
    assert report["summary"]["record_count"] == 2
    assert report["summary"]["any_overlap_rate"] == 0.5
    assert report["summary"]["mean_precision"] == 0.25
    assert report["summary"]["mean_recall"] == 0.5
    assert report["summary"]["mean_f1"] == 0.3333


def test_component_benchmark_markdown_warns_about_core_constructs():
    report = benchmark_classification(
        [{"task_id": "1", "gold_label": "high", "predicted_label": "low"}]
    )
    markdown = render_markdown(report)

    assert "# Component Benchmark" in markdown
    assert "does not validate core materiality or substantive resolution" in markdown

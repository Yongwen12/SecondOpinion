from secondopinion.scoring_memory import (
    build_scoring_benchmark_suite,
    build_guardrail_report,
    build_memory_records,
    build_memory_records_from_normalized,
    hybrid_score,
    retrieve_memory,
    render_scoring_suite_markdown,
    score_dimensions_with_memory,
    score_with_memory,
)


def test_build_memory_records_maps_external_labels_to_dimension_scores():
    records = [
        {
            "task_id": "r1",
            "dataset": "ReAct",
            "comment": "Please compare against a standard retrieval baseline.",
            "gold_label": "actionable",
            "aspect": "experiment",
        },
        {
            "task_id": "r2",
            "dataset": "ReAct",
            "comment": "The paper is not very exciting.",
            "gold_label": "not_actionable",
        },
    ]

    memory = build_memory_records(records, dimension="actionability", text_fields=["comment"])

    assert len(memory) == 2
    assert memory[0]["schema_version"] == "scoring-memory-v0.1"
    assert memory[0]["dimension"] == "actionability"
    assert memory[0]["mapped_score"] == 0.9
    assert memory[1]["mapped_score"] == 0.15
    assert memory[0]["context_text"] == "experiment"


def test_retrieve_memory_and_hybrid_score_blend_prior_with_llm_score():
    memory = build_memory_records(
        [
            {
                "task_id": "a",
                "dataset": "ReAct",
                "comment": "Add a baseline comparison and report runtime.",
                "gold_label": "actionable",
            },
            {
                "task_id": "b",
                "dataset": "ReAct",
                "comment": "The submission is somewhat boring.",
                "gold_label": "not_actionable",
            },
        ],
        dimension="actionability",
        text_fields=["comment"],
    )

    retrieved = retrieve_memory("The reviewer asks for a baseline comparison.", memory, dimension="actionability", top_k=1)
    result = hybrid_score(llm_score=0.7, retrieved_examples=retrieved, llm_weight=0.6)

    assert retrieved[0]["gold_label"] == "actionable"
    assert result["source"] == "hybrid"
    assert result["memory_prior"]["prior_score"] == 0.9
    assert result["final_score"] == 0.78


def test_score_with_memory_returns_dimension_and_examples():
    memory = build_memory_records(
        [
            {
                "task_id": "c1",
                "dataset": "ContraSciView",
                "premise": "The experiments are convincing.",
                "hypothesis": "The experiments are insufficient.",
                "gold_label": "contradiction",
            }
        ],
        dimension="consensus_conflict",
        text_fields=["premise", "hypothesis"],
    )

    result = score_with_memory(
        query_text="One reviewer says experiments are convincing while another says they are insufficient.",
        memory_records=memory,
        dimension="consensus_conflict",
        llm_score=0.3,
        top_k=3,
    )

    assert result["dimension"] == "consensus_conflict"
    assert result["retrieved_examples"]
    assert result["memory_prior"]["label_counts"] == {"contradiction": 1}


def test_score_dimensions_with_memory_returns_hybrid_scores_by_dimension():
    memory = build_memory_records(
        [
            {
                "task_id": "a",
                "dataset": "ReAct",
                "input_text": "Add a baseline comparison.",
                "gold_label": "actionable",
            },
            {
                "task_id": "s",
                "dataset": "SubstanReview",
                "input_text": "The reviewer cites Table 2 as evidence.",
                "gold_label": "substantiated",
            },
        ],
        dimension="actionability",
        text_fields=["input_text"],
    )
    memory.extend(
        build_memory_records(
            [
                {
                    "task_id": "s",
                    "dataset": "SubstanReview",
                    "input_text": "The reviewer cites Table 2 as evidence.",
                    "gold_label": "substantiated",
                }
            ],
            dimension="substantiation",
            text_fields=["input_text"],
        )
    )

    result = score_dimensions_with_memory(
        query_text="Please add a baseline comparison and cite the table.",
        memory_records=memory,
        llm_scores={"actionability": 0.8, "substantiation": 0.6},
        dimensions=["actionability", "substantiation"],
    )

    assert result["schema_version"] == "hybrid-scoring-v0.1"
    assert set(result["hybrid_scores"]) == {"actionability", "substantiation"}
    assert result["overall_score"] is not None
    assert result["hybrid_scores"]["actionability"]["source"] == "hybrid"


def test_build_memory_records_from_normalized_uses_record_dimension():
    memory = build_memory_records_from_normalized(
        [
            {
                "task_id": "a",
                "dataset": "ReAct",
                "dimension": "actionability",
                "input_text": "Add a baseline.",
                "gold_label": "actionable",
                "mapped_score": 0.9,
            },
            {
                "task_id": "s",
                "dataset": "SubstanReview",
                "dimension": "substantiation",
                "input_text": "The reviewer cites Table 2.",
                "gold_label": "substantiated",
                "mapped_score": 0.9,
            },
        ]
    )

    assert {record["dimension"] for record in memory} == {"actionability", "substantiation"}
    assert all(record["mapped_score"] == 0.9 for record in memory)


def test_guardrail_report_fails_on_metric_regression():
    current = {"summary": {"accuracy": 0.71, "macro_f1": 0.62}}
    baseline = {"summary": {"accuracy": 0.76, "macro_f1": 0.68}}

    report = build_guardrail_report(
        current,
        baseline_report=baseline,
        min_accuracy=0.7,
        min_macro_f1=0.6,
        max_accuracy_drop=0.02,
        max_macro_f1_drop=0.02,
    )

    assert report["status"] == "fail"
    failed = {check["name"] for check in report["checks"] if check["status"] == "fail"}
    assert failed == {"accuracy_drop", "macro_f1_drop"}


def test_scoring_benchmark_suite_groups_by_dimension():
    report = build_scoring_benchmark_suite(
        [
            {
                "task_id": "1",
                "dataset": "ReAct",
                "dimension": "actionability",
                "gold_label": "actionable",
                "predicted_label": "actionable",
            },
            {
                "task_id": "2",
                "dataset": "SubstanReview",
                "dimension": "substantiation",
                "gold_label": "substantiated",
                "predicted_label": "unsubstantiated",
            },
        ]
    )
    markdown = render_scoring_suite_markdown(report)

    assert report["schema_version"] == "scoring-benchmark-suite-v0.1"
    assert report["summary"]["dimension_count"] == 2
    assert "actionability" in report["by_dimension"]
    assert "# Scoring Memory Benchmark Suite" in markdown

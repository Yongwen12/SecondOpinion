import json

from secondopinion.external_dataset_ingestion import (
    expand_dataset_keys,
    parse_ape_argument_pairs,
    read_aries_joined_records,
    render_ingestion_markdown,
)


def test_expand_dataset_keys_handles_batches_without_duplicates():
    keys = expand_dataset_keys("first,react,second,re2")

    assert keys[0] == "react"
    assert keys.count("react") == 1
    assert "reviewcritique" in keys
    assert "ape" in keys
    assert keys[-1] == "re2"


def test_parse_ape_argument_pairs_groups_review_and_reply_spans():
    records = parse_ape_argument_pairs(
        [
            "The baseline is missing.\tB-Review\tB-1\tReview\tpaper-a",
            "Please compare to X.\tI-Review\tI-1\tReview\tpaper-a",
            "We added X in Table 2.\tB-Reply\tB-1\tReply\tpaper-a",
            "The notation is unclear.\tB-Review\tB-2\tReview\tpaper-a",
        ]
    )

    assert records[0]["review_argument"] == "The baseline is missing. Please compare to X."
    assert records[0]["rebuttal_argument"] == "We added X in Table 2."
    assert records[0]["is_pair"] == "yes"
    assert records[1]["is_pair"] == "no"


def test_read_aries_joined_records_maps_positive_edits(tmp_path):
    (tmp_path / "review_comments.jsonl").write_text(
        json.dumps(
            {
                "doc_id": "doc-1",
                "comment_id": "comment-1",
                "comment": "Please add the missing ablation.",
                "annotation": "request",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "edit_labels_train.jsonl").write_text(
        json.dumps(
            {
                "doc_id": "doc-1",
                "comment_id": "comment-1",
                "positive_edits": [{"after": "Added ablation results in Table 3."}],
                "negative_edits": [],
                "annotation": "request",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    records = read_aries_joined_records(tmp_path)

    assert records[0]["task_id"] == "aries:doc-1:comment-1:train:0"
    assert records[0]["review_comment"] == "Please add the missing ablation."
    assert records[0]["paper_edit"] == "Added ablation results in Table 3."
    assert records[0]["is_linked"] == "yes"


def test_render_ingestion_markdown_lists_ready_and_blocked_datasets():
    markdown = render_ingestion_markdown(
        {
            "schema_version": "external-full-lite-ingestion-v0.1",
            "generated_at": "2026-06-20T00:00:00+00:00",
            "selected_datasets": ["react", "revci"],
            "summary": {
                "normalized_record_count": 10,
                "ready_dataset_count": 1,
                "blocked_dataset_count": 1,
            },
            "datasets": [
                {
                    "dataset": "ReAct",
                    "batch": "first",
                    "mode": "full-lite",
                    "status": "ready",
                    "normalized_records": 10,
                    "dimensions": ["actionability"],
                    "use_in_scoring": "Actionability prior.",
                    "blockers": [],
                    "normalize_blockers": [],
                },
                {
                    "dataset": "RevCI",
                    "batch": "first",
                    "mode": "metadata-only",
                    "status": "blocked",
                    "normalized_records": 0,
                    "dimensions": ["consensus_conflict"],
                    "use_in_scoring": "Conflict intensity.",
                    "blockers": ["No stable raw URL."],
                    "normalize_blockers": [],
                },
            ],
        }
    )

    assert "| ReAct | first | full-lite | `ready` | 10 | `actionability` | Actionability prior. |" in markdown
    assert "**RevCI**: No stable raw URL." in markdown

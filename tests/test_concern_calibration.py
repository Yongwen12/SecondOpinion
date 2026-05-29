import unittest

from secondopinion.concern_calibration import (
    build_negative_calibration_sample,
    build_concern_calibration_report,
    build_gold_expansion_calibration_sample,
    build_preference_pairs,
    build_rag_memory_records,
    build_sft_examples,
    is_high_confidence_training_candidate,
    label_concern_calibration_item,
    merge_calibration_labels,
    normalized_calibration_record,
    validate_concern_calibration_label,
)


class FakeCalibrationLLM:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def complete_json(self, *, model, messages, schema_name, schema):
        self.calls.append({"model": model, "messages": messages, "schema_name": schema_name, "schema": schema})
        return self.payload


def sample_item():
    return {
        "task_id": "paper1:review1:0",
        "paper_id": "paper1",
        "review_id": "review1",
        "title": "Test Paper",
        "decision_label": "reject",
        "claim_text": "The paper lacks ablation studies.",
        "claim_type": "ablation",
        "importance": "major",
        "source_field": "weaknesses",
        "source_sentence": "The paper lacks ablation studies.",
        "auto_survival_label": "survived",
        "auto_survival_score": 0.52,
        "matched_meta_segment": "Reviewers raised concerns about missing ablations.",
        "matched_terms": ["ablation"],
        "meta_review_text": "Reviewers raised concerns about missing ablations.",
    }


class ConcernCalibrationTests(unittest.TestCase):
    def test_label_concern_calibration_item_validates_payload(self):
        client = FakeCalibrationLLM(
            {
                "labels": {
                    "meta_review_match": "survived",
                    "ac_treatment": "endorsed_or_relied_on",
                    "concern_quality": "high",
                    "label_evidence_strength": "high",
                    "confidence": "high",
                    "training_use": "include",
                    "rationale": "The meta-review repeats the same missing-ablation concern.",
                },
                "notes": "clear match",
            }
        )

        label = label_concern_calibration_item(sample_item(), llm_client=client, model="test-model")

        self.assertEqual(validate_concern_calibration_label(label), [])
        self.assertEqual(label["labels"]["meta_review_match"], "survived")
        self.assertEqual(client.calls[0]["schema_name"], "concern_survival_calibration_label")

    def test_merge_calibration_labels_marks_high_confidence_candidates(self):
        item = sample_item()
        label = {
            "label_id": "label1",
            "task_id": item["task_id"],
            "paper_id": "paper1",
            "review_id": "review1",
            "label_schema_version": "concern-calibration-label-v0.2",
            "annotator_type": "llm",
            "annotator_id": "llm:test",
            "model": "test",
            "auto_survival_label": "survived",
            "auto_survival_score": 0.52,
            "labels": {
                "meta_review_match": "survived",
                "ac_treatment": "endorsed_or_relied_on",
                "concern_quality": "high",
                "label_evidence_strength": "high",
                "confidence": "high",
                "training_use": "include",
                "rationale": "The same concern is repeated.",
            },
            "notes": "",
            "created_at": "2026-05-28T00:00:00+00:00",
        }

        merged = merge_calibration_labels([item], [label])

        self.assertEqual(len(merged), 1)
        self.assertTrue(merged[0]["auto_agrees_with_llm"])
        self.assertTrue(is_high_confidence_training_candidate(merged[0]))

    def test_build_concern_calibration_report_counts_agreement(self):
        item = sample_item()
        merged = [
            {
                **item,
                "llm_meta_review_match": "survived",
                "llm_concern_quality": "high",
                "llm_ac_treatment": "endorsed_or_relied_on",
                "auto_agrees_with_llm": True,
                "high_confidence_training_candidate": True,
            }
        ]
        label = {
            "task_id": item["task_id"],
            "labels": {
                "meta_review_match": "survived",
                "ac_treatment": "endorsed_or_relied_on",
                "concern_quality": "high",
            },
        }

        report = build_concern_calibration_report(items=[item], labels=[label], merged=merged)

        self.assertEqual(report["high_confidence_count"], 1)
        self.assertEqual(report["auto_llm_agreement_rate"], 1.0)

    def test_old_field_names_are_normalized_for_existing_outputs(self):
        record = normalized_calibration_record(
            {
                **sample_item(),
                "llm_survival_label": "survived",
                "llm_ac_stance": "endorsed_or_relied_on",
                "llm_evidence_clarity": "high",
                "llm_concern_quality": "high",
                "llm_confidence": "high",
            }
        )

        self.assertEqual(record["llm_meta_review_match"], "survived")
        self.assertEqual(record["llm_ac_treatment"], "endorsed_or_relied_on")
        self.assertEqual(record["llm_label_evidence_strength"], "high")

    def test_training_exports_use_renamed_fields(self):
        record = {
            **sample_item(),
            "llm_meta_review_match": "survived",
            "llm_ac_treatment": "endorsed_or_relied_on",
            "llm_concern_quality": "high",
            "llm_label_evidence_strength": "high",
            "llm_confidence": "high",
            "llm_rationale": "The AC repeats the concern.",
            "high_confidence_training_candidate": True,
        }

        rag = build_rag_memory_records([record])
        sft = build_sft_examples([record])
        pairs = build_preference_pairs([record])

        self.assertEqual(rag[0]["meta_review"]["match"], "survived")
        self.assertIn("meta_review_match", sft[0]["messages"][2]["content"])
        self.assertIn("rejected", pairs[0])

    def test_negative_calibration_sample_prefers_auto_not_found_low_score(self):
        report = {
            "snapshot": {"snapshot_id": "snap"},
            "papers": [
                {
                    "paper_id": "paper1",
                    "forum_id": "paper1",
                    "title": "Test Paper",
                    "decision": "Reject",
                    "decision_label": "reject",
                    "meta_review_text": "No mention.",
                    "reviews": [
                        {
                            "review_id": "review1",
                            "claims": [
                                {
                                    "claim_text": "Unmatched claim.",
                                    "claim_type": "clarity",
                                    "importance": "major",
                                    "source_field": "weaknesses",
                                    "source_sentence": "Unmatched claim.",
                                    "survival_label": "not_found",
                                    "survival_score": 0.02,
                                    "matched_meta_segment": "",
                                },
                                {
                                    "claim_text": "Matched claim.",
                                    "claim_type": "ablation",
                                    "importance": "major",
                                    "source_field": "weaknesses",
                                    "source_sentence": "Matched claim.",
                                    "survival_label": "survived",
                                    "survival_score": 0.5,
                                    "matched_meta_segment": "Matched claim.",
                                },
                            ],
                        }
                    ],
                }
            ],
        }

        sample = build_negative_calibration_sample(report, sample_size=10, max_auto_score=0.16)

        self.assertEqual(sample["sample_size"], 1)
        self.assertEqual(sample["items"][0]["auto_survival_label"], "not_found")
        self.assertEqual(sample["items"][0]["sampling_reason"], "auto_not_found_low_score")

    def test_gold_expansion_sample_excludes_existing_and_targets_negatives(self):
        report = {
            "snapshot": {"snapshot_id": "snap"},
            "papers": [
                {
                    "paper_id": "paper1",
                    "forum_id": "paper1",
                    "title": "Test Paper",
                    "decision": "Reject",
                    "decision_label": "reject",
                    "meta_review_text": "No mention.",
                    "reviews": [
                        {
                            "review_id": "review1",
                            "claims": [
                                {
                                    "claim_text": "Already labeled.",
                                    "claim_type": "ablation",
                                    "importance": "major",
                                    "source_field": "weaknesses",
                                    "source_sentence": "Already labeled.",
                                    "survival_label": "survived",
                                    "survival_score": 0.5,
                                },
                                {
                                    "claim_text": "This minor writing issue is unclear.",
                                    "claim_type": "writing",
                                    "importance": "minor",
                                    "source_field": "weaknesses",
                                    "source_sentence": "This minor writing issue is unclear.",
                                    "survival_label": "not_found",
                                    "survival_score": 0.01,
                                },
                            ],
                        }
                    ],
                }
            ],
        }

        sample = build_gold_expansion_calibration_sample(
            report,
            existing_records=[{"task_id": "paper1:review1:0"}],
            sample_size=10,
            seed=1,
        )

        self.assertEqual(sample["sample_size"], 1)
        self.assertEqual(sample["items"][0]["task_id"], "paper1:review1:1")
        self.assertIn(sample["items"][0]["sampling_reason"], {"auto_not_found_very_low_score", "possible_low_quality"})


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from secondopinion.reviewer_calibration import (
    build_consensus_calibration_report,
    build_consensus_calibration_sample,
    build_rebuttal_resolution_calibration_report,
    build_rebuttal_resolution_calibration_sample,
    calibrate_reviewer_reliability,
    calibrate_paper,
    label_consensus_item,
    label_rebuttal_resolution_item,
    merge_consensus_labels,
    merge_rebuttal_resolution_labels,
    write_json,
)


def content(**values):
    return {key: {"value": value} for key, value in values.items()}


def concern_report():
    return {
        "survival_version": "test-survival",
        "snapshot": {"snapshot_id": "snap"},
        "papers": [
            {
                "paper_id": "paper1",
                "forum_id": "paper1",
                "title": "Test Paper",
                "decision": "Reject",
                "decision_label": "reject",
                "reviews": [
                    {
                        "review_id": "review1",
                        "status": "ok",
                        "rating_raw": "3: reject",
                        "rating_normalized": 3.0,
                        "confidence_raw": "4: confident",
                        "confidence_normalized": 8.0,
                        "claims": [
                            {
                                "claim_text": "The paper lacks ablation studies for the retrieval module.",
                                "claim_type": "ablation",
                                "importance": "major",
                                "source_sentence": "The paper lacks ablation studies for the retrieval module.",
                                "survival_label": "survived",
                                "survival_score": 0.5,
                                "matched_meta_segment": "Reviewers raised missing ablations.",
                            }
                        ],
                    },
                    {
                        "review_id": "review2",
                        "status": "ok",
                        "rating_raw": "5: marginal",
                        "rating_normalized": 5.0,
                        "confidence_raw": "3",
                        "confidence_normalized": 6.0,
                        "claims": [
                            {
                                "claim_text": "Missing ablations make it hard to assess the retrieval component.",
                                "claim_type": "ablation",
                                "importance": "major",
                                "source_sentence": "Missing ablations make it hard to assess the retrieval component.",
                                "survival_label": "partial",
                                "survival_score": 0.25,
                                "matched_meta_segment": "Reviewers raised missing ablations.",
                            }
                        ],
                    },
                ],
            }
        ],
    }


class FakeRebuttalLLM:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def complete_json(self, *, model, messages, schema_name, schema):
        self.calls.append({"model": model, "messages": messages, "schema_name": schema_name, "schema": schema})
        return self.payload


class FakeConsensusLLM(FakeRebuttalLLM):
    pass


class ReviewerCalibrationTests(unittest.TestCase):
    def test_calibrate_paper_adds_consensus_and_rebuttal_resolution(self):
        paper = concern_report()["papers"][0]
        aux = {
            "author_responses": [
                "We thank the reviewers. We added ablation studies for the retrieval module in Appendix C."
            ],
            "reviewer_or_ac_discussions": ["The ablation concern remains important."],
        }

        result = calibrate_paper(paper, aux)

        first_claim = result["reviews"][0]["claims"][0]
        self.assertEqual(first_claim["consensus"]["label"], "strong")
        self.assertEqual(first_claim["rebuttal_resolution"]["label"], "likely_resolved_or_answered")
        self.assertEqual(first_claim["discussion_followup"]["label"], "followed_up")
        self.assertIn("lifecycle_robustness", first_claim)
        self.assertIn(first_claim["lifecycle_robustness"]["label"], {"low", "medium", "high"})
        self.assertGreaterEqual(result["reviews"][0]["mean_lifecycle_robustness_score"], 0)
        self.assertGreater(result["reviews"][0]["review_reliability_score"], 0)

    def test_calibrate_reviewer_reliability_reads_snapshot_auxiliary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_json(
                root / "manifest.json",
                {
                    "raw_files": ["notes_page_0000.json"],
                    "snapshot_id": "snap",
                    "source": "openreview",
                    "venue": "ICLR",
                    "year": 2024,
                },
            )
            write_json(
                root / "notes_page_0000.json",
                {
                    "notes": [
                        {
                            "id": "paper1",
                            "forum": "paper1",
                            "content": content(title="Test Paper"),
                            "details": {
                                "replies": [
                                    {
                                        "id": "authors1",
                                        "forum": "paper1",
                                        "invitations": ["ICLR.cc/2024/Conference/Submission1/-/Official_Comment"],
                                        "signatures": ["ICLR.cc/2024/Conference/Submission1/Authors"],
                                        "content": content(
                                            title="Rebuttal",
                                            comment="We added ablation studies for the retrieval module.",
                                        ),
                                    }
                                    ,
                                    {
                                        "id": "review1",
                                        "forum": "paper1",
                                        "invitations": ["ICLR.cc/2024/Conference/Submission1/-/Official_Review"],
                                        "signatures": ["ICLR.cc/2024/Conference/Submission1/Reviewer_ABC"],
                                        "content": content(summary="Review", rating="3: reject"),
                                    },
                                ]
                            },
                        }
                    ]
                },
            )

            report = calibrate_reviewer_reliability(concern_report(), snapshot_dir=root)

        self.assertEqual(report["summary"]["review_count"], 2)
        self.assertEqual(report["summary"]["paper_with_author_response_count"], 1)
        self.assertIn("claim_consensus_counts", report["summary"])
        self.assertIn("claim_rebuttal_resolution_counts", report["summary"])
        self.assertIn("claim_lifecycle_robustness_counts", report["summary"])
        self.assertEqual(report["papers"][0]["reviews"][0]["reviewer_signature_role"], "reviewer")

    def test_rebuttal_resolution_calibration_sample_and_merge(self):
        reviewer_report = calibrate_reviewer_reliability(concern_report())
        sample = build_rebuttal_resolution_calibration_sample(reviewer_report, sample_size=2, seed=1)
        item = sample["items"][0]
        client = FakeRebuttalLLM(
            {
                "labels": {
                    "rebuttal_response_label": "likely_resolved",
                    "rebuttal_effect_on_claim": "resolved_or_weakened",
                    "response_specificity": "specific",
                    "confidence": "high",
                    "training_use": "include",
                    "rationale": "The response directly says the missing ablation was added.",
                },
                "notes": "clear",
            }
        )

        label = label_rebuttal_resolution_item(item, llm_client=client, model="test-model")
        merged = merge_rebuttal_resolution_labels([item], [label])
        report = build_rebuttal_resolution_calibration_report(items=[item], labels=[label], merged=merged)

        self.assertEqual(client.calls[0]["schema_name"], "rebuttal_resolution_calibration_label")
        self.assertEqual(merged[0]["llm_rebuttal_response_label"], "likely_resolved")
        self.assertTrue(merged[0]["high_confidence_training_candidate"])
        self.assertEqual(report["high_confidence_count"], 1)

    def test_reviewer_calibration_backfills_llm_rebuttal_labels(self):
        label = {
            "task_id": "paper1:review1:0",
            "llm_label_id": "label1",
            "llm_rebuttal_response_label": "likely_resolved",
            "llm_rebuttal_effect_on_claim": "resolved_or_weakened",
            "llm_response_specificity": "specific",
            "llm_confidence": "high",
            "llm_training_use": "include",
            "llm_rationale": "The author response resolves the missing ablation concern.",
            "high_confidence_training_candidate": True,
        }

        report = calibrate_reviewer_reliability(concern_report(), rebuttal_labels=[label])
        review = report["papers"][0]["reviews"][0]
        claim = review["claims"][0]

        self.assertEqual(claim["rebuttal_resolution"]["llm_calibration"]["rebuttal_response_label"], "likely_resolved")
        self.assertEqual(review["llm_rebuttal_labeled_claim_count"], 1)
        self.assertLess(review["llm_calibrated_review_reliability_score"], review["review_reliability_score"])
        self.assertEqual(report["summary"]["claim_llm_rebuttal_response_counts"]["likely_resolved"], 1)
        self.assertIn(
            "author_response_likely_resolved_or_weakened_claim",
            claim["lifecycle_robustness"]["weakening_factors"],
        )

    def test_consensus_calibration_sample_merge_and_backfill(self):
        reviewer_report = calibrate_reviewer_reliability(concern_report())
        sample = build_consensus_calibration_sample(reviewer_report, sample_size=2, seed=1)
        item = sample["items"][0]
        client = FakeConsensusLLM(
            {
                "labels": {
                    "consensus_label": "same_concern",
                    "relation": "supports",
                    "confidence": "high",
                    "training_use": "include",
                    "rationale": "Both reviewer claims raise the same missing ablation concern.",
                },
                "notes": "clear",
            }
        )

        label = label_consensus_item(item, llm_client=client, model="test-model")
        merged = merge_consensus_labels([item], [label])
        calibration_report = build_consensus_calibration_report(items=[item], labels=[label], merged=merged)
        final_report = calibrate_reviewer_reliability(concern_report(), consensus_labels=merged)

        self.assertEqual(client.calls[0]["schema_name"], "inter_reviewer_consensus_calibration_label")
        self.assertEqual(merged[0]["llm_consensus_label"], "same_concern")
        self.assertEqual(calibration_report["high_confidence_count"], 1)
        labeled_claims = [
            claim
            for review in final_report["papers"][0]["reviews"]
            for claim in review["claims"]
            if claim["consensus"].get("llm_calibration")
        ]
        self.assertEqual(labeled_claims[0]["consensus"]["llm_calibration"]["consensus_label"], "same_concern")
        self.assertIn("claim_llm_consensus_response_counts", final_report["summary"])

    def test_lifecycle_robustness_uses_llm_consensus_and_rebuttal_labels(self):
        rebuttal_label = {
            "task_id": "paper1:review1:0",
            "llm_label_id": "rebuttal_label1",
            "llm_rebuttal_response_label": "not_addressed",
            "llm_rebuttal_effect_on_claim": "does_not_address",
            "llm_response_specificity": "none",
            "llm_confidence": "high",
            "llm_training_use": "include",
            "llm_rationale": "No specific response addresses the missing ablation.",
            "high_confidence_training_candidate": True,
        }
        consensus_label = {
            "task_id": "paper1:review1:0",
            "llm_label_id": "consensus_label1",
            "llm_consensus_label": "same_concern",
            "llm_consensus_relation": "supports",
            "llm_confidence": "high",
            "llm_training_use": "include",
            "llm_rationale": "Another reviewer raises the same missing ablation concern.",
            "high_confidence_training_candidate": True,
        }

        report = calibrate_reviewer_reliability(
            concern_report(),
            rebuttal_labels=[rebuttal_label],
            consensus_labels=[consensus_label],
        )
        review = report["papers"][0]["reviews"][0]
        robustness = review["claims"][0]["lifecycle_robustness"]

        self.assertEqual(robustness["source"], "llm_calibrated_when_available")
        self.assertEqual(robustness["signal_scores"]["consensus"], 1.0)
        self.assertEqual(robustness["signal_scores"]["rebuttal_robustness"], 0.85)
        self.assertIn("not_resolved_by_author_response", robustness["supporting_factors"])
        self.assertGreater(review["mean_lifecycle_robustness_score"], 0.7)


if __name__ == "__main__":
    unittest.main()

import unittest

from secondopinion.evidence_chain import (
    build_benchmark_validation_report,
    build_evidence_chain_benchmark,
    build_evidence_chain_benchmark_from_calibration,
    build_evidence_chain_demo,
    build_pseudo_expert_labels,
    build_pseudo_expert_report,
)


def sample_audit_result():
    return {
        "schema_version": "0.1",
        "audits": [
            {
                "audit_id": "audit1",
                "paper_id": "paper1",
                "paper_title": "Test Paper",
                "review_id": "review1",
                "rating_raw": "4: reject",
                "reviewer_confidence_raw": "3",
                "rqs_score": 60,
                "summary": "Review summary.",
                "claims": [
                    {
                        "claim_id": "claim1",
                        "claim_text": "The paper lacks ablation studies.",
                        "claim_type": "ablation",
                        "importance": "major",
                        "source_sentence": "The paper lacks ablation studies.",
                        "stance": "agree",
                        "support_score": 70,
                        "specificity_score": 80,
                        "rebuttal_guidance": {
                            "priority": "medium",
                            "strategy": "cite_existing_evidence",
                            "suggested_response": "Explain the ablation evidence.",
                            "evidence_to_cite": [],
                            "risks_to_avoid": [],
                        },
                        "evidence": [
                            {
                                "evidence_id": "ev1",
                                "source_type": "paper",
                                "section": "Experiment",
                                "text": "The paper reports ablations in Table 2.",
                                "score": 0.8,
                            },
                            {
                                "evidence_id": "ev2",
                                "source_type": "venue_guideline",
                                "title": "ICLR rubric",
                                "text": "Reviewers should assess empirical support.",
                                "score": 0.7,
                            },
                        ],
                    }
                ],
            }
        ],
    }


def sample_reviewer_calibration():
    return {
        "calibration_version": "reviewer-calibration-v0.1",
        "papers": [
            {
                "paper_id": "paper1",
                "reviews": [
                    {
                        "review_id": "review1",
                        "llm_calibrated_review_reliability_score": 0.76,
                        "mean_lifecycle_robustness_score": 0.82,
                        "claims": [
                            {
                                "claim_text": "The paper lacks ablation studies.",
                                "source_sentence": "The paper lacks ablation studies.",
                                "consensus": {
                                    "label": "strong",
                                    "score": 0.9,
                                    "matched_claim_text": "Another reviewer also asks for ablations.",
                                    "matched_review_id": "review2",
                                },
                                "rebuttal_resolution": {
                                    "label": "not_addressed",
                                    "score": 0.0,
                                    "matched_segment": "We thank the reviewer.",
                                },
                                "discussion_followup": {
                                    "label": "followed_up",
                                    "score": 0.6,
                                    "matched_segment": "The ablation concern remains.",
                                },
                                "meta_review_uptake": {
                                    "label": "survived",
                                    "score": 0.8,
                                    "matched_segment": "AC notes missing ablations.",
                                },
                                "lifecycle_robustness": {
                                    "score": 0.84,
                                    "label": "high",
                                    "signal_scores": {
                                        "grounding": 1.0,
                                        "specificity": 0.8,
                                        "consensus": 1.0,
                                        "rebuttal_robustness": 0.85,
                                        "discussion_followup": 0.7,
                                        "meta_review_uptake": 1.0,
                                    },
                                    "supporting_factors": ["taken_up_in_meta_review"],
                                },
                            }
                        ],
                    }
                ],
            }
        ],
    }


class EvidenceChainTests(unittest.TestCase):
    def test_demo_builder_preserves_claim_ids_and_scores(self):
        demo = build_evidence_chain_demo(
            sample_audit_result(),
            reviewer_calibration=sample_reviewer_calibration(),
            paper_id="paper1",
        )
        claim = demo["reviewers"][0]["claims"][0]

        self.assertEqual(claim["claim_id"], "claim1")
        self.assertEqual(claim["scores"]["grounding"], 1.0)
        self.assertEqual(claim["scores"]["consensus"], 1.0)
        self.assertEqual(claim["scores"]["lifecycle_robustness"], 0.84)
        self.assertEqual(demo["summary"]["high_priority_claim_count"], 1)

    def test_evidence_chain_contains_source_categories(self):
        demo = build_evidence_chain_demo(sample_audit_result(), reviewer_calibration=sample_reviewer_calibration())
        chain = demo["reviewers"][0]["claims"][0]["evidence_chain"]

        self.assertEqual(chain["manuscript"][0]["source_type"], "paper")
        self.assertEqual(chain["external"][0]["source_type"], "venue_guideline")
        self.assertEqual(chain["rebuttal"][0]["source_type"], "author_rebuttal")
        self.assertEqual(chain["meta_review"][0]["source_type"], "meta_review")
        self.assertEqual(chain["consensus"][0]["source_type"], "inter_reviewer_consensus")

    def test_rebuttal_priority_promotes_high_robustness(self):
        demo = build_evidence_chain_demo(sample_audit_result(), reviewer_calibration=sample_reviewer_calibration())
        guidance = demo["reviewers"][0]["claims"][0]["rebuttal_guidance"]

        self.assertEqual(guidance["priority"], "must")
        self.assertIn(guidance["strategy"], {"acknowledge_and_fix", "cite_existing_evidence"})

    def test_benchmark_packet_has_three_variants_and_report(self):
        benchmark = build_evidence_chain_benchmark(
            sample_audit_result(),
            reviewer_calibration=sample_reviewer_calibration(),
            paper_limit=1,
            claims_per_paper=1,
        )
        item = benchmark["items"][0]
        report = build_benchmark_validation_report(benchmark)

        self.assertEqual(set(item["variants"]), {"review_only", "review_manuscript", "full_evidence_chain"})
        self.assertEqual(report["summary"]["variants"]["full_evidence_chain"]["score_coverage"], 1.0)

    def test_calibration_benchmark_uses_reviewer_calibration_claims(self):
        benchmark = build_evidence_chain_benchmark_from_calibration(
            sample_reviewer_calibration(),
            normalized_dataset={
                "dataset": "sample",
                "papers": [{"paper_id": "paper1", "title": "Test Paper", "decision": "Reject"}],
            },
            paper_limit=1,
            claims_per_paper=1,
            sample_size=1,
        )
        item = benchmark["items"][0]

        self.assertEqual(benchmark["summary"]["paper_count"], 1)
        self.assertEqual(item["paper"]["title"], "Test Paper")
        self.assertEqual(item["variants"]["full_evidence_chain"]["scores"]["lifecycle_robustness"], 0.84)
        self.assertEqual(item["variants"]["full_evidence_chain"]["evidence_chain"]["meta_review"][0]["source_type"], "meta_review")

    def test_pseudo_expert_labels_and_report(self):
        demo = build_evidence_chain_demo(sample_audit_result(), reviewer_calibration=sample_reviewer_calibration())
        claim = demo["reviewers"][0]["claims"][0]
        task = {
            "task_id": "task1",
            "run_id": "run1",
            "task_type": "evidence_chain_quality",
            "paper_id": "paper1",
            "review_id": "review1",
            "claim_id": claim["claim_id"],
            "context": {
                "claim_text": claim["claim_text"],
                "source_sentence": claim["source_sentence"],
                "evidence_chain": claim["evidence_chain"],
            },
            "system_output": {
                "importance": claim["importance"],
                "scores": claim["scores"],
                "rebuttal_guidance": claim["rebuttal_guidance"],
                "system_judgment": claim["system_judgment"],
            },
            "provenance": {"annotation_task_version": "annotation-task-v0.1"},
        }

        labels = build_pseudo_expert_labels([task])
        report = build_pseudo_expert_report([task], labels)

        self.assertEqual(labels[0]["labels"]["claim_grounded"], "yes")
        self.assertEqual(labels[0]["labels"]["recommended_action"], "must_address")
        self.assertEqual(report["summary"]["label_count"], 1)
        self.assertIn("recommended_action", report["summary"]["field_match_rates"])


if __name__ == "__main__":
    unittest.main()

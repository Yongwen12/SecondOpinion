import unittest

from secondopinion.concern_survival import (
    build_concern_survival_calibration_sample,
    build_concern_survival_report,
    classify_decision,
    is_concern_claim,
    score_claim_survival,
    split_meta_review_segments,
    validate_paper_concern_survival,
)


class FakeLLMClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def complete_json(self, *, model, messages, schema_name, schema):
        self.calls.append({"model": model, "messages": messages, "schema_name": schema_name})
        return self.payload


def content(**values):
    return {key: {"value": value} for key, value in values.items()}


def reply(note_id, invitations, signatures, content_payload):
    return {
        "id": note_id,
        "forum": "paper1",
        "invitations": invitations,
        "signatures": signatures,
        "content": content_payload,
        "cdate": 1000,
        "tcdate": 1000,
        "mdate": 1000,
        "tmdate": 1000,
    }


class ConcernSurvivalTests(unittest.TestCase):
    def test_score_claim_survival_matches_meta_review_concern(self):
        meta_segments = split_meta_review_segments(
            "The main remaining concern is the lack of ablation studies and weak baselines."
        )
        claim = {
            "claim_text": "The paper lacks ablation studies.",
            "claim_type": "ablation",
            "importance": "major",
            "source_field": "weaknesses",
            "source_sentence": "The paper lacks ablation studies.",
        }

        result = score_claim_survival(
            claim,
            meta_segments,
            survived_threshold=0.34,
            partial_threshold=0.2,
        )

        self.assertEqual(result["survival_label"], "survived")
        self.assertIn("ablation", result["matched_terms"])

    def test_is_concern_claim_filters_positive_strengths(self):
        self.assertTrue(is_concern_claim({"source_field": "weaknesses", "claim_text": "The paper lacks ablations."}))
        self.assertTrue(is_concern_claim({"source_field": "questions", "claim_text": "Could the authors clarify?"}))
        self.assertFalse(is_concern_claim({"source_field": "strengths", "claim_text": "The experiments are clear."}))
        self.assertFalse(is_concern_claim({"source_field": "summary", "claim_text": "The paper proposes a method."}))

    def test_validate_paper_concern_survival_extracts_claims_and_scores_them(self):
        paper = {
            "id": "paper1",
            "forum": "paper1",
            "content": content(title="Test Paper"),
            "details": {
                "replies": [
                    reply(
                        "review1",
                        ["ICLR.cc/2024/Conference/Submission1/-/Official_Review"],
                        ["ICLR.cc/2024/Conference/Submission1/Reviewer_abc"],
                        content(
                            weaknesses="The paper lacks ablation studies.",
                            rating="5: marginally below",
                            confidence="3: confident",
                        ),
                    ),
                    reply(
                        "meta1",
                        ["ICLR.cc/2024/Conference/Submission1/-/Meta_Review"],
                        ["ICLR.cc/2024/Conference/Submission1/Area_Chair_xyz"],
                        content(metareview="The lack of ablation studies remains a key concern."),
                    ),
                    reply(
                        "decision1",
                        ["ICLR.cc/2024/Conference/Submission1/-/Decision"],
                        ["ICLR.cc/2024/Conference/Program_Chairs"],
                        content(decision="Reject"),
                    ),
                ]
            },
        }
        client = FakeLLMClient(
            {
                "claims": [
                    {
                        "claim_text": "The paper lacks ablation studies.",
                        "claim_type": "ablation",
                        "importance": "major",
                        "source_field": "weaknesses",
                        "source_sentence": "The paper lacks ablation studies.",
                        "rationale": "Missing ablations are auditable.",
                    }
                ]
            }
        )

        result = validate_paper_concern_survival(
            paper,
            llm_client=client,
            model="test-model",
            max_claims=8,
            review_limit=None,
            survived_threshold=0.34,
            partial_threshold=0.2,
        )

        self.assertEqual(result["claim_count"], 1)
        self.assertEqual(result["decision"], "Reject")
        self.assertEqual(result["decision_label"], "reject")
        self.assertEqual(result["survival_counts"], {"survived": 1})
        self.assertEqual(result["reviews"][0]["claims"][0]["survival_label"], "survived")
        self.assertEqual(client.calls[0]["model"], "test-model")

    def test_build_concern_survival_report_summarizes_claim_counts(self):
        paper = {
            "has_meta_review": True,
            "claim_count": 2,
            "review_count_evaluated": 1,
            "extraction_error_count": 0,
            "reviews": [
                {
                    "review_id": "review1",
                    "claims": [
                        {"survival_label": "survived", "claim_type": "ablation", "importance": "major"},
                        {"survival_label": "not_found", "claim_type": "clarity", "importance": "minor"},
                    ],
                }
            ],
        }

        report = build_concern_survival_report(
            [paper],
            snapshot={"snapshot_id": "snap"},
            model="test-model",
            thresholds={"survived": 0.34, "partial": 0.2},
        )

        self.assertEqual(report["summary"]["claim_count"], 2)
        self.assertEqual(report["summary"]["strict_survival_rate"], 0.5)
        self.assertEqual(report["summary"]["by_claim_type"]["ablation"]["loose_survival_rate"], 1.0)

    def test_classify_decision(self):
        self.assertEqual(classify_decision("Accept: poster"), "accept")
        self.assertEqual(classify_decision("Reject"), "reject")
        self.assertEqual(classify_decision("Desk rejected"), "reject")
        self.assertEqual(classify_decision("Withdrawn"), "other")

    def test_build_calibration_sample_balances_auto_labels(self):
        paper = {
            "paper_id": "paper1",
            "forum_id": "paper1",
            "title": "Test Paper",
            "decision": "Accept",
            "decision_label": "accept",
            "meta_review_text": "The meta-review mentions ablations.",
            "has_meta_review": True,
            "claim_count": 3,
            "review_count_evaluated": 1,
            "extraction_error_count": 0,
            "reviews": [
                {
                    "review_id": "review1",
                    "rating_raw": "6",
                    "rating_normalized": 6,
                    "confidence_raw": "3",
                    "confidence_normalized": 3,
                    "claims": [
                        {
                            "survival_label": "survived",
                            "survival_score": 0.5,
                            "claim_text": "The paper lacks ablations.",
                            "claim_type": "ablation",
                            "importance": "major",
                            "source_field": "weaknesses",
                            "source_sentence": "The paper lacks ablations.",
                            "matched_meta_segment": "The meta-review mentions ablations.",
                            "matched_terms": ["ablation"],
                        },
                        {
                            "survival_label": "partial",
                            "survival_score": 0.25,
                            "claim_text": "The baselines are weak.",
                            "claim_type": "baseline",
                            "importance": "major",
                            "source_field": "weaknesses",
                            "source_sentence": "The baselines are weak.",
                            "matched_meta_segment": "The meta-review mentions evaluation.",
                        },
                        {
                            "survival_label": "not_found",
                            "survival_score": 0.0,
                            "claim_text": "The writing is unclear.",
                            "claim_type": "writing",
                            "importance": "minor",
                            "source_field": "weaknesses",
                            "source_sentence": "The writing is unclear.",
                            "matched_meta_segment": "",
                        },
                    ],
                }
            ],
        }
        report = build_concern_survival_report(
            [paper],
            snapshot={"snapshot_id": "snap"},
            model="test-model",
            thresholds={"survived": 0.34, "partial": 0.2},
        )

        sample = build_concern_survival_calibration_sample(report, sample_size=3, seed=1)

        self.assertEqual(sample["sample_size"], 3)
        self.assertEqual(sample["summary"]["sample_auto_label_counts"]["survived"], 1)
        self.assertEqual(sample["summary"]["sample_auto_label_counts"]["partial"], 1)
        self.assertEqual(sample["summary"]["sample_auto_label_counts"]["not_found"], 1)
        self.assertEqual(sample["items"][0]["human_survival_label"], "")
        self.assertIn("meta_review_text", sample["items"][0])


if __name__ == "__main__":
    unittest.main()

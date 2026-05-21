import json
import unittest
from pathlib import Path

from secondopinion.audit import audit_dataset
from secondopinion.claim_extraction import extract_claims


class SampleClaimClient:
    def complete_json(self, *, model, messages, schema_name, schema):
        prompt = messages[-1]["content"]
        if "lacks any ablation study" in prompt:
            return {
                "claims": [
                    {
                        "claim_text": "The paper lacks any ablation study.",
                        "claim_type": "ablation",
                        "importance": "major",
                        "source_field": "weaknesses",
                        "source_sentence": "The paper lacks any ablation study and does not compare to standard baselines.",
                        "rationale": "The reviewer criticizes missing ablations.",
                    }
                ]
            }
        if "lacks ablation studies" in prompt:
            return {
                "claims": [
                    {
                        "claim_text": "The paper lacks ablation studies.",
                        "claim_type": "ablation",
                        "importance": "major",
                        "source_field": "weaknesses",
                        "source_sentence": "The paper lacks ablation studies.",
                        "rationale": "The reviewer criticizes missing ablations.",
                    }
                ]
            }
        return {
            "claims": [
                {
                    "claim_text": "The paper should explain the calibration module more clearly.",
                    "claim_type": "clarity",
                    "importance": "medium",
                    "source_field": "weaknesses",
                    "source_sentence": "The paper should explain the calibration module more clearly and include a broader discussion of failure cases.",
                    "rationale": "The reviewer asks for a clearer explanation.",
                }
            ]
        }


class SampleJudgeClient:
    def complete_json(self, *, model, messages, schema_name, schema):
        self.model = model
        self.schema_name = schema_name
        return {
            "review_point_type": "comment",
            "stance": "strongly_agree",
            "support_score": 92,
            "answer_coverage_score": 0,
            "question_value_score": 0,
            "verdict": "supported",
            "confidence": "high",
            "evidence_support": 3,
            "factual_alignment": 3,
            "severity_calibration": 4,
            "second_opinion_take": (
                "SecondOpinion finds this review point well supported. "
                "The manuscript explains the calibration module."
            ),
            "quoted_manuscript_evidence": "The manuscript explains the calibration module.",
            "reasoning_summary": "The retrieved evidence supports the clarification request.",
            "professionalism_score": 90,
            "specificity_score": 80,
            "helpfulness_score": 85,
            "fairness_score": 88,
            "rationale": "The retrieved evidence supports the reviewer's clarification request.",
            "evidence_assessments": [
                {
                    "evidence_id": "claim_ignored_ev1",
                    "verdict": "supporting_candidate",
                    "confidence": "high",
                }
            ],
        }


class FailingJudgeClient:
    def complete_json(self, *, model, messages, schema_name, schema):
        raise RuntimeError("judge unavailable")


class AuditTests(unittest.TestCase):
    def test_extract_claims_from_weaknesses(self):
        review = {"weaknesses": "The paper lacks ablation studies. The writing is fine."}
        claims = extract_claims(
            review,
            llm_client=SampleClaimClient(),
        )
        self.assertEqual(claims[0]["claim_type"], "ablation")
        self.assertIn("lacks ablation", claims[0]["claim_text"])
        self.assertEqual(claims[0]["source_field"], "weaknesses")

    def test_demo_flags_possible_contradiction_claim(self):
        dataset = json.loads(Path("examples/sample_normalized_dataset.json").read_text())
        result = audit_dataset(dataset, claim_llm_client=SampleClaimClient(), claim_model="test-model")
        first = result["audits"][0]
        self.assertEqual(result["claim_extraction_version"], "claim-extraction-llm-v0.1")
        self.assertEqual(result["claim_model"], "test-model")
        self.assertEqual(result["retrieval_version"], "section-aware-bm25-v0.2")
        self.assertIn("possibly-contradicted-by-paper", first["issue_flags"])
        self.assertEqual(first["claims"][0]["verdict"], "possibly_contradicted")
        self.assertEqual(first["claims"][0]["source_field"], "weaknesses")
        self.assertEqual(first["decision"], "Reject")
        self.assertEqual(first["rating_raw"], "3: reject")
        self.assertEqual(first["rating_normalized"], 3.0)
        self.assertEqual(first["reviewer_confidence_raw"], "4: confident")
        self.assertGreater(first["audit_count"] if "audit_count" in first else result["audit_count"], 0)

    def test_llm_judge_can_override_rule_verdict(self):
        dataset = json.loads(Path("examples/sample_normalized_dataset.json").read_text())
        result = audit_dataset(
            dataset,
            claim_llm_client=SampleClaimClient(),
            judge_llm_client=SampleJudgeClient(),
            claim_model="claim-test",
            judge_model="judge-test",
            use_llm_judge=True,
        )
        first_claim = result["audits"][0]["claims"][0]
        self.assertEqual(result["model_version"], "review-point-judge-v0.2")
        self.assertEqual(result["judge_model"], "judge-test")
        self.assertEqual(first_claim["verdict"], "supported")
        self.assertEqual(first_claim["audit_confidence"], "high")
        self.assertEqual(first_claim["judge_version"], "review-point-judge-v0.2")
        self.assertEqual(first_claim["review_point_type"], "comment")
        self.assertEqual(first_claim["stance"], "strongly_agree")
        self.assertEqual(first_claim["support_score"], 92)
        self.assertEqual(first_claim["answer_coverage_score"], 0)
        self.assertEqual(first_claim["question_value_score"], 0)
        self.assertIn("SecondOpinion finds", first_claim["second_opinion_take"])
        self.assertIn("retrieved evidence supports", first_claim["judge_rationale"])
        self.assertNotIn("possibly-contradicted-by-paper", first_claim["issue_flags"])

    def test_llm_judge_failure_falls_back_to_rule_verdict(self):
        dataset = json.loads(Path("examples/sample_normalized_dataset.json").read_text())
        result = audit_dataset(
            dataset,
            claim_llm_client=SampleClaimClient(),
            judge_llm_client=FailingJudgeClient(),
            claim_model="claim-test",
            judge_model="judge-test",
            use_llm_judge=True,
        )
        first_claim = result["audits"][0]["claims"][0]
        self.assertEqual(first_claim["verdict"], "possibly_contradicted")
        self.assertIn("llm-judge-failed", first_claim["issue_flags"])
        self.assertEqual(first_claim["judge_version"], "review-point-judge-v0.2+fallback")


if __name__ == "__main__":
    unittest.main()

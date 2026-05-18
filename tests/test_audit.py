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
        self.assertGreater(first["audit_count"] if "audit_count" in first else result["audit_count"], 0)


if __name__ == "__main__":
    unittest.main()

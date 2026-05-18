import json
import unittest
from pathlib import Path

from secondopinion.audit import audit_dataset, extract_claims


class AuditTests(unittest.TestCase):
    def test_extract_claims_from_weaknesses(self):
        review = {"weaknesses": "The paper lacks ablation studies. The writing is fine."}
        claims = extract_claims(review)
        self.assertEqual(claims[0]["claim_type"], "ablation")
        self.assertIn("lacks ablation", claims[0]["claim_text"])
        self.assertEqual(claims[0]["source_field"], "weaknesses")

    def test_demo_flags_possible_contradiction_claim(self):
        dataset = json.loads(Path("examples/sample_normalized_dataset.json").read_text())
        result = audit_dataset(dataset)
        first = result["audits"][0]
        self.assertEqual(result["claim_extraction_version"], "claim-extraction-rule-v0.2")
        self.assertEqual(result["retrieval_version"], "section-aware-bm25-v0.2")
        self.assertIn("possibly-contradicted-by-paper", first["issue_flags"])
        self.assertEqual(first["claims"][0]["verdict"], "possibly_contradicted")
        self.assertEqual(first["claims"][0]["source_field"], "weaknesses")
        self.assertGreater(first["audit_count"] if "audit_count" in first else result["audit_count"], 0)


if __name__ == "__main__":
    unittest.main()

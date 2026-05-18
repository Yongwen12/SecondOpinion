import unittest

from secondopinion.claim_extraction import CLAIM_EXTRACTION_VERSION, extract_claims


class ClaimExtractionTests(unittest.TestCase):
    def test_extracts_compound_weaknesses_as_separate_claims(self):
        review = {
            "weaknesses": (
                "The paper lacks any ablation study and does not compare to standard baselines. "
                "The writing is fine."
            ),
            "questions": "Could the authors clarify the training setup?",
        }
        claims = extract_claims(review)
        self.assertEqual([claim["claim_type"] for claim in claims], ["ablation", "baseline", "clarity"])
        self.assertEqual(claims[0]["source_field"], "weaknesses")
        self.assertEqual(claims[0]["source_sentence_index"], 0)
        self.assertEqual(claims[0]["source_sentence"], "The paper lacks any ablation study and does not compare to standard baselines.")
        self.assertEqual(claims[0]["extraction_version"], CLAIM_EXTRACTION_VERSION)

    def test_ignores_positive_non_auditable_sentences(self):
        review = {"weaknesses": "The writing is fine. The topic is relevant."}
        self.assertEqual(extract_claims(review), [])

    def test_falls_back_to_review_text_when_structured_fields_missing(self):
        review = {
            "review_text": "Summary: Good topic. Weaknesses: The method is unclear and lacks evaluation details."
        }
        claims = extract_claims(review)
        self.assertEqual(claims[0]["source_field"], "review_text")
        self.assertEqual(claims[0]["claim_type"], "methodology")

    def test_action_fragments_are_normalized(self):
        review = {"weaknesses": "The paper should explain calibration and include broader failure analysis."}
        claims = extract_claims(review)
        self.assertEqual(claims[1]["claim_text"], "The paper should include broader failure analysis.")


if __name__ == "__main__":
    unittest.main()

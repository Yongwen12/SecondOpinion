import unittest

from secondopinion.grounding_validation import (
    validate_final_claim_grounding,
    validate_grounding_for_dataset,
)


class FakeLLMClient:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []

    def complete_json(self, *, model, messages, schema_name, schema):
        self.calls.append({"model": model, "messages": messages, "schema_name": schema_name, "schema": schema})
        return self.payloads.pop(0)


class GroundingValidationTests(unittest.TestCase):
    def test_validate_final_claim_grounding_checks_review_source_sentence(self):
        review = {
            "weaknesses": "The paper lacks ablation studies. The baseline comparison is incomplete.",
        }
        claim = {
            "claim_text": "The paper lacks ablation studies.",
            "claim_type": "ablation",
            "importance": "major",
            "source_field": "weaknesses",
            "source_sentence": "The paper lacks ablation studies.",
            "source_sentence_index": 0,
        }

        result = validate_final_claim_grounding(review, claim, claim_index=0)

        self.assertTrue(result["grounding_pass"])
        self.assertTrue(result["exact_match"])
        self.assertTrue(result["normalized_match"])
        self.assertTrue(result["source_span_found"])
        self.assertEqual(result["source_char_start"], 0)
        self.assertEqual(result["source_char_end"], len("The paper lacks ablation studies."))
        self.assertEqual(result["source_paragraph_index"], 0)
        self.assertTrue(result["source_sentence_index_found"])
        self.assertEqual(result["failure_reasons"], [])

    def test_validate_grounding_for_dataset_reports_raw_failures_and_final_passes(self):
        dataset = {
            "dataset": "test",
            "papers": [
                {
                    "paper_id": "paper-1",
                    "title": "Ablation Paper",
                    "reviews": [
                        {
                            "review_id": "review-1",
                            "weaknesses": "The paper lacks ablation studies.",
                        }
                    ],
                }
            ],
        }
        client = FakeLLMClient(
            [
                {
                    "claims": [
                        {
                            "claim_text": "The paper lacks ablation studies.",
                            "claim_type": "ablation",
                            "importance": "major",
                            "source_field": "weaknesses",
                            "source_sentence": "The paper lacks ablation studies.",
                            "rationale": "The reviewer criticizes missing ablations.",
                        },
                        {
                            "claim_text": "The paper omits a user study.",
                            "claim_type": "experiment",
                            "importance": "major",
                            "source_field": "weaknesses",
                            "source_sentence": "The paper omits a user study.",
                            "rationale": "This fabricated source should fail grounding.",
                        },
                    ]
                }
            ]
        )

        report = validate_grounding_for_dataset(
            dataset,
            llm_client=client,
            model="test-model",
            review_limit=1,
            max_claims=8,
        )

        stats = report["stats"]
        self.assertEqual(report["status"], "pass")
        self.assertEqual(stats["review_count"], 1)
        self.assertEqual(stats["raw_candidate_count"], 2)
        self.assertEqual(stats["raw_grounding_fail_count"], 1)
        self.assertEqual(stats["final_claim_count"], 1)
        self.assertEqual(stats["final_grounding_pass_rate"], 1.0)
        self.assertEqual(stats["source_span_found_rate"], 1.0)
        self.assertEqual(stats["raw_failure_reason_counts"], {"source_sentence_not_found": 1})
        self.assertEqual(len(report["examples"]["raw_grounding_failures"]), 1)
        self.assertEqual(client.calls[0]["model"], "test-model")

    def test_validate_grounding_for_dataset_records_extraction_errors(self):
        dataset = {
            "papers": [
                {
                    "paper_id": "paper-1",
                    "reviews": [{"review_id": "review-1", "weaknesses": "The paper lacks ablations."}],
                }
            ],
        }

        class BrokenClient:
            def complete_json(self, *, model, messages, schema_name, schema):
                raise RuntimeError("temporary failure")

        report = validate_grounding_for_dataset(dataset, llm_client=BrokenClient(), review_limit=1)

        self.assertEqual(report["status"], "needs_attention")
        self.assertEqual(report["stats"]["review_error_count"], 1)
        self.assertIn("temporary failure", report["reviews"][0]["error"])


if __name__ == "__main__":
    unittest.main()

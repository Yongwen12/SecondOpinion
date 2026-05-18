import unittest

from secondopinion.claim_extraction import (
    CLAIM_EXTRACTION_VERSION,
    claim_extraction_schema,
    extract_claims,
    validate_claim_payload,
)


class FakeLLMClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def complete_json(self, *, model, messages, schema_name, schema):
        self.calls.append({"model": model, "messages": messages, "schema_name": schema_name, "schema": schema})
        return self.payload


class ClaimExtractionTests(unittest.TestCase):
    def test_extract_claims_uses_llm_and_validates_source_sentence(self):
        review = {
            "weaknesses": (
                "The paper lacks any ablation study and does not compare to standard baselines. "
                "The writing is fine."
            )
        }
        client = FakeLLMClient(
            {
                "claims": [
                    {
                        "claim_text": "The paper lacks any ablation study.",
                        "claim_type": "ablation",
                        "importance": "major",
                        "source_field": "weaknesses",
                        "source_sentence": "The paper lacks any ablation study and does not compare to standard baselines.",
                        "rationale": "The reviewer criticizes missing ablations.",
                    },
                    {
                        "claim_text": "The paper omits a user study.",
                        "claim_type": "experiment",
                        "importance": "major",
                        "source_field": "weaknesses",
                        "source_sentence": "The paper omits a user study.",
                        "rationale": "This fabricated sentence should be rejected.",
                    },
                ]
            }
        )
        claims = extract_claims(review, llm_client=client, model="test-model")
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0]["claim_type"], "ablation")
        self.assertEqual(claims[0]["source_sentence_index"], 0)
        self.assertEqual(claims[0]["extraction_version"], CLAIM_EXTRACTION_VERSION)
        self.assertEqual(client.calls[0]["model"], "test-model")

    def test_no_rule_fallback_when_llm_returns_no_claims(self):
        review = {"weaknesses": "The paper lacks ablation studies."}
        claims = extract_claims(review, llm_client=FakeLLMClient({"claims": []}))
        self.assertEqual(claims, [])

    def test_validate_claim_payload_deduplicates(self):
        review = {"questions": "Could the authors clarify the training setup?"}
        payload = {
            "claims": [
                {
                    "claim_text": "The authors should clarify the training setup.",
                    "claim_type": "clarity",
                    "importance": "question",
                    "source_field": "questions",
                    "source_sentence": "Could the authors clarify the training setup?",
                    "rationale": "The reviewer asks for clarification.",
                },
                {
                    "claim_text": "The authors should clarify the training setup.",
                    "claim_type": "clarity",
                    "importance": "question",
                    "source_field": "questions",
                    "source_sentence": "Could the authors clarify the training setup?",
                    "rationale": "Duplicate.",
                },
            ]
        }
        claims = validate_claim_payload(payload, review, max_claims=8)
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0]["source_field"], "questions")

    def test_schema_uses_strict_structured_shape(self):
        schema = claim_extraction_schema(max_claims=4)
        self.assertFalse(schema["additionalProperties"])
        self.assertFalse(schema["properties"]["claims"]["items"]["additionalProperties"])


if __name__ == "__main__":
    unittest.main()

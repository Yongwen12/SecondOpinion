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
        self.assertIn("Task boundary", client.calls[0]["messages"][0]["content"])
        self.assertIn("Decision procedure", client.calls[0]["messages"][1]["content"])

    def test_no_rule_fallback_when_llm_returns_no_claims(self):
        review = {"weaknesses": "The paper lacks ablation studies."}
        claims = extract_claims(review, llm_client=FakeLLMClient({"claims": []}))
        self.assertEqual(claims, [])

    def test_validate_claim_payload_deduplicates(self):
        review = {
            "questions": "Could the authors clarify the training setup?",
            "review_text": (
                "Questions: Could the authors clarify the training setup? "
                "Weaknesses: The paper should explain the calibration module more clearly."
            ),
            "weaknesses": (
                "The paper should explain the calibration module more clearly. "
                "The calibration module needs clearer explanation. "
                "Include a broader discussion of failure cases. "
                "There is a need for a broader discussion of failure cases. "
                "The calibration module needs clearer explanation and a broader discussion of failure cases."
            ),
        }
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
                {
                    "claim_text": "The authors should clarify the training setup.",
                    "claim_type": "clarity",
                    "importance": "question",
                    "source_field": "review_text",
                    "source_sentence": "Questions: Could the authors clarify the training setup?",
                    "rationale": "Same point repeated in review text.",
                },
                {
                    "claim_text": "The calibration module needs clearer explanation and a broader discussion of failure cases.",
                    "claim_type": "clarity",
                    "importance": "major",
                    "source_field": "weaknesses",
                    "source_sentence": "The calibration module needs clearer explanation and a broader discussion of failure cases.",
                    "rationale": "Composite duplicate of earlier points.",
                },
                {
                    "claim_text": "There is a request to explain calibration module more clearly and discuss failure cases; combine two related critiques into separate items.",
                    "claim_type": "clarity",
                    "importance": "medium",
                    "source_field": "review_text",
                    "source_sentence": "Weaknesses: The paper should explain the calibration module more clearly.",
                    "rationale": "Source sentence contains two critiques; split into separate auditable points.",
                },
                {
                    "claim_text": "The paper should explain the calibration module more clearly.",
                    "claim_type": "clarity",
                    "importance": "major",
                    "source_field": "weaknesses",
                    "source_sentence": "The paper should explain the calibration module more clearly.",
                    "rationale": "Clarification request.",
                },
                {
                    "claim_text": "The calibration module needs clearer explanation.",
                    "claim_type": "clarity",
                    "importance": "major",
                    "source_field": "review_text",
                    "source_sentence": "Weaknesses: The paper should explain the calibration module more clearly.",
                    "rationale": "Near duplicate clarification request.",
                },
                {
                    "claim_text": "Include a broader discussion of failure cases.",
                    "claim_type": "general",
                    "importance": "major",
                    "source_field": "weaknesses",
                    "source_sentence": "Include a broader discussion of failure cases.",
                    "rationale": "Failure analysis request.",
                },
                {
                    "claim_text": "There is a need for a broader discussion of failure cases.",
                    "claim_type": "general",
                    "importance": "major",
                    "source_field": "weaknesses",
                    "source_sentence": "There is a need for a broader discussion of failure cases.",
                    "rationale": "Near duplicate failure analysis request.",
                },
            ]
        }
        claims = validate_claim_payload(payload, review, max_claims=8)
        self.assertEqual(
            [claim["claim_text"] for claim in claims],
            [
                "The authors should clarify the training setup.",
                "The paper should explain the calibration module more clearly.",
                "Include a broader discussion of failure cases.",
            ],
        )

    def test_validate_claim_payload_drops_subsumed_points(self):
        review = {
            "weaknesses": (
                "The authors should clarify the training setup and report the impact of each module. "
                "The authors should clarify the training setup."
            )
        }
        payload = {
            "claims": [
                {
                    "claim_text": "The authors should clarify the training setup and report the impact of each module.",
                    "claim_type": "methodology",
                    "importance": "major",
                    "source_field": "weaknesses",
                    "source_sentence": "The authors should clarify the training setup and report the impact of each module.",
                    "rationale": "Broader actionable request.",
                },
                {
                    "claim_text": "The authors should clarify the training setup.",
                    "claim_type": "clarity",
                    "importance": "major",
                    "source_field": "weaknesses",
                    "source_sentence": "The authors should clarify the training setup.",
                    "rationale": "Subsumed by the broader request.",
                },
            ]
        }
        claims = validate_claim_payload(payload, review, max_claims=8)
        self.assertEqual(
            [claim["claim_text"] for claim in claims],
            ["The authors should clarify the training setup and report the impact of each module."],
        )

    def test_validate_claim_payload_deduplicates_absence_paraphrases(self):
        review = {
            "review_text": (
                "Weaknesses: The paper lacks any ablation study and does not compare to standard baselines. "
                "The authors should clarify the training setup."
            )
        }
        payload = {
            "claims": [
                {
                    "claim_text": "The paper lacks any ablation study and does not compare to standard baselines.",
                    "claim_type": "baseline",
                    "importance": "major",
                    "source_field": "review_text",
                    "source_sentence": "Weaknesses: The paper lacks any ablation study and does not compare to standard baselines.",
                    "rationale": "Missing ablation and baselines.",
                },
                {
                    "claim_text": "The review notes that there is no ablation and no standard baselines, which is a limitation to be addressed.",
                    "claim_type": "baseline",
                    "importance": "major",
                    "source_field": "review_text",
                    "source_sentence": "Weaknesses: The paper lacks any ablation study and does not compare to standard baselines.",
                    "rationale": "Paraphrase of the same absence claim.",
                },
            ]
        }
        claims = validate_claim_payload(payload, review, max_claims=8)
        self.assertEqual(
            [claim["claim_text"] for claim in claims],
            ["The paper lacks any ablation study and does not compare to standard baselines."],
        )

    def test_validate_claim_payload_repairs_meta_artifact_from_source_sentence(self):
        review = {
            "review_text": (
                "Weaknesses: The paper should explain the calibration module more clearly "
                "and include a broader discussion of failure cases."
            )
        }
        payload = {
            "claims": [
                {
                    "claim_text": "There is a request to explain calibration module more clearly and discuss failure cases; combine two related critiques into separate items.",
                    "claim_type": "clarity",
                    "importance": "medium",
                    "source_field": "review_text",
                    "source_sentence": (
                        "Weaknesses: The paper should explain the calibration module more clearly "
                        "and include a broader discussion of failure cases."
                    ),
                    "rationale": "Meta extraction artifact.",
                }
            ]
        }
        claims = validate_claim_payload(payload, review, max_claims=8)
        self.assertEqual(
            [claim["claim_text"] for claim in claims],
            ["The paper should explain the calibration module more clearly and include a broader discussion of failure cases."],
        )

    def test_validate_claim_payload_filters_rating_and_confidence_meta_points(self):
        review = {
            "review_text": (
                "Summary: The paper proposes a retrieval method. Strengths: The topic is relevant. "
                "Weaknesses: The paper lacks any ablation study. Rating: 3: reject. Confidence: 4."
            )
        }
        payload = {
            "claims": [
                {
                    "claim_text": "Rate or justify the rejection status in the review text",
                    "claim_type": "tone",
                    "importance": "tone-only",
                    "source_field": "review_text",
                    "source_sentence": review["review_text"],
                    "rationale": "Contains explicit rejection judgment and rating.",
                },
                {
                    "claim_text": "Rating of 3: reject describes the reviewer decision",
                    "claim_type": "tone",
                    "importance": "tone-only",
                    "source_field": "review_text",
                    "source_sentence": review["review_text"],
                    "rationale": "Contains explicit rating and decision.",
                },
                {
                    "claim_text": "The reviewer confidence is not a technical claim and thus not included.",
                    "claim_type": "tone",
                    "importance": "tone-only",
                    "source_field": "review_text",
                    "source_sentence": review["review_text"],
                    "rationale": "Mentions confidence.",
                },
            ]
        }
        self.assertEqual(validate_claim_payload(payload, review, max_claims=8), [])

    def test_validate_claim_payload_strips_inferred_parenthetical(self):
        review = {"weaknesses": "The paper should explain the calibration module more clearly."}
        payload = {
            "claims": [
                {
                    "claim_text": "The calibration module needs clearer explanation (implied need for better documentation in methods).",
                    "claim_type": "clarity",
                    "importance": "major",
                    "source_field": "weaknesses",
                    "source_sentence": "The paper should explain the calibration module more clearly.",
                    "rationale": "Clarification request.",
                }
            ]
        }
        claims = validate_claim_payload(payload, review, max_claims=8)
        self.assertEqual([claim["claim_text"] for claim in claims], ["The calibration module needs clearer explanation"])

    def test_validate_claim_payload_filters_neutral_summary_and_praise(self):
        review = {
            "summary": (
                "The paper proposes a graph neural network for citation prediction. "
                "The paper studies black-box optimization."
            ),
            "strengths": (
                "The method is elegant and well written. "
                "The method could be useful for practitioners. "
                "The method is elegant, but the experiments are limited to one dataset."
            ),
            "weaknesses": "The writing is fine. The paper lacks ablation studies.",
            "questions": "Could the authors clarify the training setup?",
        }
        payload = {
            "claims": [
                {
                    "claim_text": "The paper proposes a graph neural network for citation prediction.",
                    "claim_type": "general",
                    "importance": "medium",
                    "source_field": "summary",
                    "source_sentence": "The paper proposes a graph neural network for citation prediction.",
                    "rationale": "Neutral summary should not be audited.",
                },
                {
                    "claim_text": "The paper studies black-box optimization.",
                    "claim_type": "general",
                    "importance": "medium",
                    "source_field": "summary",
                    "source_sentence": "The paper studies black-box optimization.",
                    "rationale": "The substring in black-box should not count as a lack cue.",
                },
                {
                    "claim_text": "The method is elegant and well written.",
                    "claim_type": "general",
                    "importance": "minor",
                    "source_field": "strengths",
                    "source_sentence": "The method is elegant and well written.",
                    "rationale": "Pure praise should not be audited.",
                },
                {
                    "claim_text": "The method could be useful for practitioners.",
                    "claim_type": "general",
                    "importance": "minor",
                    "source_field": "strengths",
                    "source_sentence": "The method could be useful for practitioners.",
                    "rationale": "Could by itself should not make praise actionable.",
                },
                {
                    "claim_text": "The experiments are limited to one dataset.",
                    "claim_type": "experiment",
                    "importance": "medium",
                    "source_field": "strengths",
                    "source_sentence": "The method is elegant, but the experiments are limited to one dataset.",
                    "rationale": "The sentence contains a limitation despite appearing in strengths.",
                },
                {
                    "claim_text": "The writing is fine.",
                    "claim_type": "writing",
                    "importance": "minor",
                    "source_field": "weaknesses",
                    "source_sentence": "The writing is fine.",
                    "rationale": "Praise-only text should be filtered even from weaknesses.",
                },
                {
                    "claim_text": "The paper lacks ablation studies.",
                    "claim_type": "ablation",
                    "importance": "major",
                    "source_field": "weaknesses",
                    "source_sentence": "The paper lacks ablation studies.",
                    "rationale": "The reviewer criticizes missing ablations.",
                },
                {
                    "claim_text": "The authors should clarify the training setup.",
                    "claim_type": "clarity",
                    "importance": "question",
                    "source_field": "questions",
                    "source_sentence": "Could the authors clarify the training setup?",
                    "rationale": "The reviewer asks a clarification question.",
                },
            ]
        }
        claims = validate_claim_payload(payload, review, max_claims=8)
        self.assertEqual(
            [claim["claim_text"] for claim in claims],
            [
                "The experiments are limited to one dataset.",
                "The paper lacks ablation studies.",
                "The authors should clarify the training setup.",
            ],
        )

    def test_schema_uses_strict_structured_shape(self):
        schema = claim_extraction_schema(max_claims=4)
        self.assertFalse(schema["additionalProperties"])
        self.assertFalse(schema["properties"]["claims"]["items"]["additionalProperties"])


if __name__ == "__main__":
    unittest.main()

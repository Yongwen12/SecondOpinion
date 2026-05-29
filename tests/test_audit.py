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


class TwoClaimClient:
    def complete_json(self, *, model, messages, schema_name, schema):
        return {
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
                    "claim_text": "The authors should clarify the training setup.",
                    "claim_type": "clarity",
                    "importance": "medium",
                    "source_field": "weaknesses",
                    "source_sentence": "The authors should clarify the training setup.",
                    "rationale": "The reviewer asks for clarification.",
                },
            ]
        }


class SampleJudgeClient:
    def __init__(self):
        self.calls = []

    def complete_json(self, *, model, messages, schema_name, schema):
        self.model = model
        self.schema_name = schema_name
        self.calls.append({"model": model, "messages": messages, "schema_name": schema_name, "schema": schema})
        if schema_name == "review_point_batch_judgement":
            prompt = messages[-1]["content"]
            batch_input = json.loads(prompt.split("Batch audit input JSON:\n", 1)[1])
            return {
                "claim_judgements": [
                    {"claim_id": point["claim_id"], **self.judgement_payload()}
                    for point in batch_input["review_points"]
                ]
            }
        return self.judgement_payload()

    def judgement_payload(self):
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
                "The manuscript states that Table 2 reports an ablation study over the retriever, reranker, and calibration modules."
            ),
            "quoted_manuscript_evidence": "Table 2 reports an ablation study over the retriever, reranker, and calibration modules.",
            "reasoning_summary": "The retrieved evidence supports the clarification request.",
            "rebuttal_guidance": {
                "priority": "high",
                "strategy": "acknowledge_and_clarify",
                "suggested_response": "Acknowledge the concern and point to the clarified calibration module text.",
                "evidence_to_cite": ["Section 3.1"],
                "risks_to_avoid": ["Do not dismiss the concern."],
            },
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


class UnreliableJudgeClient(SampleJudgeClient):
    def judgement_payload(self):
        payload = super().judgement_payload()
        payload.update(
            {
                "stance": "strongly_agree",
                "support_score": 95,
                "verdict": "insufficient",
                "confidence": "high",
                "evidence_support": 1,
                "factual_alignment": 1,
                "second_opinion_take": "LLM fallback prompt schema says this needs human check.",
                "quoted_manuscript_evidence": "This quote is not in the retrieved evidence.",
                "rationale": "The supplied evidence is too thin.",
            }
        )
        return payload


class EvidenceIdJudgeClient(SampleJudgeClient):
    def complete_json(self, *, model, messages, schema_name, schema):
        self.model = model
        self.schema_name = schema_name
        self.calls.append({"model": model, "messages": messages, "schema_name": schema_name, "schema": schema})
        prompt = messages[-1]["content"]
        batch_input = json.loads(prompt.split("Batch audit input JSON:\n", 1)[1])
        judgements = []
        for point in batch_input["review_points"]:
            payload = self.judgement_payload()
            evidence_ids = [item["evidence_id"] for item in point["retrieved_evidence"][:2]]
            payload["rebuttal_guidance"]["evidence_to_cite"] = evidence_ids
            payload["reasoning_summary"] = "This is similar to claim_deadbeef00 and cites claim_deadbeef00_ev1."
            payload["rationale"] = "Similar to claim_deadbeef00."
            judgements.append({"claim_id": point["claim_id"], **payload})
        return {"claim_judgements": judgements}


class IncompleteBatchJudgeClient(SampleJudgeClient):
    def complete_json(self, *, model, messages, schema_name, schema):
        self.model = model
        self.schema_name = schema_name
        self.calls.append({"model": model, "messages": messages, "schema_name": schema_name, "schema": schema})
        if schema_name == "review_point_batch_judgement":
            prompt = messages[-1]["content"]
            batch_input = json.loads(prompt.split("Batch audit input JSON:\n", 1)[1])
            first = batch_input["review_points"][0]
            return {"claim_judgements": [{"claim_id": first["claim_id"], **self.judgement_payload()}]}
        return self.judgement_payload()


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
        self.assertEqual(result["claim_extraction_version"], "claim-extraction-llm-v0.3")
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
        judge_client = SampleJudgeClient()
        result = audit_dataset(
            dataset,
            claim_llm_client=SampleClaimClient(),
            judge_llm_client=judge_client,
            claim_model="claim-test",
            judge_model="judge-test",
            use_llm_judge=True,
        )
        first_claim = result["audits"][0]["claims"][0]
        self.assertEqual(result["model_version"], "review-point-judge-v0.4")
        self.assertEqual(result["judge_model"], "judge-test")
        self.assertEqual(judge_client.calls[0]["schema_name"], "review_point_batch_judgement")
        self.assertIn("Task boundary", judge_client.calls[0]["messages"][0]["content"])
        self.assertIn("Adjudication procedure", judge_client.calls[0]["messages"][0]["content"])
        self.assertEqual(len(judge_client.calls), result["audit_count"])
        self.assertEqual(first_claim["verdict"], "supported")
        self.assertEqual(first_claim["audit_confidence"], "high")
        self.assertEqual(first_claim["judge_version"], "review-point-judge-v0.4")
        self.assertEqual(first_claim["review_point_type"], "comment")
        self.assertEqual(first_claim["stance"], "strongly_agree")
        self.assertEqual(first_claim["support_score"], 92)
        self.assertEqual(first_claim["answer_coverage_score"], 0)
        self.assertEqual(first_claim["question_value_score"], 0)
        self.assertIn("Reviewer argues", first_claim["second_opinion_take"])
        self.assertIn("SecondOpinion concludes", first_claim["second_opinion_take"])
        self.assertEqual(first_claim["rebuttal_guidance"]["priority"], "high")
        self.assertEqual(first_claim["rebuttal_guidance"]["strategy"], "acknowledge_and_clarify")
        self.assertIn("Section 3.1", first_claim["rebuttal_guidance"]["evidence_to_cite"])
        self.assertIn("retrieved evidence supports", first_claim["judge_rationale"])
        self.assertNotIn("possibly-contradicted-by-paper", first_claim["issue_flags"])

    def test_llm_judge_batches_all_claims_in_one_review_call(self):
        dataset = {
            "dataset": "two-claim",
            "papers": [
                {
                    "paper_id": "paper1",
                    "title": "Ablation Study",
                    "abstract": (
                        "Table 2 reports an ablation study over the retriever, reranker, and calibration modules. "
                        "Section 3 explains the training setup."
                    ),
                    "decision": "Reject",
                    "reviews": [
                        {
                            "review_id": "review1",
                            "review_text": "The paper lacks ablation studies. The authors should clarify the training setup.",
                            "weaknesses": "The paper lacks ablation studies. The authors should clarify the training setup.",
                            "rating_raw": "4: reject",
                            "rating_normalized": 4.0,
                            "confidence_raw": "3",
                            "confidence_normalized": 6.0,
                        }
                    ],
                }
            ],
        }
        judge_client = SampleJudgeClient()
        result = audit_dataset(
            dataset,
            claim_llm_client=TwoClaimClient(),
            judge_llm_client=judge_client,
            claim_model="claim-test",
            judge_model="judge-test",
            use_llm_judge=True,
        )
        claims = result["audits"][0]["claims"]
        self.assertEqual(len(judge_client.calls), 1)
        self.assertEqual(len(claims), 2)
        self.assertTrue(all(claim["judge_version"] == "review-point-judge-v0.4" for claim in claims))

    def test_incomplete_batch_judge_retries_missing_claims_singly(self):
        dataset = {
            "dataset": "two-claim",
            "papers": [
                {
                    "paper_id": "paper1",
                    "title": "Ablation Study",
                    "abstract": (
                        "Table 2 reports an ablation study over the retriever, reranker, and calibration modules. "
                        "Section 3 explains the training setup."
                    ),
                    "decision": "Reject",
                    "reviews": [
                        {
                            "review_id": "review1",
                            "review_text": "The paper lacks ablation studies. The authors should clarify the training setup.",
                            "weaknesses": "The paper lacks ablation studies. The authors should clarify the training setup.",
                            "rating_raw": "4: reject",
                            "rating_normalized": 4.0,
                            "confidence_raw": "3",
                            "confidence_normalized": 6.0,
                        }
                    ],
                }
            ],
        }
        judge_client = IncompleteBatchJudgeClient()
        result = audit_dataset(
            dataset,
            claim_llm_client=TwoClaimClient(),
            judge_llm_client=judge_client,
            claim_model="claim-test",
            judge_model="judge-test",
            use_llm_judge=True,
        )
        claims = result["audits"][0]["claims"]
        self.assertEqual([call["schema_name"] for call in judge_client.calls], ["review_point_batch_judgement", "review_point_judgement"])
        self.assertTrue(all(claim["judge_version"] == "review-point-judge-v0.4" for claim in claims))
        self.assertNotIn("llm-batch-judge-incomplete", claims[1]["issue_flags"])
        self.assertNotIn("llm-judge-failed", claims[1]["issue_flags"])

    def test_reliability_gate_rewrites_unverified_high_confidence_judgement(self):
        dataset = json.loads(Path("examples/sample_normalized_dataset.json").read_text())
        result = audit_dataset(
            dataset,
            claim_llm_client=SampleClaimClient(),
            judge_llm_client=UnreliableJudgeClient(),
            claim_model="claim-test",
            judge_model="judge-test",
            use_llm_judge=True,
        )
        first_claim = result["audits"][0]["claims"][0]
        self.assertEqual(first_claim["verdict"], "insufficient")
        self.assertEqual(first_claim["audit_confidence"], "low")
        self.assertEqual(first_claim["stance"], "mixed")
        self.assertLessEqual(first_claim["support_score"], 40)
        self.assertNotIn("not in the retrieved evidence", first_claim["quoted_manuscript_evidence"])
        self.assertNotIn("LLM fallback prompt schema", first_claim["second_opinion_take"])
        self.assertIn("unverified-quoted-evidence", first_claim["issue_flags"])
        self.assertIn("confidence-downgraded-evidence-limited", first_claim["issue_flags"])
        self.assertIn("stance-corrected-by-reliability-gate", first_claim["issue_flags"])
        self.assertNotIn("user-facing-copy-rewritten", first_claim["issue_flags"])

    def test_reliability_gate_rewrites_structured_assessment_artifacts(self):
        dataset = json.loads(Path("examples/sample_normalized_dataset.json").read_text())
        client = SampleJudgeClient()
        payload = client.judgement_payload()
        payload["second_opinion_take"] = (
            "reviewer point: The reviewer asks for ablations.\n\n"
            "Manuscript evidence: Table 2 mentions ablations.\n\n"
            "Conclusion: partially supported.\n\n"
            "Rebuttal guidance: cite the table."
        )

        class StructuredArtifactJudgeClient(SampleJudgeClient):
            def judgement_payload(self_inner):
                return payload

        result = audit_dataset(
            dataset,
            claim_llm_client=SampleClaimClient(),
            judge_llm_client=StructuredArtifactJudgeClient(),
            claim_model="claim-test",
            judge_model="judge-test",
            use_llm_judge=True,
        )
        first_claim = result["audits"][0]["claims"][0]
        self.assertNotIn("reviewer point:", first_claim["second_opinion_take"].lower())
        self.assertNotIn("rebuttal guidance", first_claim["second_opinion_take"].lower())
        self.assertIn("SecondOpinion concludes", first_claim["second_opinion_take"])
        self.assertNotIn("user-facing-copy-rewritten", first_claim["issue_flags"])

    def test_rebuttal_guidance_humanizes_evidence_ids(self):
        dataset = json.loads(Path("examples/sample_normalized_dataset.json").read_text())
        dataset["papers"][0]["paper_sections"] = [
            {
                "source_type": "paper",
                "section": "methods",
                "page": 4,
                "text": "Table 2 reports an ablation study over the retriever and calibration modules.",
            }
        ]
        result = audit_dataset(
            dataset,
            claim_llm_client=SampleClaimClient(),
            judge_llm_client=EvidenceIdJudgeClient(),
            claim_model="claim-test",
            judge_model="judge-test",
            use_llm_judge=True,
        )
        citations = result["audits"][0]["claims"][0]["rebuttal_guidance"]["evidence_to_cite"]
        self.assertIn("Paper abstract", citations)
        self.assertIn("Section methods p.4", citations)
        self.assertNotIn("Author response", citations)
        self.assertFalse(any(item.startswith("claim_") for item in citations))
        claim = result["audits"][0]["claims"][0]
        self.assertNotIn("claim_", claim["reasoning_summary"])
        self.assertNotIn("claim_", claim["judge_rationale"])
        self.assertIn("another extracted review point", claim["reasoning_summary"])

    def test_rule_audit_adds_default_rebuttal_guidance(self):
        dataset = json.loads(Path("examples/sample_normalized_dataset.json").read_text())
        result = audit_dataset(dataset, claim_llm_client=SampleClaimClient(), claim_model="test-model")
        guidance = result["audits"][0]["claims"][0]["rebuttal_guidance"]
        self.assertIn(guidance["priority"], {"high", "medium", "low"})
        self.assertIn("suggested_response", guidance)
        self.assertIsInstance(guidance["evidence_to_cite"], list)
        self.assertIsInstance(guidance["risks_to_avoid"], list)

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
        self.assertEqual(first_claim["judge_version"], "review-point-judge-v0.4+fallback")

    def test_review_assessment_ignores_author_response(self):
        dataset = {
            "dataset": "temporal_boundary",
            "papers": [
                {
                    "paper_id": "p1",
                    "title": "A Model for Review Auditing",
                    "abstract": "We introduce a model for review auditing.",
                    "decision": "Reject",
                    "reviews": [
                        {
                            "review_id": "r1",
                            "review_text": "The paper lacks ablation studies.",
                            "weaknesses": "The paper lacks ablation studies.",
                            "rating_raw": "3: reject",
                            "rating_normalized": 3.0,
                            "confidence_raw": "4: confident",
                            "confidence_normalized": 8.0,
                        }
                    ],
                    "rebuttals": [
                        {
                            "id": "reply1",
                            "text": "We added a new ablation study in the revised PDF.",
                        }
                    ],
                    "paper_sections": [],
                }
            ],
        }
        result = audit_dataset(dataset, claim_llm_client=SampleClaimClient())
        claim = result["audits"][0]["claims"][0]
        self.assertNotEqual(claim["verdict"], "possibly_contradicted")
        self.assertNotIn("possibly-contradicted-by-paper", claim["issue_flags"])
        self.assertFalse(any(item["source_type"] == "rebuttal" for item in claim["evidence"]))

    def test_external_evidence_can_be_attached_during_audit(self):
        dataset = json.loads(Path("examples/sample_normalized_dataset.json").read_text())
        result = audit_dataset(
            dataset,
            claim_llm_client=SampleClaimClient(),
            claim_model="test-model",
            use_external_evidence=True,
            external_providers=("venue_guidelines",),
        )
        first_claim = result["audits"][0]["claims"][0]
        self.assertEqual(result["external_evidence_version"], "external-evidence-v0.1")
        self.assertTrue(any(item["source_type"] == "venue_guideline" for item in first_claim["evidence"]))


if __name__ == "__main__":
    unittest.main()

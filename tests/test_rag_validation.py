import unittest

from secondopinion.rag_validation import (
    judgment_messages,
    retrieve_concern_cases,
    run_rag_judgment_ablation,
    validate_concern_rag,
)


class FakeJudgeLLM:
    def complete_json(self, *, model, messages, schema_name, schema):
        content = messages[-1]["content"]
        if "missing ablations" in content:
            return {
                "meta_review_match": "survived",
                "ac_treatment": "endorsed_or_relied_on",
                "concern_quality": "high",
                "confidence": "high",
                "rationale": "The concern is repeated.",
            }
        return {
            "meta_review_match": "not_found",
            "ac_treatment": "not_mentioned",
            "concern_quality": "low",
            "confidence": "medium",
            "rationale": "No matching concern.",
        }


def calibration_record(task_id, claim, match, quality, claim_type="experiment", paper_id="paper1"):
    return {
        "task_id": task_id,
        "paper_id": paper_id,
        "review_id": f"review-{task_id}",
        "title": "Test Paper",
        "claim_text": claim,
        "claim_type": claim_type,
        "source_sentence": claim,
        "matched_meta_segment": "Reviewers raised concerns about missing ablations.",
        "meta_review_text": "Reviewers raised concerns about missing ablations.",
        "llm_meta_review_match": match,
        "llm_ac_treatment": "endorsed_or_relied_on" if match == "survived" else "not_mentioned",
        "llm_concern_quality": quality,
        "llm_label_evidence_strength": "high",
        "llm_confidence": "high",
        "llm_rationale": "Rationale.",
        "high_confidence_training_candidate": True,
    }


def memory_record(task_id, claim, match, quality, claim_type="experiment", paper_id="paper2"):
    return {
        "memory_id": f"concern_case:{task_id}",
        "source_task_id": task_id,
        "paper_id": paper_id,
        "review_id": f"review-{task_id}",
        "title": "Memory Paper",
        "claim": {
            "text": claim,
            "type": claim_type,
            "source_sentence": claim,
        },
        "meta_review": {
            "match": match,
            "ac_treatment": "endorsed_or_relied_on" if match == "survived" else "not_mentioned",
            "matched_segment": "",
        },
        "quality": {
            "concern_quality": quality,
            "label_evidence_strength": "high",
            "confidence": "high",
        },
        "rationale": "Memory rationale.",
    }


class RagValidationTests(unittest.TestCase):
    def test_retrieve_concern_cases_finds_similar_claim(self):
        query = calibration_record("q1", "The paper lacks missing ablations.", "survived", "high")
        memory = [
            memory_record("m1", "Missing ablations weaken the evaluation.", "survived", "high"),
            memory_record("m2", "The notation is unclear.", "not_found", "low", claim_type="clarity"),
        ]

        retrieved = retrieve_concern_cases(query, memory, top_k=1)

        self.assertEqual(retrieved[0]["source_task_id"], "m1")

    def test_validate_concern_rag_reports_hits_and_knn_accuracy(self):
        records = [
            calibration_record("q1", "The paper lacks missing ablations.", "survived", "high"),
            calibration_record("q2", "The notation is unclear.", "not_found", "low", claim_type="clarity"),
        ]
        memory = [
            memory_record("m1", "Missing ablations weaken the evaluation.", "survived", "high"),
            memory_record("m2", "The notation is unclear.", "not_found", "low", claim_type="clarity"),
        ]

        report = validate_concern_rag(records, memory, top_ks=(1, 2))

        self.assertEqual(report["summary"]["query_count"], 2)
        self.assertGreaterEqual(report["summary"]["match_hit@1"], 0.5)
        self.assertIn("random_match_hit@1", report["summary"])

    def test_validate_concern_rag_can_filter_to_semantic_decisive_high_confidence_records(self):
        usable = calibration_record("q1", "The paper lacks missing ablations.", "survived", "high")
        unsure = calibration_record("q2", "The notation is unclear.", "unsure", "low", claim_type="clarity")
        low_confidence = calibration_record("q3", "The motivation is weak.", "partial", "medium")
        low_confidence["high_confidence_training_candidate"] = False
        memory = [
            calibration_record("m1", "Missing ablations weaken the evaluation.", "survived", "high", paper_id="paper2"),
            calibration_record("m2", "Unclear notation.", "unsure", "low", claim_type="clarity", paper_id="paper2"),
            calibration_record("m3", "Weak motivation.", "partial", "medium", paper_id="paper2"),
        ]
        memory[-1]["high_confidence_training_candidate"] = False

        report = validate_concern_rag(
            [usable, unsure, low_confidence],
            memory,
            top_ks=(1,),
            only_decisive_meta_labels=True,
            only_high_confidence=True,
        )

        self.assertEqual(report["summary"]["input_query_count"], 3)
        self.assertEqual(report["summary"]["query_count"], 1)
        self.assertEqual(report["summary"]["memory_count"], 1)
        self.assertEqual(report["summary"]["filters"]["only_decisive_meta_labels"], True)
        self.assertEqual(report["summary"]["majority_match_baseline"], 1.0)

    def test_run_rag_judgment_ablation_uses_llm_schema(self):
        record = calibration_record("q1", "The paper lacks missing ablations.", "survived", "high")
        memory = [memory_record("m1", "Missing ablations weaken the evaluation.", "survived", "high")]

        report = run_rag_judgment_ablation(
            [record],
            memory,
            llm_client=FakeJudgeLLM(),
            model="test",
            limit=1,
            exclude_same_paper=True,
            include_current_meta_review=False,
        )

        self.assertEqual(report["summary"]["query_count"], 1)
        self.assertTrue(report["summary"]["exclude_same_paper"])
        self.assertFalse(report["summary"]["include_current_meta_review"])
        self.assertEqual(report["summary"]["with_rag_match_accuracy"], 1.0)

    def test_judgment_messages_hide_current_meta_review_by_default(self):
        record = calibration_record("q1", "The paper lacks missing ablations.", "survived", "high")

        closed_book = judgment_messages(record, [])
        open_book = judgment_messages(record, [], include_current_meta_review=True)

        self.assertNotIn("meta_review_text", closed_book[-1]["content"])
        self.assertIn("meta_review_text", open_book[-1]["content"])


if __name__ == "__main__":
    unittest.main()

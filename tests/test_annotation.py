import tempfile
import unittest
from pathlib import Path

from secondopinion.annotation import (
    ANNOTATION_LABEL_VERSION,
    compare_annotations,
    export_annotation_tasks,
    label_id,
    llm_label_tasks,
    read_jsonl,
    validate_labels,
    write_annotation_html,
    write_jsonl,
)


class FakeAnnotationLLM:
    def complete_json(self, *, model, messages, schema_name, schema):
        if "claim_quality" in schema_name:
            return {
                "labels": {
                    "claim_valid": "valid",
                    "claim_error_type": "none",
                    "claim_type_correct": "yes",
                    "correct_claim_type": "ablation",
                },
                "notes": "Claim is faithful.",
            }
        if "evidence_relevance" in schema_name:
            return {
                "labels": {
                    "evidence_relevance": "high",
                    "evidence_error_type": "none",
                    "better_evidence": "",
                },
                "notes": "Evidence is relevant.",
            }
        if "verdict_correctness" in schema_name:
            return {
                "labels": {
                    "verdict_correct": "yes",
                    "correct_verdict": "possibly_contradicted",
                    "confidence_correct": "yes",
                    "correct_confidence": "medium",
                },
                "notes": "Verdict is reasonable.",
            }
        return {
            "labels": {
                "rqs_reasonable": "yes",
                "main_issue_detected": "yes",
                "needs_human_expert": "no",
                "report_usefulness": 4,
            },
            "notes": "Report is useful.",
        }


def sample_audit_result():
    return {
        "schema_version": "0.1",
        "dataset": "sample",
        "audit_count": 1,
        "model_version": "rule-baseline-v0.1",
        "rubric_version": "rubric-v0.1",
        "claim_extraction_version": "claim-extraction-llm-v0.1",
        "claim_model": "test-claim-model",
        "retrieval_version": "section-aware-bm25-v0.2",
        "audits": [
            {
                "audit_id": "audit1",
                "review_id": "review1",
                "paper_id": "paper1",
                "rqs_score": 55,
                "audit_confidence": "medium",
                "issue_flags": ["possibly-contradicted-by-paper"],
                "summary": "Audit summary.",
                "dimensions": {"claim_accuracy_and_evidence": 2.0},
                "claims": [
                    {
                        "claim_id": "claim1",
                        "review_id": "review1",
                        "claim_text": "The paper lacks ablation studies.",
                        "claim_type": "ablation",
                        "importance": "major",
                        "source_field": "weaknesses",
                        "source_sentence_index": 0,
                        "source_sentence": "The paper lacks ablation studies.",
                        "extraction_reason": "LLM extracted.",
                        "extraction_version": "claim-extraction-llm-v0.1",
                        "verdict": "possibly_contradicted",
                        "audit_confidence": "medium",
                        "issue_flags": ["possibly-contradicted-by-paper"],
                        "evidence_support": 0,
                        "factual_alignment": 0,
                        "evidence": [
                            {
                                "evidence_id": "evidence1",
                                "claim_id": "claim1",
                                "source_type": "paper",
                                "section": "abstract",
                                "page": None,
                                "text": "Table 2 reports an ablation study.",
                                "verdict": "possibly_contradicting_candidate",
                                "confidence": "medium",
                                "score": 0.5,
                            }
                        ],
                    },
                    {
                        "claim_id": "claim2",
                        "review_id": "review1",
                        "claim_text": "The paper should explain calibration.",
                        "claim_type": "clarity",
                        "importance": "medium",
                        "source_field": "weaknesses",
                        "source_sentence_index": 1,
                        "source_sentence": "The paper should explain calibration.",
                        "extraction_reason": "LLM extracted.",
                        "extraction_version": "claim-extraction-llm-v0.1",
                        "verdict": "insufficient",
                        "audit_confidence": "low",
                        "issue_flags": ["unsupported-major-claim"],
                        "evidence_support": 1,
                        "factual_alignment": 1,
                        "evidence": [],
                    },
                ],
            }
        ],
    }


class AnnotationTests(unittest.TestCase):
    def test_export_tasks_count_and_provenance(self):
        run_id, tasks = export_annotation_tasks(sample_audit_result(), run_id="run1")
        self.assertEqual(run_id, "run1")
        self.assertEqual(len(tasks), 6)
        self.assertEqual(tasks[0]["task_type"], "review_audit_quality")
        self.assertEqual(tasks[0]["provenance"]["claim_model"], "test-claim-model")
        self.assertEqual(tasks[0]["provenance"]["reserved_external_evidence_source_types"][0], "venue_guideline")

    def test_task_id_is_stable(self):
        _, first = export_annotation_tasks(sample_audit_result(), run_id="run1")
        _, second = export_annotation_tasks(sample_audit_result(), run_id="run1")
        self.assertEqual([task["task_id"] for task in first], [task["task_id"] for task in second])

    def test_html_does_not_include_llm_labels(self):
        _, tasks = export_annotation_tasks(sample_audit_result(), run_id="run1")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "packet.html"
            write_annotation_html(tasks, path)
            html = path.read_text(encoding="utf-8")
        self.assertIn("SecondOpinion Annotation Packet", html)
        self.assertNotIn("LLM annotation", html)
        self.assertIn("llm_label_visible: false", html)

    def test_label_validation_finds_missing_fields(self):
        issues = validate_labels([{"task_id": "task1"}])
        self.assertEqual(issues[0]["line"], 1)
        self.assertIn("missing:annotation_id", issues[0]["errors"])

    def test_llm_labeler_with_fake_client(self):
        _, tasks = export_annotation_tasks(sample_audit_result(), run_id="run1")
        labels = llm_label_tasks(tasks, llm_client=FakeAnnotationLLM(), model="test-model")
        self.assertEqual(len(labels), len(tasks))
        self.assertEqual(validate_labels(labels), [])
        self.assertEqual(labels[0]["annotator_type"], "llm")

    def test_compare_annotations_counts_disagreements(self):
        _, tasks = export_annotation_tasks(sample_audit_result(), run_id="run1")
        llm_labels = llm_label_tasks(tasks, llm_client=FakeAnnotationLLM(), model="test-model")
        human_labels = []
        for label in llm_labels:
            human = dict(label)
            human["annotation_id"] = label_id(label["task_id"], "human", "human1")
            human["annotator_type"] = "human"
            human["annotator_id"] = "human1"
            human["label_schema_version"] = ANNOTATION_LABEL_VERSION
            human["llm_label_visible"] = False
            human["labels"] = dict(label["labels"])
            human_labels.append(human)
        human_labels[0]["labels"]["rqs_reasonable"] = "no"
        comparison = compare_annotations(human_labels, llm_labels, tasks=tasks)
        self.assertEqual(comparison["common_label_count"], len(tasks))
        self.assertEqual(comparison["disagreement_count"], 1)
        self.assertEqual(comparison["by_task_type"]["review_audit_quality"]["common"], 1)

    def test_jsonl_roundtrip(self):
        _, tasks = export_annotation_tasks(sample_audit_result(), run_id="run1")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tasks.jsonl"
            write_jsonl(path, tasks)
            loaded = read_jsonl(path)
        self.assertEqual(loaded[0]["task_id"], tasks[0]["task_id"])


if __name__ == "__main__":
    unittest.main()

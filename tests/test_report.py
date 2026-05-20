import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from secondopinion.report import (
    claim_assessment_text,
    claim_source_label,
    claim_type_label,
    evidence_label,
    flag_label,
    verdict_label,
    write_html_report,
)


class ReportTests(unittest.TestCase):
    def test_report_labels_are_human_readable(self):
        self.assertEqual(
            claim_source_label({"source_field": "weaknesses", "source_sentence_index": 3}),
            "reviewer weaknesses, sentence 4",
        )
        self.assertIn("unclear", claim_type_label("clarity"))
        self.assertIn("support", verdict_label("supported").lower())
        self.assertIn("clear next step", flag_label("missing-actionable-suggestions"))

    def test_evidence_label_distinguishes_pdf_and_rebuttal_sources(self):
        pdf_label = evidence_label(
            {
                "source_type": "paper",
                "section": "2.2 MODELS",
                "page": 4,
                "score": 0.891,
            }
        )
        rebuttal_label = evidence_label(
            {
                "source_type": "rebuttal",
                "section": "author_response_1",
                "score": 0.5,
            }
        )
        self.assertEqual(pdf_label, "PDF evidence - Section 2.2 MODELS p.4 score=0.89")
        self.assertEqual(rebuttal_label, "Author response / rebuttal - author_response_1 score=0.50")

    def test_rule_assessment_says_it_is_not_llm_judge(self):
        assessment = claim_assessment_text(
            {
                "verdict": "supported",
                "audit_confidence": "high",
                "judge_version": "rule-baseline-v0.1",
                "evidence": [
                    {
                        "source_type": "paper",
                        "section": "abstract",
                        "score": 0.8,
                    }
                ],
            }
        )
        self.assertIn("not an LLM judge evaluation", assessment)
        self.assertIn("Paper abstract", assessment)

    def test_llm_assessment_surfaces_rationale(self):
        assessment = claim_assessment_text(
            {
                "verdict": "possibly_contradicted",
                "audit_confidence": "medium",
                "judge_version": "llm-rag-judge-v0.1",
                "judge_rationale": "The paper gives the requested setup details.",
                "evidence": [],
            }
        )
        self.assertIn("LLM rationale", assessment)
        self.assertIn("requested setup details", assessment)

    def test_html_report_strips_pdf_control_characters(self):
        audit = {
            "dataset": "sample",
            "paper_count": 1,
            "audits": [
                {
                    "review_id": "r1",
                    "paper_id": "p1",
                    "summary": "ok",
                    "rqs_score": 80,
                    "audit_confidence": "high",
                    "issue_flags": [],
                    "claims": [
                        {
                            "claim_text": "Needs details",
                            "source_field": "weaknesses",
                            "source_sentence_index": 0,
                            "source_sentence": "Needs details",
                            "claim_type": "clarity",
                            "verdict": "supported",
                            "audit_confidence": "high",
                            "judge_version": "rule-baseline-v0.1",
                            "issue_flags": [],
                            "evidence": [
                                {
                                    "source_type": "paper",
                                    "section": "2",
                                    "page": 1,
                                    "score": 0.9,
                                    "verdict": "supporting_candidate",
                                    "text": "bad\x00pdf text",
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.html"
            write_html_report(audit, path)
            data = path.read_bytes()
        self.assertNotIn(b"\x00", data)
        self.assertIn(b"bad pdf text", data)


if __name__ == "__main__":
    unittest.main()

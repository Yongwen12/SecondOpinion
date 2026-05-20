import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from secondopinion.report import (
    claim_assessment_text,
    claim_source_label,
    claim_type_label,
    evidence_label,
    flag_label,
    review_rating_label,
    reviewer_confidence_label,
    verdict_label,
    write_html_report,
)


class ReportTests(unittest.TestCase):
    def test_report_labels_are_human_readable(self):
        self.assertEqual(
            claim_source_label({"source_field": "weaknesses", "source_sentence_index": 3}),
            "Weaknesses section, sentence 4",
        )
        self.assertIn("unclear", claim_type_label("clarity"))
        self.assertIn("grounded", verdict_label("supported").lower())
        self.assertIn("limited guidance", flag_label("missing-actionable-suggestions"))
        self.assertEqual(
            review_rating_label({"rating_raw": "3: reject", "rating_normalized": 3.0}),
            "3: reject (normalized: 3.0)",
        )
        self.assertEqual(
            reviewer_confidence_label(
                {
                    "reviewer_confidence_raw": "4: confident",
                    "reviewer_confidence_normalized": 8.0,
                }
            ),
            "4: confident (normalized: 8.0)",
        )

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
        self.assertEqual(pdf_label, "Manuscript section 2.2 MODELS p.4")
        self.assertEqual(rebuttal_label, "Author response")

    def test_rule_assessment_is_user_facing(self):
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
        self.assertIn("SecondOpinion screened", assessment)
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
        self.assertIn("Rationale", assessment)
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
                    "rating_raw": "3: reject",
                    "rating_normalized": 3.0,
                    "reviewer_confidence_raw": "4: confident",
                    "reviewer_confidence_normalized": 8.0,
                    "decision": "Reject",
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
        self.assertIn(b"Reviewer rating", data)
        self.assertIn(b"Final decision", data)
        self.assertIn(b"SecondOpinion assessment", data)
        self.assertNotIn(b"Reviewer source", data)
        self.assertNotIn(b"System verdict", data)
        self.assertNotIn(b"LLM judge", data)


if __name__ == "__main__":
    unittest.main()

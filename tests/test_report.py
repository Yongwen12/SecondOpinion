import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from secondopinion.report import (
    claim_assessment_text,
    claim_reasoning_text,
    claim_source_label,
    claim_type_label,
    evidence_label,
    flag_label,
    rebuttal_guidance_text,
    review_rating_label,
    reviewer_confidence_label,
    stance_label,
    support_percent,
    verdict_label,
    write_html_report,
)


class ReportTests(unittest.TestCase):
    def test_report_labels_are_human_readable(self):
        self.assertEqual(
            claim_source_label({"source_field": "weaknesses", "source_sentence_index": 3}),
            "Weaknesses section, sentence 4",
        )
        self.assertEqual(
            claim_source_label({"source_field": "weaknesses", "source_bullet_index": 1, "source_char_start": 20, "source_char_end": 42}),
            "Weaknesses section, bullet 2",
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
        self.assertEqual(stance_label({"stance": "strongly_disagree"}), "Strongly disagree")
        self.assertEqual(stance_label({"stance": "well_supported"}), "Agree")

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

    def test_evidence_label_distinguishes_external_sources(self):
        guideline_label = evidence_label(
            {
                "source_type": "venue_guideline",
                "section": "ICLR review criteria: empirical validation",
                "metadata": {"venue": "ICLR"},
            }
        )
        external_label = evidence_label(
            {
                "source_type": "external_reference",
                "section": "OpenAlex related paper: Retrieval Baselines",
                "metadata": {"title": "Retrieval Baselines", "publication_year": 2022},
            }
        )
        self.assertEqual(guideline_label, "ICLR guideline: ICLR review criteria: empirical validation")
        self.assertEqual(external_label, "External reference: Retrieval Baselines (2022)")

    def test_support_percent_measures_support_for_review_point(self):
        self.assertGreaterEqual(support_percent({"verdict": "supported", "evidence_support": 3}), 80)
        self.assertLessEqual(support_percent({"verdict": "possibly_contradicted", "evidence_support": 3}), 25)

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
                        "text": "The paper explains the training setup in detail.",
                    }
                ],
            }
        )
        self.assertIn("well supported", assessment)
        self.assertIn("training setup", assessment)

    def test_llm_assessment_surfaces_rationale(self):
        assessment = claim_assessment_text(
            {
                "verdict": "possibly_contradicted",
                "audit_confidence": "medium",
                "judge_version": "review-point-judge-v0.4",
                "judge_rationale": "The paper gives the requested setup details.",
                "evidence": [],
            }
        )
        self.assertIn("Rationale", assessment)
        self.assertIn("requested setup details", assessment)

    def test_rebuttal_guidance_text_is_user_facing(self):
        guidance = rebuttal_guidance_text(
            {
                "rebuttal_guidance": {
                    "priority": "high",
                    "strategy": "cite_existing_evidence",
                    "suggested_response": "Point to Section 2 and clarify the setup.",
                    "evidence_to_cite": ["Section 2"],
                    "risks_to_avoid": ["Do not say the reviewer is wrong."],
                }
            }
        )
        self.assertIn("High priority", guidance)
        self.assertIn("Cite existing evidence", guidance)
        self.assertIn("Section 2", guidance)

    def test_claim_reasoning_text_combines_summary_and_rationale(self):
        reasoning = claim_reasoning_text(
            {
                "reasoning_summary": "The manuscript mentions ablations and baselines.",
                "judge_rationale": "The reviewer overstates complete absence.",
            }
        )
        self.assertIn("mentions ablations", reasoning)
        self.assertIn("overstates", reasoning)

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
                            "reasoning_summary": "The manuscript text directly supports the assessment.",
                            "rebuttal_guidance": {
                                "priority": "medium",
                                "strategy": "concede_and_fix",
                                "suggested_response": "Acknowledge the concern and clarify the missing details.",
                                "evidence_to_cite": ["Section 2"],
                                "risks_to_avoid": ["Do not over-defend."],
                            },
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
        self.assertIn(b"Review Assessment", data)
        self.assertIn(b"Judgment Basis", data)
        self.assertIn(b"directly supports", data)
        self.assertIn(b"Rebuttal Guidance", data)
        self.assertIn(b"Concede and fix", data)
        self.assertIn(b"Strongly agree", data)
        self.assertIn(b"Reference material", data)
        self.assertNotIn(b"SecondOpinion take", data)
        self.assertNotIn(b"Reviewer source", data)
        self.assertNotIn(b"System verdict", data)
        self.assertNotIn(b"LLM judge", data)
        self.assertNotIn(b"Assessment source", data)


if __name__ == "__main__":
    unittest.main()

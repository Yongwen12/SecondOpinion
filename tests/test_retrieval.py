import unittest

from secondopinion.retrieval import RETRIEVAL_VERSION, make_snippet, retrieve_evidence


class RetrievalTests(unittest.TestCase):
    def test_section_aware_retrieval_prefers_ablation_appendix(self):
        paper = {
            "paper_id": "paper1",
            "title": "A Model for Review Auditing",
            "abstract": "We introduce a model for review auditing and calibration.",
            "paper_sections": [
                {
                    "source_type": "paper",
                    "section": "2 Method",
                    "page": 2,
                    "text": "The model uses a retriever and a reranker.",
                },
                {
                    "source_type": "appendix",
                    "section": "Appendix B Ablation Studies",
                    "page": 12,
                    "text": "The ablation study removes the retriever, reranker, and calibration modules.",
                },
            ],
        }
        evidence = retrieve_evidence(
            "claim1",
            "The paper lacks ablation studies for individual modules.",
            paper,
            claim_type="ablation",
        )
        self.assertEqual(evidence[0].section, "Appendix B Ablation Studies")
        self.assertEqual(evidence[0].page, 12)
        self.assertGreater(evidence[0].score, 0.35)

    def test_make_snippet_centers_matched_term(self):
        text = "Intro text. " * 80 + "The ablation study removes the retriever module. " + "Tail text. " * 80
        snippet = make_snippet(text, ["ablation"], max_chars=160)
        self.assertIn("ablation study", snippet)
        self.assertLessEqual(len(snippet), 166)

    def test_retrieval_version_is_v2(self):
        self.assertEqual(RETRIEVAL_VERSION, "section-aware-bm25-v0.2")


if __name__ == "__main__":
    unittest.main()

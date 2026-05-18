import unittest

from secondopinion.normalize import normalize_openreview_notes, normalize_rating


class NormalizeTests(unittest.TestCase):
    def test_rating_normalization(self):
        self.assertEqual(normalize_rating("3: reject"), 3.0)
        self.assertEqual(normalize_rating("3 out of 5"), 6.0)
        self.assertEqual(normalize_rating("8: accept"), 8.0)

    def test_normalize_v2_content_and_replies(self):
        notes = [
            {
                "id": "paper1",
                "forum": "paper1",
                "invitations": ["ICLR.cc/2024/Conference/-/Submission"],
                "content": {
                    "title": {"value": "A Test Paper"},
                    "abstract": {"value": "Abstract text."},
                    "pdf": {"value": "/pdf?id=paper1"}
                },
                "details": {
                    "replies": [
                        {
                            "id": "review1",
                            "invitations": ["ICLR.cc/2024/Conference/Submission1/-/Official_Review"],
                            "content": {
                                "summary": {"value": "Summary."},
                                "weaknesses": {"value": "The paper lacks baselines."},
                                "rating": {"value": "3: reject"},
                                "confidence": {"value": "4: confident"}
                            }
                        }
                    ]
                }
            }
        ]
        dataset = normalize_openreview_notes(notes, venue="ICLR", year=2024)
        self.assertEqual(dataset["paper_count"], 1)
        self.assertEqual(dataset["review_count"], 1)
        self.assertEqual(dataset["papers"][0]["reviews"][0]["rating_normalized"], 3.0)


if __name__ == "__main__":
    unittest.main()

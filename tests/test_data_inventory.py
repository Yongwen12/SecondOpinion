import unittest

from secondopinion.data_inventory import build_inventory_report, inventory_paper


def content(**values):
    return {key: {"value": value} for key, value in values.items()}


def reply(note_id, invitations, signatures, content_payload, *, cdate=1000, mdate=None):
    return {
        "id": note_id,
        "forum": "paper1",
        "invitations": invitations,
        "signatures": signatures,
        "content": content_payload,
        "cdate": cdate,
        "tcdate": cdate,
        "mdate": mdate if mdate is not None else cdate,
        "tmdate": mdate if mdate is not None else cdate,
    }


class DataInventoryTests(unittest.TestCase):
    def test_inventory_paper_classifies_core_openreview_reply_types(self):
        paper = {
            "id": "paper1",
            "forum": "paper1",
            "content": content(title="Test Paper"),
            "details": {
                "replies": [
                    reply(
                        "review1",
                        ["ICLR.cc/2024/Conference/Submission1/-/Official_Review"],
                        ["ICLR.cc/2024/Conference/Submission1/Reviewer_abc"],
                        content(summary="Paper summary", rating="6: accept", confidence="3: confident"),
                        cdate=1000,
                        mdate=3000,
                    ),
                    reply(
                        "authors1",
                        ["ICLR.cc/2024/Conference/Submission1/-/Official_Comment"],
                        ["ICLR.cc/2024/Conference/Submission1/Authors"],
                        content(title="Rebuttal", comment="We thank the reviewers."),
                        cdate=2000,
                    ),
                    reply(
                        "reviewer-comment",
                        ["ICLR.cc/2024/Conference/Submission1/-/Official_Comment"],
                        ["ICLR.cc/2024/Conference/Submission1/Reviewer_abc"],
                        content(comment="The response addresses my concern."),
                        cdate=2500,
                    ),
                    reply(
                        "meta1",
                        ["ICLR.cc/2024/Conference/Submission1/-/Meta_Review"],
                        ["ICLR.cc/2024/Conference/Submission1/Area_Chair_xyz"],
                        content(metareview="The main remaining concern is evaluation."),
                        cdate=4000,
                    ),
                    reply(
                        "decision1",
                        ["ICLR.cc/2024/Conference/Submission1/-/Decision"],
                        ["ICLR.cc/2024/Conference/Program_Chairs"],
                        content(decision="Accept", comment="Accepted after discussion."),
                        cdate=5000,
                    ),
                ]
            },
        }

        result = inventory_paper(paper)

        self.assertEqual(result["review_count"], 1)
        self.assertEqual(result["author_response_count"], 1)
        self.assertEqual(result["meta_review_count"], 1)
        self.assertEqual(result["decision_count"], 1)
        self.assertEqual(result["reviewer_or_ac_discussion_count"], 1)
        self.assertEqual(result["post_rebuttal_reviewer_comment_count"], 1)
        self.assertEqual(result["post_rebuttal_review_update_count"], 1)
        self.assertTrue(result["metric_feasibility"]["rebuttal_alignment"])
        self.assertTrue(result["metric_feasibility"]["concern_survival_meta_review"])
        self.assertTrue(result["metric_feasibility"]["concern_survival_decision_comment"])
        self.assertEqual(result["decision"], "Accept")
        self.assertEqual(result["rating_values"], [6.0])

    def test_build_inventory_report_summarizes_metric_feasibility(self):
        paper = {
            "paper_id": "paper1",
            "reply_count": 1,
            "note_type_counts": {"official_review": 1},
            "signer_role_counts": {"reviewer": 1},
            "availability": {
                "has_reviews": True,
                "has_two_or_more_reviews": False,
                "has_ratings": True,
                "has_confidence": True,
                "has_author_response": False,
                "has_meta_review": False,
                "has_meta_review_text": False,
                "has_decision_note": False,
                "has_decision_label": False,
                "has_decision_comment_text": False,
                "has_official_comments": False,
                "has_reviewer_or_ac_discussion": False,
                "has_post_rebuttal_reviewer_comments": False,
                "has_post_rebuttal_review_update": False,
            },
            "metric_feasibility": {
                "claim_grounding": True,
                "rebuttal_alignment": False,
                "concern_survival_meta_review": False,
                "concern_survival_decision_comment": False,
                "concern_survival_meta_or_decision": False,
                "reviewer_discussion_followup": False,
                "post_rebuttal_discussion_followup": False,
                "post_rebuttal_review_update_proxy": False,
                "inter_review_consensus": False,
                "rating_text_calibration": True,
                "confidence_calibration": True,
            },
        }

        report = build_inventory_report([paper], snapshot={"snapshot_id": "snap"})

        self.assertEqual(report["summary"]["paper_count"], 1)
        self.assertEqual(report["summary"]["metric_feasibility"]["claim_grounding"]["paper_count"], 1)
        self.assertEqual(report["summary"]["metric_feasibility"]["rebuttal_alignment"]["status"], "not_available")


if __name__ == "__main__":
    unittest.main()

from secondopinion.reviewer_public_scorecard import build_public_scorecard


def test_build_public_scorecard_from_hybrid_scores_hides_internal_fields():
    source = {
        "paper": {"title": "Demo Paper", "venue": "ICLR", "year": 2026},
        "summary": {"situation": "Score first, then triage."},
        "reviewers": [
            {
                "display_id": "R1",
                "rating": 5,
                "confidence": 4,
                "summary": "Actionable baseline request.",
                "claims": [
                    {
                        "claim_text": "Please add a retrieval baseline and report runtime.",
                        "second_opinion_take": "Concrete and answerable.",
                        "hybrid_scores": {
                            "specificity": {"final_score": 0.8, "memory_prior": {"prior_score": 0.9}},
                            "substantiation": {"final_score": 0.7},
                            "actionability": {"final_score": 0.9},
                            "consensus_conflict": {"final_score": 0.6},
                            "rebuttal_robustness": {"final_score": 0.5},
                            "professionalism": {"final_score": 0.8},
                        },
                    }
                ],
            }
        ],
    }

    public = build_public_scorecard(source)

    assert public["schema_version"] == "reviewer-public-scorecard-v0.1"
    assert public["paper"]["conference"] == "ICLR 2026"
    assert public["summary"]["reviewer_count"] == 1
    assert public["summary"]["signal_label"] == "Solid review"
    assert public["summary"]["situation"] == "Reviewer comments are scored first, then surfaced for the community."
    assert public["reviewers"][0]["nickname"] == "Baseline Hawk"
    assert public["reviewers"][0]["score"] == 72
    assert public["reviewers"][0]["label"] == "Solid review"
    assert public["comments"][0]["text"] == "Please add a retrieval baseline and report runtime."
    assert public["leaderboards"]["red"] == ["R1"]
    rendered = str(public)
    assert "hybrid_scores" not in rendered
    assert "memory_prior" not in rendered
    assert "mapped_score" not in rendered


def test_build_public_scorecard_creates_black_list_for_low_score_reviewer():
    source = {
        "paper": {"title": "Demo Paper"},
        "reviewers": [
            {
                "display_id": "R1",
                "summary": "Useful review.",
                "claims": [{"claim_text": "Add a baseline.", "hybrid_scores": {"specificity": {"final_score": 0.9}}}],
            },
            {
                "display_id": "R2",
                "summary": "Weak review.",
                "claims": [{"claim_text": "This is not convincing.", "hybrid_scores": {"specificity": {"final_score": 0.2}}}],
            },
        ],
    }

    public = build_public_scorecard(source)

    assert public["leaderboards"]["red"][0] == "R1"
    assert public["leaderboards"]["black"][0] == "R2"
    assert public["reviewers"][1]["nickname"] == "Vague Thunder"


def test_build_public_scorecard_does_not_seed_synthetic_votes():
    source = {
        "paper": {"title": "Demo Paper"},
        "reviewers": [
            {
                "display_id": "R1",
                "claims": [
                    {"claim_text": "Add a baseline.", "hybrid_scores": {"specificity": {"final_score": 0.9}}}
                ],
            },
        ],
    }

    public = build_public_scorecard(source)

    assert public["reviewers"][0]["social"] == {"up": 0, "down": 0}
    assert all(comment["up"] == 0 and comment["down"] == 0 for comment in public["comments"])

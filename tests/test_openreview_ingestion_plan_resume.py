from secondopinion.openreview_ingestion_plan import build_ingestion_plan


def test_pull_commands_are_data_minimized_by_default():
    plan = build_ingestion_plan(
        {
            "venues": [
                {
                    "venue_id": "ICLR",
                    "year": 2025,
                    "status": "open_reviews_available",
                    "recommendation": "pull_and_score",
                    "selected_invitation": "ICLR.cc/2025/Conference/-/Submission",
                    "invitation_candidates": ["ICLR.cc/2025/Conference/-/Submission"],
                }
            ]
        }
    )

    command = plan["venues"][0]["commands"][0]["command"]
    assert "--snapshot iclr_2025_full" in command
    assert "--resume" not in command
    assert "--raw-root" not in command
    assert "--raw-snapshot" not in command

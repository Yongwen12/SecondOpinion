from secondopinion.openreview_scale_estimate import build_openreview_scale_estimate, render_openreview_scale_estimate_markdown


def batch_cost():
    return {
        "summary": {
            "request_count": 100,
            "estimated_input_tokens": 200000,
            "estimated_output_tokens": 10000,
            "estimated_batch_cost_usd": 1.0,
        }
    }


def test_scale_estimate_projects_cost_from_inventory_sample():
    inventory = {
        "venues": [
            {
                "venue_id": "ICLR",
                "status": "open_reviews_available",
                "include_in_inventory": True,
                "sample_stats": {"paper_count": 50, "review_count": 200, "mean_reviews_per_paper": 4.0},
            },
            {"venue_id": "JMLR", "status": "excluded_no_public_reviews", "include_in_inventory": False},
        ]
    }

    report = build_openreview_scale_estimate(inventory=inventory, batch_cost=batch_cost(), max_total_cost_usd=25)
    markdown = render_openreview_scale_estimate_markdown(report)

    assert report["status"] == "ready_for_budget_review"
    assert report["baseline"]["cost_per_review_usd"] == 0.01
    assert report["summary"]["estimated_review_count"] == 200
    assert report["summary"]["estimated_batch_cost_usd"] == 2.0
    assert "ICLR" in markdown


def test_scale_estimate_blocks_when_inventory_has_no_sample_counts():
    inventory = {
        "venues": [
            {
                "venue_id": "ICLR",
                "status": "challenge_required",
                "include_in_inventory": True,
                "sample_stats": {"paper_count": 0, "review_count": 0},
            }
        ]
    }

    report = build_openreview_scale_estimate(inventory=inventory, batch_cost=batch_cost())

    assert report["status"] == "blocked_missing_inventory_sample"
    assert report["summary"]["blocked_venues"] == ["ICLR"]
    assert report["venues"][0]["estimate_status"] == "blocked_missing_inventory_sample"



def test_scale_estimate_blocks_when_inventory_has_no_target_venues():
    report = build_openreview_scale_estimate(inventory={"venues": []}, batch_cost=batch_cost())

    assert report["status"] == "blocked_missing_inventory_sample"
    assert report["summary"]["venue_count"] == 0

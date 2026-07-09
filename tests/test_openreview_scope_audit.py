from secondopinion.openreview_scope_audit import audit_openreview_scope, render_scope_audit_markdown


def venue(venue_id, **extra):
    payload = {
        "venue_id": venue_id,
        "year": 2025,
        "category": "top_conference",
        "invitation_candidates": [f"{venue_id}.cc/2025/Conference/-/Submission"],
    }
    payload.update(extra)
    return payload


def base_config():
    return [
        venue("ICLR", scope_decision="score_public_reviews"),
        venue("ICML", scope_decision="score_public_reviews"),
        venue("NEURIPS", scope_decision="score_public_reviews"),
        venue("TMLR", category="top_journal", rolling_venue=True, year_filter="decision_or_activity_year", scope_decision="score_public_reviews"),
        venue(
            "JMLR",
            category="top_journal",
            include_in_inventory=False,
            manual_status="excluded_no_public_reviews",
            invitation_candidates=[],
            scope_decision="exclude_no_public_reviews",
        ),
        venue(
            "JAIR",
            category="top_journal",
            include_in_inventory=False,
            manual_status="excluded_no_public_reviews",
            invitation_candidates=[],
            scope_decision="exclude_no_public_reviews",
        ),
        venue(
            "MLJ",
            category="top_journal",
            include_in_inventory=False,
            manual_status="excluded_no_public_reviews",
            invitation_candidates=[],
            scope_decision="exclude_no_public_reviews",
        ),
    ]


def test_scope_audit_passes_with_core_and_excluded_journals():
    report = audit_openreview_scope(venues=base_config())

    assert report["status"] == "passed"
    assert report["config"]["core_venues"] == ["ICLR", "ICML", "NEURIPS", "TMLR"]
    assert report["config"]["excluded_top_journals"] == ["JAIR", "JMLR", "MLJ"]
    assert report["completeness"]["priority1_core_ids"] == ["ICLR", "ICML", "NEURIPS", "TMLR"]
    assert report["completeness"]["explicitly_excluded_top_journal_ids"] == ["JAIR", "JMLR", "MLJ"]


def test_scope_audit_fails_when_core_venue_is_missing():
    config = [item for item in base_config() if item["venue_id"] != "TMLR"]
    report = audit_openreview_scope(venues=config)

    assert report["status"] == "failed"
    assert "missing required core venue: TMLR" in report["errors"]


def test_scope_audit_validates_inventory_and_plan_consistency():
    inventory = {
        "summary": {
            "ready_to_pull_and_score": [],
            "needs_openreview_auth": ["ICLR", "ICML", "NEURIPS", "TMLR"],
            "status_counts": {"challenge_required": 4, "excluded_no_public_reviews": 3},
        },
        "venues": [
            {"venue_id": "ICLR", "status": "challenge_required"},
            {"venue_id": "ICML", "status": "challenge_required"},
            {"venue_id": "NEURIPS", "status": "challenge_required"},
            {"venue_id": "TMLR", "status": "challenge_required"},
            {"venue_id": "JMLR", "status": "excluded_no_public_reviews"},
            {"venue_id": "JAIR", "status": "excluded_no_public_reviews"},
            {"venue_id": "MLJ", "status": "excluded_no_public_reviews"},
        ],
    }
    plan = {
        "summary": {
            "ready": [],
            "blocked_openreview_auth": ["ICLR", "ICML", "NEURIPS", "TMLR"],
            "excluded_not_scored": ["JMLR", "JAIR", "MLJ"],
            "readiness_counts": {"blocked_openreview_auth": 4, "excluded_not_scored": 3},
        },
        "venues": [
            {"venue_id": "ICLR", "readiness": "blocked_openreview_auth"},
            {"venue_id": "ICML", "readiness": "blocked_openreview_auth"},
            {"venue_id": "NEURIPS", "readiness": "blocked_openreview_auth"},
            {"venue_id": "TMLR", "readiness": "blocked_openreview_auth"},
            {"venue_id": "JMLR", "readiness": "excluded_not_scored", "commands": []},
            {"venue_id": "JAIR", "readiness": "excluded_not_scored", "commands": []},
            {"venue_id": "MLJ", "readiness": "excluded_not_scored", "commands": []},
        ],
    }

    report = audit_openreview_scope(venues=base_config(), inventory=inventory, plan=plan)
    markdown = render_scope_audit_markdown(report)

    assert report["status"] == "passed"
    assert "no venues are ready yet" in report["warnings"][0]
    assert "Priority 1 core" in markdown
    assert "Excluded from scoring" in markdown

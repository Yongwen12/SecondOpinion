from secondopinion.openreview_cookie_handoff import build_cookie_handoff, render_cookie_handoff_markdown


def test_cookie_handoff_reports_missing_cookie_without_values():
    report = build_cookie_handoff(
        secret_check={"ok": False, "cookie": {"set": False, "cookie_names": []}},
        challenge_resume={"auth_diagnosis": {"reason": "missing_cookie_or_token", "auth_status": "challenge_required"}},
    )
    markdown = render_cookie_handoff_markdown(report)

    assert report["status"] == "ready_for_cookie_export"
    assert report["diagnosis_reason"] == "missing_cookie_or_token"
    assert "openreview_cookie_preflight" in report["commands"][0]
    assert "openreview_secret_check" in report["commands"][1]
    assert "openreview_challenge_resume" in markdown
    assert "openreview_session" in markdown
    assert "cf_clearance" in markdown


def test_cookie_handoff_flags_cookie_warnings():
    report = build_cookie_handoff(
        secret_check={
            "ok": True,
            "cookie": {
                "set": True,
                "cookie_names": ["openreview_session"],
                "diagnostics": {"warnings": ["missing_cf_clearance_cookie"]},
            },
        },
        challenge_resume={"auth_diagnosis": {"reason": "api_challenge_required", "auth_status": "challenge_required"}},
    )

    assert report["status"] == "cookie_needs_refresh"
    assert report["cookie_warnings"] == ["missing_cf_clearance_cookie"]

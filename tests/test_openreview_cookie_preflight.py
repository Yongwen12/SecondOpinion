from secondopinion.openreview_cookie_preflight import build_cookie_preflight, render_cookie_preflight_markdown


def test_cookie_preflight_ready_with_login_and_clearance_cookie(tmp_path):
    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text("openreview_session=abc; cf_clearance=secret_clearance", encoding="utf-8")

    report = build_cookie_preflight(cookie_file=str(cookie_file))
    markdown = render_cookie_preflight_markdown(report)

    assert report["status"] == "ready_for_auth_check"
    assert report["blocking_warnings"] == []
    assert "openreview_auth_check" in report["next_commands"][0]
    assert "abc" not in str(report)
    assert "secret_clearance" not in markdown


def test_cookie_preflight_blocks_missing_login_cookie(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENREVIEW_COOKIE", raising=False)
    monkeypatch.delenv("OPENREVIEW_COOKIE_FILE", raising=False)
    monkeypatch.delenv("OPENREVIEW_TOKEN", raising=False)
    monkeypatch.delenv("OPENREVIEW_TOKEN_FILE", raising=False)

    report = build_cookie_preflight(cookie_file="")

    assert report["status"] == "missing_cookie_or_token"
    assert report["secret_ok"] is False


def test_cookie_preflight_blocks_expired_netscape_login_cookie(tmp_path):
    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text(
        "# Netscape HTTP Cookie File\n"
        ".openreview.net\tTRUE\t/\tTRUE\t1\topenreview_session\told_secret\n"
        "api2.openreview.net\tFALSE\t/\tTRUE\t1893456000\tcf_clearance\tclear\n",
        encoding="utf-8",
    )

    report = build_cookie_preflight(cookie_file=str(cookie_file))

    assert report["status"] == "needs_cookie_refresh"
    assert "netscape_cookie_jar_contains_expired_openreview_cookies" in report["blocking_warnings"]
    assert "old_secret" not in str(report)

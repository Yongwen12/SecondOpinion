from secondopinion.openreview_secret_check import run_openreview_secret_check


def test_secret_check_reports_raw_cookie_names_without_values():
    result = run_openreview_secret_check(cookie="openreview_session=abc; cf_clearance=value_not_printed_789")

    assert result["ok"] is True
    assert result["recommendation"] == "run_openreview_pipeline_gate"
    assert result["cookie"]["source"] == "OPENREVIEW_COOKIE"
    assert result["cookie"]["format"] == "raw_header"
    assert result["cookie"]["cookie_names"] == ["openreview_session", "cf_clearance"]
    assert "abc" not in str(result)
    assert "value_not_printed_789" not in str(result)


def test_secret_check_reports_netscape_cookie_jar(tmp_path):
    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text(
        "# Netscape HTTP Cookie File\n"
        ".openreview.net\tTRUE\t/\tTRUE\t1893456000\topenreview_session\tabc\n"
        "api2.openreview.net\tFALSE\t/\tTRUE\t1893456000\tcf_clearance\tclear\n",
        encoding="utf-8",
    )

    result = run_openreview_secret_check(cookie_file=str(cookie_file))

    assert result["ok"] is True
    assert result["cookie"]["source"] == "OPENREVIEW_COOKIE_FILE"
    assert result["cookie"]["format"] == "netscape_cookie_jar"
    assert result["cookie"]["cookie_count"] == 2
    assert result["cookie"]["cookie_names"] == ["openreview_session", "cf_clearance"]


def test_secret_check_flags_missing_secret_file(tmp_path):
    result = run_openreview_secret_check(cookie_file=str(tmp_path / "missing.cookie"))

    assert result["ok"] is False
    assert result["recommendation"] == "fix_secret_file_path"
    assert result["cookie"]["format"] == "missing_file"

def test_secret_check_loads_dotenv_cookie_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENREVIEW_COOKIE", raising=False)
    monkeypatch.delenv("OPENREVIEW_COOKIE_FILE", raising=False)
    cookie_file = tmp_path / "openreview.cookie"
    cookie_file.write_text("openreview_session=abc\n", encoding="utf-8")
    (tmp_path / ".env").write_text(f"OPENREVIEW_COOKIE_FILE={cookie_file}\n", encoding="utf-8")

    result = run_openreview_secret_check()

    assert result["ok"] is True
    assert result["cookie"]["source"] == "OPENREVIEW_COOKIE_FILE"
    assert result["cookie"]["cookie_names"] == ["openreview_session"]
    assert "abc" not in str(result)



def test_secret_check_warns_when_cookie_has_clearance_but_no_openreview_login():
    result = run_openreview_secret_check(cookie="cf_clearance=value_not_printed")

    assert result["ok"] is True
    assert result["recommendation"] == "refresh_browser_cookie_missing_openreview_login"
    assert result["cookie"]["diagnostics"]["has_openreview_login_cookie"] is False
    assert "missing_openreview_login_cookie" in result["cookie"]["diagnostics"]["warnings"]
    assert "value_not_printed" not in str(result)


def test_secret_check_warns_for_expired_netscape_openreview_cookie(tmp_path):
    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text(
        "# Netscape HTTP Cookie File\n"
        ".openreview.net\tTRUE\t/\tTRUE\t1\topenreview_session\told_secret\n"
        "api2.openreview.net\tFALSE\t/\tTRUE\t1893456000\tcf_clearance\tclear\n",
        encoding="utf-8",
    )

    result = run_openreview_secret_check(cookie_file=str(cookie_file))

    assert result["ok"] is True
    assert result["recommendation"] == "refresh_browser_cookie_expired_entries"
    diagnostics = result["cookie"]["diagnostics"]
    assert diagnostics["has_openreview_login_cookie"] is True
    assert diagnostics["expired_cookie_names"] == ["openreview_session"]
    assert "old_secret" not in str(result)

import uuid
from pathlib import Path

from secondopinion.openreview_auth_setup import install_openreview_cookie


def test_auth_setup_installs_netscape_cookie_jar_without_leaking_values():
    root = Path("data/test_tmp") / f"auth_setup_{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    source = root / "cookies.txt"
    source.write_text(
        "# Netscape HTTP Cookie File\n"
        ".openreview.net\tTRUE\t/\tTRUE\t1893456000\topenreview_session\tsecret_session\n"
        "api2.openreview.net\tFALSE\t/\tTRUE\t1893456000\tcf_clearance\tsecret_clearance\n",
        encoding="utf-8",
    )
    out_cookie = root / "openreview.cookie"
    env_path = root / ".env"

    result = install_openreview_cookie(cookie_file=str(source), out_cookie=out_cookie, env_path=env_path)

    assert result["ok"] is True
    assert result["cookie"]["source_format"] == "netscape_cookie_jar"
    assert result["cookie"]["cookie_names"] == ["openreview_session", "cf_clearance"]
    assert out_cookie.read_text(encoding="utf-8") == "openreview_session=secret_session; cf_clearance=secret_clearance\n"
    assert env_path.read_text(encoding="utf-8") == f"OPENREVIEW_COOKIE_FILE={out_cookie}\n"
    assert "secret_session" not in str(result)
    assert "secret_clearance" not in str(result)


def test_auth_setup_updates_existing_env_file():
    root = Path("data/test_tmp") / f"auth_setup_{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    env_path = root / ".env"
    env_path.write_text("OPENAI_API_KEY=keep\nOPENREVIEW_COOKIE_FILE=old.cookie\n", encoding="utf-8")
    out_cookie = root / "openreview.cookie"

    result = install_openreview_cookie(
        cookie="openreview_session=abc",
        out_cookie=out_cookie,
        env_path=env_path,
    )

    assert result["ok"] is True
    assert env_path.read_text(encoding="utf-8") == f"OPENAI_API_KEY=keep\nOPENREVIEW_COOKIE_FILE={out_cookie}\n"


def test_auth_setup_reports_missing_cookie_input():
    root = Path("data/test_tmp") / f"auth_setup_{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)

    result = install_openreview_cookie(out_cookie=root / "openreview.cookie", env_path=root / ".env")

    assert result["ok"] is False
    assert result["recommendation"] == "provide_cookie_or_cookie_file"



def test_auth_setup_reports_cookie_diagnostics_without_values():
    root = Path("data/test_tmp") / f"auth_setup_{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    out_cookie = root / "openreview.cookie"
    env_path = root / ".env"

    result = install_openreview_cookie(
        cookie="cf_clearance=secret_clearance_only",
        out_cookie=out_cookie,
        env_path=env_path,
    )

    assert result["ok"] is True
    assert result["recommendation"] == "refresh_browser_cookie_missing_openreview_login"
    assert result["cookie"]["diagnostics"]["has_openreview_login_cookie"] is False
    assert "missing_openreview_login_cookie" in result["cookie"]["diagnostics"]["warnings"]
    assert "secret_clearance_only" not in str(result)

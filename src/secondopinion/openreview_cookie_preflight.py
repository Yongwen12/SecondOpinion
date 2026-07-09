from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from .openreview_secret_check import run_openreview_secret_check

COOKIE_PREFLIGHT_SCHEMA_VERSION = "openreview-cookie-preflight-v0.1"
BLOCKING_WARNINGS = {
    "missing_openreview_login_cookie",
    "netscape_cookie_jar_contains_expired_openreview_cookies",
}
SOFT_WARNINGS = {"missing_cf_clearance_cookie"}


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def build_cookie_preflight(*, cookie_file: str = "", token_file: str = "") -> dict[str, Any]:
    secret = run_openreview_secret_check(cookie_file=cookie_file or None, token_file=token_file or None)
    cookie = secret.get("cookie") or {}
    token = secret.get("token") or {}
    diagnostics = cookie.get("diagnostics") or {}
    warnings = list(diagnostics.get("warnings") or [])
    blocking = [warning for warning in warnings if warning in BLOCKING_WARNINGS]
    soft = [warning for warning in warnings if warning in SOFT_WARNINGS]
    if token.get("set"):
        status = "ready_for_auth_check"
        recommendation = "run_openreview_auth_check"
    elif not cookie.get("set"):
        status = "missing_cookie_or_token"
        recommendation = secret.get("recommendation", "provide_browser_cookie_file")
    elif blocking:
        status = "needs_cookie_refresh"
        recommendation = secret.get("recommendation", "refresh_browser_cookie")
    else:
        status = "ready_for_auth_check"
        recommendation = "run_openreview_auth_check_then_probe"
    return {
        "schema_version": COOKIE_PREFLIGHT_SCHEMA_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "recommendation": recommendation,
        "secret_ok": bool(secret.get("ok")),
        "cookie": cookie,
        "token": token,
        "blocking_warnings": blocking,
        "soft_warnings": soft,
        "next_commands": next_commands(status=status, cookie_file=cookie_file),
    }


def next_commands(*, status: str, cookie_file: str) -> list[str]:
    placeholder = cookie_file or "path\\to\\browser-cookies.txt"
    if status == "ready_for_auth_check":
        return [
            f"python -m secondopinion.tools.openreview_auth_check --cookie-file {placeholder} --out data/validation/openreview_auth_check.json",
            f"python -m secondopinion.tools.openreview_challenge_resume --cookie-file {placeholder} --execute-probe --skip-existing",
            "python -m secondopinion.tools.openreview_local_refresh --max-total-cost-usd 25",
        ]
    return [f"python -m secondopinion.tools.openreview_cookie_preflight --cookie-file {placeholder}"]


def render_cookie_preflight_markdown(report: dict[str, Any]) -> str:
    cookie = report.get("cookie") or {}
    lines = [
        "# OpenReview Cookie Preflight",
        "",
        f"- Created: `{report.get('created_at', '')}`",
        f"- Status: `{report.get('status', '')}`",
        f"- Recommendation: `{report.get('recommendation', '')}`",
        f"- Secret ok: `{report.get('secret_ok', False)}`",
        f"- Cookie format: `{cookie.get('format', '')}`",
        f"- Cookie names: `{', '.join(cookie.get('cookie_names') or []) or '-'}`",
        f"- Blocking warnings: `{', '.join(report.get('blocking_warnings') or []) or '-'}`",
        f"- Soft warnings: `{', '.join(report.get('soft_warnings') or []) or '-'}`",
        "",
        "## Next Commands",
        "",
        "```powershell",
    ]
    lines.extend(report.get("next_commands") or [])
    lines.extend(["```", ""])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a browser-exported OpenReview cookie file before running authenticated probes.")
    parser.add_argument("--cookie-file", default="")
    parser.add_argument("--token-file", default="")
    parser.add_argument("--out", default="data/validation/openreview_cookie_preflight.json")
    parser.add_argument("--markdown", default="reports/validation/openreview_cookie_preflight.md")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    report = build_cookie_preflight(cookie_file=args.cookie_file, token_file=args.token_file)
    write_json(args.out, report)
    write_text(args.markdown, render_cookie_preflight_markdown(report))
    print(json.dumps({"status": report["status"], "recommendation": report["recommendation"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

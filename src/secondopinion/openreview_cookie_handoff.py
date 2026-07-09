from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from .openreview_readiness_dashboard import read_json_if_exists
from .openreview_secret_check import CLEARANCE_COOKIE_NAMES, OPENREVIEW_COOKIE_NAMES

COOKIE_HANDOFF_SCHEMA_VERSION = "openreview-cookie-handoff-v0.1"


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


def build_cookie_handoff(
    *,
    secret_check: dict[str, Any] | None = None,
    challenge_resume: dict[str, Any] | None = None,
    cookie_file_placeholder: str = "path\\to\\browser-cookies.txt",
) -> dict[str, Any]:
    secret_check = secret_check or {}
    challenge_resume = challenge_resume or {}
    diagnosis = challenge_resume.get("auth_diagnosis") or {}
    cookie = secret_check.get("cookie") or {}
    required_cookie_names = {
        "login_any_of": sorted(OPENREVIEW_COOKIE_NAMES),
        "challenge_any_of": sorted(CLEARANCE_COOKIE_NAMES),
    }
    commands = [
        f"python -m secondopinion.tools.openreview_cookie_preflight --cookie-file {cookie_file_placeholder}",
        f"python -m secondopinion.tools.openreview_secret_check --cookie-file {cookie_file_placeholder} --out data/validation/openreview_secret_check.json",
        f"python -m secondopinion.tools.openreview_challenge_resume --cookie-file {cookie_file_placeholder} --execute-probe --skip-existing",
        "python -m secondopinion.tools.openreview_local_refresh --max-total-cost-usd 25",
    ]
    status = "ready_for_cookie_export"
    if diagnosis.get("reason") == "auth_ok":
        status = "auth_ready"
    elif cookie.get("set") and cookie.get("diagnostics", {}).get("warnings"):
        status = "cookie_needs_refresh"
    elif cookie.get("set"):
        status = "cookie_present_but_api_not_ready"
    return {
        "schema_version": COOKIE_HANDOFF_SCHEMA_VERSION,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "diagnosis_reason": diagnosis.get("reason", "missing"),
        "auth_status": diagnosis.get("auth_status", "missing"),
        "secret_ok": bool(secret_check.get("ok")),
        "cookie_names_seen": cookie.get("cookie_names") or [],
        "cookie_warnings": (cookie.get("diagnostics") or {}).get("warnings") or [],
        "required_cookie_names": required_cookie_names,
        "commands": commands,
        "notes": [
            "Do not paste cookie values into chat or commit them.",
            "Export cookies after logging into openreview.net and completing any browser challenge.",
            "A raw Cookie header or Netscape cookie jar export is accepted.",
            "The local checker reports cookie names only; it redacts values.",
        ],
    }


def render_cookie_handoff_markdown(report: dict[str, Any]) -> str:
    required = report.get("required_cookie_names") or {}
    lines = [
        "# OpenReview Cookie Handoff",
        "",
        f"- Created: `{report.get('created_at', '')}`",
        f"- Status: `{report.get('status', '')}`",
        f"- Diagnosis: `{report.get('diagnosis_reason', '')}`",
        f"- Auth status: `{report.get('auth_status', '')}`",
        f"- Secret ok: `{report.get('secret_ok', False)}`",
        f"- Cookie names seen: `{', '.join(report.get('cookie_names_seen') or []) or '-'}`",
        f"- Cookie warnings: `{', '.join(report.get('cookie_warnings') or []) or '-'}`",
        f"- Login cookie names accepted: `{', '.join(required.get('login_any_of') or [])}`",
        f"- Challenge cookie names accepted: `{', '.join(required.get('challenge_any_of') or [])}`",
        "",
        "## Commands",
        "",
        "```powershell",
    ]
    lines.extend(report.get("commands") or [])
    lines.extend(["```", "", "## Notes", ""])
    lines.extend(f"- {note}" for note in report.get("notes") or [])
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a redacted handoff report for obtaining and validating OpenReview cookies.")
    parser.add_argument("--secret-check", default="data/validation/openreview_secret_check.json")
    parser.add_argument("--challenge-resume", default="data/validation/openreview_challenge_resume.json")
    parser.add_argument("--cookie-file-placeholder", default="path\\to\\browser-cookies.txt")
    parser.add_argument("--out", default="data/validation/openreview_cookie_handoff.json")
    parser.add_argument("--markdown", default="reports/validation/openreview_cookie_handoff.md")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    report = build_cookie_handoff(
        secret_check=read_json_if_exists(args.secret_check),
        challenge_resume=read_json_if_exists(args.challenge_resume),
        cookie_file_placeholder=args.cookie_file_placeholder,
    )
    write_json(args.out, report)
    write_text(args.markdown, render_cookie_handoff_markdown(report))
    print(json.dumps({"status": report["status"], "diagnosis_reason": report["diagnosis_reason"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

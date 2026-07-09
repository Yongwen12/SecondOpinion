from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any, Callable

from .openreview_auth_check import run_openreview_auth_check
from .openreview_auth_setup import install_openreview_cookie
from .openreview_client import OpenReviewClient
from .openreview_safe_pipeline import run_openreview_safe_pipeline
from .openreview_venue_inventory import load_venue_specs


AUTH_PILOT_SCHEMA_VERSION = "openreview-auth-pilot-v0.1"


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: str | Path, text: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


def run_openreview_auth_pilot(
    *,
    venue_specs: list[dict[str, Any]],
    cookie: str = "",
    cookie_file: str = "",
    out_cookie: str | Path = "data/secrets/openreview.cookie",
    env_path: str | Path = ".env",
    venue: str = "ICLR",
    pull_limit: int = 50,
    execute_safe: bool = False,
    probe_when_auth_blocked: bool = True,
    api_base: str = "https://api2.openreview.net",
    timeout: int = 60,
    auth_client_factory: Callable[[], OpenReviewClient] | None = None,
    safe_pipeline_runner: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    created_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    auth_setup = install_openreview_cookie(
        cookie=cookie,
        cookie_file=cookie_file,
        out_cookie=out_cookie,
        env_path=env_path,
    )
    if not auth_setup.get("ok"):
        return {
            "schema_version": AUTH_PILOT_SCHEMA_VERSION,
            "created_at": created_at,
            "status": "blocked_cookie_setup",
            "recommendation": "provide_browser_verified_cookie_file",
            "openai_submit_used": False,
            "auth_setup": auth_setup,
            "auth_check": {},
            "safe_pipeline": {},
            "next_commands": ["python -m secondopinion.tools.openreview_auth_pilot --cookie-file path\\to\\browser-cookies.txt"],
        }

    auth_client = auth_client_factory() if auth_client_factory else OpenReviewClient(base_url=api_base, timeout=timeout)
    auth_check = run_openreview_auth_check(client=auth_client)
    if not auth_check.get("ok"):
        return {
            "schema_version": AUTH_PILOT_SCHEMA_VERSION,
            "created_at": created_at,
            "status": "blocked_auth_check",
            "recommendation": auth_check.get("recommendation", "refresh_browser_cookie"),
            "openai_submit_used": False,
            "auth_setup": auth_setup,
            "auth_check": auth_check,
            "safe_pipeline": {},
            "next_commands": [
                "python -m secondopinion.tools.openreview_auth_setup --cookie-file path\\to\\browser-cookies.txt",
                "python -m secondopinion.tools.openreview_auth_check --out data/validation/openreview_auth_check.json",
            ],
        }

    runner = safe_pipeline_runner or run_openreview_safe_pipeline
    safe_pipeline = runner(
        venue_specs=venue_specs,
        execute_safe=execute_safe,
        venues=[venue],
        pull_limit=pull_limit,
        probe_when_auth_blocked=probe_when_auth_blocked,
        api_base=api_base,
        timeout=timeout,
    )
    status = "pilot_executed" if execute_safe else "pilot_ready_dry_run"
    if str(safe_pipeline.get("gate_status") or "") != "ready_for_safe_runner_execute":
        status = "blocked_safe_pipeline_gate"
    return {
        "schema_version": AUTH_PILOT_SCHEMA_VERSION,
        "created_at": created_at,
        "status": status,
        "recommendation": "run_execute_safe_pilot" if status == "pilot_ready_dry_run" else safe_pipeline.get("gate_recommendation", "inspect_safe_pipeline"),
        "openai_submit_used": False,
        "auth_setup": auth_setup,
        "auth_check": auth_check,
        "safe_pipeline": {
            "action": safe_pipeline.get("action", ""),
            "gate_status": safe_pipeline.get("gate_status", ""),
            "gate_recommendation": safe_pipeline.get("gate_recommendation", ""),
            "selected_venues": safe_pipeline.get("selected_venues", []),
            "pull_limit": safe_pipeline.get("pull_limit", pull_limit),
            "safe_runner_status_counts": safe_pipeline.get("safe_runner_status_counts", {}),
            "pilot_readiness_status": safe_pipeline.get("pilot_readiness_status", ""),
        },
        "next_commands": next_commands_for_status(status, venue=venue, pull_limit=pull_limit),
    }


def next_commands_for_status(status: str, *, venue: str, pull_limit: int) -> list[str]:
    if status == "pilot_ready_dry_run":
        return [
            "python -m secondopinion.tools.openreview_auth_pilot --cookie-file path\\to\\browser-cookies.txt "
            + f"--venue {venue} --pull-limit {pull_limit} --execute-safe"
        ]
    if status == "pilot_executed":
        return [
            "python -m secondopinion.tools.openreview_pilot_readiness --plan data/validation/openreview_ingestion_plan_2025.json "
            + f"--venue {venue}"
        ]
    return ["python -m secondopinion.tools.openreview_auth_pilot --cookie-file path\\to\\browser-cookies.txt"]


def render_auth_pilot_markdown(report: dict[str, Any]) -> str:
    auth_setup = report.get("auth_setup") or {}
    auth_check = report.get("auth_check") or {}
    safe = report.get("safe_pipeline") or {}
    lines = [
        "# OpenReview Auth Pilot",
        "",
        f"- Created: `{report.get('created_at', '')}`",
        f"- Status: `{report.get('status', '')}`",
        f"- Recommendation: `{report.get('recommendation', '')}`",
        f"- OpenAI submit used: `{report.get('openai_submit_used', False)}`",
        f"- Auth setup: `{auth_setup.get('recommendation', '')}`",
        f"- Auth check: `{auth_check.get('status', '')}`",
        f"- Safe pipeline gate: `{safe.get('gate_status', '')}`",
        f"- Safe runner counts: `{safe.get('safe_runner_status_counts', {})}`",
        "",
        "## Next Commands",
        "",
        "```powershell",
    ]
    lines.extend(report.get("next_commands") or ["# No automatic command suggested."])
    lines.extend(["```", ""])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install OpenReview cookie, verify auth, then run a safe venue pilot when ready.")
    parser.add_argument("--venues", default="data/config/openreview_venues_2025.json")
    parser.add_argument("--cookie", default="", help="Raw Cookie header. Prefer --cookie-file to avoid shell history.")
    parser.add_argument("--cookie-file", default="", help="Browser-exported raw Cookie header or Netscape cookie jar.")
    parser.add_argument("--out-cookie", default="data/secrets/openreview.cookie")
    parser.add_argument("--env", default=".env")
    parser.add_argument("--venue", default="ICLR")
    parser.add_argument("--pull-limit", type=int, default=50)
    parser.add_argument("--execute-safe", action="store_true")
    parser.add_argument("--no-probe-when-auth-blocked", action="store_true")
    parser.add_argument("--api-base", default="https://api2.openreview.net")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--out", default="data/validation/openreview_auth_pilot.json")
    parser.add_argument("--markdown", default="reports/validation/openreview_auth_pilot.md")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    report = run_openreview_auth_pilot(
        venue_specs=load_venue_specs(args.venues),
        cookie=args.cookie,
        cookie_file=args.cookie_file,
        out_cookie=args.out_cookie,
        env_path=args.env,
        venue=args.venue,
        pull_limit=args.pull_limit,
        execute_safe=args.execute_safe,
        probe_when_auth_blocked=not args.no_probe_when_auth_blocked,
        api_base=args.api_base,
        timeout=args.timeout,
    )
    write_json(args.out, report)
    write_markdown(args.markdown, render_auth_pilot_markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

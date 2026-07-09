from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any, Callable

from .openreview_auth_check import run_openreview_auth_check
from .openreview_auth_setup import install_openreview_cookie
from .openreview_secret_check import run_openreview_secret_check
from .openreview_client import OpenReviewClient
from .openreview_invitation_audit import load_venues
from .openreview_probe_queue import build_probe_queue, render_probe_queue_markdown
from .openreview_probe_queue_runner import render_probe_queue_runner_markdown, run_probe_queue
from .openreview_probe_results import render_probe_results_markdown, resolve_probe_results
from .openreview_resolved_inventory import build_resolved_inventory, render_resolved_inventory_markdown
from .openreview_resolved_pipeline import run_openreview_resolved_pipeline
from .openreview_scale_estimate import write_json, write_text


CHALLENGE_RESUME_SCHEMA_VERSION = "openreview-challenge-resume-v0.1"


def default_paths() -> dict[str, str]:
    return {
        "auth_check": "data/validation/openreview_auth_check.json",
        "probe_queue": "data/validation/openreview_probe_queue_2025.json",
        "probe_queue_markdown": "reports/validation/openreview_probe_queue_2025.md",
        "probe_runner": "data/validation/openreview_probe_queue_runner.json",
        "probe_runner_markdown": "reports/validation/openreview_probe_queue_runner.md",
        "probe_results": "data/validation/openreview_probe_results_2025.json",
        "probe_results_markdown": "reports/validation/openreview_probe_results_2025.md",
        "resolved_inventory": "data/validation/openreview_resolved_inventory_2025.json",
        "resolved_inventory_markdown": "reports/validation/openreview_resolved_inventory_2025.md",
        "summary": "data/validation/openreview_challenge_resume.json",
        "summary_markdown": "reports/validation/openreview_challenge_resume.md",
    }


def run_openreview_challenge_resume(
    *,
    venue_specs: list[dict[str, Any]],
    cookie: str = "",
    cookie_file: str = "",
    out_cookie: str | Path = "data/secrets/openreview.cookie",
    env_path: str | Path = ".env",
    execute_probe: bool = False,
    execute_safe: bool = False,
    venues: list[str] | None = None,
    max_probe_items: int | None = None,
    skip_existing: bool = True,
    probe_output_dir: str | Path | None = None,
    probe_report_dir: str | Path | None = None,
    probe_result_patterns: list[str] | None = None,
    pull_limit: int | None = 50,
    api_base: str = "https://api2.openreview.net",
    timeout: int = 60,
    paths: dict[str, str] | None = None,
    require_secret: bool = True,
    client_factory: Callable[[], OpenReviewClient] | None = None,
) -> dict[str, Any]:
    paths = {**default_paths(), **(paths or {})}
    created_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    auth_setup = {}
    secret_check = run_openreview_secret_check(cookie=cookie or None, cookie_file=cookie_file or None)
    if cookie or cookie_file:
        try:
            auth_setup = install_openreview_cookie(
                cookie=cookie,
                cookie_file=cookie_file,
                out_cookie=out_cookie,
                env_path=env_path,
            )
        except OSError as exc:
            auth_setup = {
                "ok": False,
                "recommendation": "provide_existing_cookie_file",
                "error": str(exc),
            }
        if not auth_setup.get("ok"):
            return blocked_auth_report(
                paths=paths,
                created_at=created_at,
                status="blocked_cookie_setup",
                recommendation="provide_browser_verified_cookie_file",
                auth_setup=auth_setup,
                secret_check=secret_check,
                auth_check={},
            )

    if require_secret and not secret_check.get("ok"):
        return blocked_auth_report(
            paths=paths,
            created_at=created_at,
            status="blocked_missing_secret",
            recommendation="provide_browser_verified_cookie_file",
            auth_setup=auth_setup,
            secret_check=secret_check,
            auth_check={},
        )

    client = client_factory() if client_factory else OpenReviewClient(base_url=api_base, timeout=timeout)
    auth_check = run_openreview_auth_check(client=client)
    write_json(paths["auth_check"], auth_check)
    if not auth_check.get("ok"):
        return blocked_auth_report(
            paths=paths,
            created_at=created_at,
            status="blocked_auth_check",
            recommendation=auth_check.get("recommendation", "refresh_browser_cookie"),
            auth_setup=auth_setup,
            secret_check=secret_check,
            auth_check=auth_check,
        )

    probe_queue = build_probe_queue(venues=venue_specs)
    if probe_output_dir or probe_report_dir:
        rewrite_probe_queue_outputs(
            probe_queue,
            output_dir=probe_output_dir,
            report_dir=probe_report_dir,
        )
    write_json(paths["probe_queue"], probe_queue)
    write_text(paths["probe_queue_markdown"], render_probe_queue_markdown(probe_queue))
    probe_runner = run_probe_queue(
        queue=probe_queue,
        execute=execute_probe,
        venue_filter=venues,
        client=client,
        max_items=max_probe_items,
        skip_existing=skip_existing,
    )
    write_json(paths["probe_runner"], probe_runner)
    write_text(paths["probe_runner_markdown"], render_probe_queue_runner_markdown(probe_runner))

    probe_results = resolve_probe_results(patterns=probe_result_patterns or ["data/validation/openreview_probe_*_c*_*.json"], queue=probe_queue)
    write_json(paths["probe_results"], probe_results)
    write_text(paths["probe_results_markdown"], render_probe_results_markdown(probe_results))

    resolved_inventory = build_resolved_inventory(venue_specs=venue_specs, probe_results=probe_results)
    write_json(paths["resolved_inventory"], resolved_inventory)
    write_text(paths["resolved_inventory_markdown"], render_resolved_inventory_markdown(resolved_inventory))

    resolved_pipeline = run_openreview_resolved_pipeline(
        resolved_inventory=resolved_inventory,
        execute_safe=execute_safe,
        venues=venues,
        pull_limit=pull_limit,
    )
    ready = (resolved_inventory.get("summary") or {}).get("ready_to_pull_and_score") or []
    status = "ready_for_safe_execute" if ready and not execute_safe else "executed_safe_pipeline" if ready else "blocked_no_ready_venues"
    if not execute_probe:
        status = "auth_ok_probe_dry_run"
    return finish_report(
        paths,
        {
            "schema_version": CHALLENGE_RESUME_SCHEMA_VERSION,
            "created_at": created_at,
            "status": status,
            "recommendation": recommendation_for_status(status),
            "openai_submit_used": False,
            "auth_setup": auth_setup,
            "secret_check": secret_check,
            "auth_diagnosis": auth_diagnosis(secret_check=secret_check, auth_check=auth_check, auth_setup=auth_setup),
            "auth_check": auth_check,
            "probe_runner": {
                "execute": probe_runner.get("execute", False),
                "status_counts": probe_runner.get("status_counts", {}),
                "probe_count": probe_runner.get("probe_count", 0),
            },
            "probe_results_summary": probe_results.get("summary", {}),
            "resolved_inventory_summary": resolved_inventory.get("summary", {}),
            "resolved_pipeline": {
                "action": resolved_pipeline.get("action", ""),
                "runner_status_counts": resolved_pipeline.get("runner_status_counts", {}),
            },
            "paths": paths,
        },
    )


def blocked_auth_report(
    *,
    paths: dict[str, str],
    created_at: str,
    status: str,
    recommendation: str,
    auth_setup: dict[str, Any],
    secret_check: dict[str, Any],
    auth_check: dict[str, Any],
) -> dict[str, Any]:
    return finish_report(
        paths,
        {
            "schema_version": CHALLENGE_RESUME_SCHEMA_VERSION,
            "created_at": created_at,
            "status": status,
            "recommendation": recommendation,
            "openai_submit_used": False,
            "auth_setup": auth_setup,
            "secret_check": secret_check,
            "auth_diagnosis": auth_diagnosis(secret_check=secret_check, auth_check=auth_check, auth_setup=auth_setup),
            "auth_check": auth_check,
            "probe_runner": {},
            "probe_results_summary": {},
            "resolved_inventory_summary": {},
            "resolved_pipeline": {},
            "paths": paths,
        },
    )


def auth_diagnosis(*, secret_check: dict[str, Any], auth_check: dict[str, Any], auth_setup: dict[str, Any]) -> dict[str, Any]:
    cookie = secret_check.get("cookie") or {}
    token = secret_check.get("token") or {}
    cookie_warnings = (cookie.get("diagnostics") or {}).get("warnings") or []
    auth_status = str(auth_check.get("status") or "not_run")
    if auth_check.get("ok"):
        reason = "auth_ok"
        next_command = "continue_probe_queue"
    elif auth_setup and not auth_setup.get("ok"):
        reason = "cookie_setup_failed"
        next_command = "python -m secondopinion.tools.openreview_challenge_resume --cookie-file path\\to\\browser-cookies.txt --execute-probe --skip-existing"
    elif not secret_check.get("ok"):
        reason = "missing_cookie_or_token"
        next_command = "python -m secondopinion.tools.openreview_challenge_resume --cookie-file path\\to\\browser-cookies.txt --execute-probe --skip-existing"
    elif "missing_openreview_login_cookie" in cookie_warnings:
        reason = "cookie_missing_openreview_login"
        next_command = "export fresh OpenReview browser cookies, then rerun openreview_challenge_resume"
    elif "missing_cf_clearance_cookie" in cookie_warnings and auth_status == "challenge_required":
        reason = "cookie_missing_cf_clearance_for_challenge"
        next_command = "complete browser challenge on openreview.net, export cookies including cf_clearance, then rerun openreview_challenge_resume"
    elif auth_status == "challenge_required":
        reason = "api_challenge_required"
        next_command = "complete browser challenge on openreview.net, export fresh cookies, then rerun openreview_challenge_resume"
    elif auth_status == "auth_required":
        reason = "api_auth_required"
        next_command = "refresh OpenReview login cookie or token, then rerun openreview_challenge_resume"
    else:
        reason = "inspect_auth_error"
        next_command = "inspect data/validation/openreview_auth_check.json"
    return {
        "reason": reason,
        "next_command": next_command,
        "secret_ok": bool(secret_check.get("ok")),
        "cookie_set": bool(cookie.get("set")),
        "token_set": bool(token.get("set")),
        "cookie_names": cookie.get("cookie_names") or [],
        "cookie_warnings": cookie_warnings,
        "auth_status": auth_status,
    }


def recommendation_for_status(status: str) -> str:
    if status == "auth_ok_probe_dry_run":
        return "rerun_with_execute_probe"
    if status == "ready_for_safe_execute":
        return "inspect_resolved_inventory_then_run_execute_safe"
    if status == "executed_safe_pipeline":
        return "review_safe_outputs_before_batch_submit"
    return "refresh_cookie_or_probe_remaining_candidates"


def rewrite_probe_queue_outputs(
    queue: dict[str, Any],
    *,
    output_dir: str | Path | None = None,
    report_dir: str | Path | None = None,
) -> None:
    output_root = Path(output_dir) if output_dir else None
    report_root = Path(report_dir) if report_dir else None
    for item in queue.get("items", []):
        venue_id = str(item.get("venue_id") or "venue").lower()
        candidate = int(item.get("candidate_index") or 0) + 1
        sample_limit = int(queue.get("sample_limit") or 50)
        stem = f"openreview_probe_{venue_id}_c{candidate}_{sample_limit}"
        if output_root:
            item["result_json"] = str(output_root / f"{stem}.json")
        if report_root:
            item["result_markdown"] = str(report_root / f"{stem}.md")


def finish_report(paths: dict[str, str], report: dict[str, Any]) -> dict[str, Any]:
    write_json(paths["summary"], report)
    write_text(paths["summary_markdown"], render_challenge_resume_markdown(report))
    return report


def render_challenge_resume_markdown(report: dict[str, Any]) -> str:
    auth = report.get("auth_check") or {}
    diagnosis = report.get("auth_diagnosis") or {}
    runner = report.get("probe_runner") or {}
    probe = report.get("probe_results_summary") or {}
    resolved = report.get("resolved_inventory_summary") or {}
    pipeline = report.get("resolved_pipeline") or {}
    return "\n".join(
        [
            "# OpenReview Challenge Resume",
            "",
            f"- Created: `{report.get('created_at', '')}`",
            f"- Status: `{report.get('status', '')}`",
            f"- Recommendation: `{report.get('recommendation', '')}`",
            f"- OpenAI submit used: `{report.get('openai_submit_used', False)}`",
            f"- Auth status: `{auth.get('status', 'missing')}`",
            f"- Auth diagnosis: `{diagnosis.get('reason', 'missing')}`",
            f"- Auth next command: `{diagnosis.get('next_command', '-')}`",
            f"- Probe runner: `execute={runner.get('execute', False)} counts={runner.get('status_counts', {})}`",
            f"- Probe selected: `{', '.join(probe.get('selected_for_scoring') or []) or '-'}`",
            f"- Probe blocked auth: `{', '.join(probe.get('blocked_auth') or []) or '-'}`",
            f"- Probe missing: `{', '.join(probe.get('missing_results') or []) or '-'}`",
            f"- Ready to pull: `{', '.join(resolved.get('ready_to_pull_and_score') or []) or '-'}`",
            f"- Resolved blocked auth: `{', '.join(resolved.get('blocked_openreview_auth') or []) or '-'}`",
            f"- Resolved pipeline: `{pipeline.get('action', 'missing')}`",
            f"- Runner counts: `{pipeline.get('runner_status_counts', {})}`",
            "",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resume OpenReview 2025 inventory after browser challenge/cookie refresh.")
    parser.add_argument("--venues", default="data/config/openreview_venues_2025.json")
    parser.add_argument("--cookie", default="", help="Raw Cookie header. Prefer --cookie-file.")
    parser.add_argument("--cookie-file", default="")
    parser.add_argument("--out-cookie", default="data/secrets/openreview.cookie")
    parser.add_argument("--env", default=".env")
    parser.add_argument("--execute-probe", action="store_true")
    parser.add_argument("--execute-safe", action="store_true")
    parser.add_argument("--venue", action="append", default=[])
    parser.add_argument("--max-probe-items", type=int, default=None)
    parser.add_argument("--no-skip-existing", action="store_true")
    parser.add_argument("--probe-output-dir", default="")
    parser.add_argument("--probe-report-dir", default="")
    parser.add_argument("--probe-result", action="append", default=[], help="Probe result JSON glob. Repeatable.")
    parser.add_argument("--pull-limit", type=int, default=50)
    parser.add_argument("--api-base", default="https://api2.openreview.net")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--allow-anonymous-auth-check", action="store_true", help="Run OpenReview auth check even when no local cookie/token is configured.")
    parser.add_argument("--out", default="data/validation/openreview_challenge_resume.json")
    parser.add_argument("--markdown", default="reports/validation/openreview_challenge_resume.md")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    paths = default_paths()
    paths["summary"] = args.out
    paths["summary_markdown"] = args.markdown
    report = run_openreview_challenge_resume(
        venue_specs=load_venues(args.venues),
        cookie=args.cookie,
        cookie_file=args.cookie_file,
        out_cookie=args.out_cookie,
        env_path=args.env,
        execute_probe=args.execute_probe,
        execute_safe=args.execute_safe,
        venues=args.venue or None,
        max_probe_items=args.max_probe_items,
        skip_existing=not args.no_skip_existing,
        probe_output_dir=args.probe_output_dir or None,
        probe_report_dir=args.probe_report_dir or None,
        probe_result_patterns=args.probe_result or None,
        pull_limit=args.pull_limit,
        api_base=args.api_base,
        timeout=args.timeout,
        paths=paths,
        require_secret=not args.allow_anonymous_auth_check,
    )
    print(json.dumps({"status": report["status"], "recommendation": report["recommendation"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
